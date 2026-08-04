"""TAUSIK filesize gate — line-cap enforcement with exempt dirs/basenames.

Extracted from gate_runner.py for filesize compliance (gate_runner sat exactly
at the 400-line cap, so any addition broke it). gate_runner re-exports
``count_lines`` and ``run_filesize_gate`` so existing imports (tests, the
run_gates dispatch) keep working unchanged.

Cap history (task l26-filesize-gate-revisit, decision #190): the 400 cap was
deforming architecture — an audit found ~30 modules that document themselves as
split *only* to pass the gate, and five core files written to exactly 400 lines
("письмо под лимит, не под концепт"). The interim measure raises the cap to 500
(absorbs every documented wrapper-merge with margin while a genuinely 2× file
still blocks); the real fix (measure post-MRO public class surface instead of
raw lines, and de-exempt harness/claude/mcp/) is deferred to a dedicated task.

Exempt dirs/basenames are read from the COMMITTED, branch-coupled
``tausik/gates.json`` (survives a fresh clone, unlike gitignored
``.tausik/config.json``) and MERGED over the hardcoded fallbacks below, so
adding an exemption no longer requires editing this source file.
"""

from __future__ import annotations

import json
import os

# Interim cap (decision #190). See module docstring. Also mirrored in the
# ``filesize`` gate default_config in gate_registry.py — that is the canonical
# runtime source; this constant is the fallback when a caller passes no gate
# config (e.g. direct unit calls).
DEFAULT_MAX_LINES = 500


def count_lines(filepath: str) -> int:
    """Count lines in a file."""
    try:
        with open(filepath, encoding="utf-8", errors="replace") as f:
            return sum(1 for _ in f)
    except OSError:
        return 0


# Hardcoded FALLBACK exempts — used when the committed tausik/gates.json is
# absent or omits a key. The committed config is the editable source of truth;
# these stay so a consumer without the tausik/ projection still has sane
# defaults (and so the gate never crashes on a bad config).
_FILESIZE_EXEMPT_DIRS = (
    "tests/",
    # `harness/claude/mcp/` used to be exempt as a whole tree, which hid the two
    # largest modules in the repo — handlers.py (then 1281 lines and 77 handlers;
    # since cut to a 174-line dispatcher by mcp-handlers-god-module-split, and no
    # longer exempt at all) and tools.py (988, exempt on its own declarative-table
    # rationale) — from the cap entirely. Removed by filesize-mro-exempt-mcp:
    # a whole TREE is never the right exemption unit, because it grants the
    # exemption to every file anyone adds there later. The genuinely-exempt files
    # are now named individually in tausik/gates.json `exempt_files`.
    #
    # `.claude/mcp/` stays exempt: it is a byte-for-byte MIRROR that bootstrap
    # generates from harness/, so flagging it would report every violation twice
    # and let a fix look complete while the source stayed broken. The source tree
    # is the one that is now measured.
    ".claude/mcp/",
    # Common exempt dirs for source materials, ADR markdowns, agent configs.
    "docs/content/",
    "docs/architecture/",
    "backend/configs/",
    # Research dumps grow large by design (convention #122) — exempt in the
    # committed gate so a fresh clone / CI does not block on them (the per-project
    # .tausik/config.json exempt is gitignored and not present on a fresh clone).
    "docs/en/research/",
    "docs/ru/research/",
)

# Reference docs that grow by design (one entry per command/release) — exempt
# from the line cap in the committed gate, same rationale as the research dumps
# above: a fresh clone / CI must not block on them, and the per-project
# .tausik/config.json exempt is gitignored.
_FILESIZE_EXEMPT_BASENAMES = frozenset(
    {
        "CHANGELOG.md",
        "CHANGELOG.ru.md",
        "cli.md",  # docs/{en,ru}/cli.md — full CLI command reference
    }
)


def _normalize_path(p: str) -> str:
    """Canonicalize path for matching: forward slashes, strip leading './'."""
    n = os.path.normpath(p).replace("\\", "/")
    if n.startswith("./"):
        n = n[2:]
    return n


def _path_under_exempt_dir(normalized: str, exempt_dir: str) -> bool:
    """True if *normalized* (a forward-slash path) lies under *exempt_dir*,
    matched on path-SEGMENT boundaries.

    So ``tests/`` exempts ``tests/x.py`` and ``a/tests/x.py`` but NOT
    ``unittests/x.py`` — the old unanchored substring check wrongly exempted the
    latter, and the blast radius grew with every externally-editable entry added
    to tausik/gates.json (review s146, finding M2).
    """
    d = exempt_dir.rstrip("/") + "/"
    return normalized.startswith(d) or ("/" + d) in normalized


