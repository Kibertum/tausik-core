"""Is the WHOLE still coherent, after every part passed its own check?

Nothing asked that question. `tausik-reviewer` and the external reviewer look at
a task and a diff; gates look at a file, a scope, or a pair of documents. The
only repository-wide gate is `class_surface`, and it is a narrow structural one.

WHAT THIS IS NOT: nine new detectors. The measurement that shaped this module is
that the material was ALREADY being collected — nine audits exist, each with a
clean `collect_*` interface, and each is run alone and only when somebody
remembers. The whole was never assembled, not because there was nothing to
assemble, but because nobody assembled it. So this aggregates the real
producers rather than re-deriving their answers beside them, for the reason
convention #266 gives: a second copy drifts from the first, silently.

WHAT IS GENUINELY NEW here is what none of the nine does: rank findings by risk,
cap the volume, and say out loud what was NOT examined.

COLLECTION IS DETERMINISTIC, JUDGEMENT IS NOT. Everything below runs without a
model and produces the same result twice on an unchanged tree. The verdict —
which of these findings actually threaten coherence, and what they add up to —
belongs to a model reading this material, the same split already accepted for
the semantic memory lint. Mixing them would make the evidence as unrepeatable as
the opinion.

CANDIDATES, NOT TASKS. The report proposes; filing stays with a person. A lens
that opens its own tasks would be grading its own homework.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

#: The volume ceiling. A report nobody reads is worse than no report — it costs
#: attention and returns the feeling of having looked. Findings are ranked, and
#: what does not fit is COUNTED rather than dropped silently, so the reader
#: always knows how much they are not seeing.
MAX_FINDINGS = 40

#: Risk order. Not a score with invented precision — a coarse ordering, which is
#: all a ranked list needs, and all the evidence below can honestly support.
SEVERITY_ORDER = ("high", "medium", "low")


class Finding:
    """One observation, with the collector that made it and why it matters."""

    __slots__ = ("kind", "severity", "summary", "detail", "source", "count")

    def __init__(
        self,
        kind: str,
        severity: str,
        summary: str,
        *,
        source: str,
        count: int = 1,
        detail: str = "",
    ) -> None:
        self.kind = kind
        self.severity = severity
        self.summary = summary
        self.detail = detail
        self.source = source
        self.count = count

    def as_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "severity": self.severity,
            "summary": self.summary,
            "detail": self.detail,
            "source": self.source,
            "count": self.count,
        }


def _safe(name: str, fn: Callable[[], list[Finding]], skipped: list[str]) -> list[Finding]:
    """Run one collector; a failure DEMOTES it to a named gap, never to silence.

    A lens that quietly drops a collector reports a cleaner repository than it
    measured, which is the one failure mode that makes the whole thing worse
    than nothing.
    """
    try:
        return fn()
    except Exception as e:  # noqa: BLE001 — one collector must not take the lens down
        skipped.append(f"{name}: {type(e).__name__}: {e}")
        return []


def _orphans(root: Path) -> list[Finding]:
    import audit_orphan_files

    orphans = audit_orphan_files.collect_orphans(root)
    if not orphans:
        return []
    return [
        Finding(
            "orphan_files",
            "medium",
            f"{len(orphans)} tracked file(s) nothing references",
            source="audit_orphan_files",
            count=len(orphans),
            detail="\n".join(orphans[:10]),
        )
    ]


def _duplicate_tests(root: Path) -> list[Finding]:
    import audit_pytest_dedupe

    groups = audit_pytest_dedupe.collect_duplicates(root)
    if not groups:
        return []
    # `members`, not `tests` — read off the real producer rather than guessed.
    # The first draft guessed and reported "covering 0 tests", which is the
    # under-reporting direction: a lens that undercounts looks like a cleaner
    # repository than it measured.
    total = 0
    for group in groups:
        members = group.get("members")
        if isinstance(members, list):
            total += len(members)
    return [
        Finding(
            "duplicate_tests",
            "medium",
            f"{len(groups)} group(s) of structurally indistinguishable tests "
            f"covering {total} test(s)",
            source="audit_pytest_dedupe",
            count=len(groups),
            detail="Tests that share an AST shape modulo names, strings and numbers.",
        )
    ]


def _stale_docs(root: Path) -> list[Finding]:
    import audit_stale_docs

    stale = audit_stale_docs.collect_stale(root)
    if not stale:
        return []
    return [
        Finding(
            "stale_docs",
            "medium",
            f"{len(stale)} document(s) older than the code they describe",
            source="audit_stale_docs",
            count=len(stale),
            detail="\n".join(stale[:10]),
        )
    ]


def _unused_python(root: Path) -> list[Finding]:
    import audit_unused_python

    rows = audit_unused_python.collect_unused(root)
    if not rows:
        return []
    return [
        Finding(
            "unreachable_python",
            "high",
            f"{len(rows)} Python module(s) nothing imports or runs",
            source="audit_unused_python",
            count=len(rows),
            detail="\n".join(str(r.get("path", r)) for r in rows[:10]),
        )
    ]


def _translation_drift(root: Path) -> list[Finding]:
    import audit_translation_drift

    drifts, en_only, ru_only, _abbrev = audit_translation_drift.audit_pairs(root)
    out: list[Finding] = []
    if drifts:
        out.append(
            Finding(
                "translation_drift",
                "low",
                f"{len(drifts)} document pair(s) whose two languages have drifted apart",
                source="audit_translation_drift",
                count=len(drifts),
            )
        )
    lonely = len(en_only) + len(ru_only)
    if lonely:
        out.append(
            Finding(
                "unpaired_docs",
                "low",
                f"{lonely} document(s) exist in one language only",
                source="audit_translation_drift",
                count=lonely,
            )
        )
    return out


def _doc_number_drift(root: Path) -> list[Finding]:
    """Numbers the prose states about itself, against what is actually there.

    THE CALIBRATION CLASS this lens would otherwise miss. "The docs say eleven
    breaking changes and the tree has nine" is a coherence defect no per-file
    gate can see: each document is internally fine, and only the whole
    disagrees. The scanners already exist and already know how to answer —
    they were simply never asked as part of one question.
    """
    import doc_drift_scanners
    import gen_doc_constants

    payload = gen_doc_constants.build_constants_doc(root)
    version = gen_doc_constants.read_project_version(root)
    messages: list[str] = []
    for label, scan in (
        ("version refs", lambda: doc_drift_scanners.scan_version_refs(root, version)),
        ("mcp tool counts", lambda: doc_drift_scanners.scan_mcp_tool_counts(root, payload)),
        ("closed-list enums", lambda: doc_drift_scanners.scan_closed_list_enums(root, payload)),
        ("test counts", lambda: doc_drift_scanners.scan_test_counts(root, payload)),
        ("code-state counts", lambda: doc_drift_scanners.scan_code_counts(root, payload)),
    ):
        found = scan()
        messages += [f"{label}: {m}" for m in found]
    if not messages:
        return []
    return [
        Finding(
            "doc_number_drift",
            "high",
            f"{len(messages)} number(s) the documentation states about itself are wrong",
            source="doc_drift_scanners",
            count=len(messages),
            detail="\n".join(messages[:10]),
        )
    ]


def _rotted_evidence(root: Path, tasks: list[dict[str, Any]]) -> list[Finding]:
    import audit_closure_evidence

    report = audit_closure_evidence.audit_closure_evidence(str(root), tasks)
    # The producer returns {"counts": {...}, "findings": [...]}. Reading the
    # counts it publishes beats re-counting its findings here — one more place
    # to disagree with it, for nothing.
    counts = report.get("counts") or {}
    out: list[Finding] = []
    if counts.get("rotted"):
        out.append(
            Finding(
                "rotted_closure_evidence",
                "high",
                f"{counts['rotted']} closure citation(s) name a test that no longer exists",
                source="audit_closure_evidence",
                count=int(counts["rotted"]),
                detail="A closure whose evidence cannot be resolved is unverifiable today.",
            )
        )
    if counts.get("never_existed"):
        out.append(
            Finding(
                "invented_closure_evidence",
                "high",
                f"{counts['never_existed']} closure citation(s) name a test git NEVER had",
                source="audit_closure_evidence",
                count=int(counts["never_existed"]),
                detail="Worse than rot: the reference was already wrong when written.",
            )
        )
    return out


def _graph_staleness(root: Path, service: Any) -> list[Finding]:
    """The artifact graph's own honesty, folded into the same report."""
    stale = service.graph_stale_artifacts(root=str(root))
    if not stale:
        return []
    return [
        Finding(
            "stale_graph",
            "low",
            f"{len(stale)} artifact(s) in the graph no longer match the file on disk",
            source="artifact_graph",
            count=len(stale),
            detail="Answers touching these are reported partially stale by design.",
        )
    ]


