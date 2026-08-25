---
slug: complexity-ceremony-set-misses-agents-md
title: "complexity understatement counts AGENTS.md as behaviour-bearing — the ceremony it exists to subtract"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: light
call_budget: 14
defect_of: null
scope: "scripts/complexity_understatement.py, scripts/claudemd_writer.py, tests/test_complexity_understatement.py"
scope_exclude: "gate_changelog config-driven changelog list (separate downstream concern, no live defect here), any gate/verify infra"
relevant_files:
  - "scripts/complexity_understatement.py"
  - "scripts/claudemd_writer.py"
  - "tests/test_complexity_understatement.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-25T06:15:36Z"
---

## Goal

complexity_understatement._CEREMONY_FILES hand-lists {changelog.md, changelog.ru.md, claude.md} as the clerical baseline every task touches, but omits AGENTS.md — which claudemd_writer.resolve_sibling_targets writes on EVERY `update-claudemd` as a synced sibling of CLAUDE.md, and which exists in this repo. So any task whose relevant_files include AGENTS.md (routine after a session/task-close update-claudemd) gets it counted as a real, behaviour-bearing file — reproducing the exact systematic complexity overcount the module was written to kill, live in this project. Fix by sourcing the sibling basename from the producer (a shared constant on claudemd_writer) instead of hand-listing it a second time, so the two lists can never drift.

## Acceptance Criteria

1. claudemd_writer exposes the sibling basename as a module-level constant (CLAUDEMD_SIBLING_BASENAME) and resolve_sibling_targets uses it — the name 'AGENTS.md' lives in exactly one place. 2. complexity_understatement derives its ceremony entry for the sibling from that constant (imported/lowercased), not a hand-typed literal, so a task whose relevant_files = [AGENTS.md] is NOT counted toward implied complexity. 3. Regression test: understatement() over a scope of ONLY ceremony files (both changelogs, CLAUDE.md, AGENTS.md, a generated constants file, a doc mirror pair) yields implied==0 (all subtracted). 4. Negative/boundary: a task touching AGENTS.md PLUS one real behaviour file counts exactly 1 implied file, not 2 — AGENTS.md must not inflate the count, and the real file must not be dropped. 5. Existing test_complexity_understatement.py stays green. 6. Full scoped verify green.

## Plan

## Rollback

## Journal

- 2026-07-25T06:15:13Z [implementation] — Fixed: promoted the sibling basename to CLAUDEMD_SIBLING_BASENAME='AGENTS.md' in claudemd_writer.py (single source), resolve_sibling_targets now reads it. complexity_understatement imports it (ImportError fallback keeps close crash-free) and adds _SIBLING.lower() to _CEREMONY_FILES, so AGENTS.md no longer counts as behaviour-bearing. Fixed the stale return-shape docstring (added declared_count). Tests: added TestBehaviourBearingFiles.test_agents_md_is_ceremony + test_the_sibling_ceremony_entry_comes_from_the_producer + parity assertion. Ran test_complexity_understatement.py (29 passed) and claudemd/sibling suite (52 passed).
- 2026-07-25T06:15:34Z [implementation] — AC verified: 1. ✓ claudemd_writer.py: CLAUDEMD_SIBLING_BASENAME='AGENTS.md' constant added; resolve_sibling_targets uses it — name in one place. test_the_sibling_ceremony_entry_comes_from_the_producer asserts it 2. ✓ complexity_understatement imports the constant (ImportError fallback) and adds _SIBLING.lower() to _CEREMONY_FILES; test_agents_md_is_ceremony_because_update_claudemd_writes_it: behaviour_bearing_files(['AGENTS.md'])==[] 3. ✓ test_a_task_of_pure_ceremony_is_never_understated over changelogs+CLAUDE.md+AGENTS.md returns None (implied==0) 4. ✓ behaviour_bearing_files(['AGENTS.md','scripts/real.py'])==['scripts/real.py'] — sibling not counted, real file kept (exactly 1) 5. ✓ test_complexity_understatement.py 29 passed; claudemd/sibling suite 52 passed 6. ✓ verify run #1300 exit=0, pytest scoped PASS
