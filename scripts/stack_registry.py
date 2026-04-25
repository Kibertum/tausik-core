"""TAUSIK stack registry — single source of truth for stack declarations.

Layered loader:
  1. `stacks/<name>/stack.json` (built-in, ships with the framework)
  2. `.tausik/stacks/<name>/stack.json` (user override, gitignored)

User decls may declare `extends: builtin:<name>` to inherit + customize a
built-in stack. `extends` semantics:
  * extensions / filenames / path_hints / detect from the built-in are kept
    by default.
  * extensions_extra is **additive** on top of the inherited extensions.
  * gates: keys present in the user decl override the built-in entry; a
    `null` value disables an inherited gate. Missing keys are inherited.
  * guide_path: user wins if set, else inherited.

Malformed JSON or schema-invalid decls are **logged and skipped** — never
fatal — so a single bad user file can't break TAUSIK on every CLI call.
The validator from `stack_schema.validate_decl` provides actionable
messages; callers consult `StackRegistry.errors` for the accumulated list.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from stack_schema import validate_decl

logger = logging.getLogger("tausik.stack_registry")

_STACK_JSON = "stack.json"


class StackRegistry:
    """In-memory registry of resolved (built-in + user) stack declarations.

    Methods are idempotent and side-effect-free except for `load_*` and
    `reload`. Errors during load are collected in `self.errors` (list of
    actionable strings) so callers can surface them once at startup.
    """

    def __init__(self) -> None:
        self._builtin: dict[str, dict[str, Any]] = {}
        self._user: dict[str, dict[str, Any]] = {}
        self._resolved: dict[str, dict[str, Any]] | None = None
        self.errors: list[str] = []

    # --- Loading ----------------------------------------------------------

    def load_builtin(self, stacks_dir: str | os.PathLike[str]) -> None:
        """Scan stacks_dir for <name>/stack.json files and load them."""
        self._builtin = self._scan_dir(stacks_dir, layer="builtin")
        self._resolved = None

    def load_user(self, user_stacks_dir: str | os.PathLike[str]) -> None:
        """Scan user override dir; absent dir is fine (no-op)."""
        if not os.path.isdir(str(user_stacks_dir)):
            self._user = {}
            self._resolved = None
            return
        self._user = self._scan_dir(user_stacks_dir, layer="user")
        self._resolved = None

    def reload(
        self,
        stacks_dir: str | os.PathLike[str],
        user_stacks_dir: str | os.PathLike[str] | None = None,
    ) -> None:
        """Reset and reload everything. Test-only convenience."""
        self.errors = []
        self.load_builtin(stacks_dir)
        if user_stacks_dir is not None:
            self.load_user(user_stacks_dir)
        else:
            self._user = {}
            self._resolved = None

    # --- Public accessors -------------------------------------------------

    def all_stacks(self) -> frozenset[str]:
        """Names of every successfully-loaded stack (built-in ∪ user)."""
        return frozenset(self._resolve())

    def signatures_for(self, name: str) -> list[dict[str, Any]]:
        """Detect signatures: list of {file, type, keyword?} dicts.

        Empty list = stack is never auto-detected (only chosen explicitly).
        """
        decl = self._resolve().get(name)
        if not decl:
            return []
        return list(decl.get("detect") or [])

    def extensions_for(self, name: str) -> frozenset[str]:
        """File extensions that signal this stack (e.g. {'.py'})."""
        decl = self._resolve().get(name)
        if not decl:
            return frozenset()
        exts = list(decl.get("extensions") or [])
        exts.extend(decl.get("extensions_extra") or [])
        return frozenset(exts)

    def filenames_for(self, name: str) -> frozenset[str]:
        """Lowercase filenames that signal this stack (e.g. {'dockerfile'})."""
        decl = self._resolve().get(name)
        if not decl:
            return frozenset()
        return frozenset(decl.get("filenames") or [])

    def path_hints_for(self, name: str) -> frozenset[str]:
        """Path fragments that hint at this stack (e.g. {'/playbooks/'})."""
        decl = self._resolve().get(name)
        if not decl:
            return frozenset()
        return frozenset(decl.get("path_hints") or [])

    def gates_for(self, name: str) -> dict[str, dict[str, Any]]:
        """Stack-scoped gate configs. Keys with null value are excluded.

        Returns a freshly-constructed dict so callers may mutate without
        polluting the registry.
        """
        decl = self._resolve().get(name)
        if not decl:
            return {}
        out: dict[str, dict[str, Any]] = {}
        for gname, gcfg in (decl.get("gates") or {}).items():
            if gcfg is None:
                continue  # null disables inherited gate
            out[gname] = dict(gcfg)
        return out

    def guide_path_for(self, name: str) -> str | None:
        """Absolute path to the stack guide, or None if not loaded."""
        decl = self._resolve().get(name)
        if not decl:
            return None
        guide_rel = decl.get("guide_path") or "guide.md"
        stack_dir = decl.get("_stack_dir")
        if not stack_dir:
            return None
        return os.path.join(stack_dir, guide_rel)

    def source_for(self, name: str) -> str | None:
        """Layer that produced this stack: 'builtin' | 'user' | 'overridden'.

        Returns None when the stack isn't registered. 'overridden' means a
        user decl was deep-merged on top of a built-in entry; 'user' means
        a standalone user-only stack with no built-in counterpart.
        """
        if name not in self._resolve():
            return None
        in_builtin = name in self._builtin
        in_user = name in self._user
        if in_user and in_builtin:
            return "overridden"
        if in_user:
            return "user"
        return "builtin"

    def is_user_overridden(self, name: str) -> bool:
        """True iff the user layer altered the built-in entry for `name`.

        Standalone user stacks (no built-in counterpart) return False —
        they're additions, not overrides. Use `source_for` to distinguish.
        """
        return self.source_for(name) == "overridden"

    # --- Internals --------------------------------------------------------

    def _scan_dir(
        self, root: str | os.PathLike[str], *, layer: str
    ) -> dict[str, dict[str, Any]]:
        result: dict[str, dict[str, Any]] = {}
        root_str = str(root)
        if not os.path.isdir(root_str):
            self.errors.append(f"{layer}: stacks dir not found: {root_str}")
            return result
        for entry in sorted(os.listdir(root_str)):
            if entry.startswith("_") or entry.startswith("."):
                continue  # _schema.json, hidden files, etc.
            stack_dir = os.path.join(root_str, entry)
            if not os.path.isdir(stack_dir):
                continue
            decl_path = os.path.join(stack_dir, _STACK_JSON)
            if not os.path.isfile(decl_path):
                continue
            try:
                with open(decl_path, encoding="utf-8") as f:
                    decl = json.load(f)
            except (OSError, json.JSONDecodeError) as e:
                msg = f"{layer}: failed to read {decl_path}: {e}"
                logger.warning(msg)
                self.errors.append(msg)
                continue
            errs = validate_decl(decl, source=decl_path)
            if errs:
                for err in errs:
                    logger.warning(err)
                    self.errors.append(err)
                continue
            decl["_stack_dir"] = stack_dir
            decl["_source"] = layer
            name = decl.get("name")
            if name in result:
                msg = (
                    f"{layer}: duplicate stack name {name!r} (already loaded "
                    f"from {result[name].get('_stack_dir')})"
                )
                logger.warning(msg)
                self.errors.append(msg)
                continue
            result[name] = decl
        return result

    def _resolve(self) -> dict[str, dict[str, Any]]:
        """Merge built-in + user layers. Cached until next load_*."""
        if self._resolved is not None:
            return self._resolved
        merged: dict[str, dict[str, Any]] = {
            n: dict(d) for n, d in self._builtin.items()
        }
        for name, user_decl in self._user.items():
            extends = user_decl.get("extends")
            if extends:
                target = self._extends_target(extends)
                if target is None:
                    msg = (
                        f"{user_decl.get('_stack_dir', '<user>')}: "
                        f"extends target {extends!r} not found in built-ins; "
                        f"user decl skipped"
                    )
                    logger.warning(msg)
                    self.errors.append(msg)
                    continue
                base = merged.get(target) or self._builtin.get(target)
                if base is None:
                    msg = (
                        f"{user_decl.get('_stack_dir', '<user>')}: "
                        f"extends target {target!r} could not be resolved; "
                        f"user decl skipped"
                    )
                    logger.warning(msg)
                    self.errors.append(msg)
                    continue
                merged[name] = self._deep_merge(base, user_decl)
            else:
                # Standalone user stack (or override w/o extends — full replace).
                merged[name] = dict(user_decl)
        self._resolved = merged
        return merged

    @staticmethod
    def _extends_target(value: str) -> str | None:
        if not value.startswith("builtin:"):
            return None
        return value.split(":", 1)[1] or None

    @staticmethod
    def _deep_merge(base: dict[str, Any], over: dict[str, Any]) -> dict[str, Any]:
        """Merge `over` on top of `base` per stack-decl rules.

        Rules (see module docstring):
          * extensions_extra: additive on top of base.extensions; the result
            is written back into 'extensions' so consumers see the full set.
          * gates: per-key override; null in `over` disables (kept as null
            here — gates_for() filters nulls out).
          * detect / filenames / path_hints / version / guide_path: replace
            base value if present in `over`; else inherit from base.
          * Internal fields (_stack_dir, _source): take from `over` so the
            user file wins as the "definition" location.
        """
        result: dict[str, Any] = dict(base)
        for k, v in over.items():
            if k == "extends":
                continue  # consumed at resolve time
            if k == "gates":
                merged_gates: dict[str, Any] = dict(base.get("gates") or {})
                for gname, gcfg in (v or {}).items():
                    merged_gates[gname] = gcfg
                result["gates"] = merged_gates
                continue
            if k == "extensions_extra":
                base_exts = list(base.get("extensions") or [])
                added = [e for e in (v or []) if e not in base_exts]
                if added:
                    result["extensions"] = base_exts + added
                continue
            result[k] = v
        return result


# --- Module-level singleton -------------------------------------------------

_default_registry: StackRegistry | None = None


def default_registry() -> StackRegistry:
    """Return the lazy-initialized module-level registry.

    Loads built-ins from `<repo>/stacks/` (resolved from this file's location)
    and user overrides from `<cwd>/.tausik/stacks/` if present. Use
    `default_registry().reload(...)` from tests to point at fixtures.
    """
    global _default_registry
    if _default_registry is None:
        reg = StackRegistry()
        # `<repo>/stacks/` lives one level up from `scripts/`.
        scripts_dir = os.path.dirname(os.path.abspath(__file__))
        repo_root = os.path.dirname(scripts_dir)
        builtin_dir = os.path.join(repo_root, "stacks")
        reg.load_builtin(builtin_dir)
        user_dir = os.path.join(os.getcwd(), ".tausik", "stacks")
        reg.load_user(user_dir)
        _default_registry = reg
    return _default_registry
