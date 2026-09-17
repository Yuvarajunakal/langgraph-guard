"""
Mock LLM demo — deterministic, no real model calls.

Shows the guardrail behavior for all three policy actions:
- allow       (query_data)
- require_approval (send_email)
- block       (delete_account)
"""

import sys
from pathlib import Path

# Make sure we can import the package when running as a script
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from langgraph_guard import (
    load_policy,
    guarded_tool_call,
    GovernanceBlockedError,
    ApprovalRequiredError,
)


# --- "Real" tool implementations (stubs) ------------------------------------

def _real_query_data(sql: str) -> str:
    return f"[DB] Query executed: {sql} -> 42 rows"


def _real_send_email(to: str, subject: str, body: str) -> str:
    return f"[EMAIL] Sent to {to}: {subject}"


def _real_delete_account(user_id: int) -> str:
    return f"[DB] Account {user_id} deleted"


# --- Guarded tool wrappers --------------------------------------------------

policy = load_policy(Path(__file__).parent / "basic_policy.yaml")


def tool_query_data(sql: str) -> str:
    return guarded_tool_call(
        "query_data", {"sql": sql}, policy, _real_query_data
    )


def tool_send_email(to: str, subject: str, body: str) -> str:
    return guarded_tool_call(
        "send_email",
        {"to": to, "subject": subject, "body": body},
        policy,
        _real_send_email,
    )


def tool_delete_account(user_id: int) -> str:
    return guarded_tool_call(
        "delete_account", {"user_id": user_id}, policy, _real_delete_account
    )


# --- Approval handling ------------------------------------------------------

def prompt_for_approval(tool_name: str, args: dict, reason: str) -> bool:
    """CLI prompt for human approval. Returns True if approved."""
    print()
    print("  \u26a0\ufe0f  APPROVAL REQUIRED")
    print(f"     Tool:   {tool_name}")
    print(f"     Args:   {args}")
    if reason:
        print(f"     Reason: {reason}")
    print()
    answer = input("     Approve? (y/n): ").strip().lower()
    return answer == "y"


def run_tool_safely(fn, tool_name: str, args: dict):
    """
    Run a guarded tool, handling the three possible outcomes.

    Returns a string that would go back to the agent as the tool result.
    """
    try:
        result = fn(**args)
        return f"SUCCESS: {result}"

    except GovernanceBlockedError as e:
        return f"BLOCKED: {e}"

    except ApprovalRequiredError as e:
        tool_args = getattr(e, "tool_args", e.args if isinstance(e.args, dict) else {})
        approved = prompt_for_approval(tool_name, tool_args, e.message)
        if approved:
            # Re-run with the real implementation, bypassing the guard
            real_fns = {
                "send_email": _real_send_email,
            }
            result = real_fns[tool_name](**tool_args)
            return f"APPROVED & EXECUTED: {result}"
        else:
            return f"DENIED: Human rejected {tool_name}"


# --- Three demo scenarios ---------------------------------------------------

def scenario_1_allowed():
    print("\n" + "=" * 60)
    print("SCENARIO 1: Agent queries the database (allowed)")
    print("=" * 60)
    result = run_tool_safely(
        tool_query_data,
        "query_data",
        {"sql": "SELECT COUNT(*) FROM users"},
    )
    print(f"\n  Agent receives: {result}")


def scenario_2_approval():
    print("\n" + "=" * 60)
    print("SCENARIO 2: Agent sends an email (requires approval)")
    print("=" * 60)
    result = run_tool_safely(
        tool_send_email,
        "send_email",
        {
            "to": "newuser@example.com",
            "subject": "Welcome!",
            "body": "Thanks for signing up.",
        },
    )
    print(f"\n  Agent receives: {result}")


def scenario_3_blocked():
    print("\n" + "=" * 60)
    print("SCENARIO 3: Agent tries to delete an account (blocked)")
    print("=" * 60)
    result = run_tool_safely(
        tool_delete_account,
        "delete_account",
        {"user_id": 12345},
    )
    print(f"\n  Agent receives: {result}")


# --- Main -------------------------------------------------------------------

if __name__ == "__main__":
    print("\n" + "#" * 60)
    print("# langgraph-guard mock demo")
    print("#" * 60)

    scenario_1_allowed()
    scenario_2_approval()
    scenario_3_blocked()

    print("\n" + "#" * 60)
    print("# Demo complete")
    print("#" * 60 + "\n")