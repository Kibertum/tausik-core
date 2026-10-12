"""Bounded verification presentation with a complete local evidence artifact.

The service owns verdicts and persistence.  This module only writes the exact
gate output it was handed after a run was recorded, then derives a deliberately
small answer for CLI and MCP.  Keeping those concerns here prevents the two
transports from growing separate truncation rules.
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

_MAX_FAILURES = 3
_MAX_FAILURE_LINES = 4
_MAX_FAILURE_LINE_BYTES = 400
_COUNTS = re.compile(r"(?<!\d)(\d+)\s+(passed|skipped|deselected|failed|errors?)\b", re.I)
_PYTEST_FAILURE = re.compile(r"^(FAILED|ERROR)\s", re.I)
_PYTEST_SUMMARY = re.compile(r"^=*\s*\d+ (failed|passed|error|errors)\b", re.I)
_PYTEST_BATCH_START = re.compile(r"^bringing up nodes\.\.\.$", re.I)
_PYTEST_TERMINAL = re.compile(r"\b(?:passed|failed|skipped|error|errors)\b.*\bin \d", re.I)
_PYTEST_DESELECTED = re.compile(r"\bdeselected\b", re.I)


def _report_verdict(report: dict[str, Any]) -> str:
    """Use the canonical gate vocabulary for the run-level boolean."""
    from gate_runner import gate_verdict

    return gate_verdict({"passed": bool(report.get("passed"))})


def write_evidence(
    svc: Any, report: dict[str, Any], task_slug: str | None, scope: str
) -> tuple[str | None, str | None]:
    """Persist every gate body and return its project-relative path.

    A missing project root is an honest degradation for lightweight test and
    detached-service callers; it is never silently substituted with the process
    working directory.
    """
    from project_root import root_from_service

    root = root_from_service(svc)
    if not root:
        return None, "the service has no project root"
    run_id = report.get("run_id")
    name = (
        f"verify-{run_id}.log" if run_id is not None else f"verify-unrecorded-{time.time_ns()}.log"
    )
    relative = f".tausik/verification/{name}"
    counts_relative = str(Path(relative).with_suffix(".json")).replace("\\", "/")
    try:
        target = Path(root) / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        results = report.get("results") or []
        lines = [
            f"Verify evidence: task={task_slug or '-'} scope={scope}",
            f"Verdict: {_report_verdict(report)} status={report.get('status', '-')}",
            f"Gates: {len(results)}",
        ]
        for result in results:
            gate_scope = result.get("scope") or "not reported"
            lines.extend(
                (
                    "",
                    f"[{_gate_label(result)}] {result.get('name', '?')}",
                    f"Scope: {gate_scope}",
                    str(
                        result.get("artifact_output") or result.get("output") or "(no gate output)"
                    ),
                )
            )
        temporary = target.with_suffix(".tmp")
        temporary.write_text("\n".join(lines) + "\n", encoding="utf-8")
        temporary.replace(target)
    except OSError as exc:
        return None, f"could not write {relative}: {type(exc).__name__}: {exc}"
    try:
        counts_target = Path(root) / counts_relative
        counts_temporary = counts_target.with_suffix(".tmp")
        counts_temporary.write_text(
            json.dumps(
                _machine_evidence(report, task_slug, scope, relative),
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        counts_temporary.replace(counts_target)
    except OSError as exc:
        return relative, (f"could not write {counts_relative}: {type(exc).__name__}: {exc}")
    return relative, None


def _machine_evidence(
    report: dict[str, Any], task_slug: str | None, scope: str, log_path: str
) -> dict[str, Any]:
    """Stable counts and provenance without duplicating the complete log."""
    results = list(report.get("results") or [])
    return {
        "schema_version": 1,
        "run_id": report.get("run_id"),
        "task_slug": task_slug,
        "scope": scope,
        "status": report.get("status"),
        "verdict": _report_verdict(report),
        "log": log_path,
        "gate_counts": _gate_counts(results),
        "tests": _test_counts(results),
        "gates": [
            {
                key: result.get(key)
                for key in (
                    "name",
                    "outcome",
                    "reason_code",
                    "passed",
                    "skipped",
                    "severity",
                    "duration_ms",
                    "scope",
                )
                if key in result
            }
            for result in results
        ],
    }


def compact_lines(
    report: dict[str, Any],
    task_slug: str | None,
    scope: str,
    evidence: str | None,
    evidence_error: str | None,
) -> list[str]:
    """Render counts and bounded actionable failures without changing verdicts."""
    results = list(report.get("results") or [])
    gates = _gate_counts(results)
    tests = _test_counts(results)
    denominator = _scope_denominator(results, task_slug)
    verdict = _report_verdict(report)
    lines = [
        f"Verify (scope={scope}, task={task_slug or '-'}): {verdict}; status={report.get('status', '-')}; "
        f"denominator={denominator}; gates="
        f"{len(results)} (passed={gates['passed']}, skipped={gates['skipped']}, failed={gates['failed']}); "
        f"tests(passed={_count(tests['passed'])}, skipped={_count(tests['skipped'])}, "
        f"deselected={_count(tests['deselected'])})."
    ]
    if evidence:
        lines.append(f"Full evidence: {evidence}")
        counts_path = str(Path(evidence).with_suffix(".json")).replace("\\", "/")
        if evidence_error:
            lines.append(f"Machine counts: UNAVAILABLE ({evidence_error}).")
        else:
            lines.append(f"Machine counts: {counts_path}")
    else:
        lines.append(
            f"Full evidence: UNAVAILABLE ({evidence_error or 'unknown persistence error'})."
        )
    failures = [r for r in results if not r.get("passed")]
    if failures:
        shown = failures[:_MAX_FAILURES]
        lines.append(
            f"Actionable failures: showing {len(shown)}/{len(failures)} (full detail: {evidence or 'unavailable'})."
        )
        for result in shown:
            lines.extend(_failure_lines(result, evidence))
        if len(failures) > len(shown):
            lines.append(
                f"… {len(failures) - len(shown)} more failure(s) omitted; see full evidence."
            )
    skipped = [str(r.get("name") or "?") for r in results if r.get("skipped")]
    if skipped:
        lines.append(
            f"Skipped gates: {', '.join(skipped)} did NOT execute; a skip is not verification."
        )
    return lines


def compact_task_done_report(svc: Any, report: dict[str, Any], task_slug: str) -> dict[str, Any]:
    """Project a close report without returning complete gate bodies to MCP."""
    results = list(report.get("gates") or [])
    if not results:
        return report
    validation = {
        "passed": bool(report.get("gates_passed")),
        "status": report.get("cache_status") or "task-done",
        "results": results,
    }
    evidence, evidence_error = write_evidence(svc, validation, task_slug, "task-done")
    projected = dict(report)
    projected["validation_summary"] = "\n".join(
        compact_lines(validation, task_slug, "task-done", evidence, evidence_error)
    )
    projected["gates"] = [
        {
            key: row.get(key)
            for key in (
                "name",
                "outcome",
                "reason_code",
                "passed",
                "skipped",
                "severity",
                "duration_ms",
                "scope",
            )
            if key in row
        }
        for row in results
    ]
    projected["blocking_failures"] = [
        {key: value for key, value in failure.items() if key not in {"output"}}
        | ({"evidence": evidence} if failure.get("output") and evidence else {})
        for failure in report.get("blocking_failures") or []
    ]
    return projected


def _gate_label(result: dict[str, Any]) -> str:
    from gate_runner import gate_verdict

    return gate_verdict(result)


def _gate_counts(results: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "passed": sum(1 for r in results if r.get("passed") and not r.get("skipped")),
        "skipped": sum(1 for r in results if r.get("skipped")),
        "failed": sum(1 for r in results if not r.get("passed")),
    }


def _test_counts(results: list[dict[str, Any]]) -> dict[str, int | None]:
    counts: dict[str, int | None] = {"passed": None, "skipped": None, "deselected": None}
    for result in results:
        if "pytest" not in str(result.get("name") or "").lower():
            continue
        for batch in _pytest_batches(str(result.get("output") or "")):
            for label, amount in batch.items():
                counts[label] = (counts[label] or 0) + amount
    return counts


def _pytest_batches(output: str) -> list[dict[str, int]]:
    """Read one final summary per pytest batch, not one for the whole gate.

    The runner concatenates independent pytest invocations.  Each begins with
    xdist's ``bringing up nodes...`` banner (often printed twice); a banner
    after a terminal summary starts the next session.  Repeated terminal lines
    inside one session are echoes, so the latest value per count kind wins.
    """
    sessions: list[list[str]] = [[]]
    terminal_seen = False
    for line in output.splitlines():
        if _PYTEST_BATCH_START.match(line.strip()) and terminal_seen:
            sessions.append([])
            terminal_seen = False
        sessions[-1].append(line)
        if _PYTEST_TERMINAL.search(line):
            terminal_seen = True

    batches: list[dict[str, int]] = []
    for session in sessions:
        values: dict[str, int] = {}
        for line in session:
            if not (_PYTEST_TERMINAL.search(line) or _PYTEST_DESELECTED.search(line)):
                continue
            for amount, label in _COUNTS.findall(line):
                normalized = "failed" if label.lower().startswith("error") else label.lower()
                if normalized in {"passed", "skipped", "deselected"}:
                    values[normalized] = int(amount)
        if values:
            batches.append(values)
    return batches


def _count(value: int | None) -> str:
    return str(value) if value is not None else "unknown"


def _failure_lines(result: dict[str, Any], evidence: str | None) -> list[str]:
    from gate_runner import failure_excerpt

    raw = str(result.get("output") or "(no diagnostic output)").splitlines()
    candidate = failure_excerpt("\n".join(raw))
    important = [
        line
        for line in candidate
        if _PYTEST_FAILURE.match(line.strip()) or _PYTEST_SUMMARY.match(line.strip())
    ]
    excerpt = (important + [line for line in candidate if line not in important])[
        :_MAX_FAILURE_LINES
    ]
    clipped = any(len(line.encode("utf-8")) > _MAX_FAILURE_LINE_BYTES for line in excerpt)
    lines = [f"  [{_bounded(str(result.get('name') or '?'))}] {_bounded(line)}" for line in excerpt]
    if len(raw) > len(excerpt) or clipped:
        lines.append(
            f"  … output truncated after {_MAX_FAILURE_LINES} lines; see {evidence or 'full evidence'}."
        )
    return lines


def _scope_denominator(results: list[dict[str, Any]], task_slug: str | None) -> str:
    """Show the runner's trusted mapped scope, never a source-file proxy."""
    scopes = [_summary_scope(str(result["scope"])) for result in results if result.get("scope")]
    if scopes:
        return "; ".join(dict.fromkeys(scopes))
    return "full-suite" if task_slug is None else "not reported"


def _summary_scope(scope: str) -> str:
    """Keep the denominator, move the potentially long file list to evidence."""
    head, separator, _detail = scope.partition("; ")
    return head + ("; detail retained in full evidence" if separator else "")


def _bounded(text: str) -> str:
    """Keep a hostile one-line diagnostic from defeating the presentation cap."""
    encoded = text.encode("utf-8")
    if len(encoded) <= _MAX_FAILURE_LINE_BYTES:
        return text
    clipped = encoded[:_MAX_FAILURE_LINE_BYTES]
    while True:
        try:
            return clipped.decode("utf-8") + "…"
        except UnicodeDecodeError:
            clipped = clipped[:-1]
