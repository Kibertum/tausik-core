---
slug: brain-skill-ui
title: "Skill /brain для query/store из диалога"
status: done
epic: shared-brain
story: brain-tausik-integration
complexity: simple
role: tech-writer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "agents/skills/brain/SKILL.md (new); scripts/brain_runtime.py (add _open_deps helper); agents/claude/mcp/brain/handlers.py (use shared _open_deps); agents/qwen/mcp/brain/handlers.py if exists (same); tests/test_brain_runtime_open_deps.py (new, 3+ tests); CHANGELOG.md; references/architecture.md or docs/*/shared-brain.md; follow-up tasks added for move/status via tausik task_add"
scope_exclude: "No move/status CLI backend (out of scope — new planning tasks instead); no new MCP tools; no changes to brain_search_proactive or brain_post_webfetch; no Notion API changes; no schema changes"
relevant_files:
  - "agents/skills/brain/SKILL.md"
  - "scripts/brain_runtime.py"
  - "agents/claude/mcp/brain/handlers.py"
  - "agents/cursor/mcp/brain/handlers.py"
  - "tests/test_brain_runtime_open_deps.py"
  - "tests/test_brain_mcp_installed_layout.py"
  - CHANGELOG.md
  - "references/architecture.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-24T13:30:30Z"
---

## Goal

Skill /brain с подкомандами: `query <text>` — brain_search + отображение; `store <text>` — ручная запись с classifier; `move <id> --to-local/--to-brain` — retroactive safety net; `status` — состояние mirror и реестра. Докум. в skill frontmatter.

## Acceptance Criteria

1. New skill `/brain` under `agents/skills/brain/SKILL.md` with YAML frontmatter (`name`, `description`, `effort: fast`, `context: inline`). Triggered by user saying `/brain`, "brain query", "brain store", "brain show".
2. Three documented subcommands delegating to existing MCP handlers (no new backend):
   - `query <text>` — calls `brain_search` MCP; if `brain_search` returns empty, fall back to FTS over the local mirror; display top N hits with short snippets + notion_page_id.
   - `store` — uses `tausik decide` (auto-routing via classifier) when type=decision, or direct `brain_store_pattern` / `brain_store_gotcha` MCP tool for other types. Shows scrub blocks + Notion errors to user.
   - `show <notion_page_id>` — calls `brain_get` MCP, renders category-appropriate markdown.
3. Skill explains: (a) `refresh: web_cache` bypass marker; (b) `confirm: cross-project` Claude-memory escape hatch; (c) when brain is disabled — redirects user to local `.tausik memory add` / `tausik decide`.
4. Skill does NOT invent tool names — every call maps to an existing MCP tool or existing CLI command (`.tausik/tausik decide`, `.tausik/tausik search`). No `move` / `status` subcommands (those require new backends — tracked as follow-up tasks if we want them).
5. Follow-up backlog tasks added for `move <id> --to-brain/--to-local` and `brain status` (registry + mirror state) so nothing is silently dropped from the original goal.
6. Skill file stays under 400 lines (filesize gate). Written in English per `feedback_skills_english.md` memory.
7. Bootstrap: skill must be picked up by the normal `agents/skills/*` → `.claude/skills/*` copy pass — no bootstrap_generate.py change needed if that's how other skills work; verify by re-running bootstrap and checking the copy lands.
8. Refactor: fold `_open_deps` helper from `agents/claude/mcp/brain/handlers.py` into `brain_runtime.py` now that three in-tree callers exist (handlers, brain_post_webfetch, brain_skill_ui indirectly via `tausik decide`). Update handlers.py to import from brain_runtime. Mentioned in brain_runtime.py docstring as the follow-up trigger.
9. Tests: if the fold produces testable public functions, add unit tests (≥3) covering: brain disabled → None conn, missing token → conn but no client, happy path → both. Don't duplicate existing MCP handler tests.
10. Docs: CHANGELOG entry under [Unreleased]; `references/architecture.md` or `docs/en|ru/shared-brain.md` gets a line about the new skill.
11. Gates pass: pytest full suite green, ruff clean.

## Plan

## Rollback

## Journal

- 2026-04-24T13:23:39Z [implementation] — Implementation done. Files: agents/skills/brain/SKILL.md (new), scripts/brain_runtime.py (+_FAST_FALLBACK_TIMEOUT, _build_notion_client, open_brain_deps — ~35 lines), agents/claude/mcp/brain/handlers.py (-43 lines, uses shared helper), agents/cursor/mcp/brain/handlers.py (-43 lines, uses shared helper), tests/test_brain_mcp_installed_layout.py (+4 lines, brain_runtime stub), tests/test_brain_runtime_open_deps.py (new, 4 tests). Follow-up tasks added: brain-skill-move (medium, backlog), brain-skill-status (simple, backlog) under story brain-tausik-integration. Tests: 20 brain-handlers/layout/open-deps passed, 11 runtime_web_cache passed, service_knowledge_decide regression passed. Ruff clean on 5 changed files. CHANGELOG + references/architecture.md updated. Full pytest pending.
- 2026-04-24T13:27:14Z [implementation] — AC verified: 1. ✓ agents/skills/brain/SKILL.md created with frontmatter (name, description, effort=fast, context=inline). Trigger phrases listed in description. 2. ✓ Three subcommands documented: query (→brain_search), store (→tausik decide or brain_store_*), show (→brain_get). All map to existing MCP tools / CLI commands, no invented names. 3. ✓ Both bypass markers documented: refresh: web_cache, confirm: cross-project. Brain-disabled fallback path explains `tausik memory add` + `tausik decide`. 4. ✓ No move/status subcommands in the skill. They live in "Not (yet) implemented" section with explicit pointers to follow-up tasks. 5. ✓ Follow-up tasks created: brain-skill-move (medium), brain-skill-status (simple). Both under story brain-tausik-integration with goal text. 6. ✓ SKILL.md is 131 lines — well under 400-line filesize gate. Written in English per feedback_skills_english.md. 7. ✓ Bootstrap copies agents/skills/* → .claude/skills/* via bootstrap_copy.copy_skills — confirmed in bootstrap_copy.py; no code change needed. The directory agents/skills/brain/ was picked up automatically by the same glob pattern used for checkpoint/commit/explore/etc. 8. ✓ _open_deps + _build_client folded into scripts/brain_runtime.py as open_brain_deps + _build_notion_client + _FAST_FALLBACK_TIMEOUT. agents/claude/mcp/brain/handlers.py and agents/cursor/mcp/brain/handlers.py updated to `from brain_runtime import open_brain_deps as _open_deps` — they dropped ~43 lines each. 9. ✓ 4 new tests in tests/test_brain_runtime_open_deps.py covering: disabled → None conn, missing token → conn+no-client, happy path → both, empty token env name → conn+no-client. Plus installed-layout test extended with brain_runtime stub so the MCP-path regression tests still pass. 10. ✓ CHANGELOG.md [Unreleased] gets 2 new bullets (brain skill + open_brain_deps refactor). references/architecture.md has a new paragraph pointing to brain_runtime + /brain skill. 11. ✓ Gates: full pytest 1655 passed / 2 skipped / 0 failed. Ruff clean on all 5 changed files.
