"""SENAR Rule 5 - structured AC evidence parser (v1.4).

Replaces the v1.3 keyword-counting heuristic with a parser that extracts:
  - per-AC verification status (numbered AC items 1..N)
  - evidence type: test_ref | manual | review_ref | none
  - evidence location: e.g. "tests/test_foo.py::test_bar" or "manual run"

This module does NOT decide whether a task is closeable - it returns a
structured report that callers (QG-2 checklist) consume to produce richer
warnings than "no checklist items found in notes".

Public API:
  parse_ac_text(ac_text)         -> list[str] of AC item bodies (1-indexed)
  parse_evidence_lines(notes)    -> list[EvidenceLine]
  match_evidence_to_ac(ac_items, evidence_lines) -> AcCoverageReport
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from tausik_utils import ServiceError

CHECK_MARK_RE = re.compile(r"[\u2713\u2714\u2705]|\[v\]")
AC_NUMBER_PREFIX_RE = re.compile(r"^\s*(?:AC[-\s]*)?(\d+)[\.\):]?\s*(.*)$", re.IGNORECASE)
TEST_REF_RE = re.compile(
    r"(tests?/[\w/.\-]+\.py(?:::[\w_]+)?|test_[\w_]+\.py(?:::[\w_]+)?)",
    re.IGNORECASE,
)
NEGATIVE_RE = re.compile(r"\bnegative\b", re.IGNORECASE)
MANUAL_RE = re.compile(r"\bmanual(?:ly)?\b", re.IGNORECASE)
REVIEW_RE = re.compile(r"/review|review\s*record|adversarial", re.IGNORECASE)
# SENAR Rule 4 domain challenge (v15s-rule4-domain-challenge): does the result
# make sense OUTSIDE the tests? arXiv 2605.30353 — agents pass tests with
# physically meaningless outputs. An evidence line answering the domain question.
DOMAIN_RE = re.compile(
    r"\bdomain\b|\bsanity\b|makes?\s+sense|имеет\s+смысл|доменн|real[\s\-]?world",
    re.IGNORECASE,
)
# Start of a numbered AC item inside a single-line blob: optional "AC-" prefix,
# a number, a separator (. ) :), then whitespace. Anchored to start-of-text or a
# preceding whitespace/`;`/`(` so a mid-token number (Python 3.11, SHA-256,
# v1.4, "returns 0)") cannot start a spurious item.
AC_ITEM_BOUNDARY_RE = re.compile(
    r"(?:^|(?<=[\s;(]))(?:AC[-\s]*)?(\d+)\s*[.):]\s",
    re.IGNORECASE,
)


@dataclass
class EvidenceLine:
    raw: str
    ac_index: int | None
    has_checkmark: bool
    test_refs: list[str] = field(default_factory=list)
    is_manual: bool = False
    is_negative: bool = False
    is_review: bool = False
    is_domain: bool = False

    @property
    def evidence_type(self) -> str:
        if self.test_refs:
            return "test_ref"
        if self.is_manual:
            return "manual"
        if self.is_review:
            return "review_ref"
        if self.has_checkmark:
            return "checkmark_only"
        return "none"


@dataclass
class AcCoverageItem:
    ac_index: int
    ac_text: str
    evidence: list[EvidenceLine] = field(default_factory=list)

    @property
    def has_any_evidence(self) -> bool:
        return any(e.evidence_type != "none" for e in self.evidence)

    @property
    def has_test_ref(self) -> bool:
        return any(e.test_refs for e in self.evidence)

    @property
    def has_manual(self) -> bool:
        return any(e.is_manual for e in self.evidence)


@dataclass
class AcCoverageReport:
    total_ac: int
    items: list[AcCoverageItem]
    unmatched_evidence: list[EvidenceLine]
    has_negative_evidence: bool
    has_domain_evidence: bool = False

    @property
    def covered(self) -> int:
        return sum(1 for i in self.items if i.has_any_evidence)

    @property
    def covered_with_tests(self) -> int:
        return sum(1 for i in self.items if i.has_test_ref)

    @property
    def coverage_pct(self) -> float:
        if not self.total_ac:
            return 0.0
        return round(self.covered / self.total_ac * 100, 1)

    def gaps(self) -> list[int]:
        return [i.ac_index for i in self.items if not i.has_any_evidence]

    def to_summary(self) -> str:
        lines = [
            f"AC coverage: {self.covered}/{self.total_ac} ({self.coverage_pct}%)",
            f"  with test refs: {self.covered_with_tests}/{self.total_ac}",
        ]
        if self.gaps():
            gap_str = ", ".join(str(i) for i in self.gaps())
            lines.append(f"  gaps (no evidence): AC {gap_str}")
        if not self.has_negative_evidence:
            lines.append("  negative scenario: NOT EXERCISED in evidence")
        return "\n".join(lines)


def _split_inline_numbered(ac_text: str) -> list[str]:
    """Split a single-line blob like '1. foo 2. bar 3. baz' into item bodies.

    Only boundaries that continue the run 1, 2, 3, … (in order) are honored, so
    a stray number in prose ('Decision #138', 'returns 0', 'Python 3.11') can
    neither inflate the count nor mis-split an item. Returns [] when fewer than
    two sequential boundaries are found (caller falls back to line-based parse).
    """
    boundaries = []
    expected = 1
    for m in AC_ITEM_BOUNDARY_RE.finditer(ac_text):
        if int(m.group(1)) == expected:
            boundaries.append(m)
            expected += 1
    if len(boundaries) < 2:
        return []
    items: list[str] = []
    for i, m in enumerate(boundaries):
        start = m.end()
        end = boundaries[i + 1].start() if i + 1 < len(boundaries) else len(ac_text)
        body = ac_text[start:end].strip()
        if body:
            items.append(body)
    return items


def parse_ac_text(ac_text: str) -> list[str]:
    """Return AC item bodies in declaration order (1-indexed by position).

    Multi-line AC is parsed line-by-line. A single-line AC ('1. … 2. … N.'),
    which defeats the line-anchored parse (only the leading item matches), is
    split inline on its numbered-item boundaries.
    """
    if not ac_text:
        return []
    items: list[str] = []
    for raw in ac_text.splitlines():
        m = AC_NUMBER_PREFIX_RE.match(raw)
        if m and m.group(2).strip():
            items.append(m.group(2).strip())
    if len(items) >= 2:
        return items
    # Line-based found <2 items — try an inline split for single-line AC.
    inline = _split_inline_numbered(ac_text)
    if len(inline) >= 2:
        return inline
    if items:
        return items
    return [ln.strip() for ln in ac_text.splitlines() if ln.strip()]


def _segment_evidence_line(line: str) -> list[str]:
    """Split one evidence line on its numbered-marker boundaries.

    A one-line ``task log`` entry often packs several markers
    ('1. ✓ a 2. ✓ b 3. ✓ c'). Splitting on AC_ITEM_BOUNDARY_RE lets each marker
    own its ac_index and its own segment-local checkmark — both more correct
    than treating the whole line as one unit (which credited every criterion if
    a single ✓ appeared anywhere, and missed bare 'N.' markers entirely). A line
    with fewer than two boundary markers is returned unchanged.
    """
    matches = list(AC_ITEM_BOUNDARY_RE.finditer(line))
    if len(matches) < 2:
        return [line]
    # Guard against false segmentation of prose that merely contains numbered
    # tokens ('see 3. tests/x.py … section 7. output'). Only split when the
    # markers are unambiguously an enumeration: EITHER every boundary carries an
    # explicit 'AC' prefix, OR the bare indices run contiguously from 1. A prose
    # line ([3, 7], no prefix) fails both and is processed whole — so a stray
    # number can never falsely credit a real criterion.
    indices = [int(m.group(1)) for m in matches]
    all_ac_prefixed = all("a" in m.group(0).lower() for m in matches)
    contiguous_from_one = indices == list(range(1, len(indices) + 1))
    if not (all_ac_prefixed or contiguous_from_one):
        return [line]
    segments: list[str] = []
    preamble = line[: matches[0].start()].strip()
    if preamble:
        segments.append(preamble)
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(line)
        seg = line[m.start() : end].strip()
        if seg:
            segments.append(seg)
    return segments


def _evidence_lines_for_unit(unit: str) -> list[EvidenceLine]:
    """Build EvidenceLine(s) for one text unit (a whole line or a segment)."""
    has_check = bool(CHECK_MARK_RE.search(unit))
    test_refs = TEST_REF_RE.findall(unit)
    is_manual = bool(MANUAL_RE.search(unit))
    is_negative = bool(NEGATIVE_RE.search(unit))
    is_review = bool(REVIEW_RE.search(unit))
    is_domain = bool(DOMAIN_RE.search(unit))

    ac_indices: list[int] = []
    m = AC_NUMBER_PREFIX_RE.match(unit)
    if m and m.group(2).strip():
        try:
            ac_indices.append(int(m.group(1)))
        except (TypeError, ValueError):
            pass
    for inline in re.finditer(r"\bAC[-\s]*(\d+)\b", unit, re.IGNORECASE):
        try:
            ac_indices.append(int(inline.group(1)))
        except (TypeError, ValueError):
            continue
    indices = list(dict.fromkeys(ac_indices)) or [None]  # type: ignore[list-item]

    out: list[EvidenceLine] = []
    for ac_idx in indices:
        ev = EvidenceLine(
            raw=unit,
            ac_index=ac_idx,
            has_checkmark=has_check,
            test_refs=test_refs,
            is_manual=is_manual,
            is_negative=is_negative,
            is_review=is_review,
            is_domain=is_domain,
        )
        if (
            ev.ac_index is not None
            or ev.has_checkmark
            or ev.test_refs
            or ev.is_manual
            or ev.is_negative
            or ev.is_review
            or ev.is_domain
        ):
            out.append(ev)
    return out


def parse_evidence_lines(notes_text: str) -> list[EvidenceLine]:
    """Parse task notes into a list of EvidenceLine candidates."""
    if not notes_text:
        return []
    out: list[EvidenceLine] = []
    for raw in notes_text.splitlines():
        line = raw.strip()
        if not line:
            continue
        for unit in _segment_evidence_line(line):
            out.extend(_evidence_lines_for_unit(unit))
    return out


def match_evidence_to_ac(
    ac_items: list[str], evidence_lines: list[EvidenceLine]
) -> AcCoverageReport:
    """Map evidence lines to AC items by explicit `AC-N`/`N.` prefix."""
    items = [AcCoverageItem(ac_index=idx + 1, ac_text=text) for idx, text in enumerate(ac_items)]
    by_idx = {i.ac_index: i for i in items}
    unmatched: list[EvidenceLine] = []
    for ev in evidence_lines:
        if ev.ac_index is not None and ev.ac_index in by_idx:
            by_idx[ev.ac_index].evidence.append(ev)
        else:
            unmatched.append(ev)
    has_neg = any(ev.is_negative for ev in evidence_lines)
    has_domain = any(ev.is_domain for ev in evidence_lines)
    return AcCoverageReport(
        total_ac=len(items),
        items=items,
        unmatched_evidence=unmatched,
        has_negative_evidence=has_neg,
        has_domain_evidence=has_domain,
    )


def build_report(ac_text: str, notes_text: str) -> AcCoverageReport:
    """Top-level helper used by QG-2 checklist."""
    ac_items = parse_ac_text(ac_text)
    evidence = parse_evidence_lines(notes_text)
    return match_evidence_to_ac(ac_items, evidence)


def evidence_json_to_prose(raw: str) -> str:
    """Convert agent-supplied JSON evidence into the canonical prose form.

    Schema:
      {"ac_evidence": [
         {"n": int>=1, "status": "pass"|"fail", "evidence": str,
          "manual": bool?, "negative": bool?},
         ...
       ]}

    Output (one line per AC item, prefixed with 'AC verified:' header so
    parse_evidence_lines + service_gates._verify_ac recognise the marker):

      AC verified:
      1. ✓ tests/foo.py::test_bar
      2. ✓ manual: smoke run on prod
      3. FAIL: regression in edge case

    Raises ServiceError on any schema violation. No DB / IO.
    """
    if not isinstance(raw, str) or not raw.strip():
        raise ServiceError("invalid --evidence-json: empty input")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ServiceError(f"invalid --evidence-json: {e.msg} (line {e.lineno})") from e
    if not isinstance(data, dict):
        raise ServiceError("invalid --evidence-json: top-level must be an object")
    items = data.get("ac_evidence")
    if not isinstance(items, list):
        raise ServiceError("invalid --evidence-json: 'ac_evidence' must be a list")
    if not items:
        raise ServiceError("invalid --evidence-json: 'ac_evidence' is empty")
    lines: list[str] = ["AC verified:"]
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            raise ServiceError(f"invalid --evidence-json: ac_evidence[{idx}] must be an object")
        n = item.get("n")
        # bool is subclass of int — exclude explicitly.
        if isinstance(n, bool) or not isinstance(n, int) or n < 1:
            raise ServiceError(
                f"invalid --evidence-json: ac_evidence[{idx}].n must be a positive integer"
            )
        status = item.get("status")
        if status not in ("pass", "fail"):
            raise ServiceError(
                f"invalid --evidence-json: ac_evidence[{idx}].status must be 'pass' or 'fail'"
            )
        evidence = item.get("evidence")
        if not isinstance(evidence, str) or not evidence.strip():
            raise ServiceError(
                f"invalid --evidence-json: ac_evidence[{idx}].evidence must be a non-empty string"
            )
        marker = "✓" if status == "pass" else "FAIL:"
        tags: list[str] = []
        if item.get("manual"):
            tags.append("manual")
        if item.get("negative"):
            tags.append("negative")
        if item.get("domain"):
            tags.append("domain")
        prefix = f"{n}. {marker}"
        if tags:
            prefix += " " + " ".join(tags) + ":"
        lines.append(f"{prefix} {evidence.strip()}")
    return "\n".join(lines)
