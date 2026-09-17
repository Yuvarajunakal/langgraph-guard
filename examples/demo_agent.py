"""
Real LLM demo — uses Ollama (llama3.2:1b) via LangGraph.

The LLM decides which tool to call based on the user's prompt.
The guardrails enforce policy — regardless of what the LLM wants to do.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from langchain_core.tools import tool
from langchain_ollama import ChatOllama
from langchain.agents import create_agent

from langgraph_guard import (
    load_policy,
    guarded_tool_call,
    GovernanceBlockedError,
    ApprovalRequiredError,
)


# --- Load policy ------------------------------------------------------------

POLICY_PATH = Path(__file__).parent / "basic_policy.yaml"
policy = load_policy(POLICY_PATH)


# --- "Real" tool implementations (stubs) ------------------------------------

def _real_query_data(sql: str) -> str:
    return f"[DB] Query executed: {sql} -> 42 rows"


def _real_send_email(to: str, subject: str, body: str) -> str:
    return f"[EMAIL] Sent to {to}: {subject}"


def _real_delete_account(user_id: int) -> str:
    return f"[DB] Account {user_id} deleted"


# --- Guarded tools exposed to LangGraph -------------------------------------

@tool
def query_data(sql: str) -> str:
    """Run a read-only SQL query against the user database."""
    try:
        return guarded_tool_call(
            "query_data", {"sql": sql}, policy, _real_query_data
        )
    except GovernanceBlockedError as e:
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
        # In this simple demo, we auto-approve.
        # The approval flow is in demo_agent_approval.py.
        return (
            f"APPROVAL_PENDING: {e.tool_name} requires human approval "
            f"(args: {getattr(e, 'tool_args', {})}). "
            "In a real deployment, a human would approve or deny."
        )
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


# --- Build the agent --------------------------------------------------------

def build_agent():
    llm = ChatOllama(model="llama3.2:1b", temperature=0)
    tools = [query_data, send_email, delete_account]
    return create_agent(llm, tools)


# --- Demo prompts -----------------------------------------------------------

PROMPTS = [
    "Query the users table to count how many users we have.",
    "Delete the account with user_id 12345.",
]


def run_prompt(agent, prompt: str) -> None:
    print("\n" + "=" * 60)
    print(f"USER: {prompt}")
    print("=" * 60)

    result = agent.invoke(
        {"messages": [{"role": "user", "content": prompt}]},
        config={"recursion_limit": 10},
    )

    # Print the final AI message
    messages = result["messages"]
    final = messages[-1]
    print(f"\nAGENT FINAL RESPONSE:\n{final.content}\n")

    # Print tool calls that happened
    print("--- Tool calls made during this run ---")
    for m in messages:
        if hasattr(m, "tool_calls") and m.tool_calls:
            for tc in m.tool_calls:
                print(f"  -> {tc['name']}({tc['args']})")
        if getattr(m, "type", "") == "tool":
            print(f"     tool result: {m.content}")


if __name__ == "__main__":
    agent = build_agent()
    for prompt in PROMPTS:
        run_prompt(agent, prompt)