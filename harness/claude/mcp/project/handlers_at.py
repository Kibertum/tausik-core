"""TAUSIK MCP handlers — RENAR AT (Acceptance Test) artifacts (Sec8A).

Every handler is a thin transport over service_at — no second implementation
(mcp_handler_shape guard).
"""

from __future__ import annotations

import json as _json
from typing import Any

from tausik_utils import ServiceError


def _dump(obj: Any) -> str:
    return _json.dumps(obj, indent=2, ensure_ascii=False)


def handle_at_create(svc: Any, args: dict) -> str:
    try:
        return svc.at_create(
            args["slug"],
            args["tz_ref"],
            args["tz_text"],
            args["scenario"],
            args["source_as_of"],
            args["generated_by"],
        )
    except ServiceError as e:
        return f"Error: {e}"


def handle_at_show(svc: Any, args: dict) -> str:
    try:
        return _dump(svc.at_show(args["slug"]))
    except ServiceError as e:
        return f"Error: {e}"


def handle_at_list(svc: Any, args: dict) -> str:
    try:
        return _dump(svc.at_list(args.get("tz_ref")))
    except ServiceError as e:
        return f"Error: {e}"


def handle_at_delete(svc: Any, args: dict) -> str:
    try:
        return svc.at_delete(args["slug"])
    except ServiceError as e:
        return f"Error: {e}"


def handle_at_search(svc: Any, args: dict) -> str:
    try:
        return _dump(svc.at_search(args["query"], args.get("limit", 20)))
    except ServiceError as e:
        return f"Error: {e}"


def handle_at_check_freshness(svc: Any, args: dict) -> str:
    try:
        return _dump(svc.at_check_freshness(args.get("slug")))
    except ServiceError as e:
        return f"Error: {e}"


def handle_at_record_result(svc: Any, args: dict) -> str:
    try:
        return svc.at_record_result(args["slug"], args["outcome"], args.get("note"))
    except ServiceError as e:
        return f"Error: {e}"


def handle_at_diagnose(svc: Any, args: dict) -> str:
    try:
        return _dump(svc.at_diagnose(args["slug"], args["tc_outcome"]))
    except ServiceError as e:
        return f"Error: {e}"


def handle_at_release_readiness(svc: Any, args: dict) -> str:
    return _dump(svc.at_release_readiness())


AT_HANDLERS = {
    "tausik_at_create": handle_at_create,
    "tausik_at_show": handle_at_show,
    "tausik_at_list": handle_at_list,
    "tausik_at_delete": handle_at_delete,
    "tausik_at_search": handle_at_search,
    "tausik_at_check_freshness": handle_at_check_freshness,
    "tausik_at_record_result": handle_at_record_result,
    "tausik_at_diagnose": handle_at_diagnose,
    "tausik_at_release_readiness": handle_at_release_readiness,
}
