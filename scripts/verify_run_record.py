"""Insert a verification_run row and emit its signed receipt.

Extracted from service_verification.py for filesize-gate compliance when
l26-verify-git-diff-wire added the declared-scope columns. Follows the same
pattern as verify_cache.py / verify_files_hash.py: the logic lives here,
`service_verification` re-exports it, and every existing caller
(`service_verification.record_run`, `sv.record_run` in tests) keeps working
unchanged.

`_utcnow_iso` is defined locally rather than imported back from
service_verification — importing it would make the two modules circular, and
the same two-line helper is already defined independently in brain_status.py,
brain_metrics_log.py, model_routing_session.py and verify_endpoint.py.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def record_run(
    conn: sqlite3.Connection,
    *,
    task_slug: str | None,
    scope: str,
    command: str,
    exit_code: int,
    summary: str | None,
    files_hash: str,
    duration_ms: int | None = None,
    gate_results: list[dict[str, Any]] | None = None,
    project_dir: str | None = None,
    scope_description: dict[str, Any] | None = None,
) -> int:
    """Insert a verify run. Returns the new row id.

    With `gate_results` and a `task_slug`, also emits a signed receipt into
    the row's receipt_json (v15-receipt-emit-on-verify). Emission is
    best-effort: no project key / signing failure never breaks the run
    record. `project_dir` defaults to the current working directory (the
    CLI/MCP convention for key lookup).

    `scope_description` (l26-verify-git-diff-wire) is the dict from
    `verify_scope_honesty.describe_declared_scope`. It is persisted on the row
    AND signed into the receipt, so the proof states whether its own scope was
    known to be complete. Omitting it records "unknown" — never "complete":
    a caller that did not measure must not be able to claim full coverage by
    saying nothing.
    """
    status = str((scope_description or {}).get("status") or "unknown")
    undeclared = list((scope_description or {}).get("undeclared") or [])
    undeclared_count = int((scope_description or {}).get("undeclared_count") or 0)
    cur = conn.execute(
        """
        INSERT INTO verification_runs
            (task_slug, scope, command, exit_code, summary, files_hash,
             ran_at, duration_ms, declared_scope_status, undeclared_files)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            task_slug,
            scope,
            command,
            exit_code,
            summary,
            files_hash,
            _utcnow_iso(),
            duration_ms,
            status,
            json.dumps(undeclared, ensure_ascii=True, sort_keys=True) if undeclared else None,
        ),
    )
    conn.commit()
    run_id = int(cur.lastrowid or 0)
    if task_slug and gate_results is not None:
        from verify_receipt_emit import emit_signed_receipt

        emit_signed_receipt(
            conn,
            run_id,
            task_slug=task_slug,
            scope=scope,
            gate_results=gate_results,
            passed=exit_code == 0,
            files_hash=files_hash,
            project_dir=project_dir or ".",
            declared_scope_status=status,
            undeclared_files=undeclared,
            undeclared_count=undeclared_count,
        )
    return run_id
