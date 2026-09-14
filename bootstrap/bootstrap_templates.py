"""Shared markdown templates for CLAUDE.md, AGENTS.md, .cursorrules, QWEN.md.

Hard constraints + workflow + SENAR rules are identical across IDEs; only the
file header and IDE subdir pointers differ. Centralizing them here prevents
drift between IDEs and makes edits single-source.
"""

from __future__ import annotations

import os
import sys

# Tier-specific bodies live in bootstrap_templates_tiers (filesize cap). Imported
# rather than re-declared, and re-exported so existing `from bootstrap_templates
# import MINIMAL_MEMORY` call sites keep working.
from bootstrap_templates_tiers import (  # noqa: F401 — re-exported
    FULL_TIER_NOTE,
    COMPACTION_CONTRACT,
    MINIMAL_COMMANDS,
    MINIMAL_COMPACTION,
    MINIMAL_MEMORY,
    MINIMAL_TIER_FOOTER,
    MINIMAL_WORKFLOW,
)

# Whether the constraints below are CHECKED on this host is derived from what
# bootstrap deployed, not asserted here. The probe lives in scripts/ because that
# is the tree bootstrap deploys into every host profile; bootstrap/ is not
# deployed, so the dependency only runs in this direction.
_here = os.path.dirname(os.path.abspath(__file__))
_scripts = os.path.join(os.path.dirname(_here), "scripts")
if os.path.isdir(_scripts) and _scripts not in sys.path:
    sys.path.insert(0, _scripts)

from enforcement_coverage import build_enforcement_notice, profile_dir_for  # noqa: E402
from rule_coverage import render_rule_notice  # noqa: E402


HARD_CONSTRAINTS = """## Hard Constraints (non-negotiable)

- **No code without a task.** Run `task start <slug>` before any Write/Edit. No exceptions. (SENAR Rule 9.1)
- **QG-0 Context Gate.** `task start` requires goal + acceptance_criteria; work that changes behaviour names at least one negative scenario, work that changes only prose does not. Set both before starting.
- **QG-2 Implementation Gate (Verify-First v1.4).** Heavy gates (pytest, tsc, cargo, phpstan, …) live on a separate `verify` step. Sequence: run `tausik verify --task <slug>` once everything is in place — it caches a green; then `task done --ac-verified` looks the cache up and closes the task in milliseconds. If the cache is missing or stale → `task done` blocks with the explicit remediation command. Opt-out for CI: `.tausik/config.json` → `{ "task_done": { "auto_verify": true } }` (legacy inline behavior).
- **No commit without gates, and verification is PROPORTIONATE to the change.** Gates run automatically — fix blocking failures before committing. Run the scoped `verify` for what you touched; the full suite belongs in CI and at the release gate, not after every local step. A test asserts behaviour — never a number in a document, never that a generated file is fresh (whatever moves its source regenerates it). One test that goes red on the defect beats a suite that goes red on bookkeeping.
- **No direct DB access.** Use MCP tools or CLI. Never raw SQLite.
- **Don't guess CLI arguments.** Run `.tausik/tausik <cmd> --help` or read the CLI reference.
- **MCP-first.** Prefer MCP tools (`tausik_*`) over CLI when equivalent.
- **Git: ask before commit/push.** Always request user confirmation.
- **Max 500 lines per file.** Filesize gate warns. Exceptions: tests, generated code.
- **Continuous logging.** Run `task log <slug> "message"` after every meaningful step. (SENAR Rule 9.4)
- **Document dead ends.** Run `.tausik/tausik dead-end "approach" "reason"` on failed approaches. (SENAR Rule 9.4)
- **Checkpoint every 30-50 tool calls.** Save context periodically. (SENAR Rule 9.3)
- **Session limit: 180 min.** `.tausik/tausik status` warns on overrun. Close the session before starting a new one. (SENAR Rule 9.2)
"""

