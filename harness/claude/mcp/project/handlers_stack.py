"""MCP handlers for the stack domain — the stack registry and its user overrides.

Split out of handlers.py by mcp-handlers-god-module-split. Follows the
convention already set by handlers_spec.py / handlers_adapt.py: the module owns
its handlers AND the slice of the dispatch table that names them, and
handlers.py merges it with `_DISPATCH.update(...)`.
"""

from __future__ import annotations

import os
from typing import Any


def _handle_stack_reset(name: str) -> str:
    import shutil as _sh

    from tausik_utils import validate_slug

    try:
        validate_slug(name)
    except Exception as e:  # noqa: BLE001 — best-effort: MCP handler must not crash the server on a tool call
        return f"Error: {e}"
    user_dir = os.path.join(os.getcwd(), ".tausik", "stacks", name)
    if not os.path.isdir(user_dir):
        return f"No user override at {user_dir}"
    _sh.rmtree(user_dir)
    return f"Removed {user_dir}"


def _handle_stack_export(name: str) -> str:
    import json as _json

    from service_stack_ops import stack_show

    try:
        return _json.dumps(stack_show(name), indent=2, ensure_ascii=False)
    except KeyError as e:
        return f"Error: {e}"


def _handle_stack_list(svc: Any) -> str:
    import json as _json

    return _json.dumps(svc.stack_list(), indent=2, ensure_ascii=False)


def _handle_stack_show(name: str) -> str:
    import json as _json

    from service_stack_ops import stack_show

    try:
        return _json.dumps(stack_show(name), indent=2, ensure_ascii=False)
    except KeyError as e:
        return f"Error: {e}"


def _handle_stack_lint() -> str:
    import json as _json

    from service_stack_ops import stack_lint

    return _json.dumps(stack_lint(), indent=2, ensure_ascii=False)


def _handle_stack_diff(name: str) -> str:
    import json as _json

    from service_stack_ops import stack_diff

    return _json.dumps(stack_diff(name), indent=2, ensure_ascii=False)


def _handle_stack_scaffold(args: dict) -> str:
    import json as _json

    from service_stack_ops import stack_scaffold

    try:
        result = stack_scaffold(
            args["name"],
            args.get("extends_builtin"),
            args.get("force", False),
        )
        return _json.dumps(result, indent=2, ensure_ascii=False)
    except FileExistsError as e:
        return f"Refused: {e}"
    except (ValueError, KeyError) as e:
        return f"Error: {e}"


STACK_HANDLERS = {
    "tausik_stack_list": lambda svc, args: _handle_stack_list(svc),
    "tausik_stack_show": lambda svc, args: _handle_stack_show(args["name"]),
    "tausik_stack_lint": lambda svc, args: _handle_stack_lint(),
    "tausik_stack_diff": lambda svc, args: _handle_stack_diff(args["name"]),
    "tausik_stack_scaffold": lambda svc, args: _handle_stack_scaffold(args),
    "tausik_stack_reset": lambda svc, args: _handle_stack_reset(args["name"]),
    "tausik_stack_export": lambda svc, args: _handle_stack_export(args["name"]),
}
