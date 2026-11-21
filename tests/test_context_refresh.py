"""Host-neutral context refresh requires an explicit target and respects ownership."""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import context_refresh as cr

_MANAGED = "# x\n\n<!-- DYNAMIC:START -->\nold\n<!-- DYNAMIC:END -->\n"
_HAND = "# AGENTS.md\n\nHand maintained. No markers.\n"


def test_no_target_is_target_required(tmp_path):
    out = cr.refresh_target(str(tmp_path), None, "NEW")
    assert out.status == "target_required"
    assert not cr.outcome_is_success(out)


def test_hand_maintained_agents_never_written(tmp_path):
    path = tmp_path / "AGENTS.md"
    path.write_text(_HAND, encoding="utf-8")
    out = cr.refresh_target(str(tmp_path), "agents", "NEW STATE")
    assert out.status == "hand_maintained"
    assert path.read_text(encoding="utf-8") == _HAND
    assert json.loads(cr.dump_outcome(out))["status"] == "hand_maintained"


def test_claude_target_updates_managed_file(tmp_path):
    path = tmp_path / "CLAUDE.md"
    path.write_text(_MANAGED, encoding="utf-8")
    out = cr.refresh_target(str(tmp_path), "claude", "NEW STATE")
    assert out.status == "updated"
    assert "NEW STATE" in path.read_text(encoding="utf-8")


def test_unknown_target_refused(tmp_path):
    out = cr.refresh_target(str(tmp_path), "not-a-host", "x")
    assert out.status == "unknown_target"


def test_ownership_classifier(tmp_path):
    managed = tmp_path / "CLAUDE.md"
    managed.write_text(_MANAGED, encoding="utf-8")
    hand = tmp_path / "AGENTS.md"
    hand.write_text(_HAND, encoding="utf-8")
    assert cr.ownership_of(str(managed)) == "managed"
    assert cr.ownership_of(str(hand)) == "hand_maintained"
    assert cr.ownership_of(str(tmp_path / "missing.md")) == "missing"
