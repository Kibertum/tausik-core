"""TAUSIK MCP handlers — RENAR ACTZ artifacts (Sec5A).

Split from handlers.py (filesize hygiene). List/show/search return JSON;
mutating ops return the service's status string. Merged into handlers._DISPATCH
via ``handlers_actz.ACTZ_HANDLERS``. Every handler is a thin transport over
``service_actz`` — no second implementation (mcp_handler_shape guard).
"""

from __future__ import annotations

import json as _json
import os as _os
from typing import Any

from tausik_utils import ServiceError


def _dump(obj: Any) -> str:
    return _json.dumps(obj, indent=2, ensure_ascii=False)


def handle_actz_create(svc: Any, args: dict) -> str:
    try:
        return svc.actz_create(args["slug"], args["title"], args["tz_ref"])
    except ServiceError as e:
        return f"Error: {e}"


def handle_actz_point(svc: Any, args: dict) -> str:
    try:
        return svc.actz_point_add(args["actz_slug"], args["point_no"], args["tz_ref"], args["text"])
    except ServiceError as e:
        return f"Error: {e}"


def handle_actz_sign(svc: Any, args: dict) -> str:
    try:
        return svc.actz_sign(args["actz_slug"], args["role"], args["signed_by"], _os.getcwd())
    except ServiceError as e:
        return f"Error: {e}"


def handle_actz_verify(svc: Any, args: dict) -> str:
    try:
        return _dump(svc.actz_verify(args["slug"], _os.getcwd()))
    except ServiceError as e:
        return f"Error: {e}"


def handle_actz_show(svc: Any, args: dict) -> str:
    try:
        return _dump(svc.actz_show(args["slug"]))
    except ServiceError as e:
        return f"Error: {e}"


def handle_actz_list(svc: Any, args: dict) -> str:
    try:
        return _dump(svc.actz_list(args.get("status")))
    except ServiceError as e:
        return f"Error: {e}"


def handle_actz_delta(svc: Any, args: dict) -> str:
    try:
        return svc.actz_delta(
            args["parent_slug"],
            args["new_slug"],
            args["title"],
            args["tz_ref"],
            args.get("supersession_rationale"),
        )
    except ServiceError as e:
        return f"Error: {e}"


def handle_actz_link(svc: Any, args: dict) -> str:
    try:
        return svc.actz_link(args["actz_slug"], args["target_type"], args["target_slug"])
    except ServiceError as e:
        return f"Error: {e}"


def handle_actz_unlink(svc: Any, args: dict) -> str:
    try:
        return svc.actz_unlink(args["actz_slug"], args["target_type"], args["target_slug"])
    except ServiceError as e:
        return f"Error: {e}"


def handle_actz_delete(svc: Any, args: dict) -> str:
    try:
        return svc.actz_delete(args["slug"])
    except ServiceError as e:
        return f"Error: {e}"


def handle_actz_search(svc: Any, args: dict) -> str:
    try:
        return _dump(svc.actz_search(args["query"], args.get("limit", 20)))
    except ServiceError as e:
        return f"Error: {e}"


def handle_actz_decided_in(svc: Any, args: dict) -> str:
    try:
        return svc.actz_decided_in(
            args["adapt_slug"],
            args["finding_id"],
            args["actz_slug"],
            args["actz_point_no"],
            args["linked_by"],
        )
    except ServiceError as e:
        return f"Error: {e}"


def handle_actz_decided_in_remove(svc: Any, args: dict) -> str:
    try:
        return svc.actz_decided_in_remove(
            args["adapt_slug"], args["finding_id"], args["actz_slug"], args["actz_point_no"]
        )
    except ServiceError as e:
        return f"Error: {e}"


def handle_actz_final_tz(svc: Any, args: dict) -> str:
    return _dump(svc.final_tz_snapshot(args.get("as_of")))


def handle_actz_orphans(svc: Any, args: dict) -> str:
    return _dump(svc.orphan_signed_points())


ACTZ_HANDLERS = {
    "tausik_actz_create": handle_actz_create,
    "tausik_actz_point": handle_actz_point,
    "tausik_actz_sign": handle_actz_sign,
    "tausik_actz_verify": handle_actz_verify,
    "tausik_actz_show": handle_actz_show,
    "tausik_actz_list": handle_actz_list,
    "tausik_actz_delta": handle_actz_delta,
    "tausik_actz_link": handle_actz_link,
    "tausik_actz_unlink": handle_actz_unlink,
    "tausik_actz_delete": handle_actz_delete,
    "tausik_actz_search": handle_actz_search,
    "tausik_actz_decided_in": handle_actz_decided_in,
    "tausik_actz_decided_in_remove": handle_actz_decided_in_remove,
    "tausik_actz_final_tz": handle_actz_final_tz,
    "tausik_actz_orphans": handle_actz_orphans,
}
