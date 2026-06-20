"""Tests for the brain_post_webfetch PostToolUse hook.

Covers: disabled brain, missing token, missing mirror, empty payload,
error response, private-URL filter, already-cached-fresh skip, cached-
stale rewrite path, WebSearch skip, malformed stdin, oversized stdin,
and the happy path (successful cache write).

Strategy: we run the hook as a subprocess for realism. For the happy
path we inject a dummy `brain_runtime` module via PYTHONPATH that
captures `try_brain_write_web_cache` calls, so we can assert what the
hook actually tried to store without standing up Notion.
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import sqlite3
import subprocess
import sys
import textwrap

import pytest

_HOOK_PATH = os.path.join(
    os.path.dirname(__file__), "..", "scripts", "hooks", "brain_post_webfetch.py"
)
_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

from brain_schema import apply_schema  # noqa: E402


# ---- Helpers -------------------------------------------------------------


def _run(
    project_dir,
    payload: dict,
    *,
    extra_env: dict | None = None,
    pythonpath_prepend: str | None = None,
    stdin_override: str | None = None,
) -> subprocess.CompletedProcess:
    env = {
        **os.environ,
        "CLAUDE_PROJECT_DIR": str(project_dir),
        "TAUSIK_DIR": str(os.path.join(project_dir, ".tausik")),
        "PYTHONUTF8": "1",
        "PYTHONIOENCODING": "utf-8",
        "TAUSIK_BRAIN_HOOK_DEBUG": "1",
    }
    env.pop("TAUSIK_SKIP_HOOKS", None)
    if extra_env:
        env.update(extra_env)
    if pythonpath_prepend:
        # Include _SCRIPTS so the hook's `if _SCRIPTS_DIR not in sys.path`
        # guard short-circuits. Otherwise the hook prepends scripts/ to
        # sys.path[0] and the shim's brain_runtime loses to the real one.
        existing = env.get("PYTHONPATH", "")
        parts = [pythonpath_prepend, _SCRIPTS]
        if existing:
            parts.append(existing)
        env["PYTHONPATH"] = os.pathsep.join(parts)
    raw = stdin_override if stdin_override is not None else json.dumps(payload)
    return subprocess.run(
        [sys.executable, _HOOK_PATH],
        input=raw,
        capture_output=True,
        text=True,
        timeout=20,
        env=env,
    )


def _setup_tausik(tmp_path, brain_cfg: dict | None = None):
    tausik_dir = tmp_path / ".tausik"
    tausik_dir.mkdir()
    (tausik_dir / "tausik.db").write_text("")
    if brain_cfg is not None:
        cfg = {"brain": brain_cfg}
        (tausik_dir / "config.json").write_text(json.dumps(cfg), encoding="utf-8")
    return tausik_dir


def _make_brain_db(path) -> None:
    conn = sqlite3.connect(str(path))
    try:
        apply_schema(conn)
        conn.commit()
    finally:
        conn.close()


def _insert_web_cache(
    path,
    *,
    notion_page_id: str,
    url: str,
    fetched_at: str | None = None,
    name: str = "cached",
    content: str = "cached body",
) -> None:
    if fetched_at is None:
        fetched_at = (
            _dt.datetime.now(tz=_dt.timezone.utc).isoformat().replace("+00:00", "Z")
        )
    conn = sqlite3.connect(str(path))
    try:
        conn.execute(
            "INSERT INTO brain_web_cache("
            "  notion_page_id, name, url, query, content, fetched_at,"
            "  domain, tags, source_project_hash, content_hash,"
            "  last_edited_time, created_time) "
            "VALUES(?, ?, ?, '', ?, ?, '', '[]', 'ph', 'ch', ?, ?)",
            (
                notion_page_id,
                name,
                url,
                content,
                fetched_at,
                fetched_at,
                fetched_at,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def _fresh_config(tmp_path, *, private_patterns: list | None = None) -> dict:
    mirror = tmp_path / "brain.db"
    return {
        "enabled": True,
        "local_mirror_path": str(mirror),
        "notion_integration_token_env": "FAKE_BRAIN_TOKEN",
        "database_ids": {
            "decisions": "d1",
            "web_cache": "w1",
            "patterns": "p1",
            "gotchas": "g1",
        },
        "ttl_web_cache_days": 30,
        "private_url_patterns": private_patterns or [],
    }


def _make_stub_runtime(tmp_path, capture_file: str) -> str:
    """Write a stub `brain_runtime.py` into a shim dir and return the dir path.

    The stub captures try_brain_write_web_cache arguments to a JSON file so
    the test can assert what the hook tried to store. Paired with
    PYTHONPATH-prepending so the shim wins over scripts/brain_runtime.py.
    """
    shim = tmp_path / "shim"
    shim.mkdir()
    (shim / "brain_runtime.py").write_text(
        textwrap.dedent(
            f"""
            import json

            def try_brain_write_web_cache(url, content, cfg, *, query="", title=None):
                with open(r"{capture_file}", "w", encoding="utf-8") as f:
                    json.dump(
                        {{
                            "url": url,
                            "content_len": len(content),
                            "content_head": content[:64],
                            "query": query,
                            "title": title,
                        }},
                        f,
                    )
                return (True, "stub-page-id")
            """
        ).lstrip(),
        encoding="utf-8",
    )
    return str(shim)


# ---- AC: TAUSIK_SKIP_HOOKS + missing .tausik -----------------------------


def test_skip_hooks_env_short_circuits(tmp_path):
    # .tausik DB exists, brain enabled, but env var forces skip.
    _setup_tausik(tmp_path, brain_cfg=_fresh_config(tmp_path))
    result = _run(
        tmp_path,
        {"tool_name": "WebFetch", "tool_input": {"url": "https://x.example"}},
        extra_env={"TAUSIK_SKIP_HOOKS": "1"},
    )
    assert result.returncode == 0
    # Should be completely silent — no debug output even with debug flag.
    assert "brain_post_webfetch" not in result.stderr


def test_no_tausik_db_exits_zero_silent(tmp_path):
    result = _run(
        tmp_path,
        {"tool_name": "WebFetch", "tool_input": {"url": "https://x.example"}},
    )
    assert result.returncode == 0


# ---- AC: brain disabled / token missing / mirror missing -----------------


def test_brain_disabled_exits_zero(tmp_path):
    _setup_tausik(tmp_path, brain_cfg={"enabled": False})
    result = _run(
        tmp_path,
        {
            "tool_name": "WebFetch",
            "tool_input": {"url": "https://x.example"},
            "tool_response": {"url": "https://x.example", "result": "body"},
        },
    )
    assert result.returncode == 0


def test_token_missing_exits_zero(tmp_path, monkeypatch):
    cfg = _fresh_config(tmp_path)
    _setup_tausik(tmp_path, brain_cfg=cfg)
    _make_brain_db(tmp_path / "brain.db")
    monkeypatch.delenv("FAKE_BRAIN_TOKEN", raising=False)
    result = _run(
        tmp_path,
        {
            "tool_name": "WebFetch",
            "tool_input": {"url": "https://x.example"},
            "tool_response": {"url": "https://x.example", "result": "body"},
        },
    )
    assert result.returncode == 0
    assert "token env unset" in result.stderr


def test_mirror_missing_exits_zero(tmp_path):
    cfg = _fresh_config(tmp_path)
    _setup_tausik(tmp_path, brain_cfg=cfg)
    # Do NOT create the mirror db.
    result = _run(
        tmp_path,
        {
            "tool_name": "WebFetch",
            "tool_input": {"url": "https://x.example"},
            "tool_response": {"url": "https://x.example", "result": "body"},
        },
        extra_env={"FAKE_BRAIN_TOKEN": "tok"},
    )
    assert result.returncode == 0
    assert "mirror missing" in result.stderr


# ---- AC: WebSearch is skipped ---------------------------------------------


def test_websearch_is_skipped(tmp_path):
    cfg = _fresh_config(tmp_path)
    _setup_tausik(tmp_path, brain_cfg=cfg)
    _make_brain_db(tmp_path / "brain.db")
    capture = str(tmp_path / "capture.json")
    shim = _make_stub_runtime(tmp_path, capture)
    result = _run(
        tmp_path,
        {
            "tool_name": "WebSearch",
            "tool_input": {"query": "anything"},
            "tool_response": "Web search results...",
        },
        pythonpath_prepend=shim,
        extra_env={"FAKE_BRAIN_TOKEN": "tok"},
    )
    assert result.returncode == 0
    assert not os.path.exists(capture), "WebSearch must not trigger a cache write"


# ---- AC: empty / error / malformed payloads ------------------------------


def test_empty_tool_response_skips_write(tmp_path):
    cfg = _fresh_config(tmp_path)
    _setup_tausik(tmp_path, brain_cfg=cfg)
    _make_brain_db(tmp_path / "brain.db")
    capture = str(tmp_path / "capture.json")
    shim = _make_stub_runtime(tmp_path, capture)
    result = _run(
        tmp_path,
        {
            "tool_name": "WebFetch",
            "tool_input": {"url": "https://x.example"},
            "tool_response": {"url": "https://x.example", "result": ""},
        },
        pythonpath_prepend=shim,
        extra_env={"FAKE_BRAIN_TOKEN": "tok"},
    )
    assert result.returncode == 0
    assert not os.path.exists(capture)
    assert "empty url or content" in result.stderr


def test_error_http_code_skips_write(tmp_path):
    cfg = _fresh_config(tmp_path)
    _setup_tausik(tmp_path, brain_cfg=cfg)
    _make_brain_db(tmp_path / "brain.db")
    capture = str(tmp_path / "capture.json")
    shim = _make_stub_runtime(tmp_path, capture)
    result = _run(
        tmp_path,
        {
            "tool_name": "WebFetch",
            "tool_input": {"url": "https://x.example"},
            "tool_response": {
                "url": "https://x.example",
                "result": "Not Found",
                "code": 404,
            },
        },
        pythonpath_prepend=shim,
        extra_env={"FAKE_BRAIN_TOKEN": "tok"},
    )
    assert result.returncode == 0
    assert not os.path.exists(capture)


def test_malformed_stdin_exits_zero(tmp_path):
    cfg = _fresh_config(tmp_path)
    _setup_tausik(tmp_path, brain_cfg=cfg)
    _make_brain_db(tmp_path / "brain.db")
    result = _run(
        tmp_path,
        {},
        stdin_override="{not valid json",
        extra_env={"FAKE_BRAIN_TOKEN": "tok"},
    )
    assert result.returncode == 0


def test_oversized_stdin_exits_zero(tmp_path):
    cfg = _fresh_config(tmp_path)
    _setup_tausik(tmp_path, brain_cfg=cfg)
    _make_brain_db(tmp_path / "brain.db")
    blob = "a" * (2 * 1024 * 1024)  # 2 MiB > 1 MiB cap
    result = _run(
        tmp_path,
        {},
        stdin_override=blob,
        extra_env={"FAKE_BRAIN_TOKEN": "tok"},
    )
    assert result.returncode == 0


# ---- AC: private-URL filter ----------------------------------------------


def test_private_url_skipped(tmp_path):
    cfg = _fresh_config(tmp_path, private_patterns=[r"\.internal(?:$|/|:)"])
    _setup_tausik(tmp_path, brain_cfg=cfg)
    _make_brain_db(tmp_path / "brain.db")
    capture = str(tmp_path / "capture.json")
    shim = _make_stub_runtime(tmp_path, capture)
    result = _run(
        tmp_path,
        {
            "tool_name": "WebFetch",
            "tool_input": {"url": "https://wiki.internal/page"},
            "tool_response": {
                "url": "https://wiki.internal/page",
                "result": "internal wiki text",
            },
        },
        pythonpath_prepend=shim,
        extra_env={"FAKE_BRAIN_TOKEN": "tok"},
    )
    assert result.returncode == 0
    assert not os.path.exists(capture)
    assert "private url" in result.stderr


# ---- AC: already-cached-fresh skip ---------------------------------------


def test_already_fresh_cache_skips_write(tmp_path):
    cfg = _fresh_config(tmp_path)
    _setup_tausik(tmp_path, brain_cfg=cfg)
    mirror = tmp_path / "brain.db"
    _make_brain_db(mirror)
    target = "https://example.com/article"
    _insert_web_cache(
        mirror,
        notion_page_id="page-existing",
        url=target,
    )

    capture = str(tmp_path / "capture.json")
    shim = _make_stub_runtime(tmp_path, capture)
    result = _run(
        tmp_path,
        {
            "tool_name": "WebFetch",
            "tool_input": {"url": target, "prompt": "summarize"},
            "tool_response": {"url": target, "result": "fresh body"},
        },
        pythonpath_prepend=shim,
        extra_env={"FAKE_BRAIN_TOKEN": "tok"},
    )
    assert result.returncode == 0
    assert not os.path.exists(capture)
    assert "already fresh" in result.stderr


def test_stale_cache_triggers_write(tmp_path):
    cfg = _fresh_config(tmp_path)
    _setup_tausik(tmp_path, brain_cfg=cfg)
    mirror = tmp_path / "brain.db"
    _make_brain_db(mirror)
    target = "https://example.com/stale-article"
    stale = (
        (_dt.datetime.now(tz=_dt.timezone.utc) - _dt.timedelta(days=45))
        .isoformat()
        .replace("+00:00", "Z")
    )
    _insert_web_cache(
        mirror,
        notion_page_id="page-old",
        url=target,
        fetched_at=stale,
    )
    capture = str(tmp_path / "capture.json")
    shim = _make_stub_runtime(tmp_path, capture)
    result = _run(
        tmp_path,
        {
            "tool_name": "WebFetch",
            "tool_input": {"url": target, "prompt": "refresh query"},
            "tool_response": {"url": target, "result": "fresh content after rewrite"},
        },
        pythonpath_prepend=shim,
        extra_env={"FAKE_BRAIN_TOKEN": "tok"},
    )
    assert result.returncode == 0
    assert os.path.exists(capture), result.stderr
    with open(capture, encoding="utf-8") as f:
        cap = json.load(f)
    assert cap["url"] == target
    assert cap["content_head"].startswith("fresh content")
    assert cap["query"] == "refresh query"


# ---- AC: happy path write -------------------------------------------------


def test_happy_path_writes_to_cache(tmp_path):
    cfg = _fresh_config(tmp_path)
    _setup_tausik(tmp_path, brain_cfg=cfg)
    _make_brain_db(tmp_path / "brain.db")
    capture = str(tmp_path / "capture.json")
    shim = _make_stub_runtime(tmp_path, capture)
    target = "https://example.com/new-article"
    result = _run(
        tmp_path,
        {
            "tool_name": "WebFetch",
            "tool_input": {"url": target, "prompt": "what does this do"},
            "tool_response": {
                "url": target,
                "result": "# Article\nThis is the body.",
                "code": 200,
            },
        },
        pythonpath_prepend=shim,
        extra_env={"FAKE_BRAIN_TOKEN": "tok"},
    )
    assert result.returncode == 0
    assert os.path.exists(capture), f"expected write; stderr={result.stderr}"
    with open(capture, encoding="utf-8") as f:
        cap = json.load(f)
    assert cap["url"] == target
    assert cap["query"] == "what does this do"
    assert "Article" in cap["content_head"]


def test_string_tool_response_also_writes(tmp_path):
    """Some harness versions pass tool_response as a bare string."""
    cfg = _fresh_config(tmp_path)
    _setup_tausik(tmp_path, brain_cfg=cfg)
    _make_brain_db(tmp_path / "brain.db")
    capture = str(tmp_path / "capture.json")
    shim = _make_stub_runtime(tmp_path, capture)
    target = "https://example.com/bare"
    result = _run(
        tmp_path,
        {
            "tool_name": "WebFetch",
            "tool_input": {"url": target, "prompt": ""},
            "tool_response": "bare string content",
        },
        pythonpath_prepend=shim,
        extra_env={"FAKE_BRAIN_TOKEN": "tok"},
    )
    assert result.returncode == 0
    assert os.path.exists(capture)
    with open(capture, encoding="utf-8") as f:
        cap = json.load(f)
    assert cap["content_head"] == "bare string content"


def test_content_truncated_at_cap(tmp_path):
    cfg = _fresh_config(tmp_path)
    _setup_tausik(tmp_path, brain_cfg=cfg)
    _make_brain_db(tmp_path / "brain.db")
    capture = str(tmp_path / "capture.json")
    shim = _make_stub_runtime(tmp_path, capture)
    target = "https://example.com/huge"
    huge = "x" * 500_000  # well over 200_000 cap
    result = _run(
        tmp_path,
        {
            "tool_name": "WebFetch",
            "tool_input": {"url": target, "prompt": ""},
            "tool_response": {"url": target, "result": huge},
        },
        pythonpath_prepend=shim,
        extra_env={"FAKE_BRAIN_TOKEN": "tok"},
    )
    assert result.returncode == 0
    assert os.path.exists(capture)
    with open(capture, encoding="utf-8") as f:
        cap = json.load(f)
    # The stub captures len(content) after hook truncation.
    assert cap["content_len"] == 200_000


def test_response_url_overrides_input_url(tmp_path):
    """Redirects: response.url wins over input.url for cache key."""
    cfg = _fresh_config(tmp_path)
    _setup_tausik(tmp_path, brain_cfg=cfg)
    _make_brain_db(tmp_path / "brain.db")
    capture = str(tmp_path / "capture.json")
    shim = _make_stub_runtime(tmp_path, capture)
    input_url = "https://example.com/old"
    final_url = "https://example.com/redirected"
    result = _run(
        tmp_path,
        {
            "tool_name": "WebFetch",
            "tool_input": {"url": input_url, "prompt": ""},
            "tool_response": {"url": final_url, "result": "body", "code": 200},
        },
        pythonpath_prepend=shim,
        extra_env={"FAKE_BRAIN_TOKEN": "tok"},
    )
    assert result.returncode == 0
    with open(capture, encoding="utf-8") as f:
        cap = json.load(f)
    assert cap["url"] == final_url


# ---- Regression: hook never raises / never emits exit != 0 ---------------


def test_non_watched_tool_exits_zero(tmp_path):
    _setup_tausik(tmp_path, brain_cfg=_fresh_config(tmp_path))
    result = _run(
        tmp_path,
        {"tool_name": "Read", "tool_input": {"file_path": "/tmp/x"}},
    )
    assert result.returncode == 0


def test_non_dict_tool_input_exits_zero(tmp_path):
    _setup_tausik(tmp_path, brain_cfg=_fresh_config(tmp_path))
    result = _run(
        tmp_path,
        {"tool_name": "WebFetch", "tool_input": "not a dict"},
    )
    assert result.returncode == 0


@pytest.mark.parametrize(
    "status,issues,expect_warn",
    [
        ("scrub_blocked", [{"detector": "private_urls"}], True),
        ("notion_error", [], True),
        ("bad_fields", [], True),
    ],
)
def test_write_failure_is_silent_without_debug(tmp_path, status, issues, expect_warn):
    """All store_record failure modes must keep the hook at exit 0 + no stderr noise unless debug."""
    cfg = _fresh_config(tmp_path)
    _setup_tausik(tmp_path, brain_cfg=cfg)
    _make_brain_db(tmp_path / "brain.db")
    # Shim runtime that returns (False, reason) for the requested status.
    shim = tmp_path / "shim_fail"
    shim.mkdir()
    (shim / "brain_runtime.py").write_text(
        f'def try_brain_write_web_cache(url, content, cfg, *, query="", title=None):\n'
        f'    return (False, "{status}: stubbed")\n',
        encoding="utf-8",
    )
    env = {
        **os.environ,
        "CLAUDE_PROJECT_DIR": str(tmp_path),
        "TAUSIK_DIR": str(tmp_path / ".tausik"),
        "PYTHONUTF8": "1",
        "PYTHONIOENCODING": "utf-8",
        "FAKE_BRAIN_TOKEN": "tok",
        # Prepend shim + _SCRIPTS so the hook's sys.path guard skips the
        # _SCRIPTS_DIR re-insert and the shim brain_runtime wins. See
        # the comment in _run() for the same pattern.
        "PYTHONPATH": os.pathsep.join([str(shim), _SCRIPTS, env_pythonpath()]).rstrip(
            os.pathsep
        ),
    }
    env.pop("TAUSIK_SKIP_HOOKS", None)
    env.pop("TAUSIK_BRAIN_HOOK_DEBUG", None)
    result = subprocess.run(
        [sys.executable, _HOOK_PATH],
        input=json.dumps(
            {
                "tool_name": "WebFetch",
                "tool_input": {"url": "https://x.example"},
                "tool_response": {"url": "https://x.example", "result": "body"},
            }
        ),
        capture_output=True,
        text=True,
        timeout=15,
        env=env,
    )
    assert result.returncode == 0
    # Without debug flag, hook stays silent.
    assert result.stderr == ""


def env_pythonpath() -> str:
    return os.environ.get("PYTHONPATH", "")
