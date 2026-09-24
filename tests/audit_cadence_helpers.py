"""Shared fixture helper: make the SENAR 9.5 audit overdue under the 1.10 clock.

The cadence counts CLOSURES since the last audit mark (decision #376), so
"overdue" is a mark in the past plus as many closed tasks as the threshold.
"""

from __future__ import annotations


def make_audit_overdue(svc, closures: int = 17) -> None:
    svc.be.meta_set("last_audit_at", "2000-01-01T00:00:00Z")
    try:
        svc.epic_add("cad-e", "Cadence epic")
        svc.story_add("cad-e", "cad-s", "Cadence story")
    except Exception:  # noqa: BLE001 — already seeded by an earlier call
        pass
    for i in range(closures):
        slug = f"cad-{i}"
        svc.task_add("cad-s", slug, f"Closed {i}", role="developer", goal="g")
        svc.be.task_update(slug, status="done", completed_at="2026-09-23T00:00:00Z")
