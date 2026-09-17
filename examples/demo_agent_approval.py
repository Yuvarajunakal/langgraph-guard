"""
Real LLM demo with interactive approval.

Uses Ollama (llama3.2:1b) via LangGraph.
When the agent tries to call `send_email`, the user is prompted to approve/deny.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain_ollama import ChatOllama

from langgraph_guard import (
    load_policy,
    guarded_tool_call,
    GovernanceBlockedError,
    ApprovalRequiredError,
)


POLICY_PATH = Path(__file__).parent / "basic_policy.yaml"
policy = load_policy(POLICY_PATH)


# --- "Real" implementations -------------------------------------------------

def _real_query_data(sql: str) -> str:
    return f"[DB] Query executed: {sql} -> 42 rows"


def _real_send_email(to: str, subject: str, body: str) -> str:
    return f"Email successfully sent to {to} with subject '{subject}'. Confirmation ID: MSG-{abs(hash(to))%100000}"

def _real_delete_account(user_id: int) -> str:
    return f"[DB] Account {user_id} deleted"


# --- Approval prompt --------------------------------------------------------

def prompt_approval(tool_name: str, tool_args: dict, reason: str) -> bool:
    print()
    print("  \u26a0\ufe0f  APPROVAL REQUIRED")
    print(f"     Tool:   {tool_name}")
    print(f"     Args:   {tool_args}")
    if reason:
        print(f"     Reason: {reason}")
    print()
    answer = input("     Approve? (y/n): ").strip().lower()
    return answer == "y"


# --- Guarded tools ----------------------------------------------------------

@tool
def query_data(sql: str) -> str:
    """Run a read-only SQL query against the user database."""
    try:
        return guarded_tool_call(
            "query_data", {"sql": sql}, policy, _real_query_data
        )
    except (GovernanceBlockedError, ApprovalRequiredError) as e:
        return f"BLOCKED: {e}"


@tool
def send_email(to: str, subject: str, body: str) -> str:
    """Send an email to a recipient."""
    try:
        return guarded_tool_call(
            "send_email",
            {"to": to, "subject": subject, "body": body},
            policy,
            _real_send_email,
        )
    except ApprovalRequiredError as e:
        tool_args = getattr(e, "tool_args", {})
        if prompt_approval(e.tool_name, tool_args, e.message):
            # Human approved: bypass the guard and run the real implementation
            result = _real_send_email(**tool_args)
            return f"APPROVED & EXECUTED: {result}"
        else:
            return f"DENIED: Human rejected {e.tool_name}"
    except GovernanceBlockedError as e:
        return f"BLOCKED: {e}"


@tool
def delete_account(user_id: int) -> str:
    """Permanently delete a user account."""
    try:
        return guarded_tool_call(
            "delete_account", {"user_id": user_id}, policy, _real_delete_account
        )
    except GovernanceBlockedError as e:
        return f"BLOCKED: {e}"
    except ApprovalRequiredError as e:
        return f"APPROVAL_PENDING: {e.tool_name}"


# --- Build agent ------------------------------------------------------------

def build_agent():
    llm = ChatOllama(model="llama3.2:1b", temperature=0)
    tools = [query_data, send_email, delete_account]
    return create_agent(llm, tools)


# --- Run --------------------------------------------------------------------

PROMPTS = [
    "Send a welcome email to newuser@example.com with subject 'Welcome!' and body 'Thanks for signing up.'",
]


def run_prompt(agent, prompt: str) -> None:
    print("\n" + "=" * 60)
    print(f"USER: {prompt}")
    print("=" * 60)

    result = agent.invoke(
        {"messages": [{"role": "user", "content": prompt}]},
        config={"recursion_limit": 10},
    )

    messages = result["messages"]
    final = messages[-1]
    print(f"\nAGENT FINAL RESPONSE:\n{final.content}\n")

    print("--- Tool calls made during this run ---")
    for m in messages:
        if hasattr(m, "tool_calls") and m.tool_calls:
            for tc in m.tool_calls:
                print(f"  -> {tc['name']}({tc['args']})")
        if getattr(m, "type", "") == "tool":
            print(f"     tool result: {m.content}")


    print("\n=== GUARDRAIL VERDICT ===")
    for m in messages:
        if getattr(m, "type", "") == "tool":
            if m.content.startswith("APPROVED"):
                print("✅ Tool was APPROVED by human and executed")
            elif m.content.startswith("DENIED"):
                print("❌ Tool was DENIED by human")
            elif m.content.startswith("BLOCKED"):
                print("🚫 Tool was BLOCKED by policy")
            elif m.content.startswith("SUCCESS"):
                print("✅ Tool was ALLOWED by policy")


if __name__ == "__main__":
    agent = build_agent()
    for prompt in PROMPTS:
        run_prompt(agent, prompt)