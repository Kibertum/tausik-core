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

# WHAT counts as a marker lives in `ac_evidence_detectors` — split out when this
# module hit the 400-line gate, and the split is what gives the language-parity
# registry a home. This module owns HOW lines are segmented and matched to AC
# items. Re-exported: callers and tests import these names from here.
from ac_evidence_detectors import (  # noqa: E402,F401 — re-export for callers
    AC_HEADER_PREFIX_RE,
    AC_ITEM_BOUNDARY_RE,
    AC_NUMBER_PREFIX_RE,
    AC_SECTION_HEADING_RE,
    CHECK_MARK_RE,
    DOMAIN_RE,
    MANUAL_RE,
    NEGATIVE_RE,
    PYTEST_SUMMARY_RE,
    REVIEW_RE,
    TEST_REF_RE,
    TIMESTAMP_PREFIX_RE,
    VERIFICATION_RUN_RE,
)


def _strip_log_prefixes(unit: str) -> str:
    """Strip a leading `[timestamp]` + `AC …:` header (project-authored) so a
    start-anchored AC-number match sees the number behind them. Index detection
    only — never stored as `raw` (ac-evidence-parser-format-strict)."""
    stripped = TIMESTAMP_PREFIX_RE.sub("", unit, count=1)
    return AC_HEADER_PREFIX_RE.sub("", stripped, count=1)


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
    is_measurement: bool = False
    # verification_runs id from a `verification_run #NNNN` line (None for a bare
    # pytest-summary), so the GATE layer can fact-check it (exists/same-task/green).
    measurement_run_id: int | None = None

    @property
    def evidence_type(self) -> str:
        if self.test_refs:
            return "test_ref"
        if self.is_measurement:
            return "measurement"
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
    run_m = VERIFICATION_RUN_RE.search(unit)
    measurement_run_id: int | None = None
    if run_m:
        try:
            measurement_run_id = int(run_m.group(1))
        except (TypeError, ValueError):
            measurement_run_id = None
    is_measurement = bool(run_m) or bool(PYTEST_SUMMARY_RE.search(unit))

    ac_indices: list[int] = []
    # Match the AC number at the START of the unit, tolerating the task_log
    # timestamp + an "AC …:" header (both project-authored) in front of it.
    # Same strict regex → a numberless line still binds to no AC.
    m = AC_NUMBER_PREFIX_RE.match(_strip_log_prefixes(unit))
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
            is_measurement=is_measurement,
            measurement_run_id=measurement_run_id,
        )
        if (
            ev.ac_index is not None
            or ev.has_checkmark
            or ev.test_refs
            or ev.is_manual
            or ev.is_negative
            or ev.is_review
            or ev.is_domain
            or ev.is_measurement
        ):
            out.append(ev)
    return out


def _carries_evidence(ev: EvidenceLine) -> bool:
    """Whether a line without its own `AC-N` may inherit the section's index.

    Both halves are required and each rules out a different mistake. The check
    mark is the author marking this line as a checklist entry — without it, a
    planning note that happens to mention a path (`limitation: tests/x.py:62
    asserts …`) would be counted as evidence for whichever criterion it followed.
    The reference is the evidence itself — without it, a bare tick inherits an
    index and a claim gets counted as a verification, which is the exact
    substitution this gate exists to prevent.
    """
    if not ev.has_checkmark:
        return False
    return bool(ev.test_refs) or ev.is_manual or ev.is_review or ev.is_measurement


def parse_evidence_lines(notes_text: str) -> list[EvidenceLine]:
    """Parse task notes into a list of EvidenceLine candidates.

    EVIDENCE MAY SIT BELOW ITS HEADING, not only beside it. Matching used to
    require `AC-N` on the SAME line as the citation, so the fuller form —

        AC-2 (what is checked): the shared row is labelled and addressless
        ✓ tests/test_knowledge_read.py::TestX::test_a
        ✓ tests/test_knowledge_read.py::TestX::test_b

    — parsed as a heading with no evidence plus two citations belonging to
    nothing. The gate then reported "no acceptance criterion names a test" over
    a checklist that named several, and it did so four closes running. That is
    worse than a missing feature: a gate that denies evidence it was handed
    teaches its reader to skip its output, and it is then equally ignored on the
    closes where the checklist really is absent. The form is also not a matter
    of taste — one criterion covered by four tests does not fit on one line.

    The inheritance is SCOPED so that widening recognition does not become
    accepting anything. A section is opened ONLY by a line carrying an explicit
    `AC` token (`AC_SECTION_HEADING_RE`) and ends at the next such heading, at a
    blank line, or at the start of the next log entry; only lines that carry
    both a tick and a real citation inherit from it.

    THE `AC` TOKEN IS REQUIRED, AND THAT IS THE WHOLE SAFETY PROPERTY. An
    earlier version of this opened a section from any line whose leading token
    `AC_NUMBER_PREFIX_RE` could read as an index — and that regex makes `AC`
    optional, correctly, because it was written for the `acceptance_criteria`
    FIELD where every line is numbered by construction. Applied to free-form
    notes it reads `3 retries were added to the flaky client` as a heading for
    criterion 3, and the next citation — about something else entirely — is
    credited to it. That is not cosmetic: `_evidence_strength` aggregates real
    test citations PER TASK, and the Rule 5 hard block clears at one, so one
    ordinary sentence beginning with a digit could clear the gate for a task
    with no real coverage at all. Recognising a heading and reading an index are
    different questions, and they now use different patterns.
    """
    if not notes_text:
        return []
    out: list[EvidenceLine] = []
    section_ac: int | None = None
    for raw in notes_text.splitlines():
        line = raw.strip()
        if not line:
            # A blank line ends the section. Conservative on purpose: the cost
            # is a checklist separated by blank lines needing its own `AC-N` per
            # line, against the cost of a citation paragraphs away being
            # attributed to a criterion nobody meant it for.
            section_ac = None
            continue
        body = TIMESTAMP_PREFIX_RE.sub("", line, count=1)
        heading = AC_SECTION_HEADING_RE.match(body)
        # A new log entry is a new context — `task log` appends independently,
        # so a heading from an earlier entry says nothing about this one.
        if TIMESTAMP_PREFIX_RE.match(line) and heading is None:
            section_ac = None
        if heading is not None:
            section_ac = int(heading.group(1))
        for unit in _segment_evidence_line(line):
            for ev in _evidence_lines_for_unit(unit):
                if ev.ac_index is None and section_ac is not None and _carries_evidence(ev):
                    ev.ac_index = section_ac
                out.append(ev)
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
