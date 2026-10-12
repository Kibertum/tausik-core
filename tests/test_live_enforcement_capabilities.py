"""Evidence validation and real file observations, not a claim of live host proof."""

import json
from datetime import datetime, timezone

import pytest

from enforcement_evidence import VERSION, live_enforcement_status, profile_fingerprint
from enforcement_probe import capture_case


def evidence(tmp_path):
    profile = tmp_path / ".codex"
    profile.mkdir()
    (profile / "hooks.json").write_text(
        json.dumps(
            {"hooks": {"PreToolUse": [{"hooks": [{"type": "command", "command": "test"}]}]}}
        ),
        encoding="utf-8",
    )
    same, changed = "a" * 64, "b" * 64
    cases = {
        n: {
            "result": "completed",
            "denied": n != "allowed",
            "hook_fired": True,
            "before_sha256": same,
            "after_sha256": changed if n == "allowed" else same,
        }
        for n in ("no_task", "out_of_scope", "allowed")
    }
    return {
        "schema_version": 1,
        "mode": "live_host",
        "host": "codex",
        "host_version": "test",
        "framework_version": VERSION,
        "profile_sha256": profile_fingerprint(profile),
        "trusted": True,
        "observed_at": "2026-10-01T00:00:00Z",
        "routes": {"patch": cases},
    }


def save(root, data):
    path = root / ".tausik/enforcement/codex.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def read(root):
    return live_enforcement_status(
        str(root), "codex", host_version="test", now=datetime(2026, 10, 1, 1, tzinfo=timezone.utc)
    )


def test_installed_is_not_observed_and_routes_are_independent(tmp_path):
    data = evidence(tmp_path)
    assert read(tmp_path)["installed"] is True
    assert read(tmp_path)["routes"]["patch"] == "unknown"
    save(tmp_path, data)
    result = read(tmp_path)
    assert result["routes"] == {
        "patch": "local_report_passed",
        "shell": "unknown",
        "nested": "unknown",
    }
    assert result["hook_fired"] is True
    assert result["status"] == "incomplete_local_report"
    assert result["attestation"] == "local_self_reported"
    assert result["proof"] is False


def test_deployed_hook_change_invalidates_old_probe(tmp_path):
    data = evidence(tmp_path)
    hook = tmp_path / ".codex/scripts/hooks/task_gate.py"
    hook.parent.mkdir(parents=True)
    hook.write_text("old", encoding="utf-8")
    data["profile_sha256"] = profile_fingerprint(tmp_path / ".codex")
    save(tmp_path, data)
    assert read(tmp_path)["routes"]["patch"] == "local_report_passed"

    hook.write_text("new", encoding="utf-8")
    result = read(tmp_path)
    assert result["status"] == "stale_or_unmatched"
    assert all(value == "unknown" for value in result["routes"].values())


@pytest.mark.parametrize(
    "field,value",
    [
        ("mode", "fixture"),
        ("trusted", False),
        ("profile_sha256", "old"),
        ("framework_version", "old"),
        ("host_version", "old"),
        ("observed_at", "2026-09-01T00:00:00Z"),
        ("observed_at", "invalid"),
    ],
)
def test_untrusted_stale_or_synthetic_never_proves_denial(tmp_path, field, value):
    data = evidence(tmp_path)
    data[field] = value
    save(tmp_path, data)
    assert all(v == "unknown" for v in read(tmp_path)["routes"].values())


@pytest.mark.parametrize(
    "change,expected",
    [
        ({"result": "timeout"}, "unknown"),
        ({"hook_fired": False}, "unknown"),
        ({"denied": False}, "unknown"),
        ({"after_sha256": "b" * 64}, "local_report_failed"),
        ({"before_sha256": "not-a-hash"}, "unknown"),
    ],
)
def test_failed_invocation_is_not_a_denial(tmp_path, change, expected):
    data = evidence(tmp_path)
    data["routes"]["patch"]["no_task"].update(change)
    save(tmp_path, data)
    assert read(tmp_path)["routes"]["patch"] == expected


def test_capture_observes_actual_mutation_and_error(tmp_path):
    with pytest.raises(ValueError):
        capture_case(tmp_path, "shell", "allowed", lambda p: {})
    (tmp_path / ".tausik-probe-root").touch()

    def write(path):
        path.write_text("probe", encoding="utf-8")
        return {"denied": False, "hook_fired": False}

    result = capture_case(tmp_path, "shell", "allowed", write)
    assert result["before_sha256"] != result["after_sha256"]

    def timeout(path):
        raise TimeoutError("host did not answer")

    result = capture_case(tmp_path, "nested", "no_task", timeout)
    assert result["result"] == "failed" and result["denied"] is None
