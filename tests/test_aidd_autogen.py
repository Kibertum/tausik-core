"""Tests for scripts/project_cli_aidd_autogen.py — `tausik aidd autogen`."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from project_cli_aidd_autogen import (  # noqa: E402
    _PLACEHOLDER,
    _detect_languages,
    _detect_package_meta,
    _detect_test_framework,
    _detect_top_dirs,
    _parse_readme,
    _pyproject_has_pytest,
    cmd_aidd_autogen,
    gather_signals,
    render_vision,
)

_TEMPLATE = (
    "# Vision\n\n"
    "> AIDD layer 2 — keep < 200 lines.\n\n"
    "## Target user\n\nWho, exactly.\n\n"
    "## Core experience (3 bullets max)\n\n1. ...\n"
)


def _captured_log():
    buf: list[str] = []
    return buf, lambda msg: buf.append(msg)


class TestDetectPackageMeta:
    def test_pyproject_wins(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "acme"\ndescription = "Does things"\n',
            encoding="utf-8",
        )
        assert _detect_package_meta(str(tmp_path)) == ("acme", "Does things")

    def test_package_json_fallback(self, tmp_path):
        (tmp_path / "package.json").write_text(
            '{"name": "widget", "description": "A widget"}', encoding="utf-8"
        )
        assert _detect_package_meta(str(tmp_path)) == ("widget", "A widget")

    def test_missing_returns_none(self, tmp_path):
        assert _detect_package_meta(str(tmp_path)) == (None, None)

    def test_malformed_pyproject_does_not_crash(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text("not = valid = toml = [", encoding="utf-8")
        assert _detect_package_meta(str(tmp_path)) == (None, None)


class TestParseReadme:
    def test_title_and_first_paragraph(self):
        title, para = _parse_readme("# My Project\n\nFirst line.\nSecond line.\n\nLater.")
        assert title == "My Project"
        assert para == "First line. Second line."

    def test_skips_badges_before_prose(self):
        title, para = _parse_readme("# P\n\n![badge](x)\n\nReal description here.")
        assert title == "P"
        assert para == "Real description here."

    def test_no_heading(self):
        assert _parse_readme("just text, no heading") == (None, None)


class TestDetectTopDirs:
    def test_filters_deny_and_hidden(self, tmp_path):
        for d in ("src", "tests", "node_modules", ".git", "__pycache__"):
            (tmp_path / d).mkdir()
        assert _detect_top_dirs(str(tmp_path)) == ["src", "tests"]


class TestDetectLanguages:
    def test_orders_by_frequency(self, tmp_path):
        (tmp_path / "a.py").write_text("x", encoding="utf-8")
        (tmp_path / "b.py").write_text("x", encoding="utf-8")
        (tmp_path / "c.ts").write_text("x", encoding="utf-8")
        assert _detect_languages(str(tmp_path)) == ["Python", "TypeScript"]

    def test_skips_deny_dirs(self, tmp_path):
        (tmp_path / "node_modules").mkdir()
        (tmp_path / "node_modules" / "dep.js").write_text("x", encoding="utf-8")
        (tmp_path / "main.py").write_text("x", encoding="utf-8")
        assert _detect_languages(str(tmp_path)) == ["Python"]


class TestDetectTestFramework:
    def test_pytest_from_pyproject(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text(
            '[tool.pytest.ini_options]\naddopts = "-q"\n', encoding="utf-8"
        )
        assert _detect_test_framework(str(tmp_path)) == "pytest"

    def test_jest_from_package_json(self, tmp_path):
        (tmp_path / "package.json").write_text(
            '{"devDependencies": {"jest": "^29"}}', encoding="utf-8"
        )
        assert _detect_test_framework(str(tmp_path)) == "jest"

    def test_tests_dir_fallback(self, tmp_path):
        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "test_x.py").write_text("x", encoding="utf-8")
        assert _detect_test_framework(str(tmp_path)) == "pytest"

    def test_none_when_undetermined(self, tmp_path):
        assert _detect_test_framework(str(tmp_path)) is None

    def test_no_false_match_on_project_name(self, tmp_path):
        # Project merely named/described with a 'pytest' substring must NOT match.
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "mypytestlib"\ndescription = "not about pytest at all"\n',
            encoding="utf-8",
        )
        assert _detect_test_framework(str(tmp_path)) is None

    def test_pytest_as_dependency(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "x"\noptional-dependencies = {dev = ["pytest>=8"]}\n',
            encoding="utf-8",
        )
        assert _detect_test_framework(str(tmp_path)) == "pytest"


class TestPyprojectHasPytest:
    def test_tool_section(self):
        assert _pyproject_has_pytest({"tool": {"pytest": {}}}) is True

    def test_dependency(self):
        assert _pyproject_has_pytest({"project": {"dependencies": ["pytest==8.0"]}}) is True

    def test_substring_only_is_false(self):
        assert _pyproject_has_pytest({"project": {"name": "nopytesthere"}}) is False


class TestNonUtf8Inputs:
    def test_readme_non_utf8_does_not_crash(self, tmp_path):
        (tmp_path / "README.md").write_bytes("# Café\n\nNaïve résumé.".encode("latin-1"))
        sig = gather_signals(str(tmp_path))  # must not raise
        assert sig["name"] is not None  # title parsed (mojibake-tolerant)

    def test_merge_append_non_utf8_existing_does_not_crash(self, tmp_path):
        (tmp_path / "vision.md").write_bytes("Naïve existing vision".encode("latin-1"))
        rc = cmd_aidd_autogen(
            write=True, root=str(tmp_path), prompt=lambda _: "m", log=lambda _: None
        )
        assert rc == 0
        merged = (tmp_path / "vision.md").read_text(encoding="utf-8", errors="replace")
        assert "merged from AIDD template" in merged


class TestRenderVision:
    def test_injects_facts_before_first_section(self):
        out = render_vision(_TEMPLATE, gather_signals_stub())
        assert "## Project facts (auto-detected)" in out
        # Facts come before Target user, template sections preserved.
        assert out.index("Project facts") < out.index("## Target user")
        assert "## Core experience (3 bullets max)" in out
        assert "**Name:** acme" in out

    def test_missing_signal_becomes_placeholder(self):
        out = render_vision(
            _TEMPLATE,
            {
                "name": None,
                "description": None,
                "top_dirs": [],
                "languages": [],
                "test_framework": None,
            },
        )
        assert out.count(_PLACEHOLDER) == 5

    def test_no_section_template_appends_facts(self):
        out = render_vision("# Vision\n\nNo sections here.", gather_signals_stub())
        assert "## Project facts (auto-detected)" in out


def gather_signals_stub() -> dict:
    return {
        "name": "acme",
        "description": "Does things",
        "top_dirs": ["src", "tests"],
        "languages": ["Python"],
        "test_framework": "pytest",
    }


class TestGatherSignals:
    def test_end_to_end_python_repo(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "demo"\ndescription = "Demo app"\n'
            '[tool.pytest.ini_options]\naddopts = "-q"\n',
            encoding="utf-8",
        )
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "app.py").write_text("print(1)", encoding="utf-8")
        sig = gather_signals(str(tmp_path))
        assert sig["name"] == "demo"
        assert sig["description"] == "Demo app"
        assert "src" in sig["top_dirs"]
        assert sig["languages"] == ["Python"]
        assert sig["test_framework"] == "pytest"

    def test_readme_fills_missing_meta(self, tmp_path):
        (tmp_path / "README.md").write_text("# Cool Tool\n\nA tool that is cool.", encoding="utf-8")
        sig = gather_signals(str(tmp_path))
        assert sig["name"] == "Cool Tool"
        assert sig["description"] == "A tool that is cool."


class TestCmdAiddAutogen:
    def test_default_prints_to_stdout_writes_nothing(self, tmp_path, capsys):
        rc = cmd_aidd_autogen(write=False, root=str(tmp_path))
        assert rc == 0
        out = capsys.readouterr().out
        assert "## Project facts (auto-detected)" in out
        assert not (tmp_path / "vision.md").exists()

    def test_write_creates_seeded_vision(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "demo"\ndescription = "D"\n', encoding="utf-8"
        )
        log, log_fn = _captured_log()
        rc = cmd_aidd_autogen(write=True, root=str(tmp_path), log=log_fn)
        assert rc == 0
        vision = (tmp_path / "vision.md").read_text(encoding="utf-8")
        assert "**Name:** demo" in vision
        assert "## Target user" in vision
        assert any("created: vision.md" in line for line in log)

    def test_existing_file_skip_by_default(self, tmp_path):
        (tmp_path / "vision.md").write_text("MY VISION", encoding="utf-8")
        log, log_fn = _captured_log()
        rc = cmd_aidd_autogen(write=True, root=str(tmp_path), prompt=lambda _: "", log=log_fn)
        assert rc == 0
        assert (tmp_path / "vision.md").read_text(encoding="utf-8") == "MY VISION"

    def test_force_overwrites(self, tmp_path):
        (tmp_path / "vision.md").write_text("MY VISION", encoding="utf-8")
        rc = cmd_aidd_autogen(write=True, force=True, root=str(tmp_path), log=lambda _: None)
        assert rc == 0
        assert (tmp_path / "vision.md").read_text(encoding="utf-8") != "MY VISION"

    def test_empty_repo_never_crashes_exit_0(self, tmp_path, capsys):
        rc = cmd_aidd_autogen(write=True, root=str(tmp_path), log=lambda _: None)
        assert rc == 0
        vision = (tmp_path / "vision.md").read_text(encoding="utf-8")
        assert _PLACEHOLDER in vision
