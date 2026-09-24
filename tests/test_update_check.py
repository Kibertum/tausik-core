"""The update check (session-update-check-collides-with-the-zero-phone-home-claim)."""

from __future__ import annotations

import io
import json
import os
import sys
from datetime import datetime, timedelta, timezone

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

import update_check as uc  # noqa: E402

NOW = datetime(2026, 9, 23, 12, 0, tzinfo=timezone.utc)


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _opener(payload, sent):
    def open_(req, timeout):
        sent.append((req, timeout))
        return _Resp(json.dumps(payload).encode())

    return open_


def _failing(*_a, **_k):
    raise OSError("network unreachable")


def test_a_newer_release_is_announced_with_both_versions_and_the_link(tmp_path):
    sent: list = []
    payload = {
        "tag_name": "v1.10.0",
        "html_url": "https://github.com/Kibertum/tausik-core/releases/tag/v1.10.0",
    }
    cache = uc.refresh(str(tmp_path), NOW, _opener(payload, sent))
    line = uc.notice(cache, "1.9.0")
    assert "1.10.0" in line and "1.9.0" in line and "releases/tag/v1.10.0" in line
    assert uc.notice(cache, "1.10.0") is None


def test_the_request_carries_nothing_about_the_project(tmp_path, monkeypatch):
    """AC-5: asserted on the intercepted request, not by reading the code."""
    project = tmp_path / "secret-client-project"
    project.mkdir()
    monkeypatch.chdir(project)
    sent: list = []
    uc.refresh(str(project), NOW, _opener({"tag_name": "v1.9.0"}, sent))
    ((req, timeout),) = sent
    assert req.full_url == "https://api.github.com/repos/Kibertum/tausik-core/releases/latest"
    assert req.get_method() == "GET" and req.data is None
    blob = json.dumps([req.full_url, dict(req.header_items())]).lower()
    for leak in (
        "secret-client-project",
        str(tmp_path).lower().replace("\\", "\\\\"),
        "1.9.0",
        "schema",
    ):
        assert leak not in blob
    assert timeout <= uc.TIMEOUT_S


def test_at_most_one_request_a_day(tmp_path):
    sent: list = []
    op = _opener({"tag_name": "v1.9.0"}, sent)
    uc.refresh(str(tmp_path), NOW, op)
    uc.refresh(str(tmp_path), NOW + timedelta(hours=23), op)
    assert len(sent) == 1
    uc.refresh(str(tmp_path), NOW + timedelta(hours=25), op)
    assert len(sent) == 2


def test_no_network_keeps_the_last_answer_and_never_claims_up_to_date(tmp_path):
    """AC-4: the failure is recorded, the cache is not poisoned."""
    uc.refresh(str(tmp_path), NOW, _opener({"tag_name": "v1.10.0", "html_url": "u"}, []))
    cache = uc.refresh(str(tmp_path), NOW + timedelta(days=2), _failing)
    assert cache["latest"] == "1.10.0" and "network unreachable" in cache["error"]
    level, text = uc.doctor_line({}, cache)
    assert level == "warn" and "FAILED" in text


@pytest.mark.parametrize("payload", [{"tag_name": "nightly"}, {"message": "rate limited"}, {}])
def test_a_garbage_answer_is_an_error_not_a_version(tmp_path, payload):
    cache = uc.refresh(str(tmp_path), NOW, _opener(payload, []))
    assert "latest" not in cache and "error" in cache
    assert uc.notice(cache, "1.9.0") is None


def test_it_can_be_switched_off():
    assert uc.enabled({}) is True
    assert uc.enabled({"updates": {"check": False}}) is False
    assert uc.doctor_line({"updates": {"check": False}}, {})[1].startswith("off")


@pytest.mark.parametrize("lang,phrase", [("", "api.github.com"), (".ru", "api.github.com")])
def test_the_readme_says_what_leaves_the_machine(lang, phrase):
    with open(os.path.join(_ROOT, f"README{lang}.md"), encoding="utf-8") as f:
        text = f.read()
    assert phrase in text and "updates" in text
    assert "0 phone-home" not in text and "0 обращений наружу" not in text


def test_session_start_only_spawns_detached_and_never_raises(monkeypatch, tmp_path):
    """AC-4: the hook starts the check and returns; a failure to start is swallowed."""
    sys.path.insert(0, os.path.join(_ROOT, "scripts", "hooks"))
    import session_start as ss

    calls: list = []
    monkeypatch.setattr(ss, "_tausik_path", lambda _d: "tausik")
    monkeypatch.setattr(ss.subprocess, "Popen", lambda argv, **kw: calls.append((argv, kw)))
    ss._spawn_update_check(str(tmp_path))
    ((argv, kw),) = calls
    assert argv == ["tausik", "update-check"]
    assert kw["stdin"] is ss.subprocess.DEVNULL and kw["stdout"] is ss.subprocess.DEVNULL

    def boom(*_a, **_k):
        raise OSError("no such file")

    monkeypatch.setattr(ss.subprocess, "Popen", boom)
    ss._spawn_update_check(str(tmp_path))  # must not raise
