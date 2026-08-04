"""Class public-surface gate (filesize-mro-exempt-mcp).

The filesize gate measures the WRONG UNIT for one whole class of defect. It counts
raw lines per file, so a god-object assembled from mixins is invisible: every
mixin sits comfortably under the line cap while the class they compose does not.
Measured on this repo, `SQLiteBackend` exposes 129 public members inherited from
8 bases and `ProjectService` 117 from 9 — the next-largest class has 28. Neither
has ever tripped a gate.

Worse, the line cap actively CAUSED the split. The size distribution across
scripts/ decays monotonically from 60 modules at 100-149 lines down to 22 at
300-349, then RISES to 26 at 350-399 and collapses to 6 above 400 — a pile-up
against the old 400 boundary and a cliff past it. Modules were cut to fit, which
made the composed surface grow while every individual file looked healthier.

So this gate measures the composed public contract instead, and it ADDS TO rather
than replaces the line cap: "this class does too much" and "this file is too long
to read" are different defects and neither implies the other.

AST, never import. The gate must be able to measure a file it does not trust and
must never execute repo code to do so — a gate with side effects is a gate nobody
can run on a branch they have not read. The cost is that a dynamically attached
member (`setattr`, a metaclass) is invisible, so the count is a LOWER BOUND and is
reported as one (convention #325: a derived measurement must not be dressed up as
a declared one).
"""

from __future__ import annotations

import ast
import json
import os
from typing import Any

DEFAULT_MAX_PUBLIC_MEMBERS = 60

# Source-of-truth trees. The IDE mirrors (.claude/, .cursor/, .kilo/, .opencode/,
# .qwen/) are byte-copies produced by bootstrap; scanning them would report every
# violation six times and let a fix "pass" while the source stayed broken.
SCAN_ROOTS = ("scripts", "harness", "bootstrap")

_SKIP_DIRS = frozenset(
    {
        ".git",
        ".tausik",
        "__pycache__",
        "node_modules",
        ".venv",
        "venv",
        ".pytest_cache",
        ".mypy_cache",
    }
)


class ClassInfo:
    """One class as the AST sees it: where it lives, what it extends, what it exposes."""

    __slots__ = ("name", "path", "bases", "own_public")

    def __init__(self, name: str, path: str, bases: list[str], own_public: set[str]) -> None:
        self.name = name
        self.path = path
        self.bases = bases
        self.own_public = own_public


