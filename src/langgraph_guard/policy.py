"""
Policy loader for langgraph-guard.

Reads a YAML policy file and returns a structured dictionary of tool policies.
"""

from pathlib import Path
from dataclasses import dataclass

import yaml


class PolicyError(Exception):
    """Raised when a policy file is malformed or invalid."""
    pass


@dataclass
class ToolPolicy:
    """A single tool's policy."""
    action: str          # "allow" | "block" | "require_approval"
    reason: str = ""
    conditions: list = None


def load_policy(path: str) -> dict[str, ToolPolicy]:
    """
    Load a policy YAML file and return a mapping of tool name -> ToolPolicy.
    """
    policy_path = Path(path)

    if not policy_path.exists():
        raise PolicyError(f"Policy file not found: {path}")

    try:
        raw = yaml.safe_load(policy_path.read_text())
    except yaml.YAMLError as e:
        raise PolicyError(f"Invalid YAML in {path}: {e}")

    if not isinstance(raw, dict):
        raise PolicyError("Policy must be a YAML mapping at the top level")

    tools_raw = raw.get("tools", {})
    if not isinstance(tools_raw, dict):
        raise PolicyError("'tools' must be a mapping")

    policies: dict[str, ToolPolicy] = {}

    for name, cfg in tools_raw.items():
        if not isinstance(cfg, dict):
            raise PolicyError(f"Tool '{name}': config must be a mapping")

        action = cfg.get("action")
        if action not in ("allow", "block", "require_approval"):
            raise PolicyError(
                f"Tool '{name}': action must be 'allow', 'block', or "
                f"'require_approval' (got {action!r})"
            )

        policies[name] = ToolPolicy(
            action=action,
            reason=cfg.get("reason", ""),
            conditions=cfg.get("conditions"),
        )

    return policies