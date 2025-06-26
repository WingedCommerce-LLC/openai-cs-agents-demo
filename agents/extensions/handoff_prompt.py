"""Handoff prompt extensions for agents."""
from typing import Optional

RECOMMENDED_PROMPT_PREFIX = """You are a helpful customer service agent for an airline.
Be polite, professional, and helpful. Always try to resolve the customer's issue
efficiently. If you cannot help with a specific request, transfer the customer to the
appropriate specialist agent."""


def get_handoff_prompt(agent_type: str = "customer_service") -> str:
    """Get the appropriate handoff prompt for the given agent type."""
    prompts = {
        "customer_service": RECOMMENDED_PROMPT_PREFIX,
        "technical_support": ("You are a technical support specialist. "
                              "Help users with technical issues."),
        "billing": ("You are a billing specialist. Help customers with "
                    "payment and billing inquiries."),
        "general": "You are a helpful AI assistant.",
    }
    return prompts.get(agent_type, prompts["general"])


def format_handoff_context(context: Optional[dict] = None) -> str:
    """Format handoff context for agent transfer."""
    if not context:
        return ""

    formatted = "Previous conversation context:\n"
    for key, value in context.items():
        formatted += f"- {key}: {value}\n"
    return formatted


def create_handoff_message(from_agent: str, to_agent: str, reason: str) -> str:
    """Create a handoff message for agent transfer."""
    return f"Transferring from {from_agent} to {to_agent}. Reason: {reason}"
