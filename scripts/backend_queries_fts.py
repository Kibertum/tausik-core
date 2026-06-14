"""FTS5 maintenance — mixed into SQLiteBackend via BackendQueriesMixin.

Extracted from backend_queries.py (filesize cap). Provides manual optimize and
a threshold-gated auto-optimize used at session end (v15p-fts-optimize-cron).
"""

from __future__ import annotations

from typing import Any


class BackendQueriesFtsMixin:
    """FTS index maintenance. Relies on _q/_ex/meta_get/meta_set/event_add from
    the composed SQLiteBackend."""

    _FTS_TABLES = ("fts_tasks", "fts_memory", "fts_decisions")
    _FTS_OPTIMIZE_META_KEY = "fts.last_optimize_events"

    def fts_optimize(self) -> dict[str, str]:
        """Run FTS5 optimize on all full-text indexes."""
        results: dict[str, str] = {}
        for table in self._FTS_TABLES:
            try:
                self._ex(f"INSERT INTO {table}({table}) VALUES('optimize')")  # type: ignore[attr-defined]
                results[table] = "ok"
            except Exception as e:  # noqa: BLE001 — best-effort: maintenance/IO, non-fatal to the surrounding op
                results[table] = str(e)
        return results

    def _set_fts_baseline(self, value: int) -> None:
        try:
            self.meta_set(self._FTS_OPTIMIZE_META_KEY, str(value))  # type: ignore[attr-defined]
        except Exception:  # best-effort: a baseline write failure must not propagate  # noqa: BLE001 — best-effort: maintenance/IO, non-fatal to the surrounding op
            pass

    def fts_maybe_optimize(self, threshold: int = 200) -> dict[str, Any]:
        """Optimize FTS indexes only if write churn since the last optimize
        exceeds `threshold`. Cheap best-effort proxy: one COUNT(*) on the events
        table (every task/memory/decision mutation logs an event) approximates
        index fragmentation without parsing FTS5 internals or touching the write
        path. NOTE: direct DB migrations that bypass event_add are invisible to
        this proxy — run `tausik fts optimize` manually after such a load.
        Returns {optimized, events_delta, threshold, ...}.
        """
        try:
            current = int(self._q("SELECT count(*) AS c FROM events")[0]["c"])  # type: ignore[attr-defined]
        except Exception as e:  # best-effort: never let maintenance break session end  # noqa: BLE001 — best-effort: maintenance/IO, non-fatal to the surrounding op
            return {"optimized": False, "reason": f"events count failed: {e}"}
        try:
            last = int(self.meta_get(self._FTS_OPTIMIZE_META_KEY) or "0")  # type: ignore[attr-defined]
        except (TypeError, ValueError):
            last = 0
        delta = current - last
        if delta < 0:
            # events shrank (vacuum / DB replaced) — re-baseline, don't loop-fire.
            self._set_fts_baseline(current)
            return {
                "optimized": False,
                "events_delta": delta,
                "threshold": threshold,
                "reason": "baseline reset (events count shrank)",
            }
        if delta < threshold:
            return {"optimized": False, "events_delta": delta, "threshold": threshold}
        results = self.fts_optimize()
        try:
            self.event_add("fts", "all", "optimize", f"auto: {delta} events since last optimize")  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001 — best-effort: maintenance/IO, non-fatal to the surrounding op
            pass
        # Baseline AFTER logging so the optimize event itself isn't counted
        # toward the next window (delta truly resets to 0). If the recount fails,
        # approximate from the known count + the 1 optimize event we just logged —
        # never persist a stale (pre-optimize) baseline.
        try:
            baseline = int(self._q("SELECT count(*) AS c FROM events")[0]["c"])  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001 — best-effort: maintenance/IO, non-fatal to the surrounding op
            baseline = current + 1
        self._set_fts_baseline(baseline)
        return {
            "optimized": True,
            "events_delta": delta,
            "threshold": threshold,
            "results": results,
        }
