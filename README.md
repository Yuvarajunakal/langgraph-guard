# langgraph-guard

Policy enforcement and guardrails for LangGraph AI agents.

Define what your agent can and can't do in a simple YAML file. Every tool call gets checked before it executes. Dangerous actions get blocked. Suspicious actions get escalated for human approval. Every decision is recorded in a tamper-evident audit log.

## Why

AI agents can now take real actions — send emails, query databases, call APIs, delete accounts. Without guardrails, a single misaligned decision can cost real money or leak real data. `langgraph-guard` gives you a single chokepoint where every action is checked against your rules, paused for human approval when needed, and cryptographically logged.

## Install

```bash
pip install langgraph-guard
```

For LangGraph integration (uses `interrupt()` for human-in-the-loop):

```bash
pip install "langgraph-guard[langgraph]"
```

Requires Python 3.10+.

## Quick Start

**1. Create a policy file** (`policy.yaml`):

```yaml
version: "1"
tools:
  query_data:
    action: allow
  send_email:
    action: require_approval
    reason: "External emails need human review"
  delete_account:
    action: block
    reason: "Account deletion is forbidden for autonomous agents"
```

**2. Load it and check tool calls:**

```python
from langgraph_guard import load_policy, guarded_tool_call, GovernanceBlockedError

policy = load_policy("policy.yaml")

try:
    result = guarded_tool_call(
        "delete_account",
        {"user_id": 123},
        policy,
        my_delete_function,
    )
except GovernanceBlockedError as e:
    print(f"Blocked: {e}")
    # -> Blocked: Tool 'delete_account' is blocked by policy: Account deletion...
```

## LangGraph Integration

Use `GuardNode` inside any LangGraph graph for native human-in-the-loop:

```python
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from langgraph_guard import load_policy, prompt_cli
from langgraph_guard.integrations.langgraph import GuardNode

policy = load_policy("policy.yaml")
guard = GuardNode(policy)

def send_email_node(state):
    return {"result": guard.run("send_email", state["args"], _real_send_email)}

builder = StateGraph(State)
builder.add_node("send_email", send_email_node)
builder.add_edge(START, "send_email")
builder.add_edge("send_email", END)

graph = builder.compile(checkpointer=MemorySaver())
config = {"configurable": {"thread_id": "user-1"}}

# First pass — pauses at interrupt()
result = graph.invoke(initial_state, config=config)

# Human approves
payload = result["__interrupt__"][0].value
approved = prompt_cli(payload["tool_name"], payload["args"], payload.get("reason", ""))

# Resume the graph
final = graph.invoke(Command(resume=approved), config=config)
```

The graph pauses at the exact tool call, saves state to the checkpointer, and resumes seamlessly with the human's decision.

## Audit Trail

Every decision is recorded in a hash-chained JSONL log. Tampering with any entry breaks the chain and is detected.

```python
from langgraph_guard import AuditLog
from langgraph_guard.integrations.langgraph import GuardNode

audit = AuditLog("audit.jsonl")
guard = GuardNode(policy, audit=audit)

# After running your agent:
ok, failed_at = audit.verify()
assert ok, f"Tampering detected at sequence {failed_at}"

for entry in audit.tail(10):
    print(f"{entry.sequence} | {entry.tool_name} | {entry.decision}")
```

Each entry stores its own SHA-256 hash and the hash of the previous entry. If anyone edits, removes, or reorders entries, `verify()` reports the exact sequence number where the chain breaks.

## Policy Schema

```yaml
version: "1"

tools:
  <tool_name>:
    action: allow | block | require_approval
    reason: "optional explanation shown to humans and logs"
```

- **`allow`** — the tool runs immediately
- **`block`** — the tool never runs; the agent receives a `BLOCKED` message
- **`require_approval`** — the graph pauses; a human decides, then the graph resumes

## API Reference

### `load_policy(path: str) -> dict[str, ToolPolicy]`

Load a YAML policy file. Raises `PolicyError` if malformed.

### `guarded_tool_call(tool_name, args, policy, tool_fn) -> Any`

Execute a tool following policy. Raises:
- `GovernanceBlockedError` if the policy says `block`
- `ApprovalRequiredError` if the policy says `require_approval`
- `ToolNotFoundError` if the tool isn't in the policy

### `GuardNode(policy, audit=None)`

LangGraph integration. `.run(tool_name, args, tool_fn)` behaves like `guarded_tool_call` but uses `interrupt()` for approvals.

### `AuditLog(path)`

Hash-chained audit log. Methods:
- `.append(tool_name, args, decision, reason="")` — write an entry
- `.verify() -> (bool, Optional[int])` — check integrity
- `.tail(n=10) -> list[AuditEntry]` — recent entries

### `prompt_cli(tool_name, args, reason="") -> bool`

Interactive terminal approval prompt.

## Demos

- `examples/demo_mock.py` — deterministic, shows all three branches in 10 seconds
- `examples/demo_agent.py` — real LLM (Ollama) decides which tool to call
- `examples/demo_interrupt.py` — full interrupt/resume flow with audit logging

## Development

```bash
git clone https://github.com/Yuvarajunakal/langgraph-guard.git
cd langgraph-guard
python -m venv venv
venv\Scripts\activate    # Windows
pip install -e ".[dev]"
pytest tests/ -v
```

## Status

**Alpha** — the core API is stable, but expect additions. See [CHANGELOG.md](CHANGELOG.md) for what's shipped.

## License

MIT — see [LICENSE](LICENSE).