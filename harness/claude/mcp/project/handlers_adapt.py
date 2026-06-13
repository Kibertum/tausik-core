"""TAUSIK MCP handlers — RENAR ADAPT artifacts (v16r-adapt).

Split from handlers.py (filesize hygiene). List/show/search return JSON;
mutating ops return the service's status string. Merged into handlers._DISPATCH
via ``handlers_adapt.ADAPT_HANDLERS``. Mirrored in harness/claude + harness/cursor.
"""

from __future__ import annotations

import json as _json
import os as _os
from typing import Any

from tausik_utils import ServiceError


def _dump(obj: Any) -> str:
    return _json.dumps(obj, indent=2, ensure_ascii=False)


def handle_adapt_create(svc: Any, args: dict) -> str:
    try:
        return svc.adapt_create(args["slug"], args["title"], args["tz_ref"])
    except ServiceError as e:
        return f"Error: {e}"


def handle_adapt_interpret(svc: Any, args: dict) -> str:
    try:
        return svc.adapt_interpret(
            args["adapt_slug"],
            args["tz_ref"],
            args["citation"],
            args["engineering_interpretation"],
            args["scope_in"],
            args["scope_out"],
            args.get("term_mapping"),
            args.get("scenarios"),
        )
    except ServiceError as e:
        return f"Error: {e}"


def handle_adapt_finding(svc: Any, args: dict) -> str:
    try:
        return svc.adapt_finding(
            args["adapt_slug"],
            args["category"],
            args["description"],
            args.get("tz_ref"),
            args.get("resolution"),
        )
    except ServiceError as e:
        return f"Error: {e}"


def handle_adapt_sign(svc: Any, args: dict) -> str:
    try:
        return svc.adapt_sign(args["adapt_slug"], args["role"], args["signed_by"], _os.getcwd())
    except ServiceError as e:
        return f"Error: {e}"


def handle_adapt_show(svc: Any, args: dict) -> str:
    try:
        return _dump(svc.adapt_show(args["slug"]))
    except ServiceError as e:
        return f"Error: {e}"


def handle_adapt_list(svc: Any, args: dict) -> str:
    try:
        return _dump(svc.adapt_list(args.get("status")))
    except ServiceError as e:
        return f"Error: {e}"


def handle_adapt_delta(svc: Any, args: dict) -> str:
    try:
        return svc.adapt_delta(args["parent_slug"], args["new_slug"], args["title"], args["tz_ref"])
    except ServiceError as e:
        return f"Error: {e}"


def handle_adapt_link(svc: Any, args: dict) -> str:
    try:
        return svc.adapt_link(args["adapt_slug"], args["target_type"], args["target_slug"])
    except ServiceError as e:
        return f"Error: {e}"


def handle_adapt_search(svc: Any, args: dict) -> str:
    try:
        return _dump(svc.adapt_search(args["query"], args.get("limit", 20)))
    except ServiceError as e:
        return f"Error: {e}"


ADAPT_HANDLERS = {
    "tausik_adapt_create": handle_adapt_create,
    "tausik_adapt_interpret": handle_adapt_interpret,
    "tausik_adapt_finding": handle_adapt_finding,
    "tausik_adapt_sign": handle_adapt_sign,
    "tausik_adapt_show": handle_adapt_show,
    "tausik_adapt_list": handle_adapt_list,
    "tausik_adapt_delta": handle_adapt_delta,
    "tausik_adapt_link": handle_adapt_link,
    "tausik_adapt_search": handle_adapt_search,
}
