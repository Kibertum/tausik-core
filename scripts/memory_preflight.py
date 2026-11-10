"""Action-bound inspection of project memory before protected Codex operations."""

from __future__ import annotations

import hashlib
import json
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping

from memory_relevance import MAX_ENTRIES
from memory_preflight_classification import PROTECTED_KINDS, classify_action
from memory_preflight_query import fts_or, has_quarantined_conflict, live_conflict_count
from memory_supersedes import as_int, superseder_of
from publication_boundary import redact
from secret_patterns import secret_literal_names
from tausik_utils import ServiceError

TOKEN_TTL_SECONDS = 300
SEARCH_EXPANSION = max(MAX_ENTRIES * 8, 60)
SEARCH_SCAN_LIMIT = 2048
_WORD = re.compile(r"[A-Za-zА-Яа-яЁё0-9]{3,}")
_INJECTION = re.compile(
    r"(?:ignore|disregard)\s+(?:all\s+)?(?:previous|prior)\s+instructions|system\s+prompt",
    re.IGNORECASE,
)


class MemoryPreflightError(ServiceError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(f"{code}: {message}")


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def action_binding(tool_name: str, tool_input: Mapping[str, Any], kind: str) -> tuple[str, str]:
    if kind not in PROTECTED_KINDS:
        raise MemoryPreflightError("PROTECTED_KIND_UNKNOWN", f"unsupported kind {kind!r}")
    observed = classify_action(tool_name, tool_input)
    if observed != kind:
        raise MemoryPreflightError(
            "PROTECTED_KIND_MISMATCH",
            f"trusted identifier classifies as {observed!r}, not {kind!r}",
        )
    payload_hash = hashlib.sha256(_canonical(dict(tool_input)).encode()).hexdigest()
    target = tool_name.strip().lower()
    action_id = hashlib.sha256(f"{kind}\0{target}\0{payload_hash}".encode()).hexdigest()
    return action_id, payload_hash


def content_revision(be: Any) -> str:
    """Hash policy-bearing content, excluding access/hit telemetry by construction."""
    rows = be._q(
        "SELECT id,type,title,content,tags,task_slug,archived_at,updated_at,slug,provenance,layer,pinned "
        "FROM memory ORDER BY id"
    )
    edges = be._q(
        "SELECT source_type,source_id,target_type,target_id,relation,valid_from,valid_to "
        "FROM memory_edges ORDER BY id"
    )
    return hashlib.sha256(_canonical({"memory": rows, "edges": edges}).encode()).hexdigest()


def _terms(tool_name: str, tool_input: Mapping[str, Any], kind: str) -> list[str]:
    words = _WORD.findall(f"{kind} {tool_name} {_canonical(dict(tool_input))}".lower())
    seen: set[str] = set()
    terms: list[str] = []
    for word in words:
        if word in seen:
            continue
        seen.add(word)
        terms.append(word)
        if len(terms) == 24:
            break
    return terms


def _tags(row: Mapping[str, Any]) -> list[str]:
    raw = row.get("tags")
    if isinstance(raw, str):
        try:
            loaded = json.loads(raw)
            if isinstance(loaded, list):
                return [str(item) for item in loaded]
        except ValueError:
            return [item.strip() for item in raw.split(",") if item.strip()]
    return []


def inspect_memory(
    be: Any, tool_name: str, tool_input: Mapping[str, Any], kind: str
) -> list[dict[str, Any]]:
    """Bounded OR retrieval, deterministic rerank, then redaction for disclosure."""
    terms = _terms(tool_name, tool_input, kind)
    if not terms:
        return []
    # Ordinary context stays bounded to the newest rows. Policy-bearing rows
    # use the indexed OR query over the complete corpus, with a separate hard
    # cap before deterministic reranking and disclosure.
    ordinary = be._q(
        "SELECT * FROM memory WHERE archived_at IS NULL ORDER BY id DESC LIMIT ?",
        (SEARCH_SCAN_LIMIT,),
    )
    conflicts = be._q(
        "SELECT m.* FROM memory m JOIN fts_memory f ON m.id=f.rowid "
        "WHERE fts_memory MATCH ? AND m.archived_at IS NULL "
        "AND (m.type='dead_end' OR m.tags LIKE '%policy:active%') "
        "ORDER BY m.id ASC LIMIT ?",
        (fts_or(terms), SEARCH_SCAN_LIMIT),
    )
    rows = list({row["id"]: row for row in [*ordinary, *conflicts]}.values())
    memo: dict[Any, Any] = {}
    ranked: list[tuple[int, int, int, dict[str, Any]]] = []
    for source in rows:
        rid = as_int(source.get("id"))
        if rid is None or superseder_of(be, "memory", rid, memo) is not None:
            continue
        source_tags = _tags(source)
        conflict = source.get("type") == "dead_end" or "policy:active" in source_tags
        safe_title = redact(str(source.get("title") or "")).text
        safe_content = redact(str(source.get("content") or "")).text
        from secret_patterns import redact_secret_literals

        safe_title = redact_secret_literals(safe_title)[0]
        safe_content = redact_secret_literals(safe_content)[0]
        safe_tags = [redact_secret_literals(redact(tag).text)[0] for tag in source_tags]
        tags = " ".join(safe_tags).lower()
        title = safe_title.lower()
        body = safe_content.lower()
        score = sum(
            3 if term in tags else 2 if term in title else 1 if term in body else 0
            for term in terms
        )
        if score == 0:
            continue
        row = {
            "id": rid,
            "type": source.get("type"),
            "title": safe_title,
            "content": safe_content,
            "tags": safe_tags,
            "provenance": source.get("provenance"),
            "injection_suspected": bool(
                _INJECTION.search(" ".join([safe_title, safe_content, *safe_tags]))
            ),
            "conflict": conflict,
        }
        ranked.append((0 if row["conflict"] else 1, -score, rid, row))
    ranked.sort(key=lambda item: (item[0], item[1], item[2]))
    expanded = ranked[:SEARCH_EXPANSION]
    return [row for _conflict, _score, _rid, row in expanded[:MAX_ENTRIES]]


def issue_preflight(
    svc: Any,
    *,
    protected_kind: str,
    tool_name: str,
    tool_input: Mapping[str, Any],
    acknowledged_ids: list[int] | None = None,
    inspection_id: int | None = None,
    override_reason: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    lease = getattr(svc, "_authorized_execution_lease", None)
    if not isinstance(lease, dict):
        raise MemoryPreflightError(
            "LEASE_MISSING", "preflight requires an authorized execution lease"
        )
    action_id, payload_hash = action_binding(tool_name, tool_input, protected_kind)
    if secret_literal_names(_canonical(dict(tool_input))):
        raise MemoryPreflightError(
            "SECRET_REFUSED", "protected payload contains a credential literal"
        )
    package = lease.get("task_package_fingerprint")
    if not isinstance(package, str) or not package:
        raise MemoryPreflightError(
            "PACKAGE_MISSING", "execution lease is not bound to a task package"
        )
    revision = content_revision(svc.be)
    terms = _terms(tool_name, tool_input, protected_kind)
    if has_quarantined_conflict(svc.be, terms):
        raise MemoryPreflightError(
            "MEMORY_QUARANTINED_CONFLICT",
            "an applicable policy/dead-end was quarantined; protected action is refused",
        )
    if live_conflict_count(svc.be, terms) > MAX_ENTRIES:
        raise MemoryPreflightError(
            "MEMORY_CONFLICT_OVERFLOW",
            "applicable policy/dead-end set exceeds the bounded acknowledgement surface",
        )
    inspected = inspect_memory(svc.be, tool_name, tool_input, protected_kind)
    quarantined = [int(row["id"]) for row in inspected if row["injection_suspected"]]
    if any(row["conflict"] and row["injection_suspected"] for row in inspected):
        raise MemoryPreflightError(
            "MEMORY_QUARANTINED_CONFLICT",
            "an applicable policy/dead-end was quarantined; protected action is refused",
        )
    selected = [row for row in inspected if not row["injection_suspected"]]
    ids = [int(row["id"]) for row in selected]
    instant = now or _now()
    acknowledged = sorted({int(item) for item in (acknowledged_ids or [])})
    if acknowledged_ids is None:
        event_id = svc.be._ins(
            "INSERT INTO memory_inspection_events(lease_id,action_id,content_revision,selected_ids,inspected_at) VALUES(?,?,?,?,?)",
            (lease["id"], action_id, revision, _canonical(ids), _iso(instant)),
        )
        return {
            "status": "inspection_required",
            "inspection_id": event_id,
            "action_id": action_id,
            "content_revision": revision,
            "selected": selected,
            "acknowledge_ids": ids,
            "quarantined_ids": quarantined,
        }
    event = (
        svc.be._q1("SELECT * FROM memory_inspection_events WHERE id=?", (inspection_id,))
        if isinstance(inspection_id, int) and not isinstance(inspection_id, bool)
        else None
    )
    if (
        event is None
        or event["lease_id"] != lease["id"]
        or event["action_id"] != action_id
        or event["content_revision"] != revision
        or event["selected_ids"] != _canonical(ids)
    ):
        raise MemoryPreflightError(
            "INSPECTION_STALE", "acknowledgement is not bound to the current inspection snapshot"
        )
    if acknowledged != sorted(ids):
        raise MemoryPreflightError(
            "ACKNOWLEDGEMENT_MISMATCH", "acknowledgement must contain exactly the inspected IDs"
        )
    conflicts = [row for row in selected if row["conflict"]]
    reason = (override_reason or "").strip() or None
    if conflicts and not reason:
        raise MemoryPreflightError(
            "MEMORY_CONFLICT",
            "active policy/dead-end conflict requires an action-bound override reason",
        )
    if conflicts and reason:
        match = re.fullmatch(r"reason:(\d+)", reason)
        task_slug = lease.get("task_slug")
        step = (
            svc.be._q1(
                "SELECT kind,content FROM reasoning_steps WHERE task_slug=? AND seq=?",
                (task_slug, int(match.group(1))),
            )
            if match and task_slug
            else None
        )
        if step is None or step["kind"] != "action" or action_id not in step["content"]:
            raise MemoryPreflightError(
                "OVERRIDE_INVALID",
                "override must reference an action reasoning step containing this action_id",
            )
    token = secrets.token_urlsafe(32)
    expires = instant + timedelta(seconds=TOKEN_TTL_SECONDS)
    with svc.be.transaction():
        existing = svc.be._q1(
            "SELECT * FROM memory_preflight_tokens WHERE lease_id=? AND action_id=? AND payload_hash=? "
            "ORDER BY id DESC LIMIT 1",
            (lease["id"], action_id, payload_hash),
        )
        same_revision = bool(
            existing
            and existing["package_fingerprint"] == package
            and existing["content_revision"] == revision
            and existing["acknowledged_ids"] == _canonical(ids)
            and existing["override_reason"] == reason
        )
        if (
            existing
            and existing["status"] == "issued"
            and existing["expires_at"] > _iso(instant)
            and same_revision
        ):
            token = existing["token"]
            expires = datetime.strptime(existing["expires_at"], "%Y-%m-%dT%H:%M:%SZ").replace(
                tzinfo=timezone.utc
            )
        elif existing and existing["status"] == "issued":
            svc.be._ex(
                "UPDATE memory_preflight_tokens SET token=?,package_fingerprint=?,content_revision=?,"
                "acknowledged_ids=?,override_reason=?,issued_at=?,expires_at=? WHERE id=?",
                (
                    token,
                    package,
                    revision,
                    _canonical(ids),
                    reason,
                    _iso(instant),
                    _iso(expires),
                    existing["id"],
                ),
            )
        elif existing and existing["status"] in {"reserved", "executed"}:
            raise MemoryPreflightError(
                "TOKEN_REPLAY", "this exact action already has a terminal or reserved token"
            )
        else:
            svc.be._ins(
                "INSERT INTO memory_preflight_tokens(token,lease_id,package_fingerprint,content_revision,"
                "acknowledged_ids,protected_kind,action_id,payload_hash,override_reason,status,issued_at,expires_at) "
                "VALUES(?,?,?,?,?,?,?,?,?,'issued',?,?)",
                (
                    token,
                    lease["id"],
                    package,
                    revision,
                    _canonical(ids),
                    protected_kind,
                    action_id,
                    payload_hash,
                    reason,
                    _iso(instant),
                    _iso(expires),
                ),
            )
    return {
        "status": "issued",
        "token": token,
        "expires_at": _iso(expires),
        "inspection_id": inspection_id,
        "action_id": action_id,
        "acknowledged_ids": ids,
    }


def reserve_preflight(
    be: Any,
    lease: Mapping[str, Any],
    tool_name: str,
    tool_input: Mapping[str, Any],
    *,
    now: datetime | None = None,
) -> dict[str, Any] | None:
    kind = classify_action(tool_name, tool_input)
    if kind is None:
        return None
    action_id, payload_hash = action_binding(tool_name, tool_input, kind)
    instant = now or _now()
    terminal_error: MemoryPreflightError | None = None
    reserved: dict[str, Any] | None = None
    with be.transaction():
        row = be._q1(
            "SELECT * FROM memory_preflight_tokens WHERE lease_id=? AND action_id=? AND payload_hash=? "
            "ORDER BY id DESC LIMIT 1",
            (lease["id"], action_id, payload_hash),
        )
        if row is None:
            raise MemoryPreflightError("TOKEN_MISSING", f"{kind} requires tausik_memory_preflight")
        if row["status"] != "issued":
            raise MemoryPreflightError("TOKEN_REPLAY", f"token is already {row['status']}")
        if row["expires_at"] <= _iso(instant):
            be._ex(
                "UPDATE memory_preflight_tokens SET status='expired',completed_at=? WHERE id=?",
                (_iso(instant), row["id"]),
            )
            terminal_error = MemoryPreflightError("TOKEN_STALE", "memory preflight token expired")
        elif lease.get("task_package_fingerprint") != row["package_fingerprint"]:
            raise MemoryPreflightError("TOKEN_PACKAGE_STALE", "task context package changed")
        elif content_revision(be) != row["content_revision"]:
            raise MemoryPreflightError(
                "TOKEN_CONTENT_STALE", "memory content changed after inspection"
            )
        else:
            changed = be._ex(
                "UPDATE memory_preflight_tokens SET status='reserved',reserved_at=? WHERE id=? AND status='issued'",
                (_iso(instant), row["id"]),
            )
            if changed != 1:
                raise MemoryPreflightError("TOKEN_REPLAY", "concurrent token reservation lost")
            reserved = dict(row)
    if terminal_error is not None:
        raise terminal_error
    return reserved


def complete_preflight(
    be: Any,
    lease_id: int,
    tool_name: str,
    tool_input: Mapping[str, Any],
    *,
    failed: bool = False,
    now: datetime | None = None,
) -> bool:
    kind = classify_action(tool_name, tool_input)
    if kind is None:
        return False
    action_id, payload_hash = action_binding(tool_name, tool_input, kind)
    status = "failed" if failed else "executed"
    instant = _iso(now or _now())
    with be.transaction():
        changed = be._ex(
            "UPDATE memory_preflight_tokens SET status=?,completed_at=?,failure_code=? "
            "WHERE lease_id=? AND action_id=? AND payload_hash=? AND status='reserved'",
            (status, instant, "TOOL_FAILED" if failed else None, lease_id, action_id, payload_hash),
        )
    return bool(changed == 1)


def complete_preflight_for_thread(
    be: Any,
    project_identity: str,
    thread_id: str,
    tool_name: str,
    tool_input: Mapping[str, Any],
    *,
    host_instance: str = "codex",
    failed: bool = False,
    failure_code: str | None = None,
    now: datetime | None = None,
) -> bool:
    """Complete the exact reservation even when the action revoked its own lease."""
    kind = classify_action(tool_name, tool_input)
    if kind is None:
        return False
    action_id, payload_hash = action_binding(tool_name, tool_input, kind)
    row = be._q1(
        "SELECT t.id FROM memory_preflight_tokens t "
        "JOIN execution_leases l ON l.id=t.lease_id "
        "WHERE l.project_identity=? AND l.host_instance=? AND l.thread_id=? "
        "AND t.action_id=? AND t.payload_hash=? AND t.status='reserved' "
        "ORDER BY t.id DESC LIMIT 1",
        (project_identity, host_instance.casefold(), thread_id, action_id, payload_hash),
    )
    if row is None:
        return False
    status = "failed" if failed else "executed"
    with be.transaction():
        changed = be._ex(
            "UPDATE memory_preflight_tokens SET status=?,completed_at=?,failure_code=? "
            "WHERE id=? AND status='reserved'",
            (
                status,
                _iso(now or _now()),
                (failure_code or "TOOL_FAILED") if failed else None,
                row["id"],
            ),
        )
    return bool(changed == 1)


__all__ = [
    "PROTECTED_KINDS",
    "MemoryPreflightError",
    "action_binding",
    "classify_action",
    "complete_preflight",
    "complete_preflight_for_thread",
    "content_revision",
    "inspect_memory",
    "issue_preflight",
    "reserve_preflight",
]
