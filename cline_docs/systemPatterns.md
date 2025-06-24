# System Patterns

## Architecture Overview

### Multi-Agent System Design
The system implements a **hub-and-spoke** pattern with the Triage Agent as the central router and specialist agents as spokes. This enables intelligent request routing and maintains conversation context across agent handoffs.

### Key Architectural Decisions

#### 1. Agent Orchestration Pattern
- **Central Triage Agent** - Acts as the main entry point and router
- **Specialist Agents** - Handle domain-specific tasks
- **Bidirectional Handoffs** - Agents can route back to triage for unhandled requests
- **Context Preservation** - Shared context object maintains state across handoffs

#### 2. Guardrail Implementation
- **Input Guardrails** - Applied before agent processing
- **Dual Guardrail System** - Relevance + Jailbreak protection
- **Tripwire Pattern** - Guardrails can halt processing and return refusal messages
- **Per-Agent Guardrails** - Each agent has its own guardrail configuration

#### 3. Tool Integration Pattern
- **Function Tools** - Decorated functions that agents can call
- **Context-Aware Tools** - Tools receive and can modify the conversation context
- **Async Tool Execution** - All tools are async for better performance
- **Tool Result Tracking** - UI visualizes tool calls and results

## Core Patterns

### Agent Definition Pattern
```python
agent = Agent[ContextType](
    name="Agent Name",
    model="gpt-4.1",
    handoff_description="Description for routing",
    instructions=dynamic_instructions_function,
    tools=[tool1, tool2],
    handoffs=[other_agent1, other_agent2],
    input_guardrails=[guardrail1, guardrail2]
)
```

### Context Management Pattern
- **Typed Context** - Uses Pydantic models for type safety
- **Context Factory** - `create_initial_context()` generates fresh context
- **Context Mutation** - Tools can modify context during execution
- **Context Persistence** - Context preserved across agent handoffs

### Handoff Pattern
```python
# Simple handoff
handoffs=[other_agent]

# Handoff with callback
handoff(agent=target_agent, on_handoff=callback_function)
```

### Tool Definition Pattern
```python
@function_tool(
    name_override="custom_name",
    description_override="Custom description"
)
async def tool_function(
    context: RunContextWrapper[ContextType],
    param1: str,
    param2: int
) -> str:
    # Tool implementation
    return result
```

### Guardrail Pattern
```python
@input_guardrail(name="Guardrail Name")
async def guardrail_function(
    context: RunContextWrapper[None],
    agent: Agent,
    input: str | list[TResponseInputItem]
) -> GuardrailFunctionOutput:
    # Guardrail logic
    return GuardrailFunctionOutput(
        output_info=result,
        tripwire_triggered=should_block
    )
```

## Data Flow Patterns

### Request Processing Flow
1. **HTTP Request** → FastAPI endpoint
2. **Conversation Retrieval** → In-memory store lookup
3. **Agent Execution** → OpenAI Agents SDK Runner
4. **Result Processing** → Parse agent outputs
5. **State Persistence** → Save updated conversation state
6. **Response Formation** → Structure API response

### Agent Communication Flow
1. **Message Input** → Current agent receives user message
2. **Processing** → Agent analyzes and decides on action
3. **Tool Execution** → Agent calls tools if needed
4. **Handoff Decision** → Agent decides if handoff is needed
5. **Context Transfer** → Context passed to target agent
6. **Response Generation** → New agent generates response

### Event Tracking Pattern
- **Event Generation** - Each agent action generates events
- **Event Types** - message, handoff, tool_call, tool_output, context_update
- **Event Metadata** - Rich metadata for UI visualization
- **Event Streaming** - Events sent to frontend for real-time updates

## Error Handling Patterns

### Guardrail Failure Pattern
- **Exception Handling** - `InputGuardrailTripwireTriggered` exception
- **Graceful Degradation** - Return polite refusal message
- **State Preservation** - Conversation state maintained despite failure
- **Audit Trail** - Guardrail failures logged and tracked

### Tool Failure Pattern
- **Assertion-Based Validation** - Tools validate required context
- **Error Propagation** - Tool errors bubble up to agent
- **Fallback Responses** - Agents handle tool failures gracefully

## Performance Patterns

### Conversation State Management
- **In-Memory Storage** - Fast access for demo purposes
- **State Serialization** - Pydantic models ensure clean serialization
- **Lazy Loading** - Context created only when needed
- **Memory Cleanup** - No automatic cleanup (suitable for demo)

### Async Processing
- **Async Agents** - All agent operations are async
- **Async Tools** - Tool execution doesn't block
- **Concurrent Safety** - No shared mutable state between requests

## Security Patterns

### Input Validation
- **Pydantic Models** - Type validation for all inputs
- **Guardrail Enforcement** - Multi-layer input validation
- **Context Isolation** - Each conversation has isolated context

### API Security
- **CORS Configuration** - Restricted to localhost for demo
- **No Authentication** - Demo system, no auth required
- **Environment Variables** - Sensitive data in environment
