"""
LangGraph-native integration.

Uses LangGraph's `interrupt()` to truly pause a graph when a tool call
requires human approval. The graph state is saved, the caller is handed
the interrupt payload, and the graph resumes when the human answers.

Optionally writes every decision to a hash-chained audit log.
"""

from typing import Any, Callable, Optional

from langgraph.types import interrupt

from ..audit import AuditLog
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
        guard = GuardNode(policy, audit=AuditLog("audit.jsonl"))

        def send_email_node(state):
            return guard.run("send_email", state["args"], _real_send_email)
    """

    def __init__(
        self,
        policy: dict[str, ToolPolicy],
        audit: Optional[AuditLog] = None,
    ):
        self.policy = policy
        self.audit = audit

    def _log(self, tool_name: str, args: dict, decision: str, reason: str = "") -> None:
        if self.audit is not None:
            self.audit.append(tool_name, args, decision, reason)

    def run(
        self,
        tool_name: str,
        args: dict[str, Any],
        tool_fn: Callable[..., Any],
    ) -> Any:
        """
        Execute the tool following policy.

        - allow             -> runs tool_fn(**args), returns result
        - block             -> returns a BLOCKED string
        - require_approval  -> calls interrupt(), resumes with approval,
                               then runs or denies
        """
        if tool_name not in self.policy:
            raise ToolNotFoundError(tool_name)

        rule = self.policy[tool_name]

        if rule.action == "allow":
            result = tool_fn(**args)
            self._log(tool_name, args, "allowed")
            return result

        if rule.action == "block":
            self._log(tool_name, args, "blocked", rule.reason)
            return (
                f"BLOCKED: Tool '{tool_name}' is blocked by policy"
                + (f": {rule.reason}" if rule.reason else "")
            )

        if rule.action == "require_approval":
            decision = interrupt({
                "type": "approval_required",
                "tool_name": tool_name,
                "args": args,
                "reason": rule.reason,
            })

            approved = _is_approved(decision)

            if approved:
                result = tool_fn(**args)
                self._log(tool_name, args, "approved", rule.reason)
                return f"APPROVED & EXECUTED: {result}"
            else:
                self._log(tool_name, args, "denied", rule.reason)
                return f"DENIED: Human rejected {tool_name}"

        self._log(tool_name, args, "blocked", f"Unknown policy action {rule.action!r}")
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