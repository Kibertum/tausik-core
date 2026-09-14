"""The agent quickstart names only what exists, in both languages.

Written for an agent reading it first, so every hard fact on the page is held
to the code rather than to memory: the hosts it lists are exactly the ones
bootstrap scaffolds, every `tausik_*` tool it names is in the MCP server's
TOOLS, every CLI command it names parses, and the refusal texts it quotes are
the ones the gates and the hook print — a quickstart that teaches an agent a
message the tool will never say is worse than none.
"""

from __future__ import annotations

import os
import re
import sys

import pytest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for _p in (
    os.path.join(_ROOT, "scripts"),
    os.path.join(_ROOT, "bootstrap"),
    os.path.join(_ROOT, "harness", "claude", "mcp", "project"),
):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from bootstrap_config import SCAFFOLD_IDES  # noqa: E402

CROSSCUTTING_SCOPE = [
    "docs/",
    "harness/claude/mcp/project/",
    "scripts/gate_qg0_check.py",
    "scripts/hooks/task_gate.py",
]

_PAGES = {
    "en": os.path.join(_ROOT, "docs", "en", "agent-quickstart.md"),
    "ru": os.path.join(_ROOT, "docs", "ru", "agent-quickstart.md"),
}


def _text(lang: str) -> str:
    return open(_PAGES[lang], encoding="utf-8").read()


def _tool_names() -> set[str]:
    import tools

    return {t["name"] for t in tools.TOOLS}


@pytest.mark.parametrize("lang", ["en", "ru"])
def test_the_host_row_is_exactly_what_bootstrap_scaffolds(lang):
    text = _text(lang)
    # The bold list is the one whose members are all `--ide` values.
    m = next(
        (
            mm
            for mm in re.finditer(r"\*\*([a-z,\s]+)\*\*", text)
            if "," in mm.group(1)
            and all(h.strip() in SCAFFOLD_IDES for h in mm.group(1).split(","))
        ),
        None,
    )
    assert m, "the bold host list is gone"
    listed = [h.strip() for h in m.group(1).split(",")]
    assert listed == list(SCAFFOLD_IDES), (
        f"{lang}: page lists {listed}, bootstrap scaffolds {list(SCAFFOLD_IDES)}"
    )
    for ide in SCAFFOLD_IDES:
        assert f"`{ide}`" in text, f"{lang}: no table row for --ide {ide}"


@pytest.mark.parametrize("lang", ["en", "ru"])
def test_every_tool_named_exists(lang):
    named = set(re.findall(r"\btausik_[a-z_]+", _text(lang)))
    unknown = sorted(named - _tool_names())
    assert not unknown, f"{lang}: the page names tools the server does not have: {unknown}"
    assert {
        "tausik_session_start",
        "tausik_task_start",
        "tausik_verify",
        "tausik_task_done",
    } <= named


@pytest.mark.parametrize("lang", ["en", "ru"])
def test_every_cli_command_named_parses(lang):
    from project_parser import build_parser

    parser = build_parser()
    # `tausik <cmd> [<sub>]` — a flag after the command is not a subcommand.
    cmds = set(re.findall(r"\.tausik/tausik(?:\.cmd)? ([a-z-]+)(?: ([a-z][a-z-]*))?", _text(lang)))
    top = {a.dest: a for a in parser._actions if hasattr(a, "choices") and a.choices}
    sub = top["command"].choices
    for cmd, subcmd in sorted(cmds):
        assert cmd in sub, f"{lang}: `tausik {cmd}` is not a command"
        nested = [a for a in sub[cmd]._actions if hasattr(a, "choices") and a.choices]
        if subcmd and nested:
            assert subcmd in nested[0].choices, f"{lang}: `tausik {cmd} {subcmd}` does not parse"


# The refusal texts the page quotes, each pinned to the line of code that prints it.
_REFUSALS = [
    ("scripts/gate_qg0_check.py", "cannot start — missing"),
    ("scripts/gate_qg0_check.py", "AC has no negative scenario"),
    ("scripts/gate_ac_check.py", "cannot complete — acceptance criteria not verified"),
    ("scripts/gate_ac_check.py", "but no verification"),
    ("scripts/hooks/task_gate.py", "No active task. TAUSIK requires a task before code changes"),
    ("scripts/render_verify.py", "no project key, so no signed receipt"),
]


@pytest.mark.parametrize("lang", ["en", "ru"])
@pytest.mark.parametrize("source,phrase", _REFUSALS, ids=[p for _, p in _REFUSALS])
def test_each_quoted_refusal_is_what_the_code_prints(lang, source, phrase):
    assert phrase in _text(lang), f"{lang}: the page no longer quotes {phrase!r}"
    code = open(os.path.join(_ROOT, source), encoding="utf-8").read()
    assert phrase in code, (
        f"{source} no longer prints {phrase!r} — the page quotes a message the tool will never say"
    )


@pytest.mark.parametrize("lang", ["en", "ru"])
def test_codex_is_named_with_its_trust_condition(lang):
    text = _text(lang)
    needle = "trusts the project hooks" if lang == "en" else "доверил хуки проекта"
    assert needle in text


def test_a_made_up_tool_would_be_caught():
    """Negative: the tool check reads TOOLS, not the page's own vocabulary."""
    assert "tausik_teleport" not in _tool_names()
    named = set(re.findall(r"\btausik_[a-z_]+", "call tausik_teleport now"))
    assert sorted(named - _tool_names()) == ["tausik_teleport"]
