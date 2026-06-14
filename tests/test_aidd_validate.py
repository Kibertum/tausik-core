"""Tests for scripts/project_cli_aidd_validate.py — `tausik aidd validate`."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from project_cli_aidd_validate import (  # noqa: E402
    _extract_code_bullets,
    _parse_claims,
    _verify_lang_version,
    _verify_lint_tool,
    _verify_max_filesize,
    _verify_test_framework,
    cmd_aidd_validate,
)

_CONV = (
    "# Conventions\n\n"
    "## Code\n\n"
    "- Language(s) and version pins: Python 3.11+\n"
    "- Lint / format tools: ruff\n"
    "- Testing framework: pytest\n"
    "- Max file size / cyclomatic limits (if enforced): 400 lines\n\n"
    "## Naming\n\n- Files: snake_case\n"
)


def _captured_log():
    buf: list[str] = []
    return buf, lambda msg: buf.append(msg)


class TestParsing:
    def test_extract_only_code_section(self):
        bullets = _extract_code_bullets(_CONV)
        assert any("Python 3.11+" in b for b in bullets)
        assert not any("snake_case" in b for b in bullets)  # Naming excluded

    def test_parse_all_four_claims(self):
        claims = _parse_claims(_CONV)
        assert claims["lang_version"] == "Python 3.11+"
        assert claims["lint_tool"] == "ruff"
        assert claims["test_framework"] == "pytest"
        assert claims["max_filesize"] == "400 lines"

    def test_blank_template_values_parse_as_empty(self):
        text = "## Code\n\n- Testing framework:\n"
        assert _parse_claims(text)["test_framework"] == ""

    def test_ignores_lookalike_section_headings(self):
        # '## Code of conduct' bullets must not be parsed as Code claims.
        text = "## Code of conduct\n\n- Testing framework: be nice\n"
        assert _parse_claims(text) == {}


class TestVerifyLangVersion:
    def test_ok_when_requires_python_matches(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "x"\nrequires-python = ">=3.11"\n', encoding="utf-8"
        )
        status, _ = _verify_lang_version(str(tmp_path), "Python 3.11+")
        assert status == "ok"

    def test_drift_when_version_mismatch(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "x"\nrequires-python = ">=3.9"\n', encoding="utf-8"
        )
        status, detail = _verify_lang_version(str(tmp_path), "Python 3.11+")
        assert status == "drift"
        assert "3.9" in detail

    def test_unverifiable_when_no_requires_python(self, tmp_path):
        status, _ = _verify_lang_version(str(tmp_path), "Python 3.11+")
        assert status == "unverifiable"

    def test_no_false_ok_on_version_prefix_substring(self, tmp_path):
        # '3.1' must NOT substring-match '>=3.11' (was a false-ok bug).
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "x"\nrequires-python = ">=3.11"\n', encoding="utf-8"
        )
        assert _verify_lang_version(str(tmp_path), "Python 3.1+")[0] == "drift"

    def test_blank_claim_unverifiable(self, tmp_path):
        assert _verify_lang_version(str(tmp_path), "")[0] == "unverifiable"


class TestVerifyLintTool:
    def test_ok_when_tool_in_pyproject(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text(
            "[tool.ruff]\nline-length = 100\n", encoding="utf-8"
        )
        assert _verify_lint_tool(str(tmp_path), "ruff")[0] == "ok"

    def test_ok_when_config_file_present(self, tmp_path):
        (tmp_path / "ruff.toml").write_text("line-length = 100\n", encoding="utf-8")
        assert _verify_lint_tool(str(tmp_path), "ruff, mypy")[0] == "drift"  # mypy missing
        (tmp_path / "mypy.ini").write_text("[mypy]\n", encoding="utf-8")
        assert _verify_lint_tool(str(tmp_path), "ruff, mypy")[0] == "ok"

    def test_drift_when_tool_absent(self, tmp_path):
        status, detail = _verify_lint_tool(str(tmp_path), "ruff")
        assert status == "drift"
        assert "ruff" in detail

    def test_unverifiable_when_unrecognized(self, tmp_path):
        assert _verify_lint_tool(str(tmp_path), "some-bespoke-linter")[0] == "unverifiable"

    def test_no_false_present_on_substring_dep(self, tmp_path):
        # 'flake8-bugbear' must NOT satisfy a 'flake8' claim (line-start match).
        (tmp_path / "requirements.txt").write_text("flake8-bugbear==1.0\n", encoding="utf-8")
        assert _verify_lint_tool(str(tmp_path), "flake8")[0] == "drift"

    def test_no_false_extract_on_substring_claim(self, tmp_path):
        # 'notmypy' must NOT be read as a 'mypy' claim (word boundary).
        assert _verify_lint_tool(str(tmp_path), "notmypy")[0] == "unverifiable"


class TestVerifyTestFramework:
    def test_ok_when_match(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text(
            '[tool.pytest.ini_options]\naddopts = "-q"\n', encoding="utf-8"
        )
        assert _verify_test_framework(str(tmp_path), "pytest")[0] == "ok"

    def test_drift_when_mismatch(self, tmp_path):
        (tmp_path / "package.json").write_text(
            '{"devDependencies": {"jest": "^29"}}', encoding="utf-8"
        )
        status, detail = _verify_test_framework(str(tmp_path), "pytest")
        assert status == "drift"
        assert "jest" in detail

    def test_unverifiable_when_none_detected(self, tmp_path):
        assert _verify_test_framework(str(tmp_path), "pytest")[0] == "unverifiable"

    def test_no_false_ok_on_substring_framework(self, tmp_path):
        # detected 'ava' must NOT word-match a 'javascript-tests' claim.
        (tmp_path / "package.json").write_text(
            '{"devDependencies": {"ava": "^6"}}', encoding="utf-8"
        )
        assert _verify_test_framework(str(tmp_path), "javascript-tests")[0] == "drift"


class TestVerifyMaxFilesize:
    def test_ok_when_all_under(self, tmp_path):
        (tmp_path / "a.py").write_text("x\n" * 10, encoding="utf-8")
        assert _verify_max_filesize(str(tmp_path), "400 lines")[0] == "ok"

    def test_drift_when_file_exceeds(self, tmp_path):
        (tmp_path / "big.py").write_text("x\n" * 500, encoding="utf-8")
        status, detail = _verify_max_filesize(str(tmp_path), "400 lines")
        assert status == "drift"
        assert "big.py" in detail

    def test_unverifiable_when_no_number(self, tmp_path):
        assert _verify_max_filesize(str(tmp_path), "as small as possible")[0] == "unverifiable"


class TestCmdAiddValidate:
    def test_missing_conventions_exits_2(self, tmp_path, capsys):
        rc = cmd_aidd_validate(root=str(tmp_path))
        assert rc == 2
        assert "conventions.md not found" in capsys.readouterr().err

    def test_all_ok_exits_0(self, tmp_path):
        (tmp_path / "conventions.md").write_text(_CONV, encoding="utf-8")
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "x"\nrequires-python = ">=3.11"\n'
            "[tool.ruff]\nline-length = 100\n"
            '[tool.pytest.ini_options]\naddopts = "-q"\n',
            encoding="utf-8",
        )
        (tmp_path / "small.py").write_text("x\n" * 5, encoding="utf-8")
        log, log_fn = _captured_log()
        rc = cmd_aidd_validate(root=str(tmp_path), log=log_fn)
        assert rc == 0
        assert any("Summary:" in line and "0 drift" in line for line in log)

    def test_drift_exits_1_and_names_claim(self, tmp_path):
        (tmp_path / "conventions.md").write_text(_CONV, encoding="utf-8")
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "x"\nrequires-python = ">=3.11"\n'
            "[tool.ruff]\nline-length = 100\n"
            '[tool.pytest.ini_options]\naddopts = "-q"\n',
            encoding="utf-8",
        )
        (tmp_path / "huge.py").write_text("x\n" * 999, encoding="utf-8")
        log, log_fn = _captured_log()
        rc = cmd_aidd_validate(root=str(tmp_path), log=log_fn)
        assert rc == 1
        assert any(line.startswith("[drift] Max file size") for line in log)

    def test_blank_claims_unverifiable_not_drift(self, tmp_path):
        # A freshly scaffolded conventions.md (empty values) must not drift.
        blank = (
            "# Conventions\n\n## Code\n\n"
            "- Language(s) and version pins:\n"
            "- Lint / format tools:\n"
            "- Testing framework:\n"
            "- Max file size:\n"
        )
        (tmp_path / "conventions.md").write_text(blank, encoding="utf-8")
        log, log_fn = _captured_log()
        rc = cmd_aidd_validate(root=str(tmp_path), log=log_fn)
        assert rc == 0
        assert all("[drift]" not in line for line in log)

    def test_non_utf8_conventions_does_not_crash(self, tmp_path):
        # latin-1 bytes decode (errors=replace); no detectable framework → exit 0.
        (tmp_path / "conventions.md").write_bytes(
            "## Code\n\n- Testing framework: pytést\n".encode("latin-1")
        )
        log, log_fn = _captured_log()
        rc = cmd_aidd_validate(root=str(tmp_path), log=log_fn)
        assert rc == 0  # no crash, no hard drift
        assert all("[drift]" not in line for line in log)