#: What this lens does NOT look at. Stated in the report itself, because a
#: reader who cannot see the boundary will read silence as a clean bill.
NOT_EXAMINED = (
    "runtime behaviour — nothing here executes the product",
    "semantic correctness of any document; only staleness and pairing",
    "whether a test is GOOD; only whether it is distinguishable from another",
    "security properties",
    "anything outside version control",
)


def collect(
    repo_root: str = ".", tasks: list[dict[str, Any]] | None = None, service: Any = None
) -> dict[str, Any]:
    """Run every collector and return ranked material for a model to judge.

    Deterministic: same tree, same answer. No model is consulted here.
    """
    root = Path(repo_root).resolve()
    skipped: list[str] = []
    findings: list[Finding] = []

    findings += _safe("orphan_files", lambda: _orphans(root), skipped)
    findings += _safe("duplicate_tests", lambda: _duplicate_tests(root), skipped)
    findings += _safe("stale_docs", lambda: _stale_docs(root), skipped)
    findings += _safe("unused_python", lambda: _unused_python(root), skipped)
    findings += _safe("translation_drift", lambda: _translation_drift(root), skipped)
    findings += _safe("doc_number_drift", lambda: _doc_number_drift(root), skipped)
    if tasks is not None:
        findings += _safe("closure_evidence", lambda: _rotted_evidence(root, tasks), skipped)
    if service is not None:
        findings += _safe("artifact_graph", lambda: _graph_staleness(root, service), skipped)

    findings.sort(key=lambda f: (SEVERITY_ORDER.index(f.severity), -f.count))
    shown, hidden = findings[:MAX_FINDINGS], max(0, len(findings) - MAX_FINDINGS)

    return {
        "findings": [f.as_dict() for f in shown],
        "truncated": hidden,
        "collectors_run": 6 + (1 if tasks is not None else 0) + (1 if service is not None else 0),
        "collectors_skipped": skipped,
        "not_examined": list(NOT_EXAMINED),
    }


