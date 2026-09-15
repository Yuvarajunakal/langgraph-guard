import pytest

from src.langgraph_guard import load_policy, PolicyError


def test_loads_valid_policy():
    policy = load_policy("examples/basic_policy.yaml")
    assert policy["query_data"].action == "allow"
    assert policy["send_email"].action == "require_approval"
    assert policy["delete_account"].action == "block"
    assert policy["delete_account"].reason != ""


def test_missing_file_raises():
    with pytest.raises(PolicyError, match="not found"):
        load_policy("examples/does_not_exist.yaml")


def test_invalid_action_raises():
    with pytest.raises(PolicyError, match="must be"):
        load_policy("examples/bad_policy.yaml")