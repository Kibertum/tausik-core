"""SENAR 1.5 §4.1: one case of direct modification is recognized, and the list is dated.

direct-modification-has-one-recognized-case. The docs quote the sentence the CLI
prints when it refuses a bypass record without a rationale; the quote is taken
from a live call of the command handler, not typed twice (convention #698).
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from gate_bypass_record import RECOGNIZED_AS_OF, RECOGNIZED_CASE  # noqa: E402
from project_cli_events import cmd_events_emit_supervision  # noqa: E402


def _live_refusal(tmp_path, capsys) -> str:
    svc = SimpleNamespace(tausik_dir=lambda: str(tmp_path / ".tausik"))
    args = SimpleNamespace(
        vector="direct_edit",
        kind="bypass",
        bypass_task="some-task",
        rationale="",
        risk_accepted="",
        remediation="",
        approved_by="",
        sup_source="cli",
        details=None,
    )
    with pytest.raises(SystemExit) as exc:
        cmd_events_emit_supervision(svc, args)
    assert exc.value.code == 2
    return capsys.readouterr().err


def _sentence(err: str) -> str:
    start = err.index("The one recognized case is")
    return err[start : err.index(")", start) + 1]


def test_the_live_refusal_names_one_dated_case(tmp_path, capsys):
    sentence = _sentence(_live_refusal(tmp_path, capsys))
    assert RECOGNIZED_CASE in sentence and RECOGNIZED_AS_OF in sentence


def test_the_english_docs_quote_the_live_refusal(tmp_path, capsys):
    sentence = _sentence(_live_refusal(tmp_path, capsys))
    assert sentence in (ROOT / "docs" / "en" / "cli.md").read_text(encoding="utf-8")


def test_the_russian_docs_quote_the_printed_case_and_the_date(tmp_path, capsys):
    err = _live_refusal(tmp_path, capsys)
    printed = err[err.index("The one recognized case is") :].split(" (", 1)[0]
    ru = (ROOT / "docs" / "ru" / "cli.md").read_text(encoding="utf-8")
    assert printed in ru
    assert "07.09.2026" in ru and "§10.13" in ru


@pytest.mark.parametrize("lang", ["en", "ru"])
def test_the_1_4_list_is_not_presented_as_recognized(lang):
    text = (ROOT / "docs" / lang / "cli.md").read_text(encoding="utf-8")
    assert "incident while agent capacity is unavailable" not in text
    assert "инцидент при недоступной агентской мощности" not in text
    assert "SENAR 1.4 §8.6(j)" not in text
