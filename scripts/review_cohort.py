"""Bounded two-round L3 review cohorts.

The module is deliberately transport-free. CLI and MCP call the same four
operations, and the task close gate consumes the same persisted task-indexed
receipt. Deterministic verification cohorts remain a separate subsystem.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, cast

from review_routing import review_state_fingerprint
from review_separation import review_model_family

POLICY_SIGNATURE = "bounded-l3-review.v1:rounds=2:medium-low=advisory"
_OPEN_STATES = ("open", "round1_red")
_CLOSABLE_STATES = ("green", "accepted_risk")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _root(svc: Any) -> Path:
    from project_root import root_from_service

    resolved = root_from_service(svc)
    return Path(resolved).resolve() if resolved else Path.cwd().resolve()


def _head(root: Path) -> str:
    try:
        return subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
            stdin=subprocess.DEVNULL,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError) as exc:
        raise ValueError(f"repository lineage is unavailable: {exc}") from exc


def _selector(tasks: list[str] | None, story: str | None, epic: str | None) -> tuple[str, str]:
    supplied = sum(bool(v) for v in (tasks, story, epic))
    if supplied != 1:
        raise ValueError("supply exactly one selector: tasks, story, or epic")
    if tasks:
        members = sorted(set(str(slug) for slug in tasks if str(slug).strip()))
        if not members:
            raise ValueError("tasks selector is empty")
        return "tasks", _canonical(members)
    return ("story", str(story)) if story else ("epic", str(epic))


def _selected_rows(be: Any, kind: str, value: str) -> list[dict[str, Any]]:
    if kind == "tasks":
        slugs = json.loads(value)
        rows = []
        for slug in slugs:
            row = be._q1("SELECT * FROM tasks WHERE slug=?", (slug,))
            if row is None:
                raise ValueError(f"task not found: {slug}")
            rows.append(row)
        return rows
    if kind == "story":
        exists = be._q1("SELECT 1 AS ok FROM stories WHERE slug=?", (value,))
        if not exists:
            raise ValueError(f"story not found: {value}")
        return cast(
            list[dict[str, Any]],
            be._q(
                "SELECT t.* FROM tasks t JOIN stories s ON s.id=t.story_id "
                "WHERE s.slug=? AND t.status!='done' ORDER BY t.slug",
                (value,),
            ),
        )
    exists = be._q1("SELECT 1 AS ok FROM epics WHERE slug=?", (value,))
    if not exists:
        raise ValueError(f"epic not found: {value}")
    return cast(
        list[dict[str, Any]],
        be._q(
            "SELECT t.* FROM tasks t JOIN stories s ON s.id=t.story_id "
            "JOIN epics e ON e.id=s.epic_id WHERE e.slug=? AND t.status!='done' ORDER BY t.slug",
            (value,),
        ),
    )


def _route(svc: Any, slug: str) -> dict[str, Any]:
    from project_cli_review import _route_for_task

    return _route_for_task(svc, slug, deep=False)


def _resolve(svc: Any, kind: str, value: str) -> tuple[list[str], dict[str, Any], list[str]]:
    rows = _selected_rows(svc.be, kind, value)
    if not rows:
        raise ValueError("selector resolves to no non-done tasks")
    members: list[str] = []
    routes: dict[str, Any] = {}
    not_required: list[str] = []
    not_ready: list[str] = []
    from verify_hierarchy import review_ready_reasons

    for row in sorted(rows, key=lambda item: item["slug"]):
        slug = str(row["slug"])
        route = _route(svc, slug)
        if route.get("depth") != "L3":
            not_required.append(slug)
            continue
        if route.get("deep"):
            raise ValueError(f"{slug}: L3-deep requires the explicit deep workflow")
        if row.get("status") not in ("active", "review"):
            not_ready.append(f"{slug}: status must be active or review")
        if review_model_family(row.get("started_model_id")) is None:
            not_ready.append(f"{slug}: trusted started_model_id is required for L3 separation")
        not_ready.extend(review_ready_reasons(svc.be, [slug]))
        members.append(slug)
        routes[slug] = route
    if not_ready:
        raise ValueError("L3 cohort not review-ready: " + "; ".join(not_ready))
    if not members:
        raise ValueError("selector contains no normal-L3 tasks; review not required")
    return members, routes, not_required


def _round_fingerprint(conn: Any, slug: str, root: Path) -> str:
    deps = conn.execute(
        "SELECT task_slug, depends_on_slug FROM task_deps "
        "WHERE task_slug=? OR depends_on_slug=? ORDER BY task_slug, depends_on_slug",
        (slug, slug),
    ).fetchall()
    return _digest(
        {
            "reviewed_state": review_state_fingerprint(conn, slug, root),
            "dependencies": [list(row) for row in deps],
        }
    )


def _json_value(raw: Any, fallback: Any) -> Any:
    try:
        value = json.loads(raw) if isinstance(raw, str) else raw
    except (TypeError, ValueError):
        return fallback
    return fallback if value is None else value


def _packet(
    conn: Any,
    members: list[str],
    root: Path,
    round_number: int,
    routes: Mapping[str, Any],
) -> dict[str, Any]:
    head = _head(root)
    fingerprints = {slug: _round_fingerprint(conn, slug, root) for slug in members}
    contexts: list[dict[str, Any]] = []
    for slug in members:
        row = dict(conn.execute("SELECT * FROM tasks WHERE slug=?", (slug,)).fetchone())
        deps = conn.execute(
            "SELECT task_slug, depends_on_slug FROM task_deps "
            "WHERE task_slug=? OR depends_on_slug=? ORDER BY task_slug, depends_on_slug",
            (slug, slug),
        ).fetchall()
        ac_evidence = [
            dict(log)
            for log in conn.execute(
                "SELECT id,message,phase,created_at FROM task_logs "
                "WHERE task_slug=? AND message LIKE '%AC-%' ORDER BY id",
                (slug,),
            ).fetchall()
        ]
        contexts.append(
            {
                "slug": slug,
                "title": row.get("title"),
                "goal": row.get("goal"),
                "acceptance_criteria": row.get("acceptance_criteria"),
                "numbered_ac_evidence": ac_evidence,
                "plan": _json_value(row.get("plan"), []),
                "relevant_files": _json_value(row.get("relevant_files"), []),
                "scope": row.get("scope"),
                "stack": row.get("stack"),
                "role": row.get("role"),
                "risk": _json_value(row.get("risk_json"), None),
                "route": routes[slug],
                "author_model": row.get("started_model_id"),
                "dependencies": [list(dep) for dep in deps],
                "reviewed_state_fingerprint": fingerprints[slug],
            }
        )
    packet = {
        "round": round_number,
        "members": members,
        "tasks": contexts,
        "fingerprints": fingerprints,
        "repository_head": head,
        "repository_state_digest": _digest({"head": head, "fingerprints": fingerprints}),
    }
    packet["packet_digest"] = _digest(packet)
    return packet


def _issue_packet(
    svc: Any, cohort: Mapping[str, Any], members: list[str], round_number: int
) -> dict:
    routes = json.loads(cohort["routes_json"])
    packet = _packet(svc.be._conn, members, _root(svc), round_number, routes)
    issued = svc.be._q1(
        "SELECT packet_json,packet_digest FROM review_cohort_packets "
        "WHERE cohort_pk=? AND round_number=?",
        (cohort["id"], round_number),
    )
    if issued is not None:
        try:
            stored = json.loads(issued["packet_json"])
        except (TypeError, ValueError) as exc:
            raise ValueError("issued review packet is unreadable") from exc
        if issued["packet_digest"] != packet["packet_digest"]:
            raise ValueError("issued review packet is stale; open a fresh cohort generation")
        return cast(dict[str, Any], stored)
    stamp = _now()
    svc.be._run_write(
        "INSERT INTO review_cohort_packets(cohort_pk,round_number,packet_json,packet_digest,issued_at) "
        "VALUES(?,?,?,?,?)",
        (cohort["id"], round_number, _canonical(packet), packet["packet_digest"], stamp),
    )
    return packet


def open_review_cohort(
    svc: Any,
    *,
    tasks: list[str] | None = None,
    story: str | None = None,
    epic: str | None = None,
) -> dict[str, Any]:
    """Resolve one selector and return the full round-one L3 packet."""
    kind, value = _selector(tasks, story, epic)
    members, routes, not_required = _resolve(svc, kind, value)
    root = _root(svc)
    lineage = _head(root)
    route_signatures = {slug: _digest(routes[slug]) for slug in members}
    family_key = _digest(
        {
            "selector": {"kind": kind, "value": value},
            "members": members,
            "routes": route_signatures,
            "policy": POLICY_SIGNATURE,
            "opening_lineage": lineage,
        }
    )
    with svc.be.transaction():
        existing = svc.be._q1(
            "SELECT * FROM review_cohorts WHERE family_key=? OR "
            "(family_key IS NULL AND cohort_key=?) ORDER BY generation DESC,id DESC LIMIT 1",
            (family_key, family_key),
        )
        if existing:
            reusable = existing["state"] not in (
                "repair_open",
                "awaiting_manual_review",
                "invalidated",
            )
            if existing["state"] in ("green", "accepted_risk"):
                latest = _latest_results(svc.be, int(existing["id"]))
                reusable = (
                    reusable
                    and set(latest) == set(members)
                    and all(
                        latest[slug]["reviewed_state_fingerprint"]
                        == _round_fingerprint(svc.be._conn, slug, root)
                        for slug in members
                    )
                )
            if reusable and existing["state"] in ("open", "round1_red"):
                issued = svc.be._q1(
                    "SELECT packet_json,packet_digest FROM review_cohort_packets "
                    "WHERE cohort_pk=? AND round_number=?",
                    (existing["id"], int(existing["current_round"] or 0) + 1),
                )
                if issued is not None:
                    try:
                        issued_packet = json.loads(issued["packet_json"])
                        packet_members = list(issued_packet.get("members") or [])
                        current_packet = _packet(
                            svc.be._conn,
                            packet_members,
                            root,
                            int(issued_packet.get("round") or 0),
                            json.loads(existing["routes_json"]),
                        )
                        reusable = current_packet["packet_digest"] == issued["packet_digest"]
                    except (TypeError, ValueError):
                        reusable = False
            if reusable:
                return cohort_status(svc, int(existing["id"]))
            svc.be._conn.execute(
                "UPDATE review_cohorts SET state='invalidated',updated_at=? WHERE id=?",
                (_now(), existing["id"]),
            )
        generation = int(existing["generation"] or 1) + 1 if existing else 1
        key = (
            family_key
            if generation == 1
            else _digest({"family": family_key, "generation": generation})
        )
        stamp = _now()
        cur = svc.be._conn.execute(
            "INSERT INTO review_cohorts(cohort_key, selector_kind, selector_value, members_json, "
            "routes_json, policy_signature, opening_lineage, family_key, generation, "
            "parent_cohort_pk, created_at, updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                key,
                kind,
                value,
                _canonical(members),
                _canonical(routes),
                POLICY_SIGNATURE,
                lineage,
                family_key,
                generation,
                existing["id"] if existing else None,
                stamp,
                stamp,
            ),
        )
        cohort = svc.be._q1("SELECT * FROM review_cohorts WHERE id=?", (int(cur.lastrowid),))
        packet = _issue_packet(svc, cohort, members, 1)
        return {
            "cohort_id": int(cur.lastrowid),
            "cohort_key": key,
            "generation": generation,
            "state": "open",
            "members": members,
            "review_not_required": not_required,
            "packet": packet,
            "rounds": "0/2",
        }


def _cohort(be: Any, cohort_id: int) -> dict[str, Any]:
    row = be._q1("SELECT * FROM review_cohorts WHERE id=?", (cohort_id,))
    if row is None:
        raise ValueError(f"review cohort not found: {cohort_id}")
    return cast(dict[str, Any], row)


def _latest_results(be: Any, cohort_id: int) -> dict[str, dict[str, Any]]:
    rows = be._q(
        "SELECT r.* FROM review_cohort_results r JOIN ("
        "SELECT task_slug, MAX(round_number) AS rn FROM review_cohort_results "
        "WHERE cohort_pk=? GROUP BY task_slug) latest "
        "ON latest.task_slug=r.task_slug AND latest.rn=r.round_number "
        "WHERE r.cohort_pk=? ORDER BY r.task_slug",
        (cohort_id, cohort_id),
    )
    return {str(row["task_slug"]): row for row in rows}


def _current_contract(svc: Any, cohort: Mapping[str, Any]) -> tuple[list[str], dict[str, Any]]:
    members, routes, _ = _resolve(svc, str(cohort["selector_kind"]), str(cohort["selector_value"]))
    if members != json.loads(cohort["members_json"]):
        raise ValueError("membership drift: open a new review cohort")
    stored_routes = json.loads(cohort["routes_json"])
    if {slug: _digest(route) for slug, route in routes.items()} != {
        slug: _digest(route) for slug, route in stored_routes.items()
    }:
        raise ValueError("review route drift: open a new review cohort")
    if cohort["policy_signature"] != POLICY_SIGNATURE:
        raise ValueError("review policy drift: open a new review cohort")
    return members, routes


def _round2_members(svc: Any, cohort: Mapping[str, Any]) -> tuple[list[str], list[str]]:
    members, _ = _current_contract(svc, cohort)
    prior = _latest_results(svc.be, int(cohort["id"]))
    if set(prior) != set(members):
        raise ValueError("round 1 has missing task-indexed results")
    if not all(bool(row.get("dependency_map_complete")) for row in prior.values()):
        return members, []
    root = _root(svc)
    red = {slug for slug, row in prior.items() if row["verdict"] == "red"}
    changed = {
        slug
        for slug, row in prior.items()
        if row["reviewed_state_fingerprint"] != _round_fingerprint(svc.be._conn, slug, root)
    }
    affected = set(changed)
    member_set = set(members)
    edges = svc.be._q(
        "SELECT task_slug, depends_on_slug FROM task_deps ORDER BY task_slug, depends_on_slug"
    )
    frontier = list(changed)
    while frontier:
        current = frontier.pop()
        for edge in edges:
            if edge["depends_on_slug"] == current and edge["task_slug"] in member_set:
                dependent = edge["task_slug"]
                if dependent not in affected:
                    affected.add(dependent)
                    frontier.append(dependent)
    for slug in changed:
        task = svc.be._q1("SELECT relevant_files FROM tasks WHERE slug=?", (slug,))
        try:
            files = set(json.loads(task["relevant_files"] or "[]")) if task else set()
        except (TypeError, ValueError):
            files = set()
        if not files:
            affected.update(members)
            continue
        for other in members:
            row = svc.be._q1("SELECT relevant_files FROM tasks WHERE slug=?", (other,))
            try:
                other_files = set(json.loads(row["relevant_files"] or "[]")) if row else set()
            except (TypeError, ValueError):
                other_files = set()
            if files & other_files:
                affected.add(other)
    required = sorted(red | affected)
    carried = sorted(set(members) - set(required))
    return required, carried


def cohort_status(svc: Any, cohort_id: int, *, issue_packet: bool = True) -> dict[str, Any]:
    cohort = _cohort(svc.be, cohort_id)
    if cohort["state"] in (*_OPEN_STATES, "green", "owner_decision"):
        _current_contract(svc, cohort)
    members = json.loads(cohort["members_json"])
    latest = _latest_results(svc.be, cohort_id)
    counts = {
        "green": sum(row["verdict"] == "green" for row in latest.values()),
        "advisory": sum(row["verdict"] == "advisory" for row in latest.values()),
        "accepted_risk": sum(row["verdict"] == "accepted_risk" for row in latest.values()),
        "red": sum(row["verdict"] == "red" for row in latest.values()),
        "carried": sum(bool(row["carried_forward"]) for row in latest.values()),
    }
    out: dict[str, Any] = {
        "cohort_id": cohort_id,
        "cohort_key": cohort["cohort_key"],
        "state": cohort["state"],
        "members": members,
        **counts,
        "rounds": f"{cohort['current_round']}/2",
    }
    if cohort["state"] == "open" and issue_packet:
        out["packet"] = _issue_packet(svc, cohort, members, 1)
    elif cohort["state"] == "round1_red" and issue_packet:
        required, carried = _round2_members(svc, cohort)
        out["packet"] = _issue_packet(svc, cohort, required, 2)
        out["carried_tasks"] = carried
    elif cohort["state"] == "owner_decision":
        out["owner_action"] = "accept risk, request manual review, or keep repair open"
    return out


def cohort_summary(out: Mapping[str, Any]) -> str:
    """Compact shared CLI/MCP rendering: one denominator and one next action."""
    lines = [
        f"L3 cohort: {len(out.get('members') or [])} tasks · "
        f"green {out.get('green', 0)} · advisory {out.get('advisory', 0)} · "
        f"accepted-risk {out.get('accepted_risk', 0)} · red {out.get('red', 0)} · "
        f"carried {out.get('carried', 0)} · rounds {out.get('rounds', '0/2')}",
        f"Cohort #{out.get('cohort_id')} · state {out.get('state')}",
    ]
    packet = out.get("packet")
    if isinstance(packet, Mapping):
        lines.append(
            f"Next: run L3 round {packet.get('round')} for "
            + ", ".join(str(item.get("slug")) for item in packet.get("tasks") or [])
        )
    if out.get("owner_action"):
        lines.append("Owner action: " + str(out["owner_action"]) + ".")
    return "\n".join(lines)


# Split only for the repository's 500-line module gate; these remain the public
# review_cohort API used by CLI/MCP callers.
from review_cohort_receipt import cohort_review_blockers, decide_review_cohort  # noqa: E402,F401
from review_cohort_record import record_review_round  # noqa: E402,F401
