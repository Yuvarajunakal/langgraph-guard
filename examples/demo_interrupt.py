"""
LangGraph-native demo using interrupt().

This is the real pattern for production guardrails:
- The graph pauses when an approval is required
- State is saved to a checkpointer
- The caller resumes with Command(resume=True/False)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command
from typing import TypedDict

from langgraph_guard import load_policy, prompt_cli
from langgraph_guard.integrations.langgraph import GuardNode


# --- Policy -----------------------------------------------------------------

POLICY_PATH = Path(__file__).parent / "basic_policy.yaml"
policy = load_policy(POLICY_PATH)
guard = GuardNode(policy)


# --- "Real" tool implementations --------------------------------------------

def _real_send_email(to: str, subject: str, body: str) -> str:
    return f"Email sent to {to} with subject '{subject}'"


# --- Graph state ------------------------------------------------------------

class State(TypedDict):
    tool_name: str
    args: dict
    result: str


# --- The guarded node -------------------------------------------------------

def send_email_node(state: State) -> State:
    """Node that runs the guarded send_email tool."""
    result = guard.run(
        state["tool_name"],
        state["args"],
        _real_send_email,
    )
    return {"result": result}


# --- Build the graph --------------------------------------------------------

def build_graph():
    builder = StateGraph(State)
    builder.add_node("send_email", send_email_node)
    builder.add_edge(START, "send_email")
    builder.add_edge("send_email", END)
    checkpointer = MemorySaver()
    return builder.compile(checkpointer=checkpointer)


# --- Run the demo -----------------------------------------------------------

def run_scenario() -> None:
    graph = build_graph()
    config = {"configurable": {"thread_id": "demo-interactive"}}

    initial_state = {
        "tool_name": "send_email",
        "args": {
            "to": "newuser@example.com",
            "subject": "Welcome!",
            "body": "Thanks for signing up.",
        },
        "result": "",
    }

    print("\n" + "=" * 60)
    print("INTERACTIVE DEMO")
    print("=" * 60)

    # First pass: pauses at interrupt()
    result = graph.invoke(initial_state, config=config)

    interrupts = result.get("__interrupt__", [])
    if not interrupts:
        print(f"\nNo interrupt. Result: {result.get('result')}")
        return

    payload = interrupts[0].value

    # Real human prompt
    approved = prompt_cli(
        payload["tool_name"],
        payload["args"],
        payload.get("reason", ""),
    )

    # Resume with the actual decision
    final = graph.invoke(
        Command(resume=approved),
        config=config,
    )
    print(f"\nFinal result: {final.get('result')}")

if __name__ == "__main__":
    run_scenario()