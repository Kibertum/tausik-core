"""RAG reads Godot out of the box, and any project can add its own languages
(rag-language-list-is-hardcoded-while-stacks-are-user-extensible, GitLab #11)."""

from __future__ import annotations

import json
import os
import sys

import pytest

_RAG = os.path.join(os.path.dirname(__file__), "..", "harness", "claude", "mcp", "codebase-rag")
sys.path.insert(0, os.path.abspath(_RAG))

import rag_detect  # noqa: E402
import rag_indexer  # noqa: E402
import rag_languages  # noqa: E402

GD = """extends Node

var cooldown := 3.0

func _ready() -> void:
    print("ready")
    print("spirit")

func _trigger_summon(spirit: String) -> void:
    if cooldown > 0.0:
        return
    print("summon ", spirit)
    cooldown = 3.0
"""


def _project(tmp_path, rag=None, files=None):
    (tmp_path / ".tausik").mkdir()
    if rag is not None:
        (tmp_path / ".tausik" / "config.json").write_text(
            json.dumps({"rag": rag}), encoding="utf-8"
        )
    for name, body in (files or {}).items():
        p = tmp_path / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding="utf-8")
    return str(tmp_path)


@pytest.mark.parametrize(
    "name,lang",
    [
        ("player.gd", "gdscript"),
        ("water.gdshader", "gdshader"),
        ("main.tscn", "godot-scene"),
        ("theme.tres", "godot-resource"),
        ("project.godot", "godot-project"),
    ],
)
def test_godot_files_are_built_in(name, lang):
    assert rag_detect.detect_language(name) == lang


def test_a_gdscript_function_is_one_chunk_with_its_body():
    chunks = rag_indexer.chunk_file(GD, "gdscript")
    summon = [c for c in chunks if "func _trigger_summon" in c["content"]]
    assert summon and "cooldown = 3.0" in summon[0]["content"]


def test_the_project_knob_adds_an_extension_and_its_boundary(tmp_path):
    body = (
        "--- !u!1 &1\nGameObject:\n  m_Name: Hero\n" * 3 + "--- !u!4 &2\nTransform:\n  x: 1\n" * 3
    )
    root = _project(
        tmp_path,
        rag={
            "extra_extensions": {".unity": "unity-scene"},
            "boundaries": {"unity-scene": "^--- !u!"},
        },
        files={"Assets/Main.unity": body},
    )
    files = {f["rel_path"]: f["language"] for f in rag_detect.get_file_list(root)}
    assert files.get("Assets/Main.unity") == "unity-scene"
    langs = rag_languages.load(root, rag_detect.EXT_TO_LANG)
    assert langs.problems == []
    chunks = rag_indexer.chunk_file(body, "unity-scene", langs.boundaries)
    assert all(c["content"].lstrip().startswith("--- !u!") for c in chunks)


@pytest.mark.parametrize(
    "rag,needle",
    [
        ({"extra_extensions": {"unity": "unity-scene"}}, "is not an extension"),
        ({"extra_extensions": {".unity": ""}}, "names no language"),
        ({"extra_extensions": [".unity"]}, "must be a mapping"),
        ({"boundaries": {"unity-scene": "^(unclosed"}}, "does not compile"),
        ("not-a-block", "rag must be a mapping"),
    ],
)
def test_a_bad_knob_is_skipped_and_reported_never_silent(tmp_path, rag, needle):
    root = _project(
        tmp_path, rag=rag, files={"a.unity": "x\n" * 60, "b.py": "def f():\n    pass\n"}
    )
    langs = rag_languages.load(root, rag_detect.EXT_TO_LANG)
    assert any(needle in p for p in langs.problems), langs.problems
    rels = {f["rel_path"] for f in rag_detect.get_file_list(root)}
    assert "b.py" in rels and "a.unity" not in rels  # indexing goes on, the bad entry does not


def test_the_knob_cannot_override_a_built_in(tmp_path):
    root = _project(tmp_path, rag={"extra_extensions": {".gd": "plain"}})
    langs = rag_languages.load(root, rag_detect.EXT_TO_LANG)
    assert ".gd" not in langs.extensions and "built in" in langs.problems[0]
    assert rag_detect.detect_language("x.gd", langs.extensions) == "gdscript"


def test_godot_side_files_stay_out(tmp_path):
    root = _project(
        tmp_path,
        files={"icon.png.import": "[remap]\n", "player.gd.uid": "uid://x\n", "player.gd": GD},
    )
    rels = {f["rel_path"] for f in rag_detect.get_file_list(root)}
    assert rels == {"player.gd"}


def test_rag_status_shows_the_knob_and_its_problems(tmp_path, monkeypatch):
    import rag_handlers

    class _Closable:
        def status(self):
            return {}

        def close(self):
            pass

    monkeypatch.setattr(rag_handlers, "_get_rag_store", lambda _d: _Closable())
    monkeypatch.setattr(rag_handlers, "_get_backend", lambda _d: _Closable())
    monkeypatch.setattr(rag_handlers, "_staleness_report", lambda _be: {})
    monkeypatch.setattr(rag_handlers, "_get_web_cache", lambda _d: _Closable())
    root = _project(tmp_path, rag={"extra_extensions": {"unity": "x", ".unity": "unity-scene"}})
    out = json.loads(rag_handlers.call_tool_sync("rag_status", {}, root))
    cfg = out["language_config"]
    assert cfg["extra_extensions"] == {".unity": "unity-scene"}
    assert any("is not an extension" in p for p in cfg["problems"])


def test_a_missing_config_helper_is_reported_not_silent(tmp_path, monkeypatch):
    monkeypatch.setattr(rag_languages, "_config_path", lambda _d: None)
    langs = rag_languages.load(str(tmp_path), rag_detect.EXT_TO_LANG)
    assert any("tausik_utils not found" in p for p in langs.problems)


def test_the_config_path_comes_from_the_shared_helper(tmp_path):
    from tausik_utils import tausik_config_path

    assert rag_languages._config_path(str(tmp_path)) == tausik_config_path(str(tmp_path))
