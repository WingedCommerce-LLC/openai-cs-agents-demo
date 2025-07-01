import logging
import time
from typing import Any, Dict, List, Optional
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from python_backend.main import (
    cancellation_agent,
    create_initial_context,
    faq_agent,
    flight_status_agent,
    seat_booking_agent,
    triage_agent,
)
from mcp.registry import get_registry
from mcp.server_generator import ServerGenerationConfig

# Load environment variables from .env file
load_dotenv()

try:
    from agents import (
        Handoff,
        HandoffOutputItem,
        InputGuardrailTripwireTriggered,
        ItemHelpers,
        MessageOutputItem,
        Runner,
        ToolCallItem,
        ToolCallOutputItem,
    )
except ImportError:
    # Fallback for missing agents imports - define stub classes
    class Handoff:
        pass
    class HandoffOutputItem:
        pass
    class InputGuardrailTripwireTriggered(Exception):
        pass
    class ItemHelpers:
        @staticmethod
        def text_message_output(item):
            return str(item)
    class MessageOutputItem:
        pass
    class Runner:
        @staticmethod
        async def run(*args, **kwargs):
            pass
    class ToolCallItem:
        pass
    class ToolCallOutputItem:
        pass

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# =========================
# Utility Functions for Testing
# =========================


def get_app_info():
    """Get basic application information."""
    return {
        "name": "OpenAI CS Agents Demo API",
        "version": "1.0.0",
        "status": "running"
    }


def validate_conversation_id(conversation_id: str) -> bool:
    """Validate conversation ID format."""
    if not conversation_id:
        return False
    if not isinstance(conversation_id, str):
        return False
    return len(conversation_id) > 0


def format_agent_name(name: str) -> str:
    """Format agent name for display."""
    if not name:
        return "Unknown Agent"
    return name.replace("_", " ").title()


def get_timestamp():
    """Get current timestamp."""
    import time
    return time.time()


# CORS configuration (adjust as needed for deployment)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# Models
# =========================


class ChatRequest(BaseModel):
    conversation_id: Optional[str] = None
    message: str


class MessageResponse(BaseModel):
    content: str
    agent: str


class AgentEvent(BaseModel):
    id: str
    type: str
    agent: str
    content: str
    metadata: Optional[Dict[str, Any]] = None
    timestamp: Optional[float] = None


class GuardrailCheck(BaseModel):
    id: str
    name: str
    input: str
    reasoning: str
    passed: bool
    timestamp: float


class ChatResponse(BaseModel):
    conversation_id: str
    current_agent: str
    messages: List[MessageResponse]
    events: List[AgentEvent]
    context: Dict[str, Any]
    agents: List[Dict[str, Any]]
    guardrails: List[GuardrailCheck] = []


# =========================
# In-memory store for conversation state
# =========================


