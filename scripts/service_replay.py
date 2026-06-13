"""TAUSIK ReplayMixin — RENAR task-timeline reconstruction.

Block #3 of the RENAR release: ``task replay <slug>`` stitches a task's
task_logs, reasoning_steps, events, and verification_runs (with receipt
signature) into a single chronological markdown timeline.

Mixed into TaskMixin; relies on the composed service's ``_require_task`` and
the backend's per-source readers. Read-only — never writes to the DB.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, NamedTuple

from tausik_utils import ServiceError

if TYPE_CHECKING:
    from project_backend import SQLiteBackend


class _Entry(NamedTuple):
    sort_key: float
    ts: str
    source: str
    text: str


def _ts_sort_key(ts: str | None) -> float:
    """Parse an ISO-8601 timestamp to a sortable epoch float.

    Robust against format drift (``Z`` vs ``+00:00``, naive vs aware,
    microseconds). Unparseable / missing values sort first (0.0) so a
    malformed row never crashes the merge.
    """
    if not ts or not isinstance(ts, str):
        return 0.0
    try:
        dt = datetime.fromisoformat(ts.strip().replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return 0.0
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.timestamp()


def _receipt_note(receipt_json: str | None) -> str:
    """Render a short receipt marker from a verification_run's receipt_json."""
    if not receipt_json:
        return "no receipt"
    try:
        env = json.loads(receipt_json)
    except (ValueError, TypeError):
        return "receipt: present (corrupt)"
    fp = ""
    if isinstance(env, dict):
        sig = env.get("signature")
        if isinstance(sig, dict):
            fp = str(sig.get("key_fingerprint") or "")
    return f"receipt: signed (key {fp})" if fp else "receipt: present"


def _guard_output_path(output: str) -> None:
    """Refuse to write a replay into a protected agent-memory directory.

    ``open()`` bypasses the memory-write pretool hook, so an ``--output`` (or
    MCP ``output``) pointing at ``~/.claude/**/memory/`` (or .cursor/.qwen)
    could clobber agent memory. Project-local and arbitrary temp paths stay
    allowed — the user already has full FS access via the shell.
    """
    norm = os.path.realpath(output).replace("\\", "/").lower()
    if "/memory/" in norm and any(d in norm for d in ("/.claude/", "/.cursor/", "/.qwen/")):
        raise ServiceError(
            f"Refusing to write replay into a protected agent-memory directory: {output}"
        )


class ReplayMixin:
    """Reconstruct a readable chronological timeline for a task."""

    be: SQLiteBackend

    if TYPE_CHECKING:

        def _require_task(self, slug: str) -> dict[str, Any]: ...
        def task_logs(self, slug: str, phase: str | None = ...) -> list[dict]: ...
        def reasoning_steps(self, slug: str) -> list[dict]: ...
        def events_list(
            self, entity_type: str | None = ..., entity_id: str | None = ..., n: int = ...
        ) -> list[dict]: ...

    def task_replay(self, slug: str, output: str | None = None) -> str:
        """Return a markdown timeline for ``slug`` (or write it to ``output``).

        Merges four append-only sources by timestamp. Sources that are empty
        (e.g. a historical task predating reasoning_steps) render as an
        explicit ``(none)`` marker rather than raising — replay must work on
        any task, old or new. A missing slug raises a friendly ServiceError.
        """
        task = self._require_task(slug)
        entries, counts = self._collect_entries(slug)
        entries.sort(key=lambda e: (e.sort_key, e.ts))
        md = self._render(task, entries, counts)
        if output:
            _guard_output_path(output)
            try:
                with open(output, "w", encoding="utf-8") as fh:
                    fh.write(md)
            except OSError as e:
                raise ServiceError(f"Could not write replay to '{output}': {e}") from e
            return f"Replay for '{slug}' written to {output} ({len(entries)} entries)."
        return md

    def _collect_entries(self, slug: str) -> tuple[list[_Entry], dict[str, int]]:
        """Gather all four sources into a flat entry list + per-source counts."""
        entries: list[_Entry] = []

        logs = self.task_logs(slug)
        for row in logs:
            phase = f" [{row['phase']}]" if row.get("phase") else ""
            diff = f" ({row['diff_stats']})" if row.get("diff_stats") else ""
            entries.append(
                _Entry(
                    _ts_sort_key(row.get("created_at")),
                    row.get("created_at", ""),
                    "log",
                    f"{row.get('message', '')}{phase}{diff}",
                )
            )

        steps = self.reasoning_steps(slug)
        for s in steps:
            entries.append(
                _Entry(
                    _ts_sort_key(s.get("created_at")),
                    s.get("created_at", ""),
                    "reason",
                    f"({s.get('kind')} #{s.get('seq')}) {s.get('content', '')}",
                )
            )

        events = self.events_list(entity_type="task", entity_id=slug, n=1000)
        for ev in events:
            actor = f" by {ev['actor']}" if ev.get("actor") else ""
            details = f" — {ev['details']}" if ev.get("details") else ""
            entries.append(
                _Entry(
                    _ts_sort_key(ev.get("created_at")),
                    ev.get("created_at", ""),
                    "event",
                    f"{ev.get('action', '')}{actor}{details}",
                )
            )

        runs = self.be.verification_runs_for_task(slug)
        for r in runs:
            dur = f", {r['duration_ms']}ms" if r.get("duration_ms") is not None else ""
            ec = r.get("exit_code")
            verdict = "INCOMPLETE" if ec is None else ("PASS" if ec == 0 else f"FAIL(exit={ec})")
            note = _receipt_note(r.get("receipt_json"))
            entries.append(
                _Entry(
                    _ts_sort_key(r.get("ran_at")),
                    r.get("ran_at", ""),
                    "verify",
                    f"{verdict} scope={r.get('scope')} `{r.get('command', '')}`{dur} — {note}",
                )
            )

        counts = {
            "logs": len(logs),
            "reasoning steps": len(steps),
            "events": len(events),
            "verification runs": len(runs),
        }
        return entries, counts

    @staticmethod
    def _render(task: dict[str, Any], entries: list[_Entry], counts: dict[str, int]) -> str:
        """Render the header + chronological timeline + per-source footer."""
        slug = task.get("slug", "")
        lines = [f"# Replay — {slug}", ""]
        meta = f"**Title:** {task.get('title', '')} | **Status:** {task.get('status', '')}"
        lines.append(meta)
        if task.get("goal"):
            lines.append(f"**Goal:** {task['goal']}")
        window = f"{task.get('started_at') or '—'} → {task.get('completed_at') or '—'}"
        lines.append(f"**Window:** {window}")
        lines.append("")
        lines.append(f"## Timeline ({len(entries)} entries)")
        lines.append("")
        if entries:
            for e in entries:
                lines.append(f"- `{e.ts or '—'}` **{e.source}** {e.text}")
        else:
            lines.append("(none — no logs, reasoning, events, or verification recorded)")
        lines.append("")
        lines.append("## Sources")
        lines.append("")
        for label, n in counts.items():
            lines.append(f"- {label}: {n}" + ("" if n else " (none)"))
        return "\n".join(lines) + "\n"
