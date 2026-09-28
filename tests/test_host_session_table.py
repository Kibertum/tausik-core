"""The host-session table in docs/*/hooks.md agrees with what bootstrap deploys.

Read from the profiles, not copied: a host claimed as `hook` must have both
session events in its hook source, a host claimed as `plugin` must carry the
events in the plugin, and a host claimed as `cli` must have neither — no dead
hook is written for a host that has no such event (1.10, story E).
"""

from __future__ import annotations

from pathlib import Path

import os
import re
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "bootstrap"))

from bootstrap_config import SCAFFOLD_IDES  # noqa: E402
from bootstrap_hooks import build_hooks_dict  # noqa: E402

_ROW = re.compile(r"^\| (\w+) \| (hook|plugin|cli) \| (hook|plugin|cli) \|", re.M)


def _table(lang: str) -> dict[str, tuple[str, str]]:
    text = Path(os.path.join(REPO, "docs", lang, "hooks.md")).read_text(encoding="utf-8")
    block = text.split("<!-- host-session-table -->")[1].split("<!-- /host-session-table -->")[0]
    return {m.group(1): (m.group(2), m.group(3)) for m in _ROW.finditer(block)}


def _read(*parts: str) -> str:
    return open(os.path.join(REPO, *parts), encoding="utf-8").read()


@pytest.mark.parametrize("lang", ["ru", "en"])
def test_every_host_has_a_row(lang):
    assert set(_table(lang)) == set(SCAFFOLD_IDES)


@pytest.mark.parametrize("lang", ["ru", "en"])
def test_each_claim_matches_the_profile(lang):
    shared = build_hooks_dict(lambda *a, **k: "x")
    plugin = _read("harness", "opencode", "plugins", "tausik-qg0.js")
    qwen = _read("bootstrap", "bootstrap_qwen.py")
    codex = _read("bootstrap", "bootstrap_codex.py")
    for host, (opens, closes) in _table(lang).items():
        if opens == "hook":
            # Claude, Codex and (since qwen-hooks-are-a-second-copy-of-the-
            # declaration) Qwen all build from the one shared declaration.
            assert host in ("claude", "codex", "qwen"), host
            assert {"SessionStart", "SessionEnd"} <= set(shared), host
            if host == "codex":
                assert "build_hooks_dict" in codex
            if host == "qwen":
                assert "build_hooks_dict" in qwen
        elif opens == "plugin":
            assert host == "opencode"
            assert '"session.created"' in plugin and '"session.deleted"' in plugin
        else:
            # NEGATIVE: a `cli` host gets no dead session hook from bootstrap.
            src = (
                _read("bootstrap", f"bootstrap_{host}.py")
                if os.path.exists(os.path.join(REPO, "bootstrap", f"bootstrap_{host}.py"))
                else ""
            )
            assert "SessionStart" not in src and "SessionEnd" not in src, host
