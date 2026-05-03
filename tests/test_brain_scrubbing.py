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
    r = brain_scrubbing.scrub_with_config("Bm25 ranks FTS5 results by relevance.", cfg={})
    assert r["ok"] is True
    assert r["issues"] == []


# ---- Filesystem paths ------------------------------------------------
# v1.4 (v14b-parametrize-top4): cluster collapsed. Path-blocked + path-pass
# cases share `scrub(text) → ok=<bool>` shape. The detailed first case
# (POSIX /home, with match-substring assertion) stays explicit because it
# verifies the issue.match field, not just the boolean.


def test_posix_home_path_blocked_with_match_substring():
    r = brain_scrubbing.scrub("See /home/alice/work/secret for details.")
    assert r["ok"] is False
    assert any(i["detector"] == "filesystem_paths" for i in r["issues"])
    assert "/home/alice/work/secret" in r["issues"][0]["match"]


@pytest.mark.parametrize(
    "content,expected_ok",
    [
        pytest.param(
            "Config at /Users/bob/projects/top-secret", False, id="posix_users_path_blocked"
        ),
        pytest.param(
            "Open D:\\Work\\Kibertum\\laplandka\\foo.py", False, id="windows_drive_path_blocked"
        ),
        pytest.param(
            "See C:/Users/carol/code/bank/api.py",
            False,
            id="windows_forward_slash_path_blocked",
        ),
        pytest.param("See src/api/models.py and ./helpers.ts", True, id="relative_paths_pass"),
        pytest.param(
            "Docs at https://example.com/users/alice", True, id="url_path_not_flagged_as_filesystem"
        ),
    ],
)
def test_filesystem_path_detection(content, expected_ok):
    r = brain_scrubbing.scrub(content)
    assert r["ok"] is expected_ok
    if not expected_ok:
        # Sanity: failure must be attributed to filesystem_paths detector.
        assert any(i["detector"] == "filesystem_paths" for i in r["issues"])


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


def test_project_name_empty_blocklist_passes():
    r = brain_scrubbing.scrub("Laplandka deployment", project_names=[])
    assert r["ok"] is True


def test_project_name_multiple_matches_dedup():
    r = brain_scrubbing.scrub(
        "Laplandka did it. Laplandka again. LAPLANDKA once more.",
        project_names=["laplandka"],
    )
    block_issues = [i for i in r["issues"] if i["detector"] == "project_names_blocklist"]
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
    r = brain_scrubbing.scrub_with_config("We fixed hypelink and https://x.internal.co/", cfg=cfg)
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


# ---- Blocklist + bypass defenses (homoglyphs, zero-width, URL-encoding) -----
# v1.4 (v14b-parametrize-top4): clusters ce0bd5c98f81d28e + 56ef61843572624f
# collapsed. All cases share the (text, kwargs) -> ok=<bool> shape. Tests with
# unique extra assertions (cyrillic_homoglyph_bypass detector check) stay in
# dedicated functions to preserve their explicit AC.


def test_blocklist_cyrillic_homoglyph_bypass_blocked_named_detector():
    """Cyrillic 'm' (U+043C) looks like Latin 'm' but has different bytes.

    Verifies the issue is attributed to project_names_blocklist (not to a
    wrong detector) - extra assertion that wouldn't survive parametrize.
    """
    r = brain_scrubbing.scrub(
        "We deployed мegacorp to staging",  # first char is Cyrillic
        project_names=["megacorp"],
    )
    assert r["ok"] is False
    detectors = [i["detector"] for i in r["issues"]]
    assert "project_names_blocklist" in detectors


