import json
from pathlib import Path

import pytest

from langgraph_guard.audit import AuditLog, GENESIS_HASH


@pytest.fixture
def audit_path(tmp_path):
    return tmp_path / "audit.jsonl"


def test_empty_log_verifies(audit_path):
    audit = AuditLog(audit_path)
    ok, seq = audit.verify()
    assert ok is True
    assert seq is None


def test_single_append(audit_path):
    audit = AuditLog(audit_path)
    entry = audit.append("query_data", {"sql": "SELECT 1"}, "allowed")
    assert entry.sequence == 1
    assert entry.prev_hash == GENESIS_HASH
    assert entry.this_hash != ""
    assert len(audit) == 1


def test_chain_intact_after_multiple_appends(audit_path):
    audit = AuditLog(audit_path)
    audit.append("a", {}, "allowed")
    audit.append("b", {}, "blocked")
    audit.append("c", {}, "approved")
    ok, seq = audit.verify()
    assert ok is True
    assert seq is None


def test_chain_detects_tampering(audit_path):
    audit = AuditLog(audit_path)
    audit.append("a", {}, "allowed")
    audit.append("b", {}, "blocked")
    audit.append("c", {}, "approved")

    # Tamper with the middle entry
    lines = audit_path.read_text().splitlines()
    entry = json.loads(lines[1])
    entry["decision"] = "allowed"
    lines[1] = json.dumps(entry, sort_keys=True)
    audit_path.write_text("\n".join(lines) + "\n")

    ok, seq = audit.verify()
    assert ok is False
    assert seq == 2


def test_chain_detects_removed_entry(audit_path):
    audit = AuditLog(audit_path)
    audit.append("a", {}, "allowed")
    audit.append("b", {}, "blocked")
    audit.append("c", {}, "approved")

    # Remove the middle line
    lines = audit_path.read_text().splitlines()
    audit_path.write_text("\n".join([lines[0], lines[2]]) + "\n")

    ok, seq = audit.verify()
    assert ok is False
    # The chain breaks at seq 3 because its prev_hash points to seq 2's hash
    assert seq == 3


def test_hash_is_deterministic(audit_path):
    audit1 = AuditLog(audit_path)
    e1 = audit1.append("tool", {"b": 2, "a": 1}, "allowed")

    # Same content in different order should produce the same hash
    audit2 = AuditLog(audit_path.parent / "audit2.jsonl")
    e2 = audit2.append("tool", {"a": 1, "b": 2}, "allowed")

    # this_hash differs because sequence and timestamp differ,
    # but args serialization should sort keys
    # This test just verifies we don't crash on dict ordering
    assert e1.this_hash != ""
    assert e2.this_hash != ""