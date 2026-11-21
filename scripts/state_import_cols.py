"""Column mappers: parsed tree record → DB columns for state import."""

from __future__ import annotations

from state_export import _json_object
from state_parse import parse_sections

# Imported from state_import after that module defines ABSENT / helpers —
# callers pass the shared sentinels and accessors to avoid a cycle.


def epic_cols(rec: dict, *, fm_get) -> dict:
    return {
        "title": fm_get(rec["fm"], "title"),
        "status": fm_get(rec["fm"], "status"),
        "description": rec["body"] or None,
    }


def story_cols(rec: dict, epic_id: int | None, *, fm_get) -> dict:
    return {
        "epic_id": epic_id,
        "title": fm_get(rec["fm"], "title"),
        "status": fm_get(rec["fm"], "status"),
        "description": rec["body"] or None,
    }


def task_cols(
    rec: dict,
    story_id: int | None,
    *,
    fm_get,
    fm_list,
    absent,
    task_sections: list[str],
) -> dict:
    from backend_migrations_v84 import legacy_marker_for_imported_task

    fm, secs = rec["fm"], parse_sections(rec["body"], task_sections)
    profiles = fm_list(fm, "assurance_profiles")
    impact = _json_object(fm["assurance_impact"]) if "assurance_impact" in fm else absent
    call_budget = fm_get(fm, "call_budget")
    complexity = fm_get(fm, "complexity")
    cols = {
        "story_id": story_id,
        "title": fm_get(fm, "title"),
        "status": fm_get(fm, "status"),
        "stack": fm_get(fm, "stack"),
        "complexity": complexity,
        "role": fm_get(fm, "role"),
        "tier": fm_get(fm, "tier"),
        "goal": secs["Goal"] or None,
        "plan": secs["Plan"] or None,
        "acceptance_criteria": secs["Acceptance Criteria"] or None,
        "rollback_plan": secs["Rollback"] or None,
        "scope": fm_get(fm, "scope"),
        "scope_exclude": fm_get(fm, "scope_exclude"),
        "scope_paths": fm_list(fm, "scope_paths"),
        "scope_tools": fm_list(fm, "scope_tools"),
        "relevant_files": fm_list(fm, "relevant_files"),
        "assurance_profiles": profiles,
        "assurance_impact": impact,
        "defect_of": fm_get(fm, "defect_of"),
        "call_budget": call_budget,
        "completed_at": fm_get(fm, "completed_at"),
        "resolution": fm_get(fm, "resolution"),
        "resolution_reason": fm_get(fm, "resolution_reason"),
    }
    marker = legacy_marker_for_imported_task(
        complexity=complexity,
        call_budget=None if call_budget is absent else call_budget,
        assurance_profiles=None if profiles is absent else profiles,
        assurance_impact=None if impact is absent else impact,
    )
    if marker is not None:
        cols["task_package_legacy"] = marker
    return cols


def decision_cols(rec: dict, *, fm_get) -> dict:
    secs = parse_sections(rec["body"], ["Decision", "Rationale"])
    return {
        "decision": secs["Decision"] or "",
        "task_slug": fm_get(rec["fm"], "task"),
        "rationale": secs["Rationale"] or None,
    }


def memory_cols(rec: dict, *, fm_get, fm_list) -> dict:
    fm = rec["fm"]
    return {
        "type": fm_get(fm, "type"),
        "title": fm_get(fm, "title"),
        "content": rec["body"] or "",
        "tags": fm_list(fm, "tags"),
        "task_slug": fm_get(fm, "task"),
    }
