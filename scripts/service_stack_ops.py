"""Stack registry MCP/CLI helpers — show, lint, diff, scaffold.

Service-layer free functions returning structured dicts (no printing).
CLI handlers in project_cli_stack.py format the output for terminal;
MCP handlers in agents/{ide}/mcp/project/handlers.py JSON-serialize them.

Kept out of project_service.py to respect the 400-line filesize gate.
"""

from __future__ import annotations

import difflib
import json
import os
from typing import Any

from stack_registry import default_registry
from stack_schema import validate_decl

_STACK_JSON = "stack.json"
_GUIDE_MD = "guide.md"


def _stack_paths(stack: str) -> tuple[str, str]:
    """(built-in stack.json absolute, user override stack.json absolute)."""
    here = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(here)
    builtin = os.path.join(repo_root, "stacks", stack, _STACK_JSON)
    user = os.path.join(os.getcwd(), ".tausik", "stacks", stack, _STACK_JSON)
    return builtin, user


def stack_show(name: str) -> dict[str, Any]:
    """Resolved stack decl (built-in deep-merged with user override).

    Raises KeyError when stack is unknown.
    """
    reg = default_registry()
    if name not in reg.all_stacks():
        raise KeyError(
            f"Unknown stack: {name!r}. Available: {sorted(reg.all_stacks())}"
        )
    return {
        "name": name,
        "source": reg.source_for(name),
        "is_user_overridden": reg.is_user_overridden(name),
        "detect": reg.signatures_for(name),
        "extensions": sorted(reg.extensions_for(name)),
        "filenames": sorted(reg.filenames_for(name)),
        "path_hints": sorted(reg.path_hints_for(name)),
        "gates": reg.gates_for(name),
        "guide_path": reg.guide_path_for(name),
    }


def stack_lint() -> dict[str, Any]:
    """Validate every user override under .tausik/stacks/<name>/stack.json.

    Returns: {checked: N, failed: M, results: [{path, ok, errors}]}
    """
    user_root = os.path.join(os.getcwd(), ".tausik", "stacks")
    out: dict[str, Any] = {"checked": 0, "failed": 0, "results": []}
    if not os.path.isdir(user_root):
        return out
    for entry in sorted(os.listdir(user_root)):
        if entry.startswith((".", "_")):
            continue
        decl_path = os.path.join(user_root, entry, _STACK_JSON)
        if not os.path.isfile(decl_path):
            continue
        out["checked"] += 1
        result: dict[str, Any] = {"path": decl_path, "stack": entry, "errors": []}
        try:
            with open(decl_path, encoding="utf-8") as f:
                decl = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            result["errors"].append(str(e))
            result["ok"] = False
            out["failed"] += 1
            out["results"].append(result)
            continue
        errs = validate_decl(decl, source=decl_path)
        result["errors"] = list(errs)
        result["ok"] = not errs
        if errs:
            out["failed"] += 1
        out["results"].append(result)
    return out


def stack_diff(name: str) -> dict[str, Any]:
    """Unified diff of built-in vs user override for one stack.

    Returns {stack, has_builtin, has_user, diff: <str>}.
    """
    builtin_path, user_path = _stack_paths(name)
    has_builtin = os.path.isfile(builtin_path)
    has_user = os.path.isfile(user_path)
    out: dict[str, Any] = {
        "stack": name,
        "has_builtin": has_builtin,
        "has_user": has_user,
        "diff": "",
    }
    if not has_builtin or not has_user:
        return out
    with open(builtin_path, encoding="utf-8") as f:
        builtin_lines = f.readlines()
    with open(user_path, encoding="utf-8") as f:
        user_lines = f.readlines()
    out["diff"] = "".join(
        difflib.unified_diff(
            builtin_lines,
            user_lines,
            fromfile=f"builtin:{name}",
            tofile=f"user:{name}",
            lineterm="",
        )
    )
    return out


def stack_scaffold(
    name: str, extends_builtin: str | None = None, force: bool = False
) -> dict[str, Any]:
    """Generate skeleton .tausik/stacks/<name>/{stack.json, guide.md}.

    Args:
        name: kebab-case stack slug. Validated to prevent path traversal —
              must match validate_slug rules (no '..', no separators).
        extends_builtin: if set, must be a real built-in stack name.
        force: when True, overwrite existing files (still atomic via O_EXCL
              for new files).

    Returns: {stack, dir, created: [paths], existed: [paths]}.
    Raises FileExistsError when --force not set and any target exists.
    Raises ValueError on bad name or unknown extends_builtin.
    """
    from tausik_utils import validate_slug

    validate_slug(name)
    if extends_builtin is not None:
        validate_slug(extends_builtin)
        reg = default_registry()
        if extends_builtin not in reg.all_stacks():
            raise ValueError(
                f"extends_builtin '{extends_builtin}' is not a known stack. "
                f"Available: {sorted(reg.all_stacks())}"
            )
    target_dir = os.path.join(os.getcwd(), ".tausik", "stacks", name)
    decl_path = os.path.join(target_dir, _STACK_JSON)
    guide_path = os.path.join(target_dir, _GUIDE_MD)
    existed = [p for p in (decl_path, guide_path) if os.path.isfile(p)]
    if existed and not force:
        raise FileExistsError(
            f"Refusing to overwrite: {', '.join(existed)}. Pass force=True to replace."
        )
    os.makedirs(target_dir, exist_ok=True)
    decl: dict[str, Any] = {"name": name, "version": "0.1.0"}
    if extends_builtin:
        decl["extends"] = f"builtin:{extends_builtin}"
    decl["detect"] = []
    decl["extensions"] = []
    decl["gates"] = {}
    _atomic_write_json(decl_path, decl, force)
    _atomic_write_text(guide_path, f"# {name}\n\nGuide for the {name} stack.\n", force)
    return {
        "stack": name,
        "dir": target_dir,
        "created": [decl_path, guide_path],
        "existed": existed,
    }


def _windows_safe_replace(tmp: str, path: str) -> None:
    import time as _time

    last_err: Exception | None = None
    for _ in range(4):
        try:
            os.replace(tmp, path)
            return
        except PermissionError as e:
            last_err = e
            _time.sleep(0.1)
    if last_err:
        raise last_err


def _atomic_write_json(path: str, payload: dict[str, Any], force: bool) -> None:
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
            f.write("\n")
        if not force and os.path.isfile(path):
            raise FileExistsError(path)
        _windows_safe_replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _atomic_write_text(path: str, content: str, force: bool) -> None:
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(content)
        if not force and os.path.isfile(path):
            raise FileExistsError(path)
        _windows_safe_replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
