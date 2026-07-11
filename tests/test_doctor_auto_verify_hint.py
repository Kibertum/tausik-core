"""v14-doctor-auto-verify-hint: doctor warns on auto_verify outside CI.

Unit tests of the helper plus an integration test pinning that the warning
actually surfaces in `tausik doctor` output (v14-doctor-autoverify-banner).
"""

from __future__ import annotations

import io
from contextlib import redirect_stdout
from unittest.mock import patch

import pytest

from project_cli_doctor import auto_verify_interactive_warning_detail, cmd_doctor


@pytest.mark.parametrize(
    ("cfg", "env", "expect_piece"),
    [
        ({}, {}, None),
        ({"task_done": {}}, {}, None),
        ({"task_done": {"auto_verify": False}}, {}, None),
        pytest.param(
            {"task_done": {"auto_verify": True}},
            {},
            "auto_verify=true",
            id="interactive-with-auto-verify",
        ),
        pytest.param(
            {"task_done": {"auto_verify": True}},
            {"CI": "true"},
            None,
            id="ci-suppresses-warning",
        ),
        pytest.param(
            {"task_done": {"auto_verify": True}},
            {"GITHUB_ACTIONS": "true"},
            None,
            id="gha-suppresses-warning",
        ),
        pytest.param(
            {"task_done": {"auto_verify": True}},
            {"CI": "false"},
            "auto_verify=true",
            id="ci-false-not-ci",
        ),
    ],
)
def test_auto_verify_interactive_hint(
    cfg: dict,
    env: dict[str, str],
    expect_piece: str | None,
) -> None:
    msg = auto_verify_interactive_warning_detail(cfg, env)
    if expect_piece is None:
        assert msg is None
    else:
        assert msg is not None
        assert expect_piece in msg


def _run_doctor_capture(cfg_overrides: dict, env_overrides: dict) -> str:
    """Invoke cmd_doctor with stubbed config + env, return captured stdout."""
    base_cfg = {
        "session_capacity_calls": 200,
        "session_max_minutes": 180,
        "session_warn_threshold_minutes": 150,
        "session_idle_threshold_minutes": 10,
        "verify_cache_ttl_seconds": 600,
    }
    base_cfg.update(cfg_overrides)

    # Strip every marker the code checks, not the two we happened to think of.
    # The hand-written {"CI", "GITHUB_ACTIONS"} left GITLAB_CI in place, so this
    # test passed on GitHub Actions and failed the moment it ran on GitLab —
    # `looks_like_ci_environment` saw a CI and suppressed the interactive hint.
    import os

    from project_cli_doctor import _CI_ENV_MARKERS

    base_env = {k: v for k, v in os.environ.items() if k not in _CI_ENV_MARKERS}
    base_env.update(env_overrides)

    buf = io.StringIO()
    with (
        patch("project_config.load_config", return_value=base_cfg),
        patch.dict("os.environ", base_env, clear=True),
        redirect_stdout(buf),
    ):
        try:
            from types import SimpleNamespace

            class _Svc:
                def session_active_minutes(self):
                    return 0

                def session_wall_minutes(self):
                    return 0

            cmd_doctor(_Svc(), SimpleNamespace())
        except SystemExit:
            pass
    return buf.getvalue()


def test_doctor_surfaces_warning_when_auto_verify_true(monkeypatch):
    """v14-doctor-autoverify-banner: integration — banner appears in doctor output."""
    out = _run_doctor_capture({"task_done": {"auto_verify": True}}, {})
    assert "Verify-First profile" in out
    assert "auto_verify=true" in out


def test_doctor_omits_warning_when_auto_verify_false(monkeypatch):
    out = _run_doctor_capture({"task_done": {"auto_verify": False}}, {})
    assert "Verify-First profile" not in out


def test_doctor_suppresses_warning_in_ci(monkeypatch):
    out = _run_doctor_capture({"task_done": {"auto_verify": True}}, {"CI": "true"})
    assert "Verify-First profile" not in out
