"""
Unit tests for agents.extensions modules.

Tests the agents extensions functionality.
"""

import os
import sys

# Add the project root to Python path to ensure imports work
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


class TestHandoffPrompt:
    """Test suite for handoff prompt functionality."""

    def test_import_handoff_prompt(self):
        """Test that handoff_prompt module can be imported."""
        from agents.extensions import handoff_prompt

        assert handoff_prompt is not None

    def test_recommended_prompt_prefix(self):
        """Test that the recommended prompt prefix is available."""
        from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX

        assert RECOMMENDED_PROMPT_PREFIX is not None
        assert isinstance(RECOMMENDED_PROMPT_PREFIX, str)
        assert len(RECOMMENDED_PROMPT_PREFIX) > 0

    def test_get_handoff_prompt_default(self):
        """Test getting handoff prompt with default agent type."""
        from agents.extensions.handoff_prompt import get_handoff_prompt

        prompt = get_handoff_prompt()
        assert prompt is not None
        assert isinstance(prompt, str)

    def test_get_handoff_prompt_types(self):
        """Test getting handoff prompt for different agent types."""
        from agents.extensions.handoff_prompt import get_handoff_prompt

        # Test all supported agent types
        types = [
            "customer_service",
            "technical_support",
            "billing",
            "general",
            "unknown",
        ]

        for agent_type in types:
            prompt = get_handoff_prompt(agent_type)
            assert prompt is not None
            assert isinstance(prompt, str)
            assert len(prompt) > 0

    def test_format_handoff_context_empty(self):
        """Test formatting handoff context with empty context."""
        from agents.extensions.handoff_prompt import format_handoff_context

        result = format_handoff_context({})
        assert result == ""

    def test_format_handoff_context_none(self):
        """Test formatting handoff context with None context."""
        from agents.extensions.handoff_prompt import format_handoff_context

        result = format_handoff_context(None)
        assert result == ""

    def test_format_handoff_context_with_data(self):
        """Test formatting handoff context with actual data."""
        from agents.extensions.handoff_prompt import format_handoff_context

        context = {
            "customer_name": "John Doe",
            "issue_type": "billing",
            "priority": "high",
        }

        result = format_handoff_context(context)
        assert result is not None
        assert isinstance(result, str)
        assert "Previous conversation context:" in result
        assert "customer_name: John Doe" in result

    def test_create_handoff_message(self):
        """Test creating handoff message."""
        from agents.extensions.handoff_prompt import create_handoff_message

        message = create_handoff_message(
            "customer_service",
            "technical_support",
            "Technical issue requires specialist",
        )

        assert message is not None
        assert isinstance(message, str)
        assert "customer_service" in message
        assert "technical_support" in message
        assert "Technical issue requires specialist" in message

    def test_all_functions_work(self):
        """Test that all functions work together."""
        from agents.extensions.handoff_prompt import (
            create_handoff_message,
            format_handoff_context,
            get_handoff_prompt,
        )

        # Test a complete workflow
        prompt = get_handoff_prompt("customer_service")
        context = {"issue": "billing problem"}
        formatted_context = format_handoff_context(context)
        message = create_handoff_message("agent1", "agent2", "transfer needed")

        assert all([prompt, formatted_context, message])
