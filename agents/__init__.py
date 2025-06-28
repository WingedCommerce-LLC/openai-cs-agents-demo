"""
Agents package initialization.

⚠️  IMPORTANT: TEMPORARY STUB IMPLEMENTATIONS ⚠️

This module contains STUB IMPLEMENTATIONS that are placeholders to resolve
import errors and maintain code compatibility. These are NOT functional
implementations and should be replaced with a real agent framework.

See AGENT_IMPLEMENTATION_PLAN.md for the roadmap to replace these stubs.
"""

from typing import Any, Callable, List, Optional, TypeVar

# Type variables
T = TypeVar('T')


class Agent:
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

    ⚠️  This is a temporary stub that returns empty results.
    Replace with real agent execution engine.
    """

    @staticmethod
    async def run(agent: "Agent", input_data: Any, context: Any = None):
        """STUB: Returns empty RunResult. No actual execution occurs."""
        return RunResult()


class RunResult:
    """
    STUB: Run result placeholder.

    ⚠️  This is a temporary stub that returns empty data.
    Replace with real result handling system.
    """

    def final_output_as(self, output_type: type):
        """STUB: Returns empty instance of output_type."""
        return output_type()

    @property
    def new_items(self):
        """STUB: Returns empty list."""
        return []

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
