"""Tests for brain_scrubbing — pre-write privacy linter."""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import brain_scrubbing  # noqa: E402


# ---- Clean content ---------------------------------------------------


def test_clean_content_passes():
    r = brain_scrubbing.scrub("Use pgbouncer for connection pooling.")
    assert r["ok"] is True
    assert r["issues"] == []


def test_clean_content_with_empty_config():
    r = brain_scrubbing.scrub_with_config(
        "Bm25 ranks FTS5 results by relevance.", cfg={}
    )
    assert r["ok"] is True
    assert r["issues"] == []


# ---- Filesystem paths ------------------------------------------------


def test_posix_home_path_blocked():
    r = brain_scrubbing.scrub("See /home/alice/work/secret for details.")
    assert r["ok"] is False
    assert any(i["detector"] == "filesystem_paths" for i in r["issues"])
    assert "/home/alice/work/secret" in r["issues"][0]["match"]


def test_posix_users_path_blocked():
    r = brain_scrubbing.scrub("Config at /Users/bob/projects/top-secret")
    assert r["ok"] is False
    assert r["issues"][0]["detector"] == "filesystem_paths"


def test_windows_drive_path_blocked():
    r = brain_scrubbing.scrub("Open D:\\Work\\Kibertum\\laplandka\\foo.py")
    assert r["ok"] is False
    assert r["issues"][0]["detector"] == "filesystem_paths"


def test_windows_forward_slash_path_blocked():
    r = brain_scrubbing.scrub("See C:/Users/carol/code/bank/api.py")
    assert r["ok"] is False
    assert any(i["detector"] == "filesystem_paths" for i in r["issues"])


def test_relative_paths_pass():
    r = brain_scrubbing.scrub("See src/api/models.py and ./helpers.ts")
    assert r["ok"] is True


def test_url_path_not_flagged_as_filesystem():
    r = brain_scrubbing.scrub("Docs at https://example.com/users/alice")
    assert r["ok"] is True


# ---- Emails ----------------------------------------------------------


def test_email_blocked():
    r = brain_scrubbing.scrub("Ping alice@example.com for access.")
    assert r["ok"] is False
    assert r["issues"][0]["detector"] == "emails"
    assert "alice@example.com" in r["issues"][0]["match"]


def test_multiple_emails_all_flagged():
    r = brain_scrubbing.scrub("Emails: a@b.io and c.d+tag@sub.example.co.")
    emails = [i for i in r["issues"] if i["detector"] == "emails"]
    assert len(emails) == 2


def test_email_like_without_tld_not_flagged():
    # no top-level domain → not an email
    r = brain_scrubbing.scrub("Variable: foo@bar")
    assert all(i["detector"] != "emails" for i in r["issues"])


# ---- Private URLs ----------------------------------------------------


def test_private_url_matches_configured_pattern():
    r = brain_scrubbing.scrub(
        "Grafana: https://grafana.internal.company.com/d/abc",
        private_url_patterns=[r"\.internal\."],
    )
    assert r["ok"] is False
    assert r["issues"][0]["detector"] == "private_urls"


def test_public_url_with_private_pattern_passes():
    r = brain_scrubbing.scrub(
        "Docs at https://python.org/3.12",
        private_url_patterns=[r"\.internal\."],
    )
    assert r["ok"] is True


def test_private_url_without_patterns_passes():
    r = brain_scrubbing.scrub("Internal: https://grafana.internal/board")
    assert r["ok"] is True  # no patterns configured


def test_invalid_regex_in_patterns_ignored():
    # bad regex should not crash scrub
    r = brain_scrubbing.scrub(
        "https://public.io/page",
        private_url_patterns=["[invalid(", r"\.internal\."],
    )
    assert r["ok"] is True  # neither valid pattern matches


# ---- Project-name blocklist ------------------------------------------


def test_project_name_exact_substring_blocked():
    r = brain_scrubbing.scrub(
        "Ran into this in Laplandka last week.",
        project_names=["laplandka"],
    )
    assert r["ok"] is False
    assert r["issues"][0]["detector"] == "project_names_blocklist"


def test_project_name_case_insensitive():
    r = brain_scrubbing.scrub(
        "SECRET-PROJECT delivered on time.",
        project_names=["secret-project"],
    )
    assert r["ok"] is False


def test_project_name_empty_blocklist_passes():
    r = brain_scrubbing.scrub("Laplandka deployment", project_names=[])
    assert r["ok"] is True


def test_project_name_multiple_matches_dedup():
    r = brain_scrubbing.scrub(
        "Laplandka did it. Laplandka again. LAPLANDKA once more.",
        project_names=["laplandka"],
    )
    block_issues = [
        i for i in r["issues"] if i["detector"] == "project_names_blocklist"
    ]
    assert len(block_issues) == 1  # dedup by needle


def test_project_name_ignores_non_string_entries():
    # simulate malformed config
    r = brain_scrubbing.scrub(
        "No match here",
        project_names=["laplandka", None, 42, ""],  # type: ignore[list-item]
    )
    assert r["ok"] is True


# ---- scrub_with_config -----------------------------------------------


def test_scrub_with_config_reads_fields():
    cfg = {
        "project_names": ["hypelink"],
        "private_url_patterns": [r"\.internal\."],
    }
    r = brain_scrubbing.scrub_with_config(
        "We fixed hypelink and https://x.internal.co/", cfg=cfg
    )
    assert r["ok"] is False
    detectors = {i["detector"] for i in r["issues"]}
    assert "project_names_blocklist" in detectors
    assert "private_urls" in detectors


def test_scrub_with_config_missing_fields_passes():
    r = brain_scrubbing.scrub_with_config("clean content", cfg={})
    assert r["ok"] is True


# ---- Multi-issue aggregation -----------------------------------------


def test_multiple_detectors_fire_simultaneously():
    r = brain_scrubbing.scrub(
        "Email alice@corp.com and see D:\\Work\\foo",
        project_names=["foo"],
    )
    detectors = {i["detector"] for i in r["issues"]}
    assert "emails" in detectors
    assert "filesystem_paths" in detectors
    assert "project_names_blocklist" in detectors


# ---- Types and edge cases --------------------------------------------


def test_non_string_content_raises():
    with pytest.raises(TypeError):
        brain_scrubbing.scrub(123)  # type: ignore[arg-type]


def test_empty_content_passes():
    r = brain_scrubbing.scrub("")
    assert r["ok"] is True
    assert r["issues"] == []


def test_unicode_content_cyrillic_clean():
    r = brain_scrubbing.scrub("Выбрали bm25 для ранжирования FTS5.")
    assert r["ok"] is True


def test_unicode_content_with_russian_project_name_blocked():
    r = brain_scrubbing.scrub(
        "Ленинка сегодня упала.",
        project_names=["ленинка"],
    )
    assert r["ok"] is False


# ---- Issue shape + format --------------------------------------------


def test_issue_shape_has_required_keys():
    r = brain_scrubbing.scrub("see /home/x/y")
    assert r["issues"]
    issue = r["issues"][0]
    for key in ("detector", "severity", "match", "hint"):
        assert key in issue


def test_format_issues_empty():
    md = brain_scrubbing.format_issues([])
    assert "No scrubbing issues" in md


def test_format_issues_renders_block_list():
    r = brain_scrubbing.scrub("email: a@b.com and /home/x/y")
    md = brain_scrubbing.format_issues(r["issues"])
    assert "Scrubbing blocked the write" in md
    assert "emails" in md
    assert "filesystem_paths" in md
    assert "a@b.com" in md
