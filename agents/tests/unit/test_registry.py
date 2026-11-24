"""Unit tests for agent tool registry and tool access enforcement."""

import pytest
from langchain_core.tools import tool

from reroute_agents.tools.registry import (
    ToolAccessViolationError,
    ToolRegistry,
)


@tool
def sample_web_tool(query: str) -> str:
    """Sample web tool."""
    return f"web result for {query}"


@tool
def sample_chat_tool(amount: float) -> str:
    """Sample chat tool."""
    return f"chat converted {amount}"


def test_tool_registry_registration_and_retrieval() -> None:
    reg = ToolRegistry()
    reg.register("web", sample_web_tool)
    reg.register("chat", sample_chat_tool)

    web_tools = reg.for_agent("web")
    assert len(web_tools) == 1
    assert web_tools[0].name == "sample_web_tool"

    chat_tools = reg.for_agent("chat")
    assert len(chat_tools) == 1
    assert chat_tools[0].name == "sample_chat_tool"

    plan_tools = reg.for_agent("plan")
    assert len(plan_tools) == 0


def test_tool_registry_invalid_agent_name() -> None:
    reg = ToolRegistry()
    with pytest.raises(ValueError, match="Unknown agent"):
        reg.for_agent("unknown_agent")

    with pytest.raises(ValueError, match="Unknown agent"):
        reg.register("unknown_agent", sample_web_tool)


def test_tool_registry_access_violation_loud_failure() -> None:
    reg = ToolRegistry()
    reg.register("web", sample_web_tool)

    # Authorized access succeeds
    tool_inst = reg.validate_tool_access("web", "sample_web_tool")
    assert tool_inst.name == "sample_web_tool"

    # Unauthorized access by another agent fails loud
    with pytest.raises(ToolAccessViolationError, match="not registered to agent 'chat'"):
        reg.validate_tool_access("chat", "sample_web_tool")

    # Non-existent tool fails loud
    with pytest.raises(ToolAccessViolationError, match="not registered to agent 'web'"):
        reg.validate_tool_access("web", "non_existent_tool")
