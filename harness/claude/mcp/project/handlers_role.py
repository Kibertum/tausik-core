"""MCP handlers for the role domain — CRUD over the role registry.

Split out of handlers.py by mcp-handlers-god-module-split. Follows the
convention already set by handlers_spec.py / handlers_adapt.py: the module owns
its handlers AND the slice of the dispatch table that names them, and
handlers.py merges it with `_DISPATCH.update(...)`.
"""

from __future__ import annotations

from typing import Any


def _handle_role_list(svc: Any) -> str:
    import json as _json

    from service_roles import role_list

    return _json.dumps(role_list(svc.be), indent=2, ensure_ascii=False)


def _handle_role_show(svc: Any, slug: str) -> str:
    import json as _json

    from service_roles import role_show

    try:
        return _json.dumps(role_show(svc.be, slug), indent=2, ensure_ascii=False)
    except Exception as e:  # noqa: BLE001 — best-effort: MCP handler must not crash the server on a tool call
        return f"Error: {e}"


def _handle_role_create(svc: Any, args: dict) -> str:
    import json as _json

    from service_roles import role_create

    try:
        row = role_create(
            svc.be,
            args["slug"],
            args["title"],
            args.get("description"),
            args.get("extends"),
        )
        return _json.dumps(row, indent=2, ensure_ascii=False)
    except Exception as e:  # noqa: BLE001 — best-effort: MCP handler must not crash the server on a tool call
        return f"Error: {e}"


def _handle_role_update(svc: Any, args: dict) -> str:
    import json as _json

    from service_roles import role_update

    try:
        row = role_update(svc.be, args["slug"], args.get("title"), args.get("description"))
        return _json.dumps(row, indent=2, ensure_ascii=False)
    except Exception as e:  # noqa: BLE001 — best-effort: MCP handler must not crash the server on a tool call
        return f"Error: {e}"


def _handle_role_delete(svc: Any, args: dict) -> str:
    from service_roles import role_delete

    try:
        return role_delete(svc.be, args["slug"], args.get("force", False))
    except Exception as e:  # noqa: BLE001 — best-effort: MCP handler must not crash the server on a tool call
        return f"Error: {e}"


def _handle_role_seed(svc: Any) -> str:
    import json as _json

    from service_roles import seed_existing_roles

    return _json.dumps(seed_existing_roles(svc.be), indent=2)


ROLE_HANDLERS = {
    "tausik_role_list": lambda svc, args: _handle_role_list(svc),
    "tausik_role_show": lambda svc, args: _handle_role_show(svc, args["slug"]),
    "tausik_role_create": lambda svc, args: _handle_role_create(svc, args),
    "tausik_role_update": lambda svc, args: _handle_role_update(svc, args),
    "tausik_role_delete": lambda svc, args: _handle_role_delete(svc, args),
    "tausik_role_seed": lambda svc, args: _handle_role_seed(svc),
}
