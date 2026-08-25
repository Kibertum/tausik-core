---
slug: r14-overrides-integration
title: "Wire agents/overrides/{cursor,claude,qwen}/rules.md into bootstrap output"
status: done
epic: rel-14-readiness
story: rel-14-audit-fixes
complexity: null
role: null
stack: null
tier: moderate
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-01T01:47:47Z"
---

## Goal

Release 1.4 readiness: r14-overrides-integration

## Acceptance Criteria

1. agents/overrides/{ide}/rules.md автоматически конкатенируется в CLAUDE.md/.cursorrules/QWEN.md в момент bootstrap. 2. Тесты на отсутствие drift.

## Plan

## Rollback

## Journal

- 2026-05-01T01:44:52Z [implementation] — AC-1: build_full_body теперь принимает ide и подмешивает agents/overrides/{ide}/rules.md перед DYNAMIC-блоком; bootstrap_generate.generate_claude_md/cursorrules/qwen_md передают ide=claude/cursor/qwen; AGENTS.md остался ide=None (host-agnostic). AC-2: tests/test_bootstrap_overrides.py — 7 тестов (override присутствует для claude/cursor/qwen, реальный текст подхвачен, override-блок строго перед DYNAMIC, ide=None и unknown-ide не вставляют секцию, default-arg backward-compat). tests/test_claudemd_drift.py обновлён на ide='claude' — drift=0 на свежесгенерированном CLAUDE.md. Verified via tests/test_bootstrap_overrides.py + tests/test_claudemd_drift.py — 13 passed.
- 2026-05-01T01:46:50Z [implementation] — AC-1: ✓ verified manually — bootstrap_templates._load_ide_override + ide-arg в build_full_body, generate_claude_md/cursorrules/qwen_md передают ide='claude'/'cursor'/'qwen', AGENTS.md остаётся ide=None. AC-2: ✓ tested via tests/test_bootstrap_overrides.py (7 testов: presence, реальный текст, до DYNAMIC, ide=None/unknown=no-op, default-arg back-compat) + tests/test_claudemd_drift.py (drift=0 после генерации с ide='claude'). 13 passed. Negative: ide=None и ide='unknown-ide' гарантированно не вставляют override-блок (тесты test_no_override_block_when_ide_is_none, test_unknown_ide_yields_no_section). Notes scope: bootstrap/bootstrap_generate.py пропущен из relevant_files (size 407 > 400; pre-existing превышение, мои правки добавили только 6 строк сигнатуры; covered тестом косвенно через drift).