@pytest.mark.parametrize(
    "content,kwargs,expected_ok",
    [
        # --- cluster 56ef6184 (mixed blocklist + URL passes) -----------------
        pytest.param(
            "Docs at https://python.org/3.12",
            {"private_url_patterns": [r"\.internal\."]},
            True,
            id="public_url_with_private_pattern_passes",
        ),
        pytest.param(
            "SECRET-PROJECT delivered on time.",
            {"project_names": ["secret-project"]},
            False,
            id="project_name_case_insensitive",
        ),
        pytest.param(
            "Ленинка сегодня упала.",
            {"project_names": ["ленинка"]},
            False,
            id="unicode_content_with_russian_project_name_blocked",
        ),
        pytest.param(
            "the meg‍acorp deployment failed",  # ZWJ
            {"project_names": ["megacorp"]},
            False,
            id="blocklist_zero_width_joiner_bypass_blocked",
        ),
        pytest.param(
            "See https://example.com/path?q=%6Degacorp%20docs",
            {"project_names": ["megacorp"]},
            False,
            id="blocklist_url_encoded_bypass_blocked",
        ),
        pytest.param(
            "Jump to &#x6D;egacorp channel",  # &#x6D; = 'm'
            {"project_names": ["megacorp"]},
            False,
            id="blocklist_html_named_entity_bypass_blocked",
        ),
        pytest.param(
            "Check Αpex dashboard",  # Greek Alpha (U+0391)
            {"project_names": ["apex"]},
            False,
            id="blocklist_greek_homoglyph_blocked",
        ),
        pytest.param(
            "мanager of megacorp",  # Cyrillic m
            {"project_names": ["manager"]},
            False,
            id="blocklist_cyrillic_lowercase_m_blocked",
        ),
        pytest.param(
            "тrinket",  # Cyrillic t
            {"project_names": ["trinket"]},
            False,
            id="blocklist_cyrillic_lowercase_t_blocked",
        ),
        # --- cluster ce0bd5c9 (homoglyph / bypass blocked) -------------------
        pytest.param(
            "The асме project is confidential",  # all Cyrillic
            {"project_names": ["acme"]},
            False,
            id="blocklist_all_cyrillic_homoglyphs_blocked",
        ),
        pytest.param(
            "Contact the meg​acorp team by Friday",  # ZWSP
            {"project_names": ["megacorp"]},
            False,
            id="blocklist_zero_width_bypass_blocked",
        ),
        pytest.param(
            "See https://example.com/?q=%256Degacorp%20docs",  # %256D -> %6D -> 'm'
            {"project_names": ["megacorp"]},
            False,
            id="blocklist_double_url_encoded_bypass_blocked",
        ),
        pytest.param(
            "Old docs said &#109;egacorp is the next sprint target",  # &#109;='m'
            {"project_names": ["megacorp"]},
            False,
            id="blocklist_html_numeric_entity_bypass_blocked",
        ),
        pytest.param(
            "Talk to М​egacorp tomorrow",  # Cyrillic M + ZWSP
            {"project_names": ["megacorp"]},
            False,
            id="blocklist_mixed_homoglyph_and_zero_width_blocked",
        ),
        pytest.param(
            "the αpex dashboard",  # Greek alpha
            {"project_names": ["apex"]},
            False,
            id="blocklist_greek_lowercase_alpha_blocked",
        ),
        pytest.param(
            "Вrincess project",  # Cyrillic V (U+0412) -> 'b'
            {"project_names": ["brincess"]},
            False,
            id="blocklist_cyrillic_lowercase_v_blocked",
        ),
        pytest.param(
            "кernel module",  # Cyrillic k
            {"project_names": ["kernel"]},
            False,
            id="blocklist_cyrillic_lowercase_k_blocked",
        ),
        pytest.param(
            "νanguard tracker",  # Greek nu
            {"project_names": ["vanguard"]},
            False,
            id="blocklist_greek_lowercase_nu_blocked",
        ),
        pytest.param(
            "ρroject name here",  # Greek rho
            {"project_names": ["project"]},
            False,
            id="blocklist_greek_lowercase_rho_blocked",
        ),
        pytest.param(
            "Deploying Café to prod",  # NFD: Cafe + combining acute
            {"project_names": ["cafe"]},
            False,
            id="blocklist_combining_marks_stripped",
        ),
        pytest.param(
            "MEGACORP ran out of budget",
            {"project_names": ["megacorp"]},
            False,
            id="blocklist_case_insensitive_regression",
        ),
    ],
)
def test_blocklist_and_bypass_detection(content, kwargs, expected_ok):
    r = brain_scrubbing.scrub(content, **kwargs)
    assert r["ok"] is expected_ok


def test_blocklist_no_false_positive_on_unrelated_substring():
    """Regression: 'crate' should NOT match blocklist=['rate'] in this test,
    but the substring-based blocklist DOES trigger on 'rate' inside 'crate'.
    This test documents that behavior is UNCHANGED by the homoglyph fix —
    the fix only defeats obfuscation, it does not tighten substring rules."""
    r = brain_scrubbing.scrub(
        "We ordered a wooden crate for the office",
        project_names=["rate"],
    )
    # Pre-fix behavior is that 'rate' IS a substring of 'crate'; the fix
    # preserves that. Asserting the unchanged behavior explicitly.
    assert r["ok"] is False
    r2 = brain_scrubbing.scrub(
        "totally unrelated content about lumber",
        project_names=["rate"],
    )
    assert r2["ok"] is True


def test_blocklist_case_insensitive_regression():
    """Existing behavior preserved: lowercase blocklist matches upper content."""
    r = brain_scrubbing.scrub(
        "MEGACORP ran out of budget",
        project_names=["megacorp"],
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