WORKFLOW = """## Workflow

```
start → plan → task → [review | test] → commit → end
```

- `start` — load session state, active tasks, handoff from previous session · `plan` — create task with complexity scoring + stack detection
- `task <slug>` — pick up or continue a task · `review` — code review with parallel sub-agents (bugs, fake tests, drift)
- `test` — run or write tests · `commit` — standardized commit with SENAR metadata · `end` — close session with handoff for next agent

**Cost-aware model selection:** `tausik suggest-model <complexity>` prints a recommended Claude model (Haiku for simple 1 SP tasks, Sonnet for medium 3 SP, Opus for complex 8 SP). Claude Code doesn't switch models programmatically — apply the suggestion manually via the IDE model picker, and persist your default for the next session with `tausik config set model_profile <slug>` (note: `/fast` only toggles fast-output on Opus, it does NOT downgrade to a smaller model).
"""

MEMORY = """## Memory (choose the destination by what the fact is about, not by where you are)

| Destination | Where | What goes there |
|---|---|---|
| **Project memory** (`memory add`) | `.tausik/tausik.db` | "Here it is done this way": patterns, dead ends, conventions, environment facts of THIS project. Types: `pattern`, `gotcha`, `convention`, `context`, `dead_end` |
| **Shared knowledge** (`memory add --global`) | `~/.tausik-knowledge/knowledge.db`, read back in every project as *Shared knowledge — from other projects* | "The tool is built this way": a gotcha of a library, a platform habit, a fact true outside this repository. Not redacted — never a secret or a client name |
| **Agent auto-memory** | host-specific (e.g. `~/.claude/...`) | "This is how I like to work": the user's own preferences and cross-project habits — never a fact about a project |

**Memory-first recall (hard rule).** Before asking the user for — or guessing — an established
project fact (hosts, environments, where credentials live, paths, service URLs, prior decisions),
you MUST `memory_search` / `decisions_list` FIRST; asking for something already recorded is a
process violation. Record durable environment facts as `context` so future sessions inherit them.

**Routing litmus (hard).** *Would another agent, in another tool, need this to work on THIS
project?* → `memory add`. *Is it true beyond this project — of the tool, the platform, the library?*
→ `memory add --global`. Never your host's own memory (`~/.claude/**/memory/`, `.cursor/rules/`,
`.windsurf/rules/`, `.github/copilot-instructions.md`, `.github/instructions/`, `.clinerules`, `.roo/rules/`,
`.continue/rules/`, `.aider*` — blocked by the `memory_route` gate); a cloud-side memory writes no
file for any gate to see, so there this line is the only enforcement. Skills that need persistent
data respect `CLAUDE_PLUGIN_DATA` when set, else `.tausik/plugin_data/`.
"""

SENAR_RULES = """## SENAR Rules Compliance

TAUSIK enforces these rules. Violating them triggers warnings or hard blocks.

| Rule | Purpose | Enforcement |
|---|---|---|
| QG-0 Context Gate | Goal + AC + negative scenario before starting | Hard (CLI/MCP — blocks `task_start`) |
| QG-2 Implementation Gate | Evidence + AC verified + fresh `tausik verify` green before done (Verify-First v1.4) | Hard (CLI/MCP — blocks `task_done`) |
| Rule 1 Task before code | No Write/Edit without active task | Hard where a real-time mechanism is deployed — the notice at the top of this file says whether that is the case here |
| Rule 2 Scope Boundaries | Declare scope + scope_exclude per task | Warning |
| Rule 3 Verify Against Criteria | Per-criterion evidence | Warning |
| Rule 7 Root Cause | Defect tasks require root cause | Warning |
| Rule 9.2 Session limit | 180 min per session | Hard (blocks `task_start`) |
| Rule 9.3 Checkpoint | Every 30-50 tool calls | Instruction |
| Rule 9.4 Dead Ends + Logging | Document failed approaches, log progress | Instruction |

> **Where "Hard" is hard.** Rule 1 is a process gate only on a host where TAUSIK deployed a real-time mechanism; the notice at the top of this file states which case this host is in, derived from what bootstrap actually wrote. Where it is not deployed, Rule 1 is enforced by the agent reading this line — because TAUSIK generates no payload for that host, NOT because the host cannot accept one; only the first claim is ours to make. The rest hold everywhere: QG-0, QG-2 and the session limit live in the `tausik-project` MCP server and the CLI. For a process-level Rule 1 without a mechanism, route writes through `tausik_task_start` / `tausik_task_done_v2` and treat raw file edits as non-conformant in review.

Full rule set: [SENAR v1.3](https://senar.tech).
"""


