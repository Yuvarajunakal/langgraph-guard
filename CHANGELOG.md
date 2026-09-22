# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-09-19

### Added

- **Policy engine** — Load YAML policy files with `load_policy()`. Each tool
  can be set to `allow`, `block`, or `require_approval`.
- **Interceptor** — `guarded_tool_call()` checks every tool call against the
  policy before execution.
- **Custom exceptions** — `GovernanceBlockedError`, `ApprovalRequiredError`,
  and `ToolNotFoundError` for precise error handling.
- **LangGraph integration** — `GuardNode` uses LangGraph's native `interrupt()`
  for true pause/resume human-in-the-loop workflows.
- **CLI approval helper** — `prompt_cli()` for interactive terminal approvals.
- **Hash-chained audit log** — `AuditLog` records every decision with SHA-256
  chaining. `verify()` detects any tampering, and reports the sequence number
  where the chain breaks.
- **Type hints** — Full type annotations with `py.typed` marker for IDE
  autocomplete and static analysis.
- **Demos** — `examples/demo_mock.py` (deterministic), `demo_agent.py` (real
  LLM via Ollama), and `demo_interrupt.py` (interactive human approval).

### Known Limitations

- Audit log verification is local — no distributed consensus.
- LangGraph integration requires `langgraph>=0.2.0` (install with `pip install
  langgraph-guard[langgraph]`).
- No web dashboard yet — audit inspection is via Python API or the CLI.

[0.1.1]: https://github.com/Yuvarajunakal/langgraph-guardrail/releases/tag/v0.1.1