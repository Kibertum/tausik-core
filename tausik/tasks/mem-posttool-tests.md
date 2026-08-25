---
slug: mem-posttool-tests
title: "Тесты PostToolUse memory-audit hook"
status: done
epic: memory-discipline-hardening
story: memory-post-write-audit
complexity: simple
role: qa
stack: python
tier: null
call_budget: null
defect_of: null
scope: "tests/test_memory_markers.py (новый), tests/test_memory_posttool_audit_hook.py (новый)"
scope_exclude: "Не трогать scripts/hooks/memory_markers.py, memory_posttool_audit.py. Не рефакторить существующие hook-тесты."
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-22T23:07:39Z"
---

## Goal

Pytest: hook детектит project markers (positive cases), не даёт false positive на легитимные cross-project записи (e.g. "prefers Russian responses"). Покрытие всех паттернов из markers-модуля.

## Acceptance Criteria

1. tests/test_memory_markers.py создан — unit-тесты на detect_markers: (a) abs_path Windows + Unix; (b) slug 3+ parts; (c) tausik_cmd; (d) src_file; (e) Negative: cross-project preferences (Russian, pytest, VSCode, Docker) → []; (f) Dedup: повторяющийся slug → 1 match; (g) Empty text → []; (h) Perf 47 КБ < 50 ms; (i) Match NamedTuple поля kind/match/span. 2. tests/test_memory_posttool_audit_hook.py создан — integration-тесты на hook через subprocess (pattern из test_user_prompt_submit_hook.py): (a) Positive: файл с markers → stderr 'AUDIT' + список matches + hint; (b) Negative: файл с 'user prefers Russian' → exit 0 silent; (c) tool_name=Bash → exit 0 silent; (d) file_path вне memory/ → exit 0 silent; (e) Файл не существует → exit 0; (f) Non-TAUSIK project → exit 0; (g) TAUSIK_SKIP_HOOKS=1 → exit 0; (h) Malformed stdin → exit 0; (i) MultiEdit + Edit — оба аудируются. 3. TestSettingsGeneration::test_claude/qwen — bootstrap регистрирует memory_posttool_audit.py в PostToolUse matcher Write|Edit|MultiEdit. 4. Все тесты проходят; итог suite > 1130 (pre-existing не ломаются).

## Plan

## Rollback

## Journal

- 2026-04-22T23:04:59Z [implementation] — AC verified: (1) tests/test_memory_markers.py — 29 тестов: TestPositive (9 kind-detected параметризации + NamedTuple shape + sorting) + TestNegative (14 cross-project preferences, включая kebab-lookalike: 'prefers kebab-case variable names', 'use ts-node for scripts', 'switch-case is fine', 'double-quoted') + TestDedup (repeated + different slugs) + TestEdgeCases (empty, whitespace, PATTERNS shape) + TestPerformance (47 КБ < 50 ms) ✓. (2) tests/test_memory_posttool_audit_hook.py — 21+ тест: TestDetectionEmitsWarning (markers + 3 tool parametrize + truncation >5 markers с '...and N more' + binary content b'\xff\xfe' с slug) + TestSilentOnCleanWrites + TestNonAuditedPaths (outside memory + 4 non-write tools) + TestGraceful (missing file, non-TAUSIK, SKIP_HOOKS, malformed stdin, file_path не string, tool_input missing/null/string) + TestSettingsGeneration (Claude + Qwen) ✓. (3) Bootstrap registers memory_posttool_audit.py в PostToolUse matcher Write|Edit|MultiEdit для обоих IDE ✓. (4) Full suite: 1183 passed (baseline 1130 → +53 новых) ✓. Review через general-purpose subagent нашёл 4 gap: truncation, binary content, missing tool_input variants, public alias — все закрыты. Bonus: is_in_claude_memory public alias добавлен в memory_pretool_block.py для стабильного cross-hook import.