def build_commands_section() -> str:
    """The command list, with its own COUNT rather than a hand-picked subset.

    The subset named nine of {total} commands, and the eighteen it omitted were
    ones an agent had no way to learn about — measured in session #233, where
    they simply went unused. Listing all of them is not the fix either: this text
    is re-sent to the agent on every turn and is held to a line budget for that
    reason.

    So the count is stated, `--help` is named, and the nine that carry the
    workflow stay. The count is DERIVED from the parser: a hand-typed number
    would be wrong the first time a command is added, and wrong silently.
    """
    from route_map import cli_commands

    total = len(cli_commands())
    # Absence, not a guess: if the parser could not be read, say so rather than
    # printing a number nobody measured.
    how_many = f"{total} commands" if total else "the full set"
    # Seven, not nine, and the two dropped (`task list`, `search`) are named in
    # the workflow section above — so the line spent introducing `--help` is paid
    # for rather than added. This text is re-sent every turn and the generated
    # file is held to 80-180 lines; growing it to advertise discoverability
    # would have been self-defeating.
    #
    # `graph` was added at exactly 180 lines, so it was PAID FOR, not appended:
    # `verify` and `task done` now share one line. They were always one act —
    # QG-2 is "gates, then close" — and the chained form is also the shape the
    # tool-choice nudge names as a legitimate reason to stay in the shell.
    return f"""## Commands Quick Reference

Seven carry the workflow; {how_many} exist — `.tausik/tausik --help` lists them.

```bash
.tausik/tausik status                          # project overview + warnings
.tausik/tausik task start <slug>               # activate (QG-0 enforced)
.tausik/tausik verify --task <slug> && .tausik/tausik task done <slug> --ac-verified  # QG-2
.tausik/tausik task log <slug> "message"       # log progress
.tausik/tausik dead-end "approach" "reason"    # document failure (used 0 times in 5,966 calls)
.tausik/tausik symbol <name>                   # a definition, its file:line and callers
.tausik/tausik graph show <path>               # what this file changes with, and on what evidence
```
"""


COMMANDS = build_commands_section()

QUALITY_GATES = """## Quality Gates

Gates run on three triggers:

- **`task-done`** — cheap-only (filesize, tdd_order). Closes a task in milliseconds.
- **`verify`** — heavy (pytest, tsc, cargo, phpstan, javac, js-test, terraform-validate, helm-lint, kubeval, hadolint, ansible-lint). Run via `.tausik/tausik verify --task <slug>`. Result cached for 10 min; `task done` reads the cache.
- **`commit`** — local lint (ruff, eslint, phpcs, golangci-lint).

Stack-specific gates auto-enable by detected stack. Filesize gate warns on files >500 lines.

Check status: `.tausik/tausik gates status`. Fix blocking failures before committing. Verify-First Contract opt-out: `.tausik/config.json` → `{ "task_done": { "auto_verify": true } }` runs the heavy gates inside `task done` instead of as a separate step.
"""

TOOL_ROUTING = """## Tool Routing — when to use which

Don't reach for `Grep`/`Glob` first. TAUSIK ships dedicated retrieval MCP servers; using them keeps context lean and surfaces project-specific knowledge that raw text search cannot.

| Need | Primary | Fallback |
|---|---|---|
| Find a function/symbol/usage in code | `mcp__codebase-rag__search_code` | `Grep` (only if RAG returns no hits or index is stale) |
| Recall a past project decision | `tausik_decisions_list` / `tausik_memory_search` (`type=convention/pattern`) | — |
| Cross-project pattern or gotcha | `tausik_memory_search` (the shared store is folded into the results) | — |
| Web lookup (docs, API, errors) | `WebFetch` | — |
| Understand the project structure | `tausik_status` + `tausik_roadmap` | `Glob` for raw file listing |

Run `mcp__codebase-rag__rag_status` once per session to confirm the index is fresh. If `chunks=0`, run `mcp__codebase-rag__reindex` before any `search_code` call.
"""

