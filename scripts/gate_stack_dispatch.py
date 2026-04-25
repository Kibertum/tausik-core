"""Stack-aware gate dispatch (Epic 2 critical bug fix).

Maps file extensions → candidate stacks and decides whether a gate's
`stacks` filter should let it run for a given relevant_files set.

Extracted from gate_runner.py to keep it under the filesize budget.
"""

from __future__ import annotations

import os


# Hardcoded fallback dispatch tables. Used only when stack_registry can't
# load — keeps gate_applies_to working under partial-bootstrap conditions.
_FALLBACK_EXT_TO_STACKS: dict[str, frozenset[str]] = {
    ".py": frozenset({"python", "fastapi", "django", "flask"}),
    ".ts": frozenset({"typescript", "react", "next", "vue", "nuxt", "svelte"}),
    ".tsx": frozenset({"typescript", "react", "next"}),
    ".js": frozenset({"javascript", "react", "next", "vue", "nuxt", "svelte"}),
    ".jsx": frozenset({"javascript", "react", "next"}),
    ".vue": frozenset({"vue", "nuxt"}),
    ".svelte": frozenset({"svelte"}),
    ".go": frozenset({"go"}),
    ".rs": frozenset({"rust"}),
    ".java": frozenset({"java"}),
    ".kt": frozenset({"kotlin"}),
    ".kts": frozenset({"kotlin"}),
    ".php": frozenset({"php", "laravel"}),
    ".blade.php": frozenset({"blade", "laravel", "php"}),
    ".swift": frozenset({"swift"}),
    ".dart": frozenset({"flutter"}),
    ".tf": frozenset({"terraform"}),
    ".tfvars": frozenset({"terraform"}),
}

_FALLBACK_FILENAME_TO_STACKS: dict[str, frozenset[str]] = {
    "dockerfile": frozenset({"docker"}),
    "containerfile": frozenset({"docker"}),
    "ansible.cfg": frozenset({"ansible"}),
    "chart.yaml": frozenset({"helm"}),
    "chart.yml": frozenset({"helm"}),
    "values.yaml": frozenset({"helm"}),
    "values.yml": frozenset({"helm"}),
}

_FALLBACK_PATH_HINTS: tuple[tuple[str, frozenset[str]], ...] = (
    ("/playbooks/", frozenset({"ansible"})),
    ("/roles/", frozenset({"ansible"})),
    ("/templates/", frozenset({"helm"})),
    ("/k8s/", frozenset({"kubernetes"})),
    ("/manifests/", frozenset({"kubernetes"})),
    ("/.kube/", frozenset({"kubernetes"})),
)


def _build_dispatch_tables() -> tuple[
    dict[str, frozenset[str]],
    dict[str, frozenset[str]],
    tuple[tuple[str, frozenset[str]], ...],
]:
    """Invert per-stack registry data into ext/filename/path-hint indexes.

    Compound-extension semantics: `.blade.php` inherits the `.php` stack
    set so a foo.blade.php file still matches php/laravel-scoped gates,
    matching the previous hardcoded behaviour.
    """
    try:
        from stack_registry import default_registry

        reg = default_registry()
        ext: dict[str, set[str]] = {}
        files: dict[str, set[str]] = {}
        hints: dict[str, set[str]] = {}
        for name in reg.all_stacks():
            for e in reg.extensions_for(name):
                ext.setdefault(e, set()).add(name)
            for fn in reg.filenames_for(name):
                files.setdefault(fn, set()).add(name)
            for h in reg.path_hints_for(name):
                hints.setdefault(h, set()).add(name)
        # Compound extension: .blade.php → union with .php.
        if ".blade.php" in ext and ".php" in ext:
            ext[".blade.php"] = ext[".blade.php"] | ext[".php"]
        if not ext and not files and not hints:
            return (
                _FALLBACK_EXT_TO_STACKS,
                _FALLBACK_FILENAME_TO_STACKS,
                _FALLBACK_PATH_HINTS,
            )
        return (
            {k: frozenset(v) for k, v in ext.items()},
            {k: frozenset(v) for k, v in files.items()},
            tuple((k, frozenset(v)) for k, v in hints.items()),
        )
    except Exception:  # noqa: BLE001 — gate dispatch must work even on broken registry
        import logging

        logging.getLogger("tausik.gate_dispatch").warning(
            "Stack registry unavailable; using hardcoded dispatch tables",
            exc_info=True,
        )
        return (
            _FALLBACK_EXT_TO_STACKS,
            _FALLBACK_FILENAME_TO_STACKS,
            _FALLBACK_PATH_HINTS,
        )


_EXT_TO_STACKS, _FILENAME_TO_STACKS, _PATH_HINTS = _build_dispatch_tables()


def _stacks_from_basename(basename: str) -> frozenset[str]:
    # Exact match (e.g. "Dockerfile", "Chart.yaml")
    if basename in _FILENAME_TO_STACKS:
        return _FILENAME_TO_STACKS[basename]
    # Prefix match for variants like "Dockerfile.prod", "Containerfile.dev"
    for key, stacks in _FILENAME_TO_STACKS.items():
        if basename.startswith(key + "."):
            return stacks
    return frozenset()


def infer_stacks_from_files(files: list[str]) -> set[str]:
    """Map each file's extension/filename to candidate stacks; union them."""
    out: set[str] = set()
    for f in files or []:
        if not isinstance(f, str):
            continue
        norm = f.replace("\\", "/").lower()
        # Filename heuristics first (covers Dockerfile-style files w/o ext)
        out.update(_stacks_from_basename(os.path.basename(norm)))
        if norm.endswith(".blade.php"):
            out.update(_EXT_TO_STACKS[".blade.php"])
            continue
        ext = os.path.splitext(norm)[1]
        if ext in _EXT_TO_STACKS:
            out.update(_EXT_TO_STACKS[ext])
        # Path hints — used to disambiguate YAML/JSON in IaC trees.
        # Prepend "/" so matching works for both "/k8s/x.yml" and "k8s/x.yml".
        if ext in (".yaml", ".yml", ".json"):
            anchored = f"/{norm}" if not norm.startswith("/") else norm
            for fragment, stacks in _PATH_HINTS:
                if fragment in anchored:
                    out.update(stacks)
    return out


def skipped_result(gate: dict, files: list[str]) -> dict:
    """Build the result dict reported when a gate doesn't apply to a file set."""
    return {
        "name": gate["name"],
        "severity": gate.get("severity", "warn"),
        "passed": True,
        "skipped": True,
        "output": (
            f"Not applicable for stack — gate.stacks={gate.get('stacks')}, "
            f"file-stacks={sorted(infer_stacks_from_files(files))}"
        ),
    }


def gate_applies_to(gate: dict, files: list[str]) -> bool:
    """Decide whether a stack-scoped gate should run for this file set.

    Universal gates (no `stacks` field) always run. With `stacks` set, skip
    when relevant_files contain no language matching the gate. Empty
    `files` is treated as universal — caller couldn't scope, so the gate
    runs (preserves the previous behaviour for run_gates without
    relevant_files).
    """
    gate_stacks = gate.get("stacks")
    if not gate_stacks:
        return True
    if not files:
        return True
    return bool(set(gate_stacks) & infer_stacks_from_files(files))
