---
slug: v15p-agents-md-bootstrap
title: "[P2] T10: Генерация AGENTS.md в bootstrap"
status: done
epic: v15-polish
story: v15p-agent-ux
complexity: simple
role: developer
stack: python
tier: light
call_budget: 25
defect_of: null
scope: "scripts/project_cli_extra.py (cmd_update_claudemd → multi-target + _write_dynamic_section helper), tests/test_update_claudemd_agents.py, docs note"
scope_exclude: "QWEN.md dynamic refresh (separate); bootstrap generate_agents_md already wired (no change); .cursorrules"
relevant_files:
  - "scripts/claudemd_writer.py"
  - "scripts/project_cli_extra.py"
  - "tests/test_update_claudemd_agents.py"
  - "docs/en/cli.md"
  - "docs/ru/cli.md"
  - README.md
  - "docs/_generated/constants.json"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-14T17:55:32Z"
---

## Goal

Bootstrap генерирует AGENTS.md наравне с CLAUDE.md/QWEN.md — закрытие риска №2 аудита (AGENTS.md как универсальный стандарт) и позиционирование «AGENTS.md compatible: static contract + TAUSIK runtime gates». AC: AGENTS.md рендерится из того же источника, что CLAUDE.md; dynamic-секция обновляется update_claudemd; задокументировано.

## Acceptance Criteria

AC1: bootstrap renders AGENTS.md from the same shared body as CLAUDE.md (already wired) — verified present. AC2: `tausik update-claudemd` refreshes the DYNAMIC:START section of AGENTS.md as well as CLAUDE.md (sibling at project root), so AGENTS.md no longer goes stale mid-session. AC3: update is best-effort per file — a missing AGENTS.md or absent marker is skipped with a notice, never an error; --dry-run reports drift across both and exits 1 if any would change. AC4: covered by tests (both files updated; AGENTS.md absent → CLAUDE.md still updates; marker missing → skip-notice); filesize<400. AC5: documented.

## Plan

## Rollback

git revert; change is to one CLI handler — reverting restores CLAUDE.md-only update; no schema/state change.

## Journal

- 2026-06-14T17:55:11Z [implementation] — Found generate_agents_md already wired (bootstrap.py:184) + AGENTS.md shares build_full_body with CLAUDE.md (fresh AGENTS.md has DYNAMIC markers — verified in /tmp). Real gap: update_claudemd only refreshed CLAUDE.md. Fix: extracted claudemd_writer.apply_dynamic_section + resolve_sibling_targets; cmd_update_claudemd now loops [CLAUDE.md, AGENTS.md sibling], best-effort per file (marker-less file skipped with notice, --dry-run exits 1 on any drift). project_cli_extra.py 381→352. 7 tests. Dogfood root AGENTS.md is legacy (no marker) → gracefully skipped. Docs updated en/ru.
- 2026-06-14T17:55:32Z [implementation] — AC1: ✓ AGENTS.md renders from same build_full_body as CLAUDE.md (bootstrap.py:184 already wired); fresh AGENTS.md has DYNAMIC markers — verified in /tmp/agmd. AC2: ✓ update-claudemd now refreshes AGENTS.md sibling too via resolve_sibling_targets+apply_dynamic_section loop — test_includes_agents_md_sibling + test_replaces_between_markers. AC3: ✓ best-effort per file: marker-less/absent AGENTS.md skipped with notice (dogfood smoke showed exactly this), --dry-run prints diff + exits 1 on drift — test_no_marker_is_skipped_not_error + test_dry_run_does_not_write. AC4: ✓ 7 tests; project_cli_extra.py 352<400, claudemd_writer.py 73. AC5: ✓ docs en/ru updated. Domain: on a fresh install both onboarding files stay in lockstep each session; legacy marker-less files degrade gracefully. Negative: missing end-marker → appends one; up-to-date file → no write; AGENTS.md absent → CLAUDE.md still updates.
