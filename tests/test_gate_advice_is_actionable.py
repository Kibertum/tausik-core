"""A gate that prints "run X" must be telling the truth: running X fixes it.

check_docs advised `gen_doc_constants.py` for months while that command left the
README counts untouched, so following the advice kept the gate red. This is the
regression guard against a gate whose remediation does not remediate.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts", "hooks"))

import gen_doc_constants  # noqa: E402

PAYLOAD = {
    "schema_version": 1,
    "tausik_version": "1.6.0",
    "test_count": 4540,
    "stacks_count": 25,
    "hooks_count": 21,
    "review_agents_count": 6,
    "mcp_main_tools": 124,
    "mcp_project_tools": 117,
    "mcp_brain_tools": 7,
}


def test_check_docs_advises_the_command_that_actually_fixes_it():
    """The hint string must name the write-capable command, not the old one."""
    hint = Path(__file__).parent.parent / "scripts" / "hooks" / "check_docs.py"
    src = hint.read_text(encoding="utf-8")
    assert "gen_doc_constants.py --write" in src, (
        "check_docs must advise the command that repairs cross-file drift"
    )


def test_advised_command_turns_a_red_check_green(tmp_path, monkeypatch):
    """The whole point, end to end: drift -> advised command -> green.

    build_constants_doc is stubbed so the fixture does not need the full repo;
    everything else (the writer, the re-check) is the real code path.
    """
    monkeypatch.setattr(gen_doc_constants, "build_constants_doc", lambda _root: dict(PAYLOAD))

    (tmp_path / "docs" / "_generated").mkdir(parents=True)
    # constants.json starts stale, README starts drifted on every count form.
    (tmp_path / "docs" / "_generated" / "constants.json").write_text("{}", encoding="utf-8")
    (tmp_path / "README.md").write_text(
        "[![1 tests](https://x/badge/tests-1-brightgreen.svg)](#p)\n"
        "[![v1.5.0](https://x/badge/version-v1.5.0-blue.svg)](#r)\n"
        "- **1 tests** across 99 stacks.\n",
        encoding="utf-8",
    )

    # Before: the gate is red.
    assert gen_doc_constants.run_main(tmp_path, check=True) == 1

    # Run exactly what the gate advises.
    rc = gen_doc_constants.run_write(tmp_path)

    # After: green, with no hand edits in between.
    assert rc == 0, "the advised command must leave --check green"
    text = (tmp_path / "README.md").read_text(encoding="utf-8")
    assert "tests-4540-brightgreen" in text
    assert "**4540 tests**" in text
    assert "99 stacks" not in text and "25 stacks" in text
    assert "v1.6.0" in text


def test_write_is_idempotent_end_to_end(tmp_path, monkeypatch):
    monkeypatch.setattr(gen_doc_constants, "build_constants_doc", lambda _root: dict(PAYLOAD))
    (tmp_path / "docs" / "_generated").mkdir(parents=True)
    (tmp_path / "docs" / "_generated" / "constants.json").write_text("{}", encoding="utf-8")
    (tmp_path / "README.md").write_text(
        "![1 tests](https://x/tests-1-brightgreen.svg)\n", encoding="utf-8"
    )
    assert gen_doc_constants.run_write(tmp_path) == 0
    before = (tmp_path / "README.md").read_text(encoding="utf-8")
    assert gen_doc_constants.run_write(tmp_path) == 0
    assert (tmp_path / "README.md").read_text(encoding="utf-8") == before
