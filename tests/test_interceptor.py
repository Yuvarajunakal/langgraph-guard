import pytest

from langgraph_guard import (
    load_policy,
    guarded_tool_call,
    GovernanceBlockedError,
    ApprovalRequiredError,
    ToolNotFoundError,
)


@pytest.fixture
def policy():
    return load_policy("examples/basic_policy.yaml")


@pytest.fixture
def tools():
    """Three dummy tools that record whether they were called."""
    calls = []

    def query_data(**kwargs):
        calls.append(("query_data", kwargs))
        return {"rows": 42}

    def send_email(**kwargs):
        calls.append(("send_email", kwargs))
        return {"sent": True}

    def delete_account(**kwargs):
        calls.append(("delete_account", kwargs))
        return {"deleted": True}

    return {
        "fns": {
            "query_data": query_data,
            "send_email": send_email,
            "delete_account": delete_account,
        },
        "calls": calls,
    }


def test_allow_runs_tool(policy, tools):
    result = guarded_tool_call(
        "query_data",
        {"sql": "SELECT 1"},
        policy,
        tools["fns"]["query_data"],
    )
    assert result == {"rows": 42}
    assert len(tools["calls"]) == 1
    assert tools["calls"][0][0] == "query_data"


def test_block_raises_and_does_not_run(policy, tools):
    with pytest.raises(GovernanceBlockedError) as exc_info:
        guarded_tool_call(
            "delete_account",
            {"user_id": 123},
            policy,
            tools["fns"]["delete_account"],
        )
    assert exc_info.value.tool_name == "delete_account"
    assert "Account deletion" in exc_info.value.reason
    # Tool must NOT have been called
    assert len(tools["calls"]) == 0


def test_approval_raises_with_args(policy, tools):
    with pytest.raises(ApprovalRequiredError) as exc_info:
        guarded_tool_call(
            "send_email",
            {"to": "external@example.com", "subject": "Hi"},
            policy,
            tools["fns"]["send_email"],
        )
    assert exc_info.value.tool_name == "send_email"
    # The original args must be preserved for the human reviewer
    assert "to" in exc_info.value.tool_args
    assert exc_info.value.tool_args["to"] == "external@example.com"
    # Tool must NOT have been called
    assert len(tools["calls"]) == 0


def test_unknown_tool_raises(policy, tools):
    with pytest.raises(ToolNotFoundError):
        guarded_tool_call(
            "not_in_policy",
            {},
            policy,
            lambda **kw: None,
        )