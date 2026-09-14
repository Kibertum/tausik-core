"""The version stamp in the product's CLAUDE.md names its owner (GitLab #5).

`tausik update-claudemd` writes `Session … | Branch … | <label>: 1.9.0` into the
PRODUCT's CLAUDE.md and AGENTS.md, one line above the product's own tasks and
next to its branch. With the label `Version:` the number was read as the
product's version — measured on a consumer at 0.1.0 whose CLAUDE.md declared
1.8.0, and its owner read it exactly so. The label now names the owner of the
number: `TAUSIK: 1.9.0`.

The ticket's second half — two copies of the format, CLI and MCP — was closed
before this test by `claudemd_state.build_dynamic_state`, the one producer both
callers import; the test pins that too, so the label cannot fork again.
"""

from __future__ import annotations

import ast
import os
import re
import sys

import pytest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for _p in (
    os.path.join(_ROOT, "scripts"),
    os.path.join(_ROOT, "harness", "claude", "mcp", "project"),
):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import claudemd_state as cs  # noqa: E402
from project_backend import SQLiteBackend  # noqa: E402
from project_service import ProjectService  # noqa: E402

CROSSCUTTING_SCOPE = ["scripts/claudemd_state.py", "docs/"]

_BARE_VERSION = re.compile(r"(?<![A-Za-z])Version:")


@pytest.fixture
def consumer(tmp_path, monkeypatch):
    """The ticket's measurement: a consumer project at 0.1.0 with TAUSIK inside it."""
    (tmp_path / ".tausik").mkdir()
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "tg-archive"\nversion = "0.1.0"\n', encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)
    svc = ProjectService(SQLiteBackend(str(tmp_path / ".tausik" / "tausik.db")))
    yield tmp_path, svc
    svc.be.close()


def _state_line(block: str) -> str:
    return next(ln for ln in block.splitlines() if ln.startswith("Session:"))


def test_the_stamp_names_the_framework_as_the_owner_of_the_number(consumer):
    tmp_path, svc = consumer
    line = _state_line(cs.build_dynamic_state(svc, str(tmp_path)))
    assert f"TAUSIK: {cs.resolve_version()}" in line, line
    assert "0.1.0" not in line, "the product's own version has no business in this stamp"


def test_the_stamp_carries_no_bare_version_label(consumer):
    """NEGATIVE: the defect's form. `Version: 1.9.0` in a product document reads as
    the product's version; the label must not come back in the next reformat."""
    tmp_path, svc = consumer
    line = _state_line(cs.build_dynamic_state(svc, str(tmp_path)))
    assert not _BARE_VERSION.search(line), line
    # The check itself bites: the pre-fix line is refused by the same regex.
    assert _BARE_VERSION.search("Session: #60 (active) | Branch: main | Version: 1.8.0")


def test_the_label_is_one_constant_and_the_format_has_one_producer():
    """Both callers import build_dynamic_state; neither spells the stamp itself."""
    assert cs.STAMP_LABEL == "TAUSIK"
    callers = [
        os.path.join(_ROOT, "scripts", "project_cli_extra.py"),
        os.path.join(_ROOT, "harness", "claude", "mcp", "project", "handlers_skill.py"),
    ]
    for path in callers:
        src = open(path, encoding="utf-8").read()
        assert "build_dynamic_state" in src, f"{path} no longer uses the one producer"
        spelled = [
            part.value
            for n in ast.walk(ast.parse(src))
            if isinstance(n, ast.JoinedStr)
            for part in n.values
            if isinstance(part, ast.Constant) and "Branch:" in str(part.value)
        ]
        assert spelled == [], (
            f"{path} spells the stamp itself — a second copy of the rule: {spelled}"
        )
    tree = ast.parse(
        open(os.path.join(_ROOT, "scripts", "claudemd_state.py"), encoding="utf-8").read()
    )
    literal_labels = [
        n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and n.value == "Version: "
    ]
    assert literal_labels == [], "the producer spells `Version: ` somewhere besides the constant"


@pytest.mark.parametrize("lang", ["en", "ru"])
def test_the_skill_pattern_docs_show_the_same_label(lang):
    text = open(os.path.join(_ROOT, "docs", lang, "skill-patterns.md"), encoding="utf-8").read()
    assert "| TAUSIK: {version}" in text
    assert "| Version: {version}" not in text