def render_markdown(material: dict[str, Any]) -> str:
    """The report a person reads, and a model judges from."""
    lines = ["# Repository coherence — collected material", ""]
    findings = material["findings"]
    if not findings:
        lines += [
            "No finding from any collector.",
            "",
            "TREAT THIS WITH SUSPICION on a repository of any age: a lens that "
            "reports nothing is far more often broken than the tree is perfect.",
            "",
        ]
    else:
        lines.append(f"{len(findings)} finding(s), most severe first.")
        if material["truncated"]:
            lines.append(f"{material['truncated']} more not shown (volume cap).")
        lines.append("")
        for f in findings:
            lines.append(f"## [{f['severity'].upper()}] {f['summary']}")
            lines.append(f"- collector: `{f['source']}`  |  kind: `{f['kind']}`")
            if f["detail"]:
                lines.append("")
                lines.append("```")
                lines.append(f["detail"])
                lines.append("```")
            lines.append("")

    if material["collectors_skipped"]:
        lines += ["## Collectors that did NOT run", ""]
        lines += [f"- {s}" for s in material["collectors_skipped"]]
        lines.append("")

    lines += ["## NOT examined by this lens", ""]
    lines += [f"- {n}" for n in material["not_examined"]]
    lines += [
        "",
        "---",
        "",
        "These are CANDIDATES. Filing a task remains a person's decision.",
    ]
    return "\n".join(lines)


def render_json(material: dict[str, Any]) -> str:
    return json.dumps(material, ensure_ascii=False, indent=2)