CURSOR_MCP_SETUP = """## Local MCP in Cursor (this workspace)

Bootstrap (`python bootstrap/bootstrap.py --ide cursor` or `--ide all`) generates:

- **`.cursor/mcp.json`** — TAUSIK MCP servers for Cursor (absolute paths to `.tausik/venv`, server entrypoints under **`.cursor/mcp/`**).
- **`.mcp.json` at repo root** — always points at **`.claude/mcp/`** (VS Code Claude Extension / shared); **Cursor reads `.cursor/mcp.json`** for project-scoped tools.

If tools do not appear: open **Cursor Settings → MCP**, ensure project MCP is enabled, then **Developer: Reload Window**.

Servers: `tausik-project`, optional `codebase-rag`.

"""

MULTIMODEL_NOTE = """## Are you a non-Claude agent? (GPT-5.5, Composer, Codex, OpenCode, Gemini …)

TAUSIK is model-agnostic, but the surface you actually use differs from Claude Code:

- **MCP tools first.** Every quality gate (QG-0, QG-2, session limit, dead-end tracking) is enforced inside the `tausik-project` MCP server. Calling MCP tools gives you the same hard guarantees Claude Code gets. Bash CLI is a fallback only when MCP is unreachable.
- **Slash commands may not exist.** If your host doesn't expand `/start`, `/plan`, `/ship`, `/end`, open the matching `harness/skills/<name>/SKILL.md` and execute its numbered steps. Skills are written as procedures, not host-specific magic.
- **PreToolUse hooks may not be deployed here.** The notice at the top of this file says whether they are, counted from this host's profile. Where they are not, `task_gate.py` does not protect Rule 1 ("no code without a task") and you self-enforce: always call `tausik_task_start` (or `tausik_task_quick`) before any Edit/Write. The reason is that TAUSIK generates no hooks payload for some hosts — what a given host is capable of accepting is a separate question, and not one this file answers.
- **Don't write to `~/.claude/`.** It is a Claude-specific profile. Use the project DB (`.tausik/tausik.db`) via `tausik_memory_*` MCP tools, or the path under `CLAUDE_PLUGIN_DATA` if your host sets it.
- **Verify-First Contract is universal.** Run `tausik_verify` before `tausik_task_done_v2`, regardless of model. The 60s per-MCP-tool timeout that VS Code Claude Extension applies is the strictest case; if you keep heavy work inside `verify`, every other host stays in budget too.
- **`task_done_v2` over `task_done`.** When the MCP server publishes both, prefer `tausik_task_done_v2` — its structured JSON response (`stage`, `gate_results`, `blocking_failures`) is much friendlier to non-Claude tool-use loops that expect typed payloads.
"""

RESPONSE_LANGUAGE = """## Response Language

Always respond in the user's language.
"""

# Output-economy directive, appended only when `output_mode: caveman`. Inspired by the
# caveman skill (github.com/JuliusBrussee/caveman); we ship the idea as our own rule
# rather than installing its hooks (which would collide with TAUSIK's SessionStart hook
# and settings.json ownership).
#
# This block is INJECTED EVERY SESSION, so its own length is a token line-item: a long
# directive would cost more input than the terse output saves. CAVEMAN_DIRECTIVE_MAX_CHARS
# caps it, enforced by tests. caveman's own "~65% output reduction" is THEIR figure and is
# unmeasured in our harness — we do not restate it as our result.
CAVEMAN_DIRECTIVE = """## Output economy (caveman mode)

Answer in terse, telegraphic prose — drop articles/filler, keep the meaning. \
Inspired by the caveman skill (github.com/JuliusBrussee/caveman).
- SHAPE, in this order, empty parts omitted: done → verified by → left → your call.
- KEEP BYTE-EXACT (never compress): code, shell commands, tool output, file paths, error messages.
- KEEP FULL PROSE (never compress): acceptance-criteria evidence, decisions, SPEC/ADAPT, \
task logs, handoffs — future agents parse these verbatim.
- EXCEPTIONS (named, not judged): explanation requested; destructive action needs confirmation; \
three failed debugging turns → state the assumption, ask one question; genuine ambiguity → one \
question; the rule would delete the answer itself.
- PRE-SEND: delete intent announcements, closing recaps, side branches, empty hedges; \
first line = next action, last line = current state.
"""

