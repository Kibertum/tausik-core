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
from typing import Any

from repo_coherence_collectors import (
    _doc_number_drift,
    _duplicate_tests,
    _graph_staleness,
    _orphans,
    _rotted_evidence,
    _senar_claim_citations,
    _stale_docs,
    _tests_never_observed_red,
    _translation_drift,
    _unused_python,
)
from repo_coherence_shape import (  # noqa: F401 — re-exported surface
    MAX_FINDINGS,
    NOT_EXAMINED,
    SEVERITY_ORDER,
    Finding,
    _safe,
)

#: The volume ceiling. A report nobody reads is worse than no report — it costs
#: attention and returns the feeling of having looked. Findings are ranked, and
#: what does not fit is COUNTED rather than dropped silently, so the reader
#: always knows how much they are not seeing.
def collect(
    repo_root: str = ".", tasks: list[dict[str, Any]] | None = None, service: Any = None
) -> dict[str, Any]:
    """Run every collector and return ranked material for a model to judge.

    Deterministic: same tree, same answer. No model is consulted here.
    """
    root = Path(repo_root).resolve()
    skipped: list[str] = []
    ran: list[str] = []
    findings: list[Finding] = []

    findings += _safe("orphan_files", lambda: _orphans(root), skipped, ran)
    findings += _safe("duplicate_tests", lambda: _duplicate_tests(root), skipped, ran)
    findings += _safe("stale_docs", lambda: _stale_docs(root), skipped, ran)
    findings += _safe("unused_python", lambda: _unused_python(root), skipped, ran)
    findings += _safe("translation_drift", lambda: _translation_drift(root), skipped, ran)
    findings += _safe("doc_number_drift", lambda: _doc_number_drift(root), skipped, ran)
    findings += _safe("senar_claim_citations", lambda: _senar_claim_citations(root), skipped, ran)
    findings += _safe("red_history", lambda: _tests_never_observed_red(root), skipped, ran)
    if tasks is not None:
        findings += _safe("closure_evidence", lambda: _rotted_evidence(root, tasks), skipped, ran)
    if service is not None:
        findings += _safe("artifact_graph", lambda: _graph_staleness(root, service), skipped, ran)

    findings.sort(key=lambda f: (SEVERITY_ORDER.index(f.severity), -f.count))
    shown, hidden = findings[:MAX_FINDINGS], max(0, len(findings) - MAX_FINDINGS)

    return {
        "findings": [f.as_dict() for f in shown],
        "truncated": hidden,
        "collectors_run": len(ran),
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


if __name__ == "__main__":  # pragma: no cover - exercised via subprocess in tests
    from cli_entrypoint import refuse_direct_run

    refuse_direct_run(
        __file__, ".tausik/tausik coherence          # this module's collectors, rendered"
    )
