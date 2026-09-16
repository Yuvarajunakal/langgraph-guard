"""Core interceptor: the guardrail function that checks every tool call."""

from typing import Any, Callable

from .errors import (
    ApprovalRequiredError,
    GovernanceBlockedError,
    ToolNotFoundError,
)
from .policy import ToolPolicy


def check_policy(tool_name: str, policy: dict[str, ToolPolicy]) -> ToolPolicy:
    """
    Look up a tool in the policy. Raises ToolNotFoundError if absent.
    """
    if tool_name not in policy:
        raise ToolNotFoundError(tool_name)
    return policy[tool_name]


def guarded_tool_call(
    tool_name: str,
    args: dict[str, Any],
    policy: dict[str, ToolPolicy],
    tool_fn: Callable[..., Any],
) -> Any:
    """
    Execute a tool only if the policy allows it.

    - action == "allow"              -> runs tool_fn(**args), returns result
    - action == "block"              -> raises GovernanceBlockedError
    - action == "require_approval"   -> raises ApprovalRequiredError with args
    """
    rule = check_policy(tool_name, policy)

    if rule.action == "allow":
        return tool_fn(**args)

    if rule.action == "block":
        raise GovernanceBlockedError(tool_name, rule.reason)

    if rule.action == "require_approval":
        raise ApprovalRequiredError(tool_name, args, rule.reason)

    # Defensive: if the policy file somehow contains an unknown action
    raise GovernanceBlockedError(
        tool_name,
        f"Unknown policy action: {rule.action!r}"
    )