# Hard ceiling on the injected directive. If a future edit bloats it, the guard fails —
# the whole point of the mode is fewer tokens, and a fat directive defeats it. 700 held
# brevity alone; the response contract (shape, named exceptions, pre-send check) measures
# 888 and the ceiling moves to that measured value, not to a round number.
CAVEMAN_DIRECTIVE_MAX_CHARS = 888

# The heading that marks the directive inside a generated rules file.
CAVEMAN_DIRECTIVE_MARKER = "## Output economy (caveman mode)"


def warn_output_mode_not_applied(path: str, output_mode: str) -> bool:
    """Warn when a requested output_mode cannot reach an already-existing rules file.

    Every rules generator is preserve-if-exists, so flipping `output_mode: caveman` on a
    project that was bootstrapped once changes nothing on disk. Staying quiet about that
    would leave the user believing compression is on while bootstrap prints "Done!" — a
    silent no-op, the failure class this framework refuses to ship.

    We warn rather than rewrite: the file is the user's. Returns True when a warning fired.
    """
    if (output_mode or "off").strip().lower() != "caveman":
        return False
    try:
        with open(path, "r", encoding="utf-8") as f:
            existing = f.read()
    except OSError:
        return False
    if CAVEMAN_DIRECTIVE_MARKER in existing:
        return False
    print(
        f"  WARNING: output_mode=caveman is set, but {os.path.basename(path)} already exists "
        f"and has no '{CAVEMAN_DIRECTIVE_MARKER}' section — bootstrap preserves existing rules "
        f"files, so the mode was NOT applied. Delete {path} and re-run, or paste the directive "
        "in by hand."
    )
    return True


DYNAMIC_BLOCK = """<!-- DYNAMIC:START -->
<!-- DYNAMIC:END -->
"""


def build_header(project_name: str, stacks: list[str], agent_name: str) -> str:
    """Header + project metadata. agent_name goes into the opening sentence."""
    stack_str = ", ".join(stacks) if stacks else "not detected"
    return (
        f"You are {agent_name} working on this project. Follow these instructions strictly.\n\n"
        f"## Project: {project_name}\n\n"
        f"Stack: {stack_str}\n"
        f"Framework: [TAUSIK](https://github.com/Kibertum/tausik-core) — AI agent governance implementing [SENAR v1.3](https://senar.tech)\n"
    )


def build_skills_section(ide_subdir: str) -> str:
    return (
        f"## Skills\n\n"
        f"After bootstrap, **13 core skills** ship from `harness/skills/` and are always available: "
        f"`/start`, `/end`, `/checkpoint`, `/plan`, `/task`, `/ship`, `/commit`, "
        f"`/review`, `/test`, `/debug`, `/explore`, `/interview`, `/reason`, `/i-have-adhd`.\n\n"
        f"**25+ official/vendor skills** are opt-in via `python .tausik-lib/bootstrap/bootstrap.py "
        f"--include-official` (full bundle) or `tausik skill install <name>` (per skill) from the "
        f"`tausik-skills` repo or `skills-official/`: `/audit`, `/zero-defect`, `/markitdown`, "
        f"`/excel`, `/pdf`, `/docs`, `/security`, `/onboard`, `/retro`, `/ultra`, `/jira`, "
        f"`/bitrix24`, `/sentry`, ... See `{ide_subdir}/references/skill-catalog.md`.\n\n"
        f"**Security — external skill repos are arbitrary code + instructions.** "
        f"Adding a repo clones remote content; installing may run pip/scripts. "
        f"Only use `tausik skill repo add <url>` for trusted sources; third-party URLs "
        f"require `--force` after review. See `docs/en/vendor-skills.md` and "
        f"`docs/en/skill-ecosystem.md`.\n\n"
        f"When a user request matches a trigger keyword for a not-installed skill, proactively suggest installing it.\n"
    )


def build_roles_section(ide_subdir: str) -> str:
    return (
        f"## Roles\n\n"
        f"Role field is free text. Common: `developer`, `architect`, `qa`, `tech-writer`, `ui-ux`.\n"
        f"Role profiles live in `{ide_subdir}/roles/<role>.md`.\n"
    )


