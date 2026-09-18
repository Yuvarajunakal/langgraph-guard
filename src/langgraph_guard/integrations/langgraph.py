"""
LangGraph-native integration.

Uses LangGraph's `interrupt()` to truly pause a graph when a tool call
requires human approval. The graph state is saved, the caller is handed
the interrupt payload, and the graph resumes when the human answers.
"""

from typing import Any, Callable

from langgraph.types import interrupt

from ..errors import (
    ApprovalRequiredError,
    GovernanceBlockedError,
    ToolNotFoundError,
)
from ..policy import ToolPolicy


class GuardNode:
    """
    Wraps a tool function so that every call is checked against a policy.

    Usage:

        guard = GuardNode(policy)

        def send_email_node(state):
            return guard.run("send_email", state["args"], _real_send_email)

    When the policy says `require_approval`, `interrupt()` pauses the
    graph. When the graph resumes with `Command(resume=True)`, the
    approval is granted and the tool executes. `Command(resume=False)`
    denies it.
    """

    def __init__(self, policy: dict[str, ToolPolicy]):
        self.policy = policy

    def run(
        self,
        tool_name: str,
        args: dict[str, Any],
        tool_fn: Callable[..., Any],
    ) -> Any:
        """
        Execute the tool following policy.

        - allow             -> runs tool_fn(**args), returns result
        - block             -> returns a BLOCKED string (does not raise,
                               so the agent can continue)
        - require_approval  -> calls interrupt(), resumes with approval,
                               then runs or denies
        """
        if tool_name not in self.policy:
            raise ToolNotFoundError(tool_name)

        rule = self.policy[tool_name]

        if rule.action == "allow":
            return tool_fn(**args)

        if rule.action == "block":
            return (
                f"BLOCKED: Tool '{tool_name}' is blocked by policy"
                + (f": {rule.reason}" if rule.reason else "")
            )

        if rule.action == "require_approval":
            # Pause the graph and hand the payload to the caller
            decision = interrupt({
                "type": "approval_required",
                "tool_name": tool_name,
                "args": args,
                "reason": rule.reason,
            })

            # When the graph resumes, `decision` is the value passed via
            # Command(resume=...). We accept True/"y"/"yes" as approval.
            approved = _is_approved(decision)

            if approved:
                result = tool_fn(**args)
                return f"APPROVED & EXECUTED: {result}"
            else:
                return f"DENIED: Human rejected {tool_name}"

        # Defensive: unknown action
        return f"BLOCKED: Unknown policy action {rule.action!r}"


def _is_approved(decision: Any) -> bool:
    """Normalize whatever the caller passed to Command(resume=...)."""
    if isinstance(decision, bool):
        return decision
    if isinstance(decision, str):
        return decision.strip().lower() in ("y", "yes", "true", "approve", "approved")
    if isinstance(decision, dict):
        return bool(decision.get("approved", False))
    return False