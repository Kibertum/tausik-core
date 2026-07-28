"""Invisible / hidden-instruction Unicode detector for skill content.

Task l26-skill-supply-chain-threat, AC4. A skill's SKILL.md is PROSE the agent
reads verbatim, so signature-scanning proves only WHO published it, not WHAT is
hidden inside. The 2026 attack (Unit 42, Snyk ToxicSkills) hides agent-directed
instructions in characters a human reviewer never sees:

  - U+E0000..U+E007F  Unicode TAG block — the primary "invisible instructions"
    vector; encodes ASCII as zero-width tag characters that some models read.
  - Zero-width formatting: U+200B ZWSP, U+200C ZWNJ, U+200D ZWJ, U+2060 word
    joiner, U+FEFF (BOM / zero-width no-break space) when not a leading BOM.
  - Bidi overrides / isolates (Trojan Source, CVE-2021-42574): U+202A..U+202E,
    U+2066..U+2069 — reorder visible text so the rendered form hides real intent.
  - U+00AD soft hyphen — invisible except at a line break.

This COMPLEMENTS ``brain_scrubbing._ZERO_WIDTH_RE`` (which silently *strips* such
chars while matching a brain blocklist): here we DETECT and report so the install
path can BLOCK a poisoned skill before its files land, and we additionally cover
the U+E0000 tag block that the brain regex predates.

Design note (false positives): a single leading U+FEFF is a byte-order mark many
editors emit, so it is tolerated at position 0 only; anywhere else it is flagged.
Every other class has no legitimate reason to appear in skill markdown.
"""

from __future__ import annotations

import os

# (label, lo, hi) inclusive codepoint ranges.
_SUSPECT_RANGES: tuple[tuple[str, int, int], ...] = (
    ("unicode-tag-block", 0xE0000, 0xE007F),
    ("bidi-override", 0x202A, 0x202E),
    ("bidi-isolate", 0x2066, 0x2069),
)
_SUSPECT_SINGLES: dict[int, str] = {
    0x200B: "zero-width-space",
    0x200C: "zero-width-non-joiner",
    0x200D: "zero-width-joiner",
    0x2060: "word-joiner",
    0xFEFF: "zero-width-nbsp",
    0x00AD: "soft-hyphen",
}

# Files whose prose the agent consumes directly — SKILL.md plus the reference,
# data, config and script files a SKILL.md can instruct the agent to open or
# run. A payload hidden in references/notes.py or data/config.json reaches the
# agent just as surely as one in SKILL.md, so the scan cannot be markdown-only
# (review s146, finding C2). Binary assets (images, archives, fonts) carry no
# agent-read prose and are skipped by extension.
_SCANNED_SUFFIXES = (
    ".md",
    ".markdown",
    ".txt",
    ".rst",
    ".py",
    ".sh",
    ".ps1",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".html",
    ".htm",
    ".xml",
    ".csv",
)


class SkillContentScanError(Exception):
    """A skill's prose hides agent-directed instructions in invisible Unicode."""


def _classify(cp: int) -> str | None:
    hit = _SUSPECT_SINGLES.get(cp)
    if hit:
        return hit
    for label, lo, hi in _SUSPECT_RANGES:
        if lo <= cp <= hi:
            return label
    return None


def scan_invisible_unicode(text: str) -> list[dict]:
    """Return one finding per suspect character in *text*.

    Each finding is ``{"pos": int, "codepoint": "U+XXXX", "kind": str}``.
    An empty list means clean. A single leading BOM (U+FEFF at index 0) is
    tolerated and not reported.
    """
    findings: list[dict] = []
    for i, ch in enumerate(text):
        cp = ord(ch)
        if cp == 0xFEFF and i == 0:
            continue  # leading BOM — benign editor artifact
        kind = _classify(cp)
        if kind is not None:
            findings.append({"pos": i, "codepoint": f"U+{cp:04X}", "kind": kind})
    return findings


def has_invisible_unicode(text: str) -> bool:
    """True if *text* contains any hidden-instruction Unicode character."""
    return bool(scan_invisible_unicode(text))


def scan_skill_tree(source_dir: str) -> dict[str, list[dict]]:
    """Scan every prose file under *source_dir* for hidden-instruction Unicode.

    Returns ``{relative_path: findings}`` for files with at least one finding;
    an empty dict means the whole tree is clean. Unreadable files are skipped
    (a scan must not itself crash the install path).
    """
    flagged: dict[str, list[dict]] = {}
    for root, _dirs, files in os.walk(source_dir):
        for name in files:
            if not name.lower().endswith(_SCANNED_SUFFIXES):
                continue
            path = os.path.join(root, name)
            # errors="replace", NOT "strict" (review s146, finding C3): a file
            # with one deliberately-invalid byte would raise under strict decode
            # and be silently skipped here, yet copytree still lands it byte-for-
            # byte — a fail-open. Replacement decoding keeps the valid U+E0000 /
            # zero-width / bidi codepoints intact for detection; only the invalid
            # byte becomes U+FFFD. Skip only on a real IO error.
            try:
                with open(path, encoding="utf-8", errors="replace") as fh:
                    text = fh.read()
            except OSError:
                continue
            findings = scan_invisible_unicode(text)
            if findings:
                rel = os.path.relpath(path, source_dir).replace("\\", "/")
                flagged[rel] = findings
    return flagged


def format_scan_report(flagged: dict[str, list[dict]]) -> str:
    """Human-readable one-liner-per-file summary of a ``scan_skill_tree`` result."""
    lines = []
    for rel, findings in sorted(flagged.items()):
        kinds = ", ".join(sorted({f["kind"] for f in findings}))
        first = findings[0]
        lines.append(
            f"  {rel}: {len(findings)} hidden char(s) [{kinds}] "
            f"(first: {first['codepoint']} at offset {first['pos']})"
        )
    return "\n".join(lines)


def assert_skill_tree_clean(source_dir: str, skill_name: str) -> None:
    """Raise ``SkillContentScanError`` if any prose file under *source_dir* hides
    invisible-Unicode instructions.

    The single guard that BOTH the install (`skill_manager.copy_skill`) and the
    activate (`service_skills.skill_activate`) paths call, so no route into the
    activated `.claude/skills/` tree can skip the scan. Keeping the check in one
    place is deliberate: install and activate have drifted before on a
    per-copy-path filter (see `skill_tree_ignore`'s docstring), and review s146
    found this exact recurrence — the scan lived only in copy_skill while
    skill_activate copied unscanned (finding C1).
    """
    flagged = scan_skill_tree(source_dir)
    if flagged:
        raise SkillContentScanError(
            f"Skill '{skill_name}' contains hidden-instruction Unicode "
            f"(possible prompt-injection payload) — refusing to install:\n"
            f"{format_scan_report(flagged)}"
        )
