# langgraph-guard

Policy enforcement and guardrails for LangGraph AI agents.

Define what your agent can and can't do in a simple YAML file. Every tool call gets checked before it executes. Dangerous actions get blocked. Suspicious actions get escalated for human approval.

## Install

```bash
pip install langgraph-guard
```

## Quick Start

Create a policy file:

```yaml
version: "1"
tools:
  query_data:
    action: allow
  send_email:
    action: require_approval
  delete_account:
    action: block
```

Load it in your code:

```python
from langgraph_guard import load_policy

policy = load_policy("policy.yaml")

print(policy["query_data"].action)       # "allow"
print(policy["delete_account"].action)   # "block"
```

## Status

Alpha. Under active development.

## License

MIT