def _base_name(node: ast.expr) -> str | None:
    """`Mixin` / `mod.Mixin` / `mod.sub.Mixin` → "Mixin". Anything computed → None."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _own_public_members(node: ast.ClassDef) -> set[str]:
    """Public members DECLARED on this class (methods, class attrs, annotated attrs).

    `_name` and `__name` are excluded: the gate caps the public CONTRACT, not
    internal complexity — a class with many private helpers and a small public
    surface is a different (and often fine) shape.
    """
    members: set[str] = set()
    for item in node.body:
        if isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef):
            if not item.name.startswith("_"):
                members.add(item.name)
        elif isinstance(item, ast.Assign):
            for target in item.targets:
                if isinstance(target, ast.Name) and not target.id.startswith("_"):
                    members.add(target.id)
        elif isinstance(item, ast.AnnAssign):
            if isinstance(item.target, ast.Name) and not item.target.id.startswith("_"):
                members.add(item.target.id)
    return members


def collect_classes(paths: list[str]) -> tuple[dict[tuple[str, str], ClassInfo], list[str]]:
    """Parse each file into {(path, class name): ClassInfo}, plus parse errors.

    Keyed by PATH AND NAME, never name alone. Two modules may legitimately define
    the same name — `ExportError` exists in both state_export and receipt_export
    here — and a name-keyed index would drop one of them from the measurement
    entirely, which is exactly the silent under-reporting this gate exists to stop.

    Errors are RETURNED, not swallowed. A measurer that skips what it could not
    read reports coverage it does not have (convention #305: print the denominator
    next to the verdict).
    """
    classes: dict[tuple[str, str], ClassInfo] = {}
    errors: list[str] = []
    for path in paths:
        try:
            with open(path, encoding="utf-8") as fh:
                tree = ast.parse(fh.read(), filename=path)
        except (OSError, SyntaxError, ValueError) as e:
            errors.append(f"{path}: {type(e).__name__}: {e}")
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                bases = [b for b in (_base_name(x) for x in node.bases) if b]
                classes[path, node.name] = ClassInfo(
                    node.name, path, bases, _own_public_members(node)
                )
    return classes, errors


def _by_name(classes: dict[tuple[str, str], ClassInfo]) -> dict[str, list[ClassInfo]]:
    """name → every class declaring it, for cross-module base resolution."""
    index: dict[str, list[ClassInfo]] = {}
    for info in classes.values():
        index.setdefault(info.name, []).append(info)
    return index


def public_surface(
    info: ClassInfo,
    classes: dict[tuple[str, str], ClassInfo],
    index: dict[str, list[ClassInfo]] | None = None,
) -> tuple[set[str], int]:
    """Union of public members across the class and every base we can resolve.

    Returns (members, ambiguous_base_count). Approximates the MRO: Python would
    linearize and let overrides collapse, and a set union does exactly that for
    NAMES — an override contributes its name once either way.

    Base resolution prefers a class declared in the SAME file, then a unique
    repo-wide match. A name matching several classes is left unresolved rather
    than guessed, because picking one by filesystem order would make the reported
    surface depend on directory listing order. Unresolved bases — `object`,
    stdlib, third-party, ambiguous — contribute nothing, so the count stays a
    LOWER BOUND on the true surface.
    """
    idx = index if index is not None else _by_name(classes)
    seen: set[tuple[str, str]] = set()
    members: set[str] = set()
    ambiguous = 0

    def walk(current: ClassInfo) -> None:
        nonlocal ambiguous
        key = (current.path, current.name)
        if key in seen:
            return  # diamond inheritance / cycle guard
        seen.add(key)
        members.update(current.own_public)
        for base in current.bases:
            same_file = classes.get((current.path, base))
            if same_file is not None:
                walk(same_file)
                continue
            candidates = idx.get(base, [])
            if len(candidates) == 1:
                walk(candidates[0])
            elif len(candidates) > 1:
                ambiguous += 1

    walk(info)
    return members, ambiguous


def _iter_source_files(repo_root: str, roots: tuple[str, ...] = SCAN_ROOTS) -> list[str]:
    """Every .py under the source-of-truth trees, IDE mirrors excluded."""
    found: list[str] = []
    for root in roots:
        base = os.path.join(repo_root, root)
        if not os.path.isdir(base):
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
            found.extend(os.path.join(dirpath, f) for f in sorted(filenames) if f.endswith(".py"))
    return sorted(found)


def _repo_root() -> str:
    """The .git-anchored repo root, NOT this file's parent's parent.

    Gates execute from the DEPLOYED copy (`.claude/scripts/`), where a naive
    dirname-twice lands on `.claude/` — which has a `scripts/` mirror but no
    `tausik/gates.json` and no `harness/`. That silently measured the mirror and
    lost the ratchet baseline, turning the gate red on the two classes the
    baseline exists to hold. Anchoring on `.git` makes source-tree and deployed
    invocations resolve to the same root, which is the whole point.
    """
    here = os.path.dirname(os.path.abspath(__file__))
    d = here
    for _ in range(12):
        if os.path.exists(os.path.join(d, ".git")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    # No .git (tarball export, vendored copy): fall back to the nearest ancestor
    # that actually carries a source tree, then to this file's parent.
    for candidate in (os.path.dirname(here), os.path.dirname(os.path.dirname(here))):
        if os.path.isdir(os.path.join(candidate, "harness")):
            return candidate
    return os.path.dirname(here)


def _load_config() -> dict[str, Any]:
    """`class_surface` node from the committed tausik/gates.json ({} on any defect).

    Located via gate_filesize's resolver so both gates provably read the SAME
    committed file — including its `.git` boundary, which stops an unrelated
    ancestor's gates.json (a monorepo parent, a leftover clone) from widening
    what this project exempts (review s146, finding M1).
    """
    try:
        from gate_filesize import _committed_gates_config_path

        path = _committed_gates_config_path(_repo_root())
    except Exception:  # noqa: BLE001 — resolver unavailable: fall back to the root
        path = os.path.join(_repo_root(), "tausik", "gates.json")
    if not path:
        return {}
    try:
        with open(path, encoding="utf-8") as fh:
            node = json.load(fh).get("class_surface")
        return node if isinstance(node, dict) else {}
    except (OSError, ValueError):
        return {}


def measure(
    repo_root: str | None = None, roots: tuple[str, ...] = SCAN_ROOTS
) -> tuple[list[tuple[str, int, str]], list[str], int]:
    """Every class ranked by composed public surface.

    Returns ([(class_name, surface_size, relative path)], parse_errors,
    ambiguous_base_count), largest surface first.
    """
    root = repo_root or _repo_root()
    classes, errors = collect_classes(_iter_source_files(root, roots))
    index = _by_name(classes)
    ranked: list[tuple[str, int, str]] = []
    ambiguous_total = 0
    for info in classes.values():
        members, ambiguous = public_surface(info, classes, index)
        ambiguous_total += ambiguous
        ranked.append((info.name, len(members), os.path.relpath(info.path, root)))
    ranked.sort(key=lambda row: (-row[1], row[0]))
    return ranked, errors, ambiguous_total


def run_class_surface_gate(gate: dict, files: list[str]) -> tuple[bool, str]:
    """Repo-wide public-surface check. `files` is IGNORED, by design.

    A per-file gate only ever sees what someone happened to edit, so a class that
    drifts past the cap through its BASES — nobody touching the class itself —
    stays green forever. That is not hypothetical: service_knowledge drifted to
    406 lines under the line gate and blocked no one. Whole-repo is the only scope
    in which "no class exceeds the cap" is a statement about the repo rather than
    about this commit.

    A BASELINE keeps that affordable. Known oversized classes are recorded with
    their current size; they fail only if they GROW. A gate that turns red on
    everything the day it lands gets switched off, so the ratchet lets the number
    come down over time while blocking any new god-object outright.
    """
    cfg = _load_config()
    cap = int(
        gate.get("max_public_members")
        or cfg.get("max_public_members")
        or DEFAULT_MAX_PUBLIC_MEMBERS
    )
    baseline_raw = cfg.get("baseline")
    baseline: dict[str, int] = baseline_raw if isinstance(baseline_raw, dict) else {}

    ranked, errors, ambiguous = measure()

    violations: list[str] = []
    regressions: list[str] = []
    for name, size, path in ranked:
        if size <= cap:
            continue
        allowed = baseline.get(name)
        if allowed is None:
            violations.append(f"  {path}: {name} exposes {size} public members (max {cap})")
        elif size > allowed:
            regressions.append(
                f"  {path}: {name} grew to {size} public members "
                f"(baseline {allowed}, max {cap}) — the ratchet only turns down"
            )

    scanned = len({row[2] for row in ranked})
    denominator = f"{len(ranked)} classes across {scanned} file(s)"
    caveat = " Counts are a LOWER BOUND (AST, not import)."
    if ambiguous:
        caveat += f" {ambiguous} base(s) left unresolved as name-ambiguous."

    if errors:
        # A file that could not be PARSED is a failure, not a footnote: coverage
        # cannot be claimed over a file that was never read. This is distinct from
        # an ambiguous base, which only makes an individual count conservative.
        detail = "\n".join(f"  {e}" for e in errors)
        return False, f"Could not measure every file ({denominator}):\n{detail}"

    if regressions or violations:
        parts = []
        if regressions:
            parts.append("Baselined classes that GREW:\n" + "\n".join(regressions))
        if violations:
            parts.append("Classes over the public-surface cap:\n" + "\n".join(violations))
        parts.append(f"Measured {denominator}.{caveat}")
        return False, "\n".join(parts)

    return True, f"All classes within the public-surface cap ({denominator}).{caveat}"