def _committed_gates_config_path(start: str | None = None) -> str | None:
    """Locate the committed ``tausik/gates.json``.

    Env override ``TAUSIK_GATES_CONFIG`` wins (explicit path, used by CI/tests).
    Otherwise walk up from *start*/cwd for a ``tausik/gates.json`` — the
    non-dotted, branch-coupled projection that a fresh clone actually carries
    (``.tausik/`` is gitignored). Returns ``None`` if none is found.
    """
    override = os.environ.get("TAUSIK_GATES_CONFIG")
    if override:
        return override if os.path.isfile(override) else None
    d = os.path.abspath(start or os.getcwd())
    for _ in range(12):
        candidate = os.path.join(d, "tausik", "gates.json")
        if os.path.isfile(candidate):
            return candidate
        # Stop at the repo root — never adopt a tausik/gates.json from an
        # unrelated ancestor (a shared CI workspace, a monorepo parent, a
        # leftover clone) whose exempt list would silently widen what bypasses
        # the cap for THIS project (review s146, finding M1).
        if os.path.exists(os.path.join(d, ".git")):
            break
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    return None


def _load_committed_filesize_config(start: str | None = None) -> dict:
    """Read the ``filesize`` section of the committed tausik/gates.json.

    Best-effort: a missing file, unreadable file, or malformed JSON degrades to
    ``{}`` (fallback defaults apply) rather than crashing the gate — a gate that
    dies on a bad config would block every close for a reason unrelated to the
    file under review (convention #226: degrade to a stated 'unknown', never
    hard-fail on ambient breakage).
    """
    path = _committed_gates_config_path(start)
    if not path:
        return {}
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    section = data.get("filesize")
    return section if isinstance(section, dict) else {}


def _resolve_exempts(start: str | None = None) -> tuple[tuple[str, ...], frozenset[str]]:
    """Merge committed exempts over the hardcoded fallbacks (union, additive).

    Committed config EXTENDS the defaults rather than replacing them, so a
    partial or empty committed file can never silently drop a baseline exemption.

    Note the direction: this union means an exemption can be ADDED from config but
    never REMOVED there. Retiring one — as filesize-mro-exempt-mcp did for the
    blanket `harness/claude/mcp/` — requires editing the tuple above, deliberately.
    """
    cfg = _load_committed_filesize_config(start)
    dirs = list(_FILESIZE_EXEMPT_DIRS)
    extra_dirs = cfg.get("exempt_dirs")
    if isinstance(extra_dirs, list):
        for d in extra_dirs:
            if isinstance(d, str) and d and d not in dirs:
                dirs.append(d)
    basenames = set(_FILESIZE_EXEMPT_BASENAMES)
    extra_names = cfg.get("exempt_basenames")
    if isinstance(extra_names, list):
        basenames.update(n for n in extra_names if isinstance(n, str) and n)
    return tuple(dirs), frozenset(basenames)


def _resolve_exempt_files(start: str | None = None) -> frozenset[str]:
    """Exact repo-relative paths exempt from the cap, from committed gates.json.

    File-precise BY DESIGN. A directory exemption silently covers every file added
    to that directory afterwards, which is how a whole MCP tree came to be exempt
    and hid its two largest modules. Naming a path grants the exemption to exactly
    that file, so widening it is a visible, reviewable diff rather than a default.
    """
    cfg = _load_committed_filesize_config(start)
    entries = cfg.get("exempt_files")
    if not isinstance(entries, list):
        return frozenset()
    return frozenset(
        _normalize_path(e) for e in entries if isinstance(e, str) and e and not e.startswith("_")
    )


def run_filesize_gate(gate: dict, files: list[str]) -> tuple[bool, str]:
    """Check file sizes against max_lines threshold.

    Exempt dirs/basenames come from the committed tausik/gates.json merged over
    the hardcoded fallbacks (``_resolve_exempts``). Per-file exempts via
    gate.exempt_files: entries with '/' match by exact path, bare names match by
    basename (covers a file anywhere in tree).
    """
    max_lines = gate.get("max_lines", DEFAULT_MAX_LINES)
    exempt_dirs, exempt_basenames_cfg = _resolve_exempts()
    exempt_paths: set[str] = set(_resolve_exempt_files())
    exempt_basenames: set[str] = set()
    for entry in gate.get("exempt_files") or []:
        norm = entry.replace("\\", "/")
        if "/" in norm:
            exempt_paths.add(_normalize_path(norm))
        else:
            exempt_basenames.add(norm)

    violations = []
    for f in files:
        if not os.path.isfile(f):
            continue
        normalized = f.replace("\\", "/")
        if any(_path_under_exempt_dir(normalized, d) for d in exempt_dirs):
            continue
        canon = _normalize_path(f)
        basename = os.path.basename(canon)
        if canon in exempt_paths or basename in exempt_basenames:
            continue
        if basename in exempt_basenames_cfg:
            continue
        lines = count_lines(f)
        if lines > max_lines:
            violations.append(f"  {f}: {lines} lines (max {max_lines})")
    if violations:
        return False, "Files exceeding line limit:\n" + "\n".join(violations)
    return True, "All files within line limit."
