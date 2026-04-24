"""Tests for the brain_search_proactive PreToolUse hook.

Covers: disabled brain, missing mirror DB, non-watched tools, URL-exact hits,
FTS hits, stale cache, bypass marker, malformed stdin, and TTL edge cases.
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import sqlite3
import subprocess
import sys

import pytest

_HOOK_PATH = os.path.join(
    os.path.dirname(__file__), "..", "scripts", "hooks", "brain_search_proactive.py"
)
_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

from brain_schema import apply_schema  # noqa: E402


def _run(
    project_dir,
    payload: dict,
    extra_env: dict | None = None,
) -> subprocess.CompletedProcess:
    env = {
        **os.environ,
        "CLAUDE_PROJECT_DIR": str(project_dir),
        "TAUSIK_DIR": str(os.path.join(project_dir, ".tausik")),
        "PYTHONUTF8": "1",
        "PYTHONIOENCODING": "utf-8",
    }
    env.pop("TAUSIK_SKIP_HOOKS", None)
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        [sys.executable, _HOOK_PATH],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=15,
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
    name: str,
    content: str,
    query: str = "",
    fetched_at: str | None = None,
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
            "VALUES(?, ?, ?, ?, ?, ?, ?, '[]', 'abc123', 'hash', ?, ?)",
            (
                notion_page_id,
                name,
                url,
                query,
                content,
                fetched_at,
                url.split("/")[2] if url.count("/") >= 2 else "",
                fetched_at,
                fetched_at,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def _write_transcript(tmp_path, text: str) -> str:
    path = tmp_path / "transcript.jsonl"
    event = {"type": "user", "message": {"content": text}}
    with open(path, "w", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")
    return str(path)


def _fresh_config(tmp_path) -> dict:
    mirror = tmp_path / "brain.db"
    return {
        "enabled": True,
        "local_mirror_path": str(mirror),
        "notion_integration_token_env": "FAKE_TOKEN",
        "database_ids": {
            "decisions": "d1",
            "web_cache": "w1",
            "patterns": "p1",
            "gotchas": "g1",
        },
        "ttl_web_cache_days": 30,
    }


# --- AC2: brain disabled → exit 0 -----------------------------------------


def test_brain_disabled_exits_zero(tmp_path):
    _setup_tausik(tmp_path, brain_cfg={"enabled": False})
    result = _run(
        tmp_path,
        {
            "tool_name": "WebSearch",
            "tool_input": {"query": "anything"},
            "transcript_path": "",
        },
    )
    assert result.returncode == 0
    assert result.stderr == ""


def test_no_brain_section_exits_zero(tmp_path):
    _setup_tausik(tmp_path)  # no config.json at all
    result = _run(
        tmp_path,
        {
            "tool_name": "WebSearch",
            "tool_input": {"query": "anything"},
            "transcript_path": "",
        },
    )
    assert result.returncode == 0


# --- AC3: mirror DB missing → exit 0 --------------------------------------


def test_mirror_db_missing_exits_zero(tmp_path):
    cfg = _fresh_config(tmp_path)
    # Note: do NOT create the mirror DB file.
    _setup_tausik(tmp_path, brain_cfg=cfg)
    result = _run(
        tmp_path,
        {
            "tool_name": "WebSearch",
            "tool_input": {"query": "anything"},
            "transcript_path": "",
        },
    )
    assert result.returncode == 0


def test_no_tausik_db_exits_zero(tmp_path):
    # No .tausik dir at all.
    result = _run(
        tmp_path,
        {
            "tool_name": "WebSearch",
            "tool_input": {"query": "anything"},
            "transcript_path": "",
        },
    )
    assert result.returncode == 0


# --- AC4: WebSearch FTS hit → exit 2 --------------------------------------


def test_websearch_fts_fresh_hit_blocks(tmp_path):
    cfg = _fresh_config(tmp_path)
    _setup_tausik(tmp_path, brain_cfg=cfg)
    mirror = tmp_path / "brain.db"
    _make_brain_db(mirror)
    _insert_web_cache(
        mirror,
        notion_page_id="page-abc",
        url="https://docs.python.org/3/library/asyncio.html",
        name="Python asyncio documentation",
        content="asyncio event loop primer and patterns",
        query="python asyncio event loop",
    )

    result = _run(
        tmp_path,
        {
            "tool_name": "WebSearch",
            "tool_input": {"query": "python asyncio event loop"},
            "transcript_path": "",
        },
    )
    assert result.returncode == 2, result.stderr
    assert "BLOCKED" in result.stderr
    assert "page-abc" in result.stderr
    assert "docs.python.org" in result.stderr
    assert "refresh: web_cache" in result.stderr


# --- AC5: WebFetch URL-exact hit → exit 2 ---------------------------------


def test_webfetch_exact_url_match_blocks(tmp_path):
    cfg = _fresh_config(tmp_path)
    _setup_tausik(tmp_path, brain_cfg=cfg)
    mirror = tmp_path / "brain.db"
    _make_brain_db(mirror)
    target_url = "https://example.com/article?id=42"
    _insert_web_cache(
        mirror,
        notion_page_id="page-exact",
        url=target_url,
        name="Example article",
        content="Generic article body",
    )

    result = _run(
        tmp_path,
        {
            "tool_name": "WebFetch",
            "tool_input": {"url": target_url, "prompt": "summarize this"},
            "transcript_path": "",
        },
    )
    assert result.returncode == 2
    assert "page-exact" in result.stderr
    assert target_url in result.stderr


def test_webfetch_url_mismatch_but_prompt_fts_blocks(tmp_path):
    cfg = _fresh_config(tmp_path)
    _setup_tausik(tmp_path, brain_cfg=cfg)
    mirror = tmp_path / "brain.db"
    _make_brain_db(mirror)
    _insert_web_cache(
        mirror,
        notion_page_id="page-fts",
        url="https://existing.example.com/a",
        name="kubernetes network policies",
        content="how kubernetes network policies work under CNI",
    )

    # Different URL — exact match fails — but prompt matches FTS content
    result = _run(
        tmp_path,
        {
            "tool_name": "WebFetch",
            "tool_input": {
                "url": "https://other.example.com/totally-different",
                "prompt": "kubernetes network policies",
            },
            "transcript_path": "",
        },
    )
    assert result.returncode == 2
    assert "page-fts" in result.stderr


# --- AC6: stale cache → exit 0 --------------------------------------------


def test_stale_cache_allows_fetch(tmp_path):
    cfg = _fresh_config(tmp_path)
    _setup_tausik(tmp_path, brain_cfg=cfg)
    mirror = tmp_path / "brain.db"
    _make_brain_db(mirror)
    stale = (
        (_dt.datetime.now(tz=_dt.timezone.utc) - _dt.timedelta(days=45))
        .isoformat()
        .replace("+00:00", "Z")
    )
    _insert_web_cache(
        mirror,
        notion_page_id="page-stale",
        url="https://stale.example.com/x",
        name="old",
        content="old content",
        fetched_at=stale,
    )

    result = _run(
        tmp_path,
        {
            "tool_name": "WebFetch",
            "tool_input": {"url": "https://stale.example.com/x", "prompt": "x"},
            "transcript_path": "",
        },
    )
    assert result.returncode == 0
    assert result.stderr == ""


def test_ttl_none_never_expires(tmp_path):
    cfg = _fresh_config(tmp_path)
    cfg["ttl_web_cache_days"] = None  # never expire
    _setup_tausik(tmp_path, brain_cfg=cfg)
    mirror = tmp_path / "brain.db"
    _make_brain_db(mirror)
    very_old = (
        (_dt.datetime.now(tz=_dt.timezone.utc) - _dt.timedelta(days=365 * 3))
        .isoformat()
        .replace("+00:00", "Z")
    )
    _insert_web_cache(
        mirror,
        notion_page_id="page-ancient",
        url="https://ancient.example.com/a",
        name="ancient",
        content="never decays",
        fetched_at=very_old,
    )

    result = _run(
        tmp_path,
        {
            "tool_name": "WebFetch",
            "tool_input": {"url": "https://ancient.example.com/a", "prompt": "a"},
            "transcript_path": "",
        },
    )
    assert result.returncode == 2


# --- AC7: no match → exit 0 -----------------------------------------------


def test_no_cache_hit_allows_fetch(tmp_path):
    cfg = _fresh_config(tmp_path)
    _setup_tausik(tmp_path, brain_cfg=cfg)
    mirror = tmp_path / "brain.db"
    _make_brain_db(mirror)  # empty DB, schema only

    result = _run(
        tmp_path,
        {
            "tool_name": "WebSearch",
            "tool_input": {"query": "completely unrelated never-seen-query"},
            "transcript_path": "",
        },
    )
    assert result.returncode == 0


# --- AC8: bypass marker → exit 0 ------------------------------------------


def test_bypass_marker_allows_fetch(tmp_path):
    cfg = _fresh_config(tmp_path)
    _setup_tausik(tmp_path, brain_cfg=cfg)
    mirror = tmp_path / "brain.db"
    _make_brain_db(mirror)
    _insert_web_cache(
        mirror,
        notion_page_id="page-bypass",
        url="https://cached.example.com/",
        name="stale info",
        content="content that is probably outdated",
    )
    transcript = _write_transcript(
        tmp_path, "Please re-check, I think the docs changed.\nrefresh: web_cache"
    )

    result = _run(
        tmp_path,
        {
            "tool_name": "WebFetch",
            "tool_input": {
                "url": "https://cached.example.com/",
                "prompt": "reread me",
            },
            "transcript_path": transcript,
        },
    )
    assert result.returncode == 0


# --- Non-watched tools & TAUSIK_SKIP_HOOKS & malformed stdin --------------


def test_non_watched_tool_exits_zero(tmp_path):
    cfg = _fresh_config(tmp_path)
    _setup_tausik(tmp_path, brain_cfg=cfg)
    mirror = tmp_path / "brain.db"
    _make_brain_db(mirror)
    _insert_web_cache(
        mirror,
        notion_page_id="p",
        url="https://x.example.com/",
        name="n",
        content="c",
    )

    result = _run(
        tmp_path,
        {
            "tool_name": "Bash",
            "tool_input": {"command": "ls"},
            "transcript_path": "",
        },
    )
    assert result.returncode == 0


def test_skip_hooks_env_exits_zero(tmp_path):
    cfg = _fresh_config(tmp_path)
    _setup_tausik(tmp_path, brain_cfg=cfg)
    mirror = tmp_path / "brain.db"
    _make_brain_db(mirror)
    _insert_web_cache(
        mirror,
        notion_page_id="p",
        url="https://x.example.com/",
        name="n",
        content="c",
    )
    result = _run(
        tmp_path,
        {
            "tool_name": "WebFetch",
            "tool_input": {"url": "https://x.example.com/", "prompt": "q"},
            "transcript_path": "",
        },
        extra_env={"TAUSIK_SKIP_HOOKS": "1"},
    )
    assert result.returncode == 0


def test_malformed_stdin_exits_zero(tmp_path):
    cfg = _fresh_config(tmp_path)
    _setup_tausik(tmp_path, brain_cfg=cfg)
    env = {
        **os.environ,
        "CLAUDE_PROJECT_DIR": str(tmp_path),
        "TAUSIK_DIR": str(tmp_path / ".tausik"),
    }
    env.pop("TAUSIK_SKIP_HOOKS", None)
    result = subprocess.run(
        [sys.executable, _HOOK_PATH],
        input="not json at all {",
        capture_output=True,
        text=True,
        timeout=15,
        env=env,
    )
    assert result.returncode == 0


def test_empty_query_exits_zero(tmp_path):
    cfg = _fresh_config(tmp_path)
    _setup_tausik(tmp_path, brain_cfg=cfg)
    mirror = tmp_path / "brain.db"
    _make_brain_db(mirror)
    result = _run(
        tmp_path,
        {
            "tool_name": "WebSearch",
            "tool_input": {"query": ""},
            "transcript_path": "",
        },
    )
    assert result.returncode == 0


# --- bootstrap_generate registration ---------------------------------------


def test_bootstrap_generate_registers_brain_search_proactive():
    """AC9: hook must be wired into Claude's PreToolUse handlers. Cursor has
    no hook runtime — it uses .cursorrules text — so it's intentionally scoped
    out."""
    import inspect

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "bootstrap"))
    import bootstrap_generate  # noqa: E402

    claude_src = inspect.getsource(bootstrap_generate.generate_settings_claude)
    assert "brain_search_proactive.py" in claude_src
    assert "WebSearch" in claude_src and "WebFetch" in claude_src


# --- Fresh ISO variants parse correctly -----------------------------------


@pytest.mark.parametrize(
    "ts",
    [
        "2999-04-24T10:00:00Z",
        "2999-04-24T10:00:00.000Z",
        "2999-04-24T10:00:00.123456Z",
        "2999-04-24T10:00:00+00:00",
    ],
)
def test_iso_timestamp_variants_treated_as_fresh(tmp_path, ts):
    cfg = _fresh_config(tmp_path)
    _setup_tausik(tmp_path, brain_cfg=cfg)
    mirror = tmp_path / "brain.db"
    _make_brain_db(mirror)
    _insert_web_cache(
        mirror,
        notion_page_id="page-future",
        url="https://future.example.com/x",
        name="future",
        content="future content",
        fetched_at=ts,
    )
    result = _run(
        tmp_path,
        {
            "tool_name": "WebFetch",
            "tool_input": {
                "url": "https://future.example.com/x",
                "prompt": "future",
            },
            "transcript_path": "",
        },
    )
    assert result.returncode == 2, f"ts={ts!r} should be fresh"