class ConversationStore:
    def get(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        pass

    def save(self, conversation_id: str, state: Dict[str, Any]):
        pass


class InMemoryConversationStore(ConversationStore):
    _conversations: Dict[str, Dict[str, Any]] = {}

    def get(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        return self._conversations.get(conversation_id)

    def save(self, conversation_id: str, state: Dict[str, Any]):
        self._conversations[conversation_id] = state


# TODO: when deploying this app in scale, switch to your own
# production-ready implementation
conversation_store = InMemoryConversationStore()

# =========================
# Helpers
# =========================


def _get_agent_by_name(name: str):
    """Return the agent object by name."""
    agents = {
        triage_agent.name: triage_agent,
        faq_agent.name: faq_agent,
        seat_booking_agent.name: seat_booking_agent,
        flight_status_agent.name: flight_status_agent,
        cancellation_agent.name: cancellation_agent,
    }
    return agents.get(name, triage_agent)


def _get_guardrail_name(g) -> str:
    """Extract a friendly guardrail name."""
    name_attr = getattr(g, "name", None)
    if isinstance(name_attr, str) and name_attr:
        return name_attr
    guard_fn = getattr(g, "guardrail_function", None)
    if guard_fn is not None and hasattr(guard_fn, "__name__"):
        return guard_fn.__name__.replace("_", " ").title()
    fn_name = getattr(g, "__name__", None)
    if isinstance(fn_name, str) and fn_name:
        return fn_name.replace("_", " ").title()
    return str(g)


def _build_agents_list() -> List[Dict[str, Any]]:
    """Build a list of all available agents and their metadata."""

    def make_agent_dict(agent):
        return {
            "name": agent.name,
            "description": getattr(agent, "handoff_description", ""),
            "handoffs": [
                getattr(h, "agent_name", getattr(h, "name", ""))
                for h in getattr(agent, "handoffs", [])
            ],
            "tools": [
                getattr(t, "name", getattr(t, "__name__", ""))
                for t in getattr(agent, "tools", [])
            ],
            "input_guardrails": [
                _get_guardrail_name(g) for g in getattr(agent, "input_guardrails", [])
            ],
        }

    return [
        make_agent_dict(triage_agent),
        make_agent_dict(faq_agent),
        make_agent_dict(seat_booking_agent),
        make_agent_dict(flight_status_agent),
        make_agent_dict(cancellation_agent),
    ]


# =========================
# Main Chat Endpoint
# =========================


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    """
    Main chat endpoint for agent orchestration.
    Handles conversation state, agent routing, and guardrail checks.
    """
    # Initialize or retrieve conversation state
    is_new = (
        not req.conversation_id or conversation_store.get(req.conversation_id) is None
    )
    if is_new:
        conversation_id: str = uuid4().hex
        ctx = create_initial_context()
        current_agent_name = triage_agent.name
        state: Dict[str, Any] = {
            "input_items": [],
            "context": ctx,
            "current_agent": current_agent_name,
        }
        if req.message.strip() == "":
            conversation_store.save(conversation_id, state)
            return ChatResponse(
                conversation_id=conversation_id,
                current_agent=current_agent_name,
                messages=[],
                events=[],
                context=ctx.model_dump(),
                agents=_build_agents_list(),
                guardrails=[],
            )
    else:
        conversation_id = req.conversation_id  # type: ignore
        retrieved_state = conversation_store.get(conversation_id)
        if retrieved_state is None:
            # Handle case where conversation doesn't exist - create new state
            ctx = create_initial_context()
            current_agent_name = triage_agent.name
            state: Dict[str, Any] = {
                "input_items": [],
                "context": ctx,
                "current_agent": current_agent_name,
            }
        else:
            state = retrieved_state

    current_agent = _get_agent_by_name(state["current_agent"])
    state["input_items"].append({"content": req.message, "role": "user"})
    old_context = state["context"].model_dump().copy()
    guardrail_checks: List[GuardrailCheck] = []

    try:
        result = await Runner.run(
            current_agent, state["input_items"], context=state["context"]
        )
    except InputGuardrailTripwireTriggered as e:
        failed = e.guardrail_result.guardrail
        gr_output = e.guardrail_result.output.output_info
        gr_reasoning = getattr(gr_output, "reasoning", "")
        gr_input = req.message
        gr_timestamp = time.time() * 1000
        for g in current_agent.input_guardrails:
            guardrail_checks.append(
                GuardrailCheck(
                    id=uuid4().hex,
                    name=_get_guardrail_name(g),
                    input=gr_input,
                    reasoning=(gr_reasoning if g == failed else ""),
                    passed=(g != failed),
                    timestamp=gr_timestamp,
                )
            )
        refusal = "Sorry, I can only answer questions related to airline travel."
        state["input_items"].append({"role": "assistant", "content": refusal})
        return ChatResponse(
            conversation_id=conversation_id,
            current_agent=current_agent.name,
            messages=[MessageResponse(
                content=refusal, agent=current_agent.name
            )],
            events=[],
            context=state["context"].model_dump(),
            agents=_build_agents_list(),
            guardrails=guardrail_checks,
        )

    messages: List[MessageResponse] = []
    events: List[AgentEvent] = []

    for item in result.new_items:
        if isinstance(item, MessageOutputItem):
            text = ItemHelpers.text_message_output(item)
            messages.append(MessageResponse(content=text, agent=item.agent.name))
            events.append(
                AgentEvent(
                    id=uuid4().hex, type="message", agent=item.agent.name, content=text
                )
            )
        # Handle handoff output and agent switching
        elif isinstance(item, HandoffOutputItem):
            # Record the handoff event
            events.append(
                AgentEvent(
                    id=uuid4().hex,
                    type="handoff",
                    agent=item.source_agent.name,
                    content=f"{item.source_agent.name} -> {item.target_agent.name}",
                    metadata={
                        "source_agent": item.source_agent.name,
                        "target_agent": item.target_agent.name,
                    },
                )
            )
            # If there is an on_handoff callback defined for this handoff,
            # show it as a tool call
            from_agent = item.source_agent
            to_agent = item.target_agent
            # Find the Handoff object on the source agent matching the target
            ho = next(
                (
                    h
                    for h in getattr(from_agent, "handoffs", [])
                    if isinstance(h, Handoff)
                    and getattr(h, "agent_name", None) == to_agent.name
                ),
                None,
            )
            if ho:
                fn = ho.on_invoke_handoff
                fv = fn.__code__.co_freevars
                cl = fn.__closure__ or []
                if "on_handoff" in fv:
                    idx = fv.index("on_handoff")
                    if idx < len(cl) and cl[idx].cell_contents:
                        cb = cl[idx].cell_contents
                        cb_name = getattr(cb, "__name__", repr(cb))
                        events.append(
                            AgentEvent(
                                id=uuid4().hex,
                                type="tool_call",
                                agent=to_agent.name,
                                content=cb_name,
                            )
                        )
            current_agent = item.target_agent
        elif isinstance(item, ToolCallItem):
            tool_name = getattr(item.raw_item, "name", None)
            raw_args = getattr(item.raw_item, "arguments", None)
            tool_args: Any = raw_args
            if isinstance(raw_args, str):
                try:
                    import json

                    tool_args = json.loads(raw_args)
                except Exception:
                    pass
            events.append(
                AgentEvent(
                    id=uuid4().hex,
                    type="tool_call",
                    agent=item.agent.name,
                    content=tool_name or "",
                    metadata={"tool_args": tool_args},
                )
            )
            # If the tool is display_seat_map, send a special message so the UI
            # can render the seat selector.
            if tool_name == "display_seat_map":
                messages.append(
                    MessageResponse(
                        content="DISPLAY_SEAT_MAP",
                        agent=item.agent.name,
                    )
                )
        elif isinstance(item, ToolCallOutputItem):
            events.append(
                AgentEvent(
                    id=uuid4().hex,
                    type="tool_output",
                    agent=item.agent.name,
                    content=str(item.output),
                    metadata={"tool_result": item.output},
                )
            )

    new_context = state["context"].dict()
    changes = {
        k: new_context[k] for k in new_context if old_context.get(k) != new_context[k]
    }
    if changes:
        events.append(
            AgentEvent(
                id=uuid4().hex,
                type="context_update",
                agent=current_agent.name,
                content="",
                metadata={"changes": changes},
            )
        )

    state["input_items"] = result.to_input_list()
    state["current_agent"] = current_agent.name
    conversation_store.save(conversation_id, state)

    # Build guardrail results: mark failures (if any), and any others as passed
    final_guardrails: List[GuardrailCheck] = []
    for g in getattr(current_agent, "input_guardrails", []):
        name = _get_guardrail_name(g)
        failed = next((gc for gc in guardrail_checks if gc.name == name), None)
        if failed:
            final_guardrails.append(failed)
        else:
            final_guardrails.append(
                GuardrailCheck(
                    id=uuid4().hex,
                    name=name,
                    input=req.message,
                    reasoning="",
                    passed=True,
                    timestamp=time.time() * 1000,
                )
            )

    return ChatResponse(
        conversation_id=conversation_id,
        current_agent=current_agent.name,
        messages=messages,
        events=events,
        context=state["context"].dict(),
        agents=_build_agents_list(),
        guardrails=final_guardrails,
    )


# =========================
# MCP Server Management Models
# =========================


class MCPServerCreateRequest(BaseModel):
    name: str
    description: str = ""
    openapi_spec: Dict[str, Any]
    config: ServerGenerationConfig


class MCPServerResponse(BaseModel):
    id: str
    name: str
    description: str
    status: str
    endpoint_count: int
    tool_count: int
    complexity_score: float
    created_at: str
    updated_at: str


class MCPServerListResponse(BaseModel):
    servers: List[MCPServerResponse]
    total: int


class MCPRegistryStatsResponse(BaseModel):
    total_servers: int
    status_distribution: Dict[str, int]
    running_servers: int
    total_endpoints: int
    total_tools: int
    average_complexity: float


# =========================
# MCP Server Management Endpoints
# =========================


@app.get("/mcp/servers", response_model=MCPServerListResponse)
async def list_mcp_servers():
    """List all registered MCP servers."""
    try:
        registry = get_registry()
        servers = registry.list_servers()

        server_responses = []
        for server in servers:
            server_responses.append(MCPServerResponse(
                id=server.id,
                name=server.name,
                description=server.description,
                status=server.status.value,
                endpoint_count=server.endpoint_count,
                tool_count=server.tool_count,
                complexity_score=server.complexity_score,
                created_at=server.created_at.isoformat(),
                updated_at=server.updated_at.isoformat(),
            ))

        return MCPServerListResponse(
            servers=server_responses,
            total=len(server_responses)
        )
    except Exception as e:
        logger.error(f"Failed to list MCP servers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/mcp/servers", response_model=MCPServerResponse)
async def create_mcp_server(request: MCPServerCreateRequest):
    """Create and register a new MCP server."""
    try:
        registry = get_registry()
        server_id = f"server_{uuid4().hex[:8]}"

        server_info = await registry.register_server(
            server_id=server_id,
            name=request.name,
            openapi_spec=request.openapi_spec,
            config=request.config,
            description=request.description,
            auto_generate=True
        )

        return MCPServerResponse(
            id=server_info.id,
            name=server_info.name,
            description=server_info.description,
            status=server_info.status.value,
            endpoint_count=server_info.endpoint_count,
            tool_count=server_info.tool_count,
            complexity_score=server_info.complexity_score,
            created_at=server_info.created_at.isoformat(),
            updated_at=server_info.updated_at.isoformat(),
        )
    except Exception as e:
        logger.error(f"Failed to create MCP server: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/mcp/servers/{server_id}", response_model=MCPServerResponse)
async def get_mcp_server(server_id: str):
    """Get details of a specific MCP server."""
    try:
        registry = get_registry()
        server_info = registry.get_server(server_id)

        if not server_info:
            raise HTTPException(status_code=404, detail="Server not found")

        return MCPServerResponse(
            id=server_info.id,
            name=server_info.name,
            description=server_info.description,
            status=server_info.status.value,
            endpoint_count=server_info.endpoint_count,
            tool_count=server_info.tool_count,
            complexity_score=server_info.complexity_score,
            created_at=server_info.created_at.isoformat(),
            updated_at=server_info.updated_at.isoformat(),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get MCP server {server_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/mcp/servers/{server_id}/start")
async def start_mcp_server(server_id: str):
    """Start a registered MCP server."""
    try:
        registry = get_registry()
        success = await registry.start_server(server_id)

        if not success:
            raise HTTPException(status_code=400, detail="Failed to start server")

        return {"message": f"Server {server_id} started successfully"}
    except Exception as e:
        logger.error(f"Failed to start MCP server {server_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/mcp/servers/{server_id}/stop")
async def stop_mcp_server(server_id: str):
    """Stop a running MCP server."""
    try:
        registry = get_registry()
        success = await registry.stop_server(server_id)

        if not success:
            raise HTTPException(status_code=400, detail="Failed to stop server")

        return {"message": f"Server {server_id} stopped successfully"}
    except Exception as e:
        logger.error(f"Failed to stop MCP server {server_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/mcp/servers/{server_id}")
async def delete_mcp_server(server_id: str, cleanup_files: bool = True):
    """Delete a registered MCP server."""
    try:
        registry = get_registry()
        success = await registry.delete_server(server_id, cleanup_files)

        if not success:
            raise HTTPException(status_code=400, detail="Failed to delete server")

        return {"message": f"Server {server_id} deleted successfully"}
    except Exception as e:
        logger.error(f"Failed to delete MCP server {server_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/mcp/servers/{server_id}/health")
async def get_mcp_server_health(server_id: str):
    """Get health status of a specific MCP server."""
    try:
        registry = get_registry()
        health_status = await registry.health_check(server_id)
        return health_status
    except Exception as e:
        logger.error(f"Failed to check health of MCP server {server_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/mcp/stats", response_model=MCPRegistryStatsResponse)
async def get_mcp_registry_stats():
    """Get MCP registry statistics."""
    try:
        registry = get_registry()
        stats = registry.get_registry_stats()

        return MCPRegistryStatsResponse(
            total_servers=stats["total_servers"],
            status_distribution=stats["status_distribution"],
            running_servers=stats["running_servers"],
            total_endpoints=stats["total_endpoints"],
            total_tools=stats["total_tools"],
            average_complexity=stats["average_complexity"],
        )
    except Exception as e:
        logger.error(f"Failed to get MCP registry stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