def _load_ide_override(ide: str | None) -> str:
    """Load IDE-specific override block from harness/overrides/{ide}/rules.md.

    Returns "" if `ide` is None/unknown or the override file is missing.
    Wrapped so a missing file never breaks bootstrap.
    """
    if not ide:
        return ""
    here = os.path.dirname(os.path.abspath(__file__))
    candidate = os.path.normpath(os.path.join(here, "..", "harness", "overrides", ide, "rules.md"))
    if not os.path.isfile(candidate):
        return ""
    try:
        with open(candidate, encoding="utf-8") as f:
            body = f.read().strip()
        if not body:
            return ""
        # No leading newline: the parts are joined with a newline already, and
        # the extra one rendered as the generated file's only double blank line.
        return f"\n## IDE-specific overrides ({ide})\n\n{body}\n"
    except OSError:
        return ""


def build_full_body(
    project_name: str,
    stacks: list[str],
    agent_name: str,
    ide_subdir: str,
    ide: str | None = None,
    context_tier: str = "standard",
    output_mode: str = "off",
    project_dir: str | None = None,
) -> str:
    """Compose the shared body used by all IDE-specific generators.

    Caller prepends its own file-level header (e.g. '# CLAUDE.md'). When
    `ide` is supplied, the matching `harness/overrides/<ide>/rules.md`
    block (if present) is appended right before the dynamic state block —
    closing the audit gap r14-overrides-integration where these files
    existed but were never wired into the generated CLAUDE.md/.cursorrules
    /QWEN.md.

    ``context_tier`` (from ``.tausik/config.json``) selects how verbose the
    generated rules are: ``minimal`` (short), ``standard`` (default), or
    ``full`` (standard + extra pointers for framework work).

    ``output_mode`` is ORTHOGONAL to ``context_tier``: the tier sizes the INPUT
    rules, ``output_mode: caveman`` compresses the agent's OUTPUT. When ``caveman``,
    the CAVEMAN_DIRECTIVE is appended in every tier (it applies regardless of how
    verbose the rules themselves are). Any non-``caveman`` value is a no-op.
    """
    tier = (context_tier or "standard").strip().lower()
    if tier not in ("minimal", "standard", "full"):
        tier = "standard"

    caveman = (output_mode or "off").strip().lower() == "caveman"

    header = build_header(project_name, stacks, agent_name)
    _profile = profile_dir_for(project_dir, ide)
    enforcement = build_enforcement_notice(_profile)
    # The per-host sentence answers 'checks or instructions'. This answers
    # WHICH — on a host without a real-time mechanism the answer differs by
    # rule, and one sentence cannot carry two answers. Empty where every rule
    # is intercepted, so it never becomes a paragraph readers learn to skip.
    rule_notice = render_rule_notice(_profile)
    # The rule paragraph subsumes the host sentence when it carries the
    # mechanism fact itself — one paragraph, not two, on every turn.
    if rule_notice.startswith("**NO REAL-TIME MECHANISM"):
        enforcement = ""
    if tier == "minimal":
        parts = [
            header,
            enforcement,
            rule_notice,
            HARD_CONSTRAINTS,
            MINIMAL_WORKFLOW,
            MINIMAL_MEMORY,
            MINIMAL_COMPACTION,
            MINIMAL_COMMANDS,
            RESPONSE_LANGUAGE,
            CAVEMAN_DIRECTIVE if caveman else "",
            MINIMAL_TIER_FOOTER,
            DYNAMIC_BLOCK,
        ]
        return "\n".join(p for p in parts if p)

    parts = [
        header,
        enforcement,
        rule_notice,
        HARD_CONSTRAINTS,
        WORKFLOW,
        TOOL_ROUTING,
        MEMORY,
        COMPACTION_CONTRACT,
        SENAR_RULES,
        COMMANDS,
        QUALITY_GATES,
        build_skills_section(ide_subdir),
        build_roles_section(ide_subdir),
        MULTIMODEL_NOTE,
        RESPONSE_LANGUAGE,
        _load_ide_override(ide),
    ]
    if ide == "cursor":
        idx = parts.index(MULTIMODEL_NOTE)
        parts.insert(idx, CURSOR_MCP_SETUP)
    if tier == "full":
        parts.append(FULL_TIER_NOTE)
    if caveman:
        parts.append(CAVEMAN_DIRECTIVE)
    parts.append(DYNAMIC_BLOCK)
    return "\n".join(p for p in parts if p)
