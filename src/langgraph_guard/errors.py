"""Custom exceptions for langgraph-guard."""


class GovernanceError(Exception):
    """Base exception for all guardrail errors."""
    pass


class GovernanceBlockedError(GovernanceError):
    """Raised when a tool call is blocked by policy."""

    def __init__(self, tool_name: str, reason: str = ""):
        self.tool_name = tool_name
        self.reason = reason
        message = f"Tool '{tool_name}' is blocked by policy"
        if reason:
            message += f": {reason}"
        super().__init__(message)


class ApprovalRequiredError(GovernanceError):
    """Raised when a tool call needs human approval."""

    def __init__(self, tool_name: str, args: dict, message: str = ""):
        self.tool_name = tool_name
        self.tool_args = args
        self.message = message
        super().__init__(
            f"Tool '{tool_name}' requires approval before executing"
        )


class ToolNotFoundError(GovernanceError):
    """Raised when a tool is not defined in the policy."""

    def __init__(self, tool_name: str):
        self.tool_name = tool_name
        super().__init__(
            f"Tool '{tool_name}' is not defined in the policy"
        )