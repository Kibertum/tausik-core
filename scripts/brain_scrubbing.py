"""Brain pre-write scrubbing linter — blocks project-specific leaks.

Run by the brain write-tools before persisting content to Notion. Pure
function: no I/O, no Notion calls, deterministic on the same input.

Four detectors, all `block` severity in v1:
  - filesystem_paths — absolute POSIX paths (/home/..., /Users/...) and
    Windows drive-letter paths (D:\\Work\\..., C:\\Users\\...).
  - emails — RFC5322-ish local@domain detection.
  - private_urls — any URL that matches one of the regexes configured in
    brain.private_url_patterns.
  - project_names_blocklist — case-insensitive substring match against
    project names listed in brain.project_names.

A non-empty `issues` list means `ok = False`: the write should be
refused and the issue list returned to the caller verbatim.

Design reference: references/brain-db-schema.md §2 (privacy model).
"""

from __future__ import annotations

import re
import unicodedata
from typing import Iterable
from urllib.parse import unquote

# ---- Regex sources ---------------------------------------------------

# POSIX absolute paths: /home/{user}/..., /Users/{user}/..., /root/...,
# /var/..., /opt/... (common user locations that leak project layout).
_POSIX_PATH = re.compile(
    r"(?:(?<![\w.-]))(?:/(?:home|Users|root|var|opt|srv|mnt)/[\w.\-/]{2,})"
)

# Windows drive-letter paths: C:\Users\..., D:\Work\... (both slashes).
_WINDOWS_PATH = re.compile(r"(?:(?<![\w.-]))[A-Za-z]:[\\/](?:[\w .\-]+[\\/])+[\w .\-]+")

# Email — RFC5322-ish pragmatic form.
_EMAIL = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")

# URL extractor (for private_urls detector we compile user-supplied
# regex filters on top of each matched URL).
_URL = re.compile(
    r"https?://[^\s<>\"')]+",
)


# ---- Public API ------------------------------------------------------


def _issue(detector: str, severity: str, match: str, hint: str) -> dict:
    return {
        "detector": detector,
        "severity": severity,
        "match": match,
        "hint": hint,
    }


def _compile_patterns(patterns: Iterable[str]) -> list[re.Pattern]:
    compiled: list[re.Pattern] = []
    for p in patterns or []:
        if not isinstance(p, str) or not p.strip():
            continue
        try:
            compiled.append(re.compile(p))
        except re.error:
            continue  # bad pattern — silently skip; validate_brain flags it
    return compiled


def _detect_paths(content: str) -> list[dict]:
    issues: list[dict] = []
    for m in _POSIX_PATH.finditer(content):
        path = m.group(0)
        issues.append(
            _issue(
                "filesystem_paths",
                "block",
                path,
                f"Remove absolute path '{path}'; use relative path or remove.",
            )
        )
    for m in _WINDOWS_PATH.finditer(content):
        path = m.group(0)
        issues.append(
            _issue(
                "filesystem_paths",
                "block",
                path,
                f"Remove absolute path '{path}'; use relative path or remove.",
            )
        )
    return issues


def _detect_emails(content: str) -> list[dict]:
    return [
        _issue(
            "emails",
            "block",
            m.group(0),
            f"Remove email '{m.group(0)}'; emails are personal data.",
        )
        for m in _EMAIL.finditer(content)
    ]


def _detect_private_urls(content: str, patterns: list[re.Pattern]) -> list[dict]:
    if not patterns:
        return []
    issues: list[dict] = []
    for m in _URL.finditer(content):
        url = m.group(0)
        for pat in patterns:
            if pat.search(url):
                issues.append(
                    _issue(
                        "private_urls",
                        "block",
                        url,
                        f"Remove internal URL '{url}'; matches configured"
                        f" private pattern.",
                    )
                )
                break
    return issues


#  --- Homoglyph / zero-width normalization (security-critical) ---
#
# A naive `needle.lower() in content.lower()` check lets the blocklist be
# bypassed three ways:
#   (a) Cyrillic/Greek homoglyphs (e.g. Cyrillic `а` U+0430 looks like
#       Latin `a` U+0061 but has different bytes);
#   (b) zero-width joiners/spaces/formatting chars inserted between letters
#       (e.g. `pri​ncess` with U+200B between `pri` and `ncess`);
#   (c) URL-encoded characters (`%70rincess` → `princess` only after decode).
# The normalization below canonicalizes input so each of those bypasses is
# collapsed to its plain form before substring matching.

# Common script homoglyphs → Latin. NFKC alone does NOT remap Cyrillic/Greek
# lookalikes because they live in distinct scripts, not compatibility
# decompositions.
_HOMOGLYPHS: dict[int, str] = {
    # Cyrillic lowercase
    ord("а"): "a",
    ord("е"): "e",
    ord("о"): "o",
    ord("р"): "p",
    ord("с"): "c",
    ord("х"): "x",
    ord("у"): "y",
    ord("і"): "i",
    ord("ѕ"): "s",
    ord("ј"): "j",
    # Cyrillic uppercase
    ord("А"): "A",
    ord("Е"): "E",
    ord("О"): "O",
    ord("Р"): "P",
    ord("С"): "C",
    ord("Х"): "X",
    ord("У"): "Y",
    ord("І"): "I",
    ord("Ѕ"): "S",
    ord("Ј"): "J",
    # Greek uppercase
    ord("Α"): "A",
    ord("Β"): "B",
    ord("Ε"): "E",
    ord("Ζ"): "Z",
    ord("Η"): "H",
    ord("Ι"): "I",
    ord("Κ"): "K",
    ord("Μ"): "M",
    ord("Ν"): "N",
    ord("Ο"): "O",
    ord("Ρ"): "P",
    ord("Τ"): "T",
    ord("Υ"): "Y",
    ord("Χ"): "X",
}

# ZW joiners / spaces / bidi formatting + BOM. re: (​-‏‪-‮⁠-⁤﻿)
_ZERO_WIDTH_RE = re.compile(r"[​-‏‪-‮⁠-⁤﻿]")


def _normalize_for_match(s: str) -> str:
    """Canonicalize a string for substring comparison against blocklist names.

    Steps (in order):
      1. NFKD — decompose both compatibility and canonical forms so a
         precomposed `é` (U+00E9) splits into `e` + `́` and can be
         stripped in the next step.
      2. Strip combining marks (category Mn), so `Café` (NFC) and `Cafe`
         both normalize to `cafe` after subsequent lowercasing.
      3. Remove zero-width / bidi formatting chars.
      4. Translate common Cyrillic/Greek homoglyphs to their Latin counterparts.
      5. Lowercase.
    """
    if not isinstance(s, str):
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    s = _ZERO_WIDTH_RE.sub("", s)
    s = s.translate(_HOMOGLYPHS)
    return s.lower()


def _detect_blocklist(content: str, project_names: Iterable[str]) -> list[dict]:
    issues: list[dict] = []
    if not project_names:
        return issues
    haystack_normal = _normalize_for_match(content)
    # Also scan the URL-decoded form — `%70rincess` → `princess` only after
    # decode. unquote() is safe on strings that contain no percent-escapes
    # (it returns the input unchanged).
    try:
        haystack_decoded = _normalize_for_match(unquote(content))
    except (UnicodeDecodeError, ValueError):
        haystack_decoded = haystack_normal
    seen: set[str] = set()
    for name in project_names:
        if not isinstance(name, str):
            continue
        needle = _normalize_for_match(name.strip())
        if not needle or needle in seen:
            continue
        if needle in haystack_normal or needle in haystack_decoded:
            issues.append(
                _issue(
                    "project_names_blocklist",
                    "block",
                    name,
                    f"Remove project reference '{name}'; this name is in"
                    f" the brain blocklist.",
                )
            )
            seen.add(needle)
    return issues


def scrub(
    content: str,
    *,
    project_names: Iterable[str] | None = None,
    private_url_patterns: Iterable[str] | None = None,
) -> dict:
    """Run all detectors on `content`. Returns {'ok': bool, 'issues': list}."""
    if not isinstance(content, str):
        raise TypeError("content must be a string")
    issues: list[dict] = []
    issues.extend(_detect_paths(content))
    issues.extend(_detect_emails(content))
    issues.extend(
        _detect_private_urls(content, _compile_patterns(private_url_patterns or []))
    )
    issues.extend(_detect_blocklist(content, project_names or []))
    return {"ok": not any(i["severity"] == "block" for i in issues), "issues": issues}


def scrub_with_config(
    content: str,
    cfg: dict,
    *,
    union_with_registry: bool = False,
) -> dict:
    """Scrub using blocklist + url patterns read from a brain config dict.

    When union_with_registry=True, merges in names from the global brain
    registry (~/.tausik-brain/projects.json) so a record generated inside
    project A cannot accidentally mention project B's name.
    """
    project_names = list(cfg.get("project_names") or [])
    if union_with_registry:
        import brain_project_registry

        for n in brain_project_registry.all_project_names():
            if n not in project_names:
                project_names.append(n)
    private_url_patterns = cfg.get("private_url_patterns") or []
    return scrub(
        content,
        project_names=project_names,
        private_url_patterns=private_url_patterns,
    )


def format_issues(issues: list[dict]) -> str:
    """Pretty-print scrub issues for surfacing to the MCP caller."""
    if not issues:
        return "_No scrubbing issues._"
    lines = ["**Scrubbing blocked the write.** Fix the following and retry:", ""]
    for i, issue in enumerate(issues, 1):
        lines.append(
            f"{i}. [{issue['severity']}] {issue['detector']}: `{issue['match']}`"
        )
        lines.append(f"   - {issue['hint']}")
    return "\n".join(lines)
