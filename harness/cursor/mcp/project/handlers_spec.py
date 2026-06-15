"""TAUSIK MCP handlers — RENAR SPEC artifacts (v16r-spec-types).

Split from handlers.py (filesize hygiene). List/show/search return JSON;
mutating ops return the service's status string. Merged into handlers._DISPATCH
via ``handlers_spec.SPEC_HANDLERS``.
"""

from __future__ import annotations

import json as _json
from typing import Any

from tausik_utils import ServiceError


def _dump(obj: Any) -> str:
    return _json.dumps(obj, indent=2, ensure_ascii=False)


def handle_spec_add(svc: Any, args: dict) -> str:
    try:
        return svc.spec_add(
            args["slug"],
            args["type"],
            args["title"],
            args["version"],
            args.get("content_ref"),
            args.get("status", "draft"),
        )
    except ServiceError as e:
        return f"Error: {e}"


def handle_spec_list(svc: Any, args: dict) -> str:
    try:
        return _dump(svc.spec_list(args.get("type")))
    except ServiceError as e:
        return f"Error: {e}"


def handle_spec_show(svc: Any, args: dict) -> str:
    try:
        return _dump(svc.spec_show(args["slug"]))
    except ServiceError as e:
        return f"Error: {e}"


def handle_spec_update(svc: Any, args: dict) -> str:
    try:
        return svc.spec_update(
            args["slug"],
            title=args.get("title"),
            version=args.get("version"),
            content_ref=args.get("content_ref"),
            status=args.get("status"),
        )
    except ServiceError as e:
        return f"Error: {e}"


def handle_spec_delete(svc: Any, args: dict) -> str:
    try:
        return svc.spec_delete(args["slug"])
    except ServiceError as e:
        return f"Error: {e}"


def handle_spec_link(svc: Any, args: dict) -> str:
    try:
        return svc.spec_link(
            args["task_slug"], args["spec_slug"], args.get("relation", "implements")
        )
    except ServiceError as e:
        return f"Error: {e}"


def handle_spec_unlink(svc: Any, args: dict) -> str:
    try:
        return svc.spec_unlink(
            args["task_slug"], args["spec_slug"], args.get("relation", "implements")
        )
    except ServiceError as e:
        return f"Error: {e}"


def handle_spec_search(svc: Any, args: dict) -> str:
    try:
        return _dump(svc.spec_search(args["query"], args.get("limit", 20)))
    except ServiceError as e:
        return f"Error: {e}"


SPEC_HANDLERS = {
    "tausik_spec_add": handle_spec_add,
    "tausik_spec_list": handle_spec_list,
    "tausik_spec_show": handle_spec_show,
    "tausik_spec_update": handle_spec_update,
    "tausik_spec_delete": handle_spec_delete,
    "tausik_spec_link": handle_spec_link,
    "tausik_spec_unlink": handle_spec_unlink,
    "tausik_spec_search": handle_spec_search,
}
