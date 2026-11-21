"""TB-005: configured testing.roots require pytest in .tausik/venv."""

from __future__ import annotations

import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from testing_venv_pytest import (
    doctor_venv_pytest_check,
    missing_venv_pytest_refusal,
    tausik_venv_python,
)

CROSSCUTTING_SCOPE = ["scripts/"]


def _write_roots(tmp_path: Path, roots: list[str]) -> None:
    cfg = tmp_path / ".tausik"
    cfg.mkdir(parents=True, exist_ok=True)
    (cfg / "config.json").write_text(json.dumps({"testing": {"roots": roots}}), encoding="utf-8")


def _fake_venv_python(tmp_path: Path) -> Path:
    if os.name == "nt":
        py = tmp_path / ".tausik" / "venv" / "Scripts" / "python.exe"
    else:
        py = tmp_path / ".tausik" / "venv" / "bin" / "python"
    py.parent.mkdir(parents=True, exist_ok=True)
    py.write_text("", encoding="utf-8")
    return py


def test_refusal_skips_when_roots_absent(tmp_path: Path):
    assert missing_venv_pytest_refusal(str(tmp_path)) is None


def test_refusal_skips_when_roots_empty(tmp_path: Path):
    _write_roots(tmp_path, [])
    (tmp_path / "tests").mkdir()
    assert missing_venv_pytest_refusal(str(tmp_path)) is None


def test_refusal_when_configured_root_exists_but_venv_lacks_pytest(tmp_path: Path):
    local = tmp_path / "local-tests"
    local.mkdir()
    _write_roots(tmp_path, ["local-tests"])
    py = _fake_venv_python(tmp_path)

    def _runner(argv, **_kw):
        assert argv[0] == str(py)
        return SimpleNamespace(returncode=1)

    message = missing_venv_pytest_refusal(str(tmp_path), runner=_runner)
    assert message is not None
    assert "unrunnable" in message
    assert "pytest" in message
    assert str(py) in message


def test_ok_when_venv_imports_pytest(tmp_path: Path):
    local = tmp_path / "local-tests"
    local.mkdir()
    _write_roots(tmp_path, ["local-tests"])
    py = _fake_venv_python(tmp_path)

    def _runner(argv, **_kw):
        assert "import pytest" in argv[-1]
        return SimpleNamespace(returncode=0)

    assert missing_venv_pytest_refusal(str(tmp_path), runner=_runner) is None
    row = doctor_venv_pytest_check(str(tmp_path), runner=_runner)
    assert row is not None
    assert row[0] == "ok"
    assert tausik_venv_python(str(tmp_path)) == str(py)


def test_doctor_fails_when_pytest_missing(tmp_path: Path):
    local = tmp_path / "local-tests"
    local.mkdir()
    _write_roots(tmp_path, ["local-tests"])
    _fake_venv_python(tmp_path)

    def _runner(_argv, **_kw):
        return SimpleNamespace(returncode=1)

    row = doctor_venv_pytest_check(str(tmp_path), runner=_runner)
    assert row is not None
    assert row[0] == "fail"
    assert "unrunnable" in row[2]


@pytest.mark.parametrize(
    "returncode,expect_refusal",
    [
        pytest.param(1, True, id="missing-module"),
        pytest.param(0, False, id="present"),
    ],
)
def test_refusal_matrix(tmp_path: Path, returncode: int, expect_refusal: bool):
    local = tmp_path / "local-tests"
    local.mkdir()
    _write_roots(tmp_path, ["local-tests"])
    _fake_venv_python(tmp_path)

    def _runner(_argv, **_kw):
        return SimpleNamespace(returncode=returncode)

    message = missing_venv_pytest_refusal(str(tmp_path), runner=_runner)
    assert (message is not None) is expect_refusal
