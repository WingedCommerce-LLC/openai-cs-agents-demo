"""
Agents package initialization.

⚠️  IMPORTANT: TEMPORARY STUB IMPLEMENTATIONS ⚠️

This module contains STUB IMPLEMENTATIONS that are placeholders to resolve
import errors and maintain code compatibility. These are NOT functional
implementations and should be replaced with a real agent framework.

See AGENT_IMPLEMENTATION_PLAN.md for the roadmap to replace these stubs.
"""

from typing import Any, Callable, List, Optional, TypeVar, Generic

# Type variables
T = TypeVar('T')


class Agent(Generic[T]):
    """
    STUB: Agent class placeholder.

    ⚠️  This is a temporary stub implementation that only stores parameters
    but provides no actual agent functionality. Replace with real agent library.
    """

    def __init__(
        self,
        model: str = "",
        name: str = "",
        instructions: Any = "",
        tools: Optional[List] = None,
        handoffs: Optional[List] = None,
        input_guardrails: Optional[List] = None,
        handoff_description: str = "",
        output_type: Any = None,
        **kwargs
    ):
        self.model = model
        self.name = name
        self.instructions = instructions
        self.tools = tools or []
        self.handoffs = handoffs or []
        self.input_guardrails = input_guardrails or []
        self.handoff_description = handoff_description
        self.output_type = output_type


class GuardrailFunctionOutput:
    """
    STUB: Guardrail function output placeholder.

    ⚠️  This is a temporary stub that only stores basic output info.
    Replace with real guardrail system implementation.
    """

    def __init__(self, output_info: Any = None, tripwire_triggered: bool = False):
        self.output_info = output_info
        self.tripwire_triggered = tripwire_triggered


class RunContextWrapper:
    """
    STUB: Run context wrapper placeholder.

    ⚠️  This is a temporary stub that only stores context.
    Replace with real context management system.
    """

    def __init__(self, context: Any = None):
        self.context = context


class Runner:
    """
    STUB: Runner class placeholder.

    ⚠️  This is a temporary stub that returns basic demo results.
    Replace with real agent execution engine.
    """

    @staticmethod
    async def run(agent: "Agent", input_data: Any, context: Any = None):
        """STUB: Returns basic demo RunResult for UI demonstration."""
        # Create a basic demo response
        result = RunResult()

        # Add a simple message response for demo purposes
        if isinstance(input_data, list) and len(input_data) > 0:
            last_message = input_data[-1]
            if isinstance(last_message, dict) and last_message.get("role") == "user":
                user_message = last_message.get("content", "")

                # Simple demo response based on user input
                if "seat" in user_message.lower():
                    demo_response = ("I can help you change your seat. "
                                     "Your confirmation number is ABC123. "
                                     "What seat would you like to change to?")
                elif "flight" in user_message.lower():
                    demo_response = ("Let me check your flight status. "
                                     "Flight ABC123 is on time.")
                elif "cancel" in user_message.lower():
                    demo_response = ("I can help you cancel your flight. "
                                     "Please confirm your booking details.")
                else:
                    demo_response = ("I'm here to help with your airline needs. "
                                     "How can I assist you today?")

                # Create a demo message item
                demo_item = MessageOutputItem(agent, demo_response)
                result._items = [demo_item]

        return result


class DemoMessageItem:
    """
    STUB: Demo message item for basic UI demonstration.
    """
    def __init__(self, agent, content):
        self.agent = agent
        self.content = content


class MessageOutputItem:
    """
    STUB: Message output item placeholder.
    """
    def __init__(self, agent, content):
        self.agent = agent
        self.content = content


class HandoffOutputItem:
    """
    STUB: Handoff output item placeholder.
    """
    def __init__(self, source_agent, target_agent):
        self.source_agent = source_agent
        self.target_agent = target_agent


class ToolCallItem:
    """
    STUB: Tool call item placeholder.
    """
    def __init__(self, agent, raw_item):
        self.agent = agent
        self.raw_item = raw_item


class ToolCallOutputItem:
    """
    STUB: Tool call output item placeholder.
    """
    def __init__(self, agent, output):
        self.agent = agent
        self.output = output


class ItemHelpers:
    """
    STUB: Item helpers placeholder.
    """
    @staticmethod
    def text_message_output(item):
        return getattr(item, 'content', str(item))


class RunResult:
    """
    STUB: Run result placeholder.

    ⚠️  This is a temporary stub that returns basic demo data.
    Replace with real result handling system.
    """

    def __init__(self):
        self._items = []

    def final_output_as(self, output_type: type):
        """STUB: Returns empty instance of output_type."""
        return output_type()

    @property
    def new_items(self):
        """STUB: Returns demo items."""
        return self._items

    def to_input_list(self):
        """STUB: Returns empty list."""
        return []


class TResponseInputItem:
    """
    STUB: Response input item placeholder.

    ⚠️  This is a temporary stub with no functionality.
    Replace with real response item handling.
    """

    pass


def function_tool(name_override: str = "", description_override: str = ""):
    """
    STUB: Function tool decorator placeholder.

    ⚠️  This is a temporary stub that only sets attributes.
    Replace with real tool registration system.
    """

    def decorator(func: Callable) -> Callable:
        setattr(func, "_tool_name", name_override)
        setattr(func, "_tool_description", description_override)
        return func

    return decorator


def handoff(agent: "Agent", on_handoff: Optional[Callable] = None):
    """
    STUB: Handoff function placeholder.

    ⚠️  This is a temporary stub that returns a dict.
    Replace with real agent handoff system.
    """
    return {"agent": agent, "on_handoff": on_handoff}


def input_guardrail(name: str):
    """
    STUB: Input guardrail decorator placeholder.

    ⚠️  This is a temporary stub that only sets attributes.
    Replace with real guardrail system.
    """

    def decorator(func: Callable) -> Callable:
        setattr(func, "_guardrail_name", name)
        return func

    return decorator


# Export all the required symbols
__all__ = [
    "Agent",
    "GuardrailFunctionOutput",
    "RunContextWrapper",
    "Runner",
    "TResponseInputItem",
    "function_tool",
    "handoff",
    "input_guardrail",
]
