"""memory-only advertise: SENAR write-path annotated/deferred; full path unchanged."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from memory_only_backlog import (
    DEFERRED_TOOLS,
    annotate_advertise,
    advertise_do_dont,
    measure_advertise_bytes,
)


def _tools() -> list[dict]:
    return [
        {
            "name": "tausik_session_start",
            "description": "Start a new work session",
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "tausik_verify",
            "description": "Run verification gates",
            # Realistic eager schema: defer must shrink advertise (AC-4).
            "inputSchema": {
                "type": "object",
                "properties": {
                    "task_slug": {
                        "type": "string",
                        "description": "Task slug to verify against.",
                    },
                    "scope": {
                        "type": "string",
                        "enum": [
                            "lightweight",
                            "standard",
                            "high",
                            "critical",
                            "manual",
                        ],
                        "description": "SENAR Rule 5 verification tier.",
                    },
                    "trigger": {
                        "type": "string",
                        "enum": ["verify", "task-done"],
                        "description": "Gate trigger to run.",
                    },
                },
            },
        },
        {
            "name": "tausik_task_done",
            "description": "Complete task",
            "inputSchema": {
                "type": "object",
                "properties": {"slug": {"type": "string"}},
                "required": ["slug"],
            },
        },
        {
            "name": "tausik_memory_add",
            "description": "Save project memory",
            "inputSchema": {
                "type": "object",
                "properties": {"title": {"type": "string"}},
                "required": ["title"],
            },
        },
    ]


def _svc(tmp_path: Path, profile: str | None) -> SimpleNamespace:
    if profile is not None:
        (tmp_path / "config.json").write_text(
            json.dumps({"governance_profile": profile}),
            encoding="utf-8",
        )
    return SimpleNamespace(tausik_dir=lambda: str(tmp_path))


def test_memory_only_annotates_and_defers_senar_write_path(tmp_path: Path):
    before = measure_advertise_bytes(_tools())
    out = annotate_advertise(_tools(), _svc(tmp_path, "memory-only"))
    after = measure_advertise_bytes(out)
    by_name = {t["name"]: t for t in out}
    for name in DEFERRED_TOOLS:
        assert by_name[name]["description"].startswith("[profile=disabled]")
        assert by_name[name]["inputSchema"].get("properties") != {}
        assert by_name[name]["inputSchema"].get("additionalProperties") is True
    assert "without gates" in by_name["tausik_task_done"]["description"]
    assert by_name["tausik_memory_add"]["description"] == "Save project memory"
    assert after <= before, (
        f"eager advertise should not grow under memory-only annotate "
        f"(before={before}, after={after})"
    )


def test_full_profile_advertise_is_byte_identical(tmp_path: Path):
    tools = _tools()
    out = annotate_advertise(tools, _svc(tmp_path, "full"))
    assert out == tools
    assert measure_advertise_bytes(out) == measure_advertise_bytes(tools)


def test_advertise_do_dont_matches_deferred_and_light_sets():
    surface = advertise_do_dont()
    assert surface["backlog_policy"] == "B"
    assert set(surface["dont"]) == set(DEFERRED_TOOLS)
    assert "tausik_memory_add" in surface["do"]
    assert "tausik_session_start" not in surface["do"]
