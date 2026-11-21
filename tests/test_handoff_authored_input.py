"""Authored session-handoff JSON: file/stdin/positional share one schema."""

from __future__ import annotations

import io
import json
from types import SimpleNamespace

import handoff_authored_input as hai
import pytest


def test_positional_json_with_spaces_and_cyrillic():
    raw = json.dumps(
        {"next_steps": ["продолжить задачу"], "warnings": ['quote "ok"', "path\\win"]},
        ensure_ascii=False,
    )
    got = hai.load_authored(positional=raw)
    assert got["next_steps"] == ["продолжить задачу"]
    assert got["warnings"] == ['quote "ok"', "path\\win"]


def test_json_file_reads_utf8(tmp_path):
    path = tmp_path / "h.json"
    payload = {
        "next_steps": ["a" * 4000],
        "warnings": ["длинное предупреждение"],
        "in_progress": [{"slug": "t1", "state": "step 2"}],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    got = hai.load_authored(json_file=str(path))
    assert got["next_steps"][0].endswith("a" * 10)
    assert got["in_progress"][0]["slug"] == "t1"


def test_stdin_and_positional_dash(tmp_path):
    body = '{"warnings": ["from stdin"]}'
    got = hai.load_authored(json_stdin=True, stdin=io.StringIO(body))
    assert got == {"warnings": ["from stdin"]}
    got2 = hai.load_authored(positional="-", stdin=io.StringIO(body))
    assert got2 == got


def test_none_when_no_source():
    assert hai.load_authored() is None


@pytest.mark.parametrize(
    "kwargs",
    [
        {"positional": "{}", "json_file": "x.json"},
        {"positional": "{}", "json_stdin": True},
        {"json_file": "x.json", "json_stdin": True},
    ],
)
def test_conflicting_sources_refused(kwargs):
    with pytest.raises(hai.AuthoredHandoffInputError) as ei:
        hai.load_authored(**kwargs)
    assert ei.value.code == "CONFLICT"


def test_invalid_json_structured():
    with pytest.raises(hai.AuthoredHandoffInputError) as ei:
        hai.parse_authored_text("{not json", source="positional")
    assert ei.value.code == "INVALID_JSON"
    assert "code" in ei.value.as_dict()


def test_schema_rejects_bad_next_steps():
    with pytest.raises(hai.AuthoredHandoffInputError) as ei:
        hai.validate_authored({"next_steps": "solo"})
    assert ei.value.code == "BAD_NEXT_STEPS"


def test_cli_args_adapter(tmp_path):
    path = tmp_path / "a.json"
    path.write_text('{"next_steps": ["via file"]}', encoding="utf-8")
    args = SimpleNamespace(json_data=None, json_file=str(path), json_stdin=False)
    assert hai.load_from_cli_args(args)["next_steps"] == ["via file"]


def test_mcp_validate_object_only():
    with pytest.raises(hai.AuthoredHandoffInputError) as ei:
        hai.validate_authored(["not", "object"])
    assert ei.value.code == "NOT_OBJECT"
