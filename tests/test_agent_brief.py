"""tausik_memory_brief: budgeted playbook, no session, required fields survive."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "harness" / "claude" / "mcp" / "project"))

from agent_brief import build_agent_brief  # noqa: E402
from handlers import handle_tool  # noqa: E402


def _svc(tmp_path: Path, profile: str) -> SimpleNamespace:
    tausik = tmp_path / ".tausik"
    tausik.mkdir(exist_ok=True)
    (tausik / "config.json").write_text(
        json.dumps({"governance_profile": profile}),
        encoding="utf-8",
    )
    return SimpleNamespace(
        tausik_dir=lambda: str(tausik),
        session_start=lambda *a, **k: (_ for _ in ()).throw(
            AssertionError("brief must not start a session")
        ),
        session_extend=lambda *a, **k: (_ for _ in ()).throw(
            AssertionError("brief must not extend a session")
        ),
    )


def test_memory_only_brief_has_required_surface(tmp_path: Path):
    brief = build_agent_brief(_svc(tmp_path, "memory-only"))
    req = brief["required"]
    assert req["governance_profile"] == "memory-only"
    assert req["backlog_policy"] == "B"
    assert req["session_created"] is False
    assert "tausik_memory_add" in req["do"]
    assert "tausik_session_start" in req["dont"]
    assert "tausik_verify" in req["dont"]
    routing = req["decide_vs_memory"]
    assert routing["no_task_before_decide_or_memory"] is True
    assert "owner_choice" in routing and "observed_fact" in routing
    assert "stop_doing" in routing and "weekly_draft" in routing
    assert "optional" in routing["task_slug_on_memory_add"].lower()
    hint = req["next_hint"].lower()
    assert "skip session_start" in hint and "verify" in hint
    blob = json.dumps(brief)
    assert "RENAR" not in blob
    assert "bootstrap-full" not in blob.lower()
    assert "re-bootstrap" not in blob.lower()


def test_brief_overflow_keeps_required_fields(tmp_path: Path):
    brief = build_agent_brief(_svc(tmp_path, "memory-only"), max_bytes=512)
    assert brief["overflow"] is True
    assert "governance_profile" in brief["required"]
    assert brief["required"]["backlog_policy"] == "B"
    assert brief["required"]["do"]
    assert brief["required"]["dont"]
    assert brief["bytes"] >= 512 or brief.get("overflow_reason") == "required_fields_exceed_budget"


def test_handler_does_not_touch_session(tmp_path: Path):
    raw = handle_tool(_svc(tmp_path, "memory-only"), "tausik_memory_brief", {})
    body = json.loads(raw.split("\n⚠")[0] if "\n⚠" in raw else raw)
    assert body["required"]["session_created"] is False
    assert body["required"]["governance_profile"] == "memory-only"


def test_full_profile_brief_does_not_impersonate_memory_only(tmp_path: Path):
    brief = build_agent_brief(_svc(tmp_path, "full"))
    assert brief["required"]["governance_profile"] == "full"
    assert brief["required"]["do"] == []
    assert brief["required"]["session_created"] is False


def test_skill_says_call_agent_brief_first():
    text = (ROOT / "harness" / "skills" / "tausik-memory" / "SKILL.md").read_text(encoding="utf-8")
    assert "tausik_memory_brief" in text
    assert "First call" in text
