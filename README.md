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

## Live Demo

The guardrails enforce three outcomes: **allow**, **require approval**, and **block**.

Running `examples/demo_mock.py`:

```
============================================================
SCENARIO 1: Agent queries the database (allowed)
============================================================

  Agent receives: SUCCESS: [DB] Query executed: SELECT COUNT(*) FROM users -> 42 rows

============================================================
SCENARIO 2: Agent sends an email (requires approval)
============================================================

  ⚠️  APPROVAL REQUIRED
     Tool:   send_email
     Args:   {'to': 'newuser@example.com', 'subject': 'Welcome!', 'body': 'Thanks for signing up.'}
     Reason: External emails need human review

     Approve? (y/n): y

  Agent receives: APPROVED & EXECUTED: [EMAIL] Sent to newuser@example.com: Welcome!

============================================================
SCENARIO 3: Agent tries to delete an account (blocked)
============================================================

  Agent receives: BLOCKED: Tool 'delete_account' is blocked by policy: Account deletion is forbidden for autonomous agents
```

### With a Real LLM (Ollama)

The same behavior works with a real model deciding what to call. Running `examples/demo_agent_approval.py`:

```
============================================================
USER: Send a welcome email to newuser@example.com with subject 'Welcome!' and body 'Thanks for signing up.'
============================================================

  ⚠️  APPROVAL REQUIRED
     Tool:   send_email
     Args:   {'to': 'newuser@example.com', 'subject': 'Welcome!', 'body': 'Thanks for signing up.'}
     Reason: External emails need human review

     Approve? (y/n): y

--- Tool calls made during this run ---
  -> send_email({'subject': 'Welcome!', 'body': 'Thanks for signing up.', 'to': 'newuser@example.com'})
     tool result: APPROVED & EXECUTED: Email successfully sent to newuser@example.com with subject 'Welcome!'. Confirmation ID: MSG-70971

=== GUARDRAIL VERDICT ===
✅ Tool was APPROVED by human and executed
```

The model wanted to send the email. The policy paused it. A human approved it. The email went out. That's the whole product.

## Status

Alpha. Under active development.

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.