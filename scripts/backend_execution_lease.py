"""Atomic persistence primitives for host-thread execution leases."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from tausik_utils import utcnow_iso

if TYPE_CHECKING:
    import sqlite3


class ExecutionLeaseMixin:
    """SQLite operations that keep lease issuance and revocation atomic."""

    if TYPE_CHECKING:
        _conn: sqlite3.Connection

        def _q1(self, sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None: ...

        def _ex(self, sql: str, params: tuple[Any, ...] = ()) -> int: ...

        def _ins(self, sql: str, params: tuple[Any, ...] = ()) -> int: ...

        def transaction(self): ...

    def _execution_lease_current(
        self,
        project_identity: str,
        host_instance: str,
        thread_id: str,
        at: str | None = None,
    ) -> dict[str, Any] | None:
        rows = self._conn.execute(
            "SELECT * FROM execution_leases WHERE project_identity=? "
            "AND host_instance=? AND thread_id=? AND revoked_at IS NULL AND expires_at>? "
            "AND EXISTS(SELECT 1 FROM sessions s WHERE s.id=execution_leases.session_id "
            "AND s.ended_at IS NULL) "
            "ORDER BY id DESC",
            (project_identity, host_instance, thread_id, at or utcnow_iso()),
        ).fetchall()
        if len(rows) > 1:
            raise ValueError("IDENTITY_AMBIGUOUS: multiple live execution leases")
        return dict(rows[0]) if rows else None

    def _execution_lease_by_nonce(self, nonce: str) -> dict[str, Any] | None:
        return self._q1("SELECT * FROM execution_leases WHERE nonce=?", (nonce,))

    def _execution_lease_by_assertion(self, nonce: str) -> dict[str, Any] | None:
        return self._q1("SELECT * FROM execution_leases WHERE assertion_nonce=?", (nonce,))

    def _execution_lease_issue(
        self,
        *,
        session_id: int,
        project_identity: str,
        host_instance: str,
        thread_id: str,
        assertion_nonce: str,
        assertion_issued_at: str,
        assertion_expires_at: str,
        nonce: str,
        issued_at: str,
        expires_at: str,
        projection_build: str,
        capability_min: int,
        capability_max: int,
        task_slug: str | None,
        task_package_fingerprint: str | None,
    ) -> dict[str, Any]:
        with self.transaction():
            existing = self._execution_lease_current(
                project_identity, host_instance, thread_id, issued_at
            )
            if (
                existing
                and existing["expires_at"] > issued_at
                and existing["projection_build"] == projection_build
                and existing["capability_min"] == capability_min
                and existing["capability_max"] == capability_max
            ):
                if task_slug is not None:
                    self._ex(
                        "UPDATE execution_leases SET task_slug=?, task_package_fingerprint=? "
                        "WHERE id=?",
                        (task_slug, task_package_fingerprint, existing["id"]),
                    )
                refreshed = self._q1("SELECT * FROM execution_leases WHERE id=?", (existing["id"],))
                assert refreshed is not None
                return refreshed
            self._ex(
                "UPDATE execution_leases SET revoked_at=? WHERE project_identity=? "
                "AND host_instance=? AND thread_id=? AND revoked_at IS NULL",
                (issued_at, project_identity, host_instance, thread_id),
            )
            lease_id = self._ins(
                "INSERT INTO execution_leases(session_id, project_identity, "
                "host_instance, thread_id, assertion_nonce, assertion_issued_at, "
                "assertion_expires_at, nonce, issued_at, expires_at, "
                "projection_build, capability_min, capability_max, task_slug, "
                "task_package_fingerprint) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    session_id,
                    project_identity,
                    host_instance,
                    thread_id,
                    assertion_nonce,
                    assertion_issued_at,
                    assertion_expires_at,
                    nonce,
                    issued_at,
                    expires_at,
                    projection_build,
                    capability_min,
                    capability_max,
                    task_slug,
                    task_package_fingerprint,
                ),
            )
            row = self._q1("SELECT * FROM execution_leases WHERE id=?", (lease_id,))
            assert row is not None
            return row

    def _execution_lease_revoke_session(self, session_id: int) -> int:
        return self._ex(
            "UPDATE execution_leases SET revoked_at=? WHERE session_id=? AND revoked_at IS NULL",
            (utcnow_iso(), session_id),
        )

    def _execution_lease_revoke_all(self, reason_at: str) -> int:
        return self._ex(
            "UPDATE execution_leases SET revoked_at=? WHERE revoked_at IS NULL",
            (reason_at,),
        )

    def _execution_lease_unbind_task(self, task_slug: str, changed_at: str) -> int:
        """Release live leases from a terminal task without touching other threads."""
        self._ex(
            "UPDATE execution_authorizations SET consumed_at=? "
            "WHERE consumed_at IS NULL AND lease_id IN "
            "(SELECT id FROM execution_leases WHERE task_slug=? AND revoked_at IS NULL)",
            (changed_at, task_slug),
        )
        return self._ex(
            "UPDATE execution_leases SET task_slug=NULL,task_package_fingerprint=NULL "
            "WHERE task_slug=? AND revoked_at IS NULL",
            (task_slug,),
        )

    def _execution_lease_state(self) -> dict[str, Any] | None:
        return self._q1("SELECT * FROM execution_lease_state WHERE singleton=1")

    def _execution_lease_set_state(
        self,
        *,
        mode: str,
        reason: str | None,
        projection_build: str,
        capability_version: int,
        updated_at: str,
    ) -> None:
        self._ex(
            "INSERT INTO execution_lease_state(singleton, mode, reason, projection_build, "
            "capability_version, updated_at) VALUES(1,?,?,?,?,?) "
            "ON CONFLICT(singleton) DO UPDATE SET mode=excluded.mode, reason=excluded.reason, "
            "projection_build=excluded.projection_build, "
            "capability_version=excluded.capability_version, updated_at=excluded.updated_at",
            (mode, reason, projection_build, capability_version, updated_at),
        )

    def _execution_authorization_issue(
        self, *, lease_id: int, route: str, arguments_hash: str, issued_at: str, expires_at: str
    ) -> int:
        self._ex(
            "DELETE FROM execution_authorizations WHERE consumed_at IS NOT NULL OR expires_at<=?",
            (issued_at,),
        )
        return self._ins(
            "INSERT INTO execution_authorizations(lease_id, route, arguments_hash, "
            "issued_at, expires_at) VALUES(?,?,?,?,?)",
            (lease_id, route, arguments_hash, issued_at, expires_at),
        )

    def _execution_authorization_consume(
        self, *, route: str, arguments_hash: str, consumed_at: str
    ) -> dict[str, Any] | None:
        with self.transaction():
            rows = self._conn.execute(
                "SELECT a.* FROM execution_authorizations a "
                "JOIN execution_leases l ON l.id=a.lease_id "
                "WHERE a.route=? AND a.arguments_hash=? AND a.consumed_at IS NULL "
                "AND a.expires_at>? AND l.revoked_at IS NULL AND l.expires_at>? "
                "ORDER BY a.id LIMIT 1",
                (route, arguments_hash, consumed_at, consumed_at),
            ).fetchall()
            if not rows:
                return None
            count = self._q1(
                "SELECT COUNT(*) AS count FROM execution_authorizations a "
                "JOIN execution_leases l ON l.id=a.lease_id "
                "WHERE a.route=? AND a.arguments_hash=? AND a.consumed_at IS NULL "
                "AND a.expires_at>? AND l.revoked_at IS NULL AND l.expires_at>?",
                (route, arguments_hash, consumed_at, consumed_at),
            )
            if count is not None and count["count"] != 1:
                raise ValueError("AUTHORIZATION_AMBIGUOUS: matching hook actions are not unique")
            row = dict(rows[0])
            self._ex(
                "UPDATE execution_authorizations SET consumed_at=? "
                "WHERE id=? AND consumed_at IS NULL",
                (consumed_at, row["id"]),
            )
            return row
