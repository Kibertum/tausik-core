"""A ROADMAP.md reissued by the generator does not refuse a fileless close.

A status change (task unblock) rewrote ROADMAP.md, and `task done --no-file-changes`
then refused because git saw the file dirty: the framework's own output blocked the
close it had just caused. Only an exact match with the generator is excused.
"""

from __future__ import annotations

import os
import sys
import types

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

import gate_verify_first  # noqa: E402
import state_triggers  # noqa: E402

MARK = state_triggers._ROADMAP_MARK


def _setup(tmp_path, monkeypatch, on_disk, rendered):
    (tmp_path / "ROADMAP.md").write_text(on_disk, encoding="utf-8", newline="")
    fake = types.ModuleType("release_roadmap")
    fake.render = lambda _conn: rendered
    monkeypatch.setitem(sys.modules, "release_roadmap", fake)
    return types.SimpleNamespace(be=types.SimpleNamespace(_conn=None))


def test_the_generators_own_output_is_excused(tmp_path, monkeypatch):
    text = f"{MARK} -->\n# Roadmap\ncounters 12\n"
    svc = _setup(tmp_path, monkeypatch, text, text)
    assert gate_verify_first.roadmap_is_generated(svc, str(tmp_path)) is True


def test_a_hand_edit_is_still_work(tmp_path, monkeypatch):
    """NEGATIVE: one changed line is no longer the generator's output."""
    svc = _setup(
        tmp_path,
        monkeypatch,
        f"{MARK} -->\n# Roadmap\nhand edit\n",
        f"{MARK} -->\n# Roadmap\ncounters 12\n",
    )
    assert gate_verify_first.roadmap_is_generated(svc, str(tmp_path)) is False


def test_a_file_without_the_generator_mark_is_never_excused(tmp_path, monkeypatch):
    svc = _setup(
        tmp_path, monkeypatch, "# Roadmap written by hand\n", "# Roadmap written by hand\n"
    )
    assert gate_verify_first.roadmap_is_generated(svc, str(tmp_path)) is False
