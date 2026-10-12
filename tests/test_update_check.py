"""The update check (session-update-check-collides-with-the-zero-phone-home-claim)."""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

import update_check as uc  # noqa: E402
from project_backend import SQLiteBackend  # noqa: E402
from project_cli import cmd_session  # noqa: E402
from project_service import ProjectService  # noqa: E402
from tausik_utils import ServiceError  # noqa: E402
from tausik_version import __version__  # noqa: E402

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


@pytest.mark.parametrize(
    ("left", "right", "order"),
    [
        ("1.11.10", "1.11.2", 1),
        ("1.11.1-rc.1", "1.11.1", -1),
        ("1.11.1", "1.11.1-rc.9", 1),
        ("1.11.1-beta.2", "1.11.1-beta.11", -1),
        ("1.11.1+build.2", "v1.11.1+build.9", 0),
        ("01.11.2", "1.11.1", None),
        ("1.11.2-01", "1.11.1", None),
        ("1.11.2+.", "1.11.1", None),
        ("nightly", "1.11.1", None),
    ],
)
def test_version_order_handles_numeric_prerelease_and_unknown(left, right, order):
    assert uc.compare_versions(left, right) == order


def test_version_flag_needs_no_project_or_database(tmp_path):
    result = subprocess.run(
        [sys.executable, os.path.join(_ROOT, "scripts", "project.py"), "--version"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert result.returncode == 0 and result.stdout.strip() == f"TAUSIK {__version__}"
    assert not (tmp_path / ".tausik").exists()


class _Svc:
    def __init__(self, path):
        self.path = path

    def tausik_dir(self):
        return str(self.path)


class _OpeningSvc(_Svc):
    def __init__(self, path):
        super().__init__(path)
        self.opened = False

    def session_start(self):
        self.opened = True
        return "opened"


def test_cache_writers_use_unique_temporary_files(tmp_path, monkeypatch):
    real_replace = os.replace
    barrier = threading.Barrier(2)
    sources = []

    def overlapping_replace(src, dst):
        sources.append(src)
        barrier.wait(timeout=5)
        real_replace(src, dst)

    monkeypatch.setattr(uc.os, "replace", overlapping_replace)
    opener = _opener({"tag_name": f"v{__version__}"}, [])
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _n: uc.refresh(str(tmp_path), NOW, opener, True), range(2)))

    assert len(set(sources)) == 2
    assert all(result["latest"] == __version__ for result in results)
    assert uc.read_cache(str(tmp_path))["latest"] == __version__


def test_cache_permission_failure_warns_but_session_still_opens(tmp_path, monkeypatch):
    td = tmp_path / ".tausik"
    td.mkdir()
    svc = _OpeningSvc(td)
    monkeypatch.setattr(
        uc,
        "_write_cache",
        lambda *_args: (_ for _ in ()).throw(PermissionError("read only")),
    )
    monkeypatch.setattr(
        uc.urllib.request,
        "urlopen",
        _opener({"tag_name": f"v{__version__}"}, []),
    )

    result = uc.checked_session_start(svc)

    assert svc.opened is True
    assert "cache persistence failed" in result and "opened" in result


def test_every_enabled_start_check_is_forced_and_uses_the_short_timeout(tmp_path):
    td = tmp_path / ".tausik"
    td.mkdir()
    sent: list = []
    opener = _opener({"tag_name": f"v{__version__}"}, sent)

    one = uc.session_start_release_check(_Svc(td), now=NOW, opener=opener)
    two = uc.session_start_release_check(_Svc(td), now=NOW, opener=opener)

    assert one["status"] == two["status"] == "checked"
    assert len(sent) == 2
    assert all(timeout == uc.SESSION_START_TIMEOUT_S for _, timeout in sent)


def test_newer_release_blocks_cli_before_a_session_row_opens(tmp_path, monkeypatch):
    td = tmp_path / ".tausik"
    td.mkdir()
    svc = ProjectService(SQLiteBackend(str(td / "tausik.db")))
    newer = f"{__version__.rsplit('.', 1)[0]}.{int(__version__.rsplit('.', 1)[1]) + 1}"
    monkeypatch.setattr(
        uc.urllib.request,
        "urlopen",
        _opener({"tag_name": f"v{newer}"}, []),
    )
    monkeypatch.setattr(
        uc,
        "_write_cache",
        lambda *_args: (_ for _ in ()).throw(PermissionError("read only")),
    )
    args = SimpleNamespace(session_cmd="start", host_id=None)
    with pytest.raises(
        ServiceError,
        match=rf"installed {re_escape(__version__)}.*latest {re_escape(newer)}.*\.tausik-lib",
    ):
        cmd_session(svc, args)
    assert svc.be.session_current() is None
    svc.be.close()


def re_escape(value: str) -> str:
    import re

    return re.escape(value)


@pytest.mark.parametrize(
    "payload",
    [
        OSError("offline"),
        TimeoutError("timed out"),
        {"tag_name": "nightly"},
        {"tag_name": "v01.11.2"},
        {"tag_name": "1.11.2-01"},
        {"tag_name": "1.11.2+."},
    ],
)
def test_unknown_start_check_allows_work_but_never_claims_current(tmp_path, payload):
    td = tmp_path / ".tausik"
    td.mkdir()
    if isinstance(payload, Exception):

        def opener(*_args, **_kwargs):
            raise payload
    else:
        opener = _opener(payload, [])
    result = uc.session_start_release_check(_Svc(td), now=NOW, opener=opener)
    assert result["status"] == "unknown" and result["fresh"] is False
    assert "unverified" in result["warning"]


@pytest.mark.parametrize("latest", [__version__, "0.0.1"])
def test_same_or_older_release_allows_cli_session_start(tmp_path, monkeypatch, latest):
    td = tmp_path / ".tausik"
    td.mkdir()
    svc = ProjectService(SQLiteBackend(str(td / "tausik.db")))
    monkeypatch.setattr(
        uc.urllib.request,
        "urlopen",
        _opener({"tag_name": f"v{latest}"}, []),
    )

    cmd_session(svc, SimpleNamespace(session_cmd="start", host_id=None))

    assert svc.be.session_current() is not None
    svc.be.close()


def test_privacy_opt_out_sends_nothing_and_is_explicitly_unverified(tmp_path):
    td = tmp_path / ".tausik"
    td.mkdir()
    (td / "config.json").write_text('{"updates":{"check":false}}', encoding="utf-8")

    def forbidden(*_args, **_kwargs):
        raise AssertionError("privacy opt-out made a request")

    result = uc.session_start_release_check(_Svc(td), now=NOW, opener=forbidden)
    assert result["status"] == "disabled" and result["fresh"] is False
    assert "unverified" in result["warning"]


def test_hook_surfaces_a_cli_release_refusal_as_a_work_block(monkeypatch, tmp_path):
    sys.path.insert(0, os.path.join(_ROOT, "scripts", "hooks"))
    import session_start as ss

    monkeypatch.setattr(ss, "_tausik_path", lambda _d: "tausik")
    completed = SimpleNamespace(returncode=1, stderr="Error: installed 1; latest 2", stdout="")
    monkeypatch.setattr(ss.subprocess, "run", lambda *args, **kwargs: completed)
    blocker = ss._open_host_session(str(tmp_path), {"session_id": "host-1"})
    assert "START REFUSED" in blocker and "Do not begin project work" in blocker
