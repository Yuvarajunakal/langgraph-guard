"""Approval helpers for human-in-the-loop workflows."""

from typing import Any


def prompt_cli(
    tool_name: str,
    tool_args: dict[str, Any],
    reason: str = "",
) -> bool:
    """
    Prompt a human for approval in the terminal.

    Returns True if approved, False if denied.
    """
    print()
    print("  \u26a0\ufe0f  APPROVAL REQUIRED")
    print(f"     Tool:   {tool_name}")
    print(f"     Args:   {tool_args}")
    if reason:
        print(f"     Reason: {reason}")
    print()
    while True:
        answer = input("     Approve? (y/n): ").strip().lower()
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        print("     Please answer 'y' or 'n'.")