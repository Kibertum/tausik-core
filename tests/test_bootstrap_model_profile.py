"""TAUSIK_MODEL_PROFILE env → .tausik/config.json model_profile (bootstrap)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
_BOOTSTRAP = _REPO / "bootstrap" / "bootstrap.py"

_boot_dir = str(_REPO / "bootstrap")
if _boot_dir not in sys.path:
    sys.path.insert(0, _boot_dir)

from bootstrap_config import (  # noqa: E402
    TAUSIK_MODEL_PROFILE_ENV,
    normalize_model_profile_slug,
    parse_strict_model_profile_env,
)


def test_normalize_model_profile_slug():
    assert normalize_model_profile_slug(" Codex ") == "codex"


def test_parse_strict_accepts_valid_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv(TAUSIK_MODEL_PROFILE_ENV, "gpt-5")
    assert parse_strict_model_profile_env() == "gpt-5"


def test_parse_strict_invalid_non_alnum(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv(TAUSIK_MODEL_PROFILE_ENV, "@@@")
    with pytest.raises(ValueError, match="Invalid"):
        parse_strict_model_profile_env()


def test_bootstrap_refresh_writes_model_profile(tmp_path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv(TAUSIK_MODEL_PROFILE_ENV, "claude")
    env = {**os.environ, TAUSIK_MODEL_PROFILE_ENV: "claude"}
    r = subprocess.run(
        [
            sys.executable,
            str(_BOOTSTRAP),
            "--project-dir",
            str(tmp_path),
            "--ide",
            "claude",
            "--refresh",
        ],
        cwd=str(tmp_path),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    cfg_path = tmp_path / ".tausik" / "config.json"
    assert cfg_path.is_file()
    data = json.loads(cfg_path.read_text(encoding="utf-8"))
    assert data.get("model_profile") == "claude"


def test_bootstrap_refresh_rejects_bad_profile(tmp_path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv(TAUSIK_MODEL_PROFILE_ENV, raising=False)
    env = {**os.environ, TAUSIK_MODEL_PROFILE_ENV: "!!!"}
    r = subprocess.run(
        [
            sys.executable,
            str(_BOOTSTRAP),
            "--project-dir",
            str(tmp_path),
            "--refresh",
        ],
        cwd=str(tmp_path),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    assert r.returncode != 0
