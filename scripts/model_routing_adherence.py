"""Routing adherence telemetry — recommended vs actual model per task close.

On `task done` (when both are known) we append one row pairing the model that
was *recommended* at task_start (persisted by `model_routing_session`) with the
model that was actually *active* (read from the transcript). `tausik metrics`
aggregates these into a % adherence + top deviations — calibration data for the
phase x complexity matrix (`model_routing_matrix`).

Storage is a crash-safe append-only JSONL sidecar (`.tausik/routing_adherence.jsonl`),
mirroring `.task_recommendation.json` rather than polluting the append-only task
notes journal or the LLM-usage table. Every op is best-effort: a missing
transcript, unknown family, or IO error skips the row WITHOUT raising — task
closure is never blocked.

Env knob: TAUSIK_DISABLE_ROUTING_ADHERENCE=1 makes record/aggregate no-ops.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Final

_FILENAME: Final[str] = "routing_adherence.jsonl"
_SCHEMA_VERSION: Final[int] = 1


def _path(tausik_dir: str) -> str:
    return os.path.join(tausik_dir, _FILENAME)


def _disabled() -> bool:
    return os.environ.get("TAUSIK_DISABLE_ROUTING_ADHERENCE", "").strip() == "1"


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def record_adherence(
    tausik_dir: str,
    slug: str,
    recommended_model: str | None,
    actual_model: str | None,
) -> dict[str, Any] | None:
    """Append one recommended/actual pair. Returns the row, or None when skipped.

    Skipped (no error) when slug or either model is missing, or when either
    model id has an unrecognised tier family — recording a bogus adherence row
    is worse than recording none.
    """
    if _disabled():
        return None
    if not slug or not recommended_model or not actual_model:
        return None
    try:
        # Import from the definition site (model_routing_matrix), not the
        # model_routing re-export wrapper (H3 review fix): avoids the indirection
        # and any risk of a shadowed/patched re-export diverging.
        from model_routing_matrix import _model_family

        rec_fam = _model_family(recommended_model)
        act_fam = _model_family(actual_model)
        if rec_fam is None or act_fam is None:
            return None
        row = {
            "schema_version": _SCHEMA_VERSION,
            "slug": str(slug).strip(),
            "recommended": str(recommended_model).strip(),
            "actual": str(actual_model).strip(),
            "recommended_family": rec_fam,
            "actual_family": act_fam,
            "match": rec_fam == act_fam,
            "recorded_at": _utcnow_iso(),
        }
        os.makedirs(tausik_dir, exist_ok=True)
        with open(_path(tausik_dir), "a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")
        return row
    except OSError as e:
        print(f"WARN [routing_adherence]: write failed for {tausik_dir}: {e}", file=sys.stderr)
        return None
    except Exception as e:  # noqa: BLE001 — best-effort: telemetry/degradation, non-fatal to the main flow
        print(f"WARN [routing_adherence]: record failed: {e}", file=sys.stderr)
        return None


def record_close_adherence(tausik_dir: str, slug: str) -> dict[str, Any] | None:
    """Pair the start-time recommendation with the active transcript model.

    Convenience wrapper called from `task_done`: reads the persisted
    recommendation (`model_routing_session`) + the active model (transcript)
    and records the pair. Best-effort — returns the row or None; never raises.
    """
    try:
        from model_routing_session import read_active_task_recommendation

        rec = read_active_task_recommendation(tausik_dir)
        if not rec:
            return None
        from model_routing import _auto_find_transcript, read_active_model_from_transcript

        actual = read_active_model_from_transcript(_auto_find_transcript())
        return record_adherence(tausik_dir, slug, rec.get("model"), actual)
    except Exception:  # noqa: BLE001 — best-effort: telemetry/degradation, non-fatal to the main flow
        return None


def finalize_close(tausik_dir: str, slug: str) -> None:
    """On task close: record adherence, then drop the spent recommendation.

    Single entry point for `task_done` — records the recommended-vs-actual pair
    and clears the now-consumed start-time recommendation. Best-effort, never raises.
    """
    record_close_adherence(tausik_dir, slug)
    try:
        from model_routing_session import clear_active_task_recommendation

        clear_active_task_recommendation(tausik_dir)
    except Exception:  # noqa: BLE001 — best-effort: telemetry/degradation, non-fatal to the main flow
        pass


def aggregate_adherence(tausik_dir: str) -> dict[str, Any]:
    """Aggregate the sidecar into {n, matches, pct, top_deviations}.

    `pct` is the family-match rate (0.0 when n==0). `top_deviations` lists the
    most frequent recommended->actual family shifts (up to 3). Malformed lines
    are skipped. Never raises — returns n=0 on any read failure.
    """
    n = 0
    matches = 0
    deviations: dict[str, int] = {}
    path = _path(tausik_dir)
    if os.path.isfile(path):
        try:
            with open(path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        row = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if not isinstance(row, dict):
                        continue
                    # Skip rows from a future schema rather than misread them (L1).
                    if row.get("schema_version", _SCHEMA_VERSION) != _SCHEMA_VERSION:
                        continue
                    rec_fam = row.get("recommended_family")
                    act_fam = row.get("actual_family")
                    if not rec_fam or not act_fam:
                        continue
                    n += 1
                    # Recompute the match from the family fields rather than
                    # trusting the persisted flag (M3): a corrupted/hand-edited
                    # 'match' can't inflate the adherence %.
                    if rec_fam == act_fam:
                        matches += 1
                    else:
                        key = f"{rec_fam}->{act_fam}"
                        deviations[key] = deviations.get(key, 0) + 1
        except OSError:
            pass
    pct = round(100.0 * matches / n, 1) if n else 0.0
    top = sorted(deviations.items(), key=lambda kv: (-kv[1], kv[0]))[:3]
    return {
        "n": n,
        "matches": matches,
        "pct": pct,
        "top_deviations": [{"shift": k, "count": v} for k, v in top],
    }
