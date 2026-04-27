"""Default quality gate configurations.

`DEFAULT_GATES` is the union of:
  * `UNIVERSAL_GATES` — hardcoded gates with no `stacks` filter (filesize,
    tdd_order, ruff, mypy, bandit). They live here because they don't
    belong to any single stack.
  * Stack-scoped gates pulled from `stack_registry` — pytest, tsc, eslint,
    cargo-*, phpstan, terraform-validate, etc. The canonical source is
    each stack's `stacks/<name>/stack.json` gates section.

If the registry can't load (early bootstrap, missing dir), we fall back
to a full hardcoded set so the framework still boots — keeping the
contract `from default_gates import DEFAULT_GATES` exception-free.
"""

from __future__ import annotations

# --- Universal gates (no stacks filter) -------------------------------------

UNIVERSAL_GATES: dict[str, dict] = {
    "ruff": {
        "enabled": True,
        "severity": "block",
        "trigger": ["commit"],
        "command": "ruff check {files}",
        "description": "Lint with ruff before commit",
        "file_extensions": [".py"],
    },
    "mypy": {
        "enabled": False,
        "severity": "warn",
        "trigger": ["commit"],
        "command": "mypy {files}",
        "description": "Type-check with mypy before commit",
        "file_extensions": [".py"],
    },
    "filesize": {
        "enabled": True,
        "severity": "block",
        "trigger": ["task-done", "commit"],
        "command": None,
        "description": "Warn if files exceed max_lines threshold",
        "max_lines": 400,
    },
    "bandit": {
        "enabled": False,
        "severity": "warn",
        "trigger": ["review"],
        "command": "bandit -r {files} -q",
        "description": "Security scan with bandit",
    },
    "tdd_order": {
        "enabled": False,
        "severity": "warn",
        "trigger": ["task-done"],
        "command": None,
        "description": "Verify test files were modified (TDD enforcement)",
    },
}


# Stack-scoped gates come EXCLUSIVELY from the plugin registry
# (`stacks/<name>/stack.json`). v1.3.1 dropped the 190-line hardcoded fallback
# because it silently drifted from the source-of-truth files — adding a new
# gate to a stack.json would not appear if the registry import failed; a
# removed gate would still appear. Now: registry failure logs WARNING and
# returns empty dict, surfacing the issue rather than masking it.


def _build_stack_scoped_gates() -> dict[str, dict]:
    """Read stack-scoped gates from the plugin registry. Empty + log on error."""
    try:
        from stack_registry import default_registry

        reg = default_registry()
        out: dict[str, dict] = {}
        for name in sorted(reg.all_stacks()):
            for gname, gcfg in reg.gates_for(name).items():
                if gname not in out:
                    out[gname] = dict(gcfg)
        return out
    except Exception:  # noqa: BLE001 — must not crash module import
        import logging

        logging.getLogger("tausik.default_gates").warning(
            "Stack registry unavailable — stack-scoped gates DISABLED. "
            "Run `tausik doctor` to diagnose. Universal gates (filesize, "
            "ruff, mypy, bandit, tdd_order) remain active.",
            exc_info=True,
        )
        return {}


def _build_default_gates() -> dict[str, dict]:
    """DEFAULT_GATES = UNIVERSAL_GATES ∪ registry-derived stack-scoped gates."""
    merged: dict[str, dict] = dict(UNIVERSAL_GATES)
    merged.update(_build_stack_scoped_gates())
    return merged


DEFAULT_GATES: dict[str, dict] = _build_default_gates()
