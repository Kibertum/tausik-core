"""The one list of FOREIGN memory sinks — where project knowledge must not go.

TAUSIK's claim is that everything learned about a project lands in
`.tausik/tausik.db`, so the next agent — any agent, not just the one that
learned it — inherits it. Every host ships its own memory instead: Claude has
`~/.claude/**/memory/`, Cursor `.cursor/rules/`, Copilot
`.github/copilot-instructions.md`, aider a chat history file. An agent writing
there is not misbehaving; it is doing what its host taught it. The knowledge is
simply gone the moment the project is opened in a different tool.

Three layers enforce the routing, and they must all judge by the SAME list or
the one that lags becomes the hole (convention #266 — one producer, not two
copies of the rule):

1. UNIVERSAL — the `memory_route` gate (`gate_memory_route`) and the git
   pre-commit hook that calls it. IDE-agnostic: they judge the working tree,
   so they catch a hand edit, a script, and a host TAUSIK has never heard of.
2. PER-HARNESS — the Claude PreToolUse hook (`hooks/memory_pretool_block`),
   which is faster and refuses the write before it happens, covering Write /
   Edit / MultiEdit and the Bash write vector.
3. INSTRUCTION — the litmus block in the bootstrap rule templates
   (`bootstrap_templates.MEMORY`). The honest limit: a host whose memory is
   purely cloud-side writes no file, so layers 1-2 cannot see it at all. Only
   the instruction reaches that case, and only if the agent obeys it.

WHAT IS DELIBERATELY *NOT* HERE — and this is the whole design:
`.cursorrules`, `.windsurfrules`, `CLAUDE.md`, `AGENTS.md`, `QWEN.md`,
`.opencode/tausik-rules.md`, and the `.cursor/` `.windsurf/` `.qwen/` `.kilo/`
`.opencode/` `.codex/` `.claude/` trees are TAUSIK's OWN deployment targets —
`bootstrap --ide all` writes every one of them. Listing them as foreign sinks
would make the framework block its own bootstrap, and the failure would be
INVISIBLE in this repository (they sit in `.gitignore` here) while firing in
every project that tracks them. The carve-out is derived from
`ide_utils.IDE_REGISTRY` rather than restated, so adding an IDE cannot silently
turn its adapter into a forbidden path; `test_memory_sinks` asserts no sink
pattern swallows one.

Precedence, stated rather than emergent: an explicit sink pattern WINS over the
owned-tree carve-out. `.cursor/rules/**` lives inside TAUSIK-owned `.cursor/`
and is still foreign — TAUSIK never writes there, and it is precisely where
Cursor puts what it learned.

MECHANISM GENERIC, POLICY CONFIGURABLE (convention #277): the defaults below
ship with the framework, and a project extends or exempts through
`config.gates.memory_route`. TAUSIK is bootstrapped into repositories whose
hosts it cannot enumerate in advance.

Stdlib-only and import-light — a PreToolUse hook pays for every import on every
tool call, and the gate must load without dragging in the service layer.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Iterable

# The pattern language lives in `path_glob`: `*` within a segment, `**` across
# segments (zero included), everything lowercased first. Re-exported so the
# three enforcement layers import one module, not two.
from path_glob import (  # noqa: F401 — re-exported for the layers
    glob_match,
    is_absolute,
    normalize,
)


# --- The list ---------------------------------------------------------------


@dataclass(frozen=True)
class SinkRule:
    """One foreign memory sink.

    `scope` says what the pattern is anchored to, and it is the difference
    between two enforcement reaches rather than a formatting detail:

    * ``tree`` — relative to the project root. Visible to all three layers.
    * ``home`` — relative to the user's home directory. Outside the working
      tree, so the gate and the pre-commit hook CANNOT see it; only the
      PreToolUse hook and the instruction layer reach it. Named here anyway so
      there is one list, and so the boundary is documented instead of implied.
    """

    name: str
    scope: str
    pattern: str
    host: str
    why: str


SCOPE_TREE = "tree"
SCOPE_HOME = "home"

DEFAULT_SINKS: tuple[SinkRule, ...] = (
    SinkRule(
        name="claude_home_memory",
        scope=SCOPE_HOME,
        pattern=".claude/**/memory/**",
        host="Claude Code",
        why="Claude auto-memory is per-user and cross-project; project facts written "
        "there are invisible to every other agent and to this project's next clone.",
    ),
    SinkRule(
        name="cursor_rules",
        scope=SCOPE_TREE,
        pattern=".cursor/rules/**",
        host="Cursor",
        why="Cursor project rules — where Cursor persists what it learned. Inside "
        "TAUSIK-owned .cursor/, but TAUSIK never writes this subtree.",
    ),
    SinkRule(
        name="windsurf_rules",
        scope=SCOPE_TREE,
        pattern=".windsurf/rules/**",
        host="Windsurf",
        why="Windsurf rules directory — same role as .cursor/rules for Codeium hosts.",
    ),
    SinkRule(
        name="copilot_instructions",
        scope=SCOPE_TREE,
        pattern=".github/copilot-instructions.md",
        host="GitHub Copilot",
        why="Copilot repository instructions — read by Copilot only.",
    ),
    SinkRule(
        name="copilot_path_instructions",
        scope=SCOPE_TREE,
        pattern=".github/instructions/**",
        host="GitHub Copilot",
        why="Copilot path-scoped instruction files (*.instructions.md).",
    ),
    SinkRule(
        name="cline_rules",
        scope=SCOPE_TREE,
        pattern=".clinerules/**",
        host="Cline",
        why="Cline rules directory.",
    ),
    SinkRule(
        name="cline_rules_file",
        scope=SCOPE_TREE,
        pattern=".clinerules",
        host="Cline",
        why="Cline single-file rules.",
    ),
    SinkRule(
        name="roo_rules",
        scope=SCOPE_TREE,
        pattern=".roo/rules/**",
        host="Roo Code",
        why="Roo Code rules directory.",
    ),
    SinkRule(
        name="continue_rules",
        scope=SCOPE_TREE,
        pattern=".continue/rules/**",
        host="Continue",
        why="Continue rules directory.",
    ),
    SinkRule(
        name="aider",
        scope=SCOPE_TREE,
        pattern=".aider*",
        host="aider",
        why="aider chat history / conventions files at the repository root "
        "(.aider.chat.history.md, .aider.conf.yml).",
    ),
)


def tausik_owned_paths() -> tuple[frozenset[str], frozenset[str]]:
    """`(config_dirs, rules_files)` TAUSIK itself deploys, normalised.

    Derived from `ide_utils.IDE_REGISTRY` on purpose: a hardcoded copy would
    not learn about a newly supported IDE, and the first symptom would be the
    framework blocking its own `bootstrap --ide all` in a project that tracks
    the generated files. Imported lazily — `ide_utils` is not needed to answer
    `is_foreign_sink`, and hooks pay for every import.
    """
    try:
        from ide_utils import IDE_REGISTRY
    except ImportError:  # pragma: no cover - only when scripts/ is off sys.path
        return frozenset(), frozenset()
    dirs = {normalize(e["config_dir"]) for e in IDE_REGISTRY.values() if e.get("config_dir")}
    files = {normalize(e["rules_file"]) for e in IDE_REGISTRY.values() if e.get("rules_file")}
    return frozenset(dirs), frozenset(files)


# --- Matching ---------------------------------------------------------------


def _home_relative(path: str) -> str | None:
    """`path` expressed relative to the user's home dir, or None if outside it.

    Both the literal path and its `realpath` are tried: a symlinked home (macOS
    `/var` -> `/private/var`, a junction on Windows) otherwise reads as outside
    home and the whole home-scope list stops applying.
    """
    home = normalize(os.path.expanduser("~"))
    if not home:
        return None
    expanded = os.path.expanduser(path)
    candidates = [normalize(expanded)]
    try:
        parent = os.path.dirname(expanded) or "."
        candidates.append(normalize(os.path.join(os.path.realpath(parent), os.path.basename(path))))
    except (OSError, ValueError):
        pass
    for cand in candidates:
        if cand == home:
            return ""
        if cand.startswith(home + "/"):
            return cand[len(home) + 1 :]
    return None


def _tree_relative(path: str, project_dir: str | None) -> str | None:
    """`path` expressed relative to `project_dir`, or None if outside the tree.

    A relative input is taken as already project-relative — that is the form
    `git status --porcelain` emits, which is the gate's only input.

    Absoluteness is judged by `is_absolute`, not `os.path.isabs`: the input can
    carry a `d:/proj/core` written by a Windows host while this code runs on
    Linux, and `os.path.isabs` would call it relative. The path then fell
    through as "already project-relative" and the remediation line printed the
    whole absolute path — the exact defect convention #282 forbids, reappearing
    on the other platform.
    """
    expanded = os.path.expanduser(path)
    if not is_absolute(expanded):
        return normalize(expanded)
    if not project_dir:
        return None
    root = normalize(project_dir)
    cand = normalize(expanded)
    if cand == root:
        return ""
    if cand.startswith(root + "/"):
        return cand[len(root) + 1 :]
    return None


def is_foreign_sink(
    path: str,
    project_dir: str | None = None,
    *,
    sinks: Iterable[SinkRule] | None = None,
    allow: Iterable[str] | None = None,
) -> SinkRule | None:
    """The rule `path` violates, or None.

    `allow` is a project's configured exemption list of normalised tree-relative
    glob patterns; it is checked FIRST, because an exemption a project stated in
    its own config is a policy decision, not a bypass to be out-argued.
    """
    if not path:
        return None
    rules = tuple(sinks) if sinks is not None else DEFAULT_SINKS
    rel_tree = _tree_relative(path, project_dir)
    if allow and rel_tree is not None:
        for pattern in allow:
            if glob_match(normalize(pattern), rel_tree):
                return None
    rel_home = _home_relative(path)
    for rule in rules:
        candidate = rel_home if rule.scope == SCOPE_HOME else rel_tree
        if candidate is None:
            continue
        if glob_match(rule.pattern, candidate):
            return rule
    return None


def find_foreign_sinks(
    paths: Iterable[str],
    project_dir: str | None = None,
    *,
    sinks: Iterable[SinkRule] | None = None,
    allow: Iterable[str] | None = None,
) -> list[tuple[str, SinkRule]]:
    """`(path, rule)` for every offending path, input order preserved."""
    hits: list[tuple[str, SinkRule]] = []
    for p in paths:
        rule = is_foreign_sink(p, project_dir, sinks=sinks, allow=allow)
        if rule is not None:
            hits.append((p, rule))
    return hits


# --- Configured policy ------------------------------------------------------


def sinks_from_config(cfg: Any) -> tuple[tuple[SinkRule, ...], tuple[str, ...], str | None]:
    """`(sinks, allow, config_error)` for `config.gates.memory_route`.

    Extra sinks are appended to the defaults, never substituted: a project
    naming its in-house agent's memory file must not thereby switch off the
    ones the framework ships.

    A malformed block returns an error and the DEFAULTS, so the caller can fail
    closed on the error while still having a usable list — a policy that cannot
    be read is unknown, not absent (Decision #157).
    """
    defaults = DEFAULT_SINKS
    if not isinstance(cfg, dict):
        return defaults, (), None
    gates = cfg.get("gates")
    if not isinstance(gates, dict):
        return defaults, (), None
    block = gates.get("memory_route")
    if block is None:
        return defaults, (), None
    if not isinstance(block, dict):
        return defaults, (), f"`gates.memory_route` must be an object, got {type(block).__name__}"
    extra_raw = block.get("extra_sinks", [])
    allow_raw = block.get("allow", [])
    for key, raw in (("extra_sinks", extra_raw), ("allow", allow_raw)):
        if not isinstance(raw, list) or not all(isinstance(x, str) and x.strip() for x in raw):
            return (
                defaults,
                (),
                f"`gates.memory_route.{key}` must be a list of non-empty patterns, "
                f"got {type(raw).__name__} ({raw!r})",
            )
    extra = tuple(
        SinkRule(
            name=f"configured:{p.strip()}",
            scope=SCOPE_TREE,
            pattern=normalize(p),
            host="project-configured",
            why="Declared in .tausik/config.json -> gates.memory_route.extra_sinks.",
        )
        for p in extra_raw
    )
    return defaults + extra, tuple(a.strip() for a in allow_raw), None


def display_path(path: str, project_dir: str | None = None) -> str:
    """The path as a reader should see it: project-relative, forward slashes.

    `os.path.join` of a forward-slash `CLAUDE_PROJECT_DIR` with a relative
    target yields `d:/Work/.../core\\.clinerules` — mixed separators, in the one
    line the reader is supposed to act on. A message naming a path nobody can
    paste is the defect convention #282 exists to forbid.
    """
    rel = _tree_relative(path, project_dir)
    if rel:
        return rel
    return normalize(path)


def redirect_message(
    hits: list[tuple[str, SinkRule]], cli: str, project_dir: str | None = None
) -> str:
    """The one remediation text every layer prints.

    One producer, so the gate, the git hook and the PreToolUse hook cannot drift
    into telling the reader three different things to do.
    """
    lines = [f"  {display_path(p, project_dir)}  ->  {r.host}: {r.why}" for p, r in hits]
    listed = "\n".join(lines)
    return (
        "Project knowledge is being routed into a foreign agent's memory, where "
        "the next agent — and the next clone of this project — will not find it:\n"
        f"{listed}\n"
        f"Put it in TAUSIK memory instead: `{cli} memory add "
        '--type pattern|gotcha|convention|context|dead_end --title "..." --content "..."`.\n'
        "If the write really is a cross-project user preference (not a fact about "
        "THIS project), say so explicitly — see docs/en/security.md — or exempt the "
        "path in .tausik/config.json -> gates.memory_route.allow."
    )
