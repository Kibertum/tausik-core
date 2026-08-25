---
slug: mem-pretool-tests
title: "Тесты PreToolUse memory-block hook"
status: done
epic: memory-discipline-hardening
story: memory-pre-write-block
complexity: simple
role: qa
stack: python
tier: null
call_budget: null
defect_of: null
scope: "tests/test_memory_pretool_block_hook.py (новый)"
scope_exclude: "Не трогать scripts/hooks/memory_pretool_block.py (реализация верифицирована в mem-pretool-hook). Не менять bootstrap — только assert-тесты. Не добавлять параметризацию symlinks (out-of-scope для Windows deployment)."
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-22T22:41:53Z"
---

## Goal

Pytest: hook блокирует Write к project/memory/, пропускает non-memory пути, пропускает при confirm-маркере. Edge cases: symlinks, относительные пути.

## Acceptance Criteria

1. tests/test_memory_pretool_block_hook.py создан, следует паттерну test_user_prompt_submit_hook.py (helper _run(tmp_path, stdin) через subprocess.run Python на hook с временным CLAUDE_PROJECT_DIR). 2. Блок-сценарии: Write/Edit/MultiEdit c file_path под ~/.claude/projects/*/memory/ и под вложенными subdir → exit=2, stderr содержит 'BLOCKED' + 'tausik memory add' + 'confirm: cross-project'. 3. Пропуск-сценарии: file_path вне memory (README.md; projects/X/settings.json sibling; абсолютный путь вне ~/.claude/); tool_name=Bash; отсутствие .tausik/tausik.db; TAUSIK_SKIP_HOOKS=1 → все exit=0. 4. Graceful: malformed JSON, empty stdin, array вместо object, отсутствие tool_input → exit=0. 5. Bypass: последний user turn с 'confirm: cross-project' в string content И в list-of-text-blocks content → exit=0; маркер Case-Insensitive ('CONFIRM: Cross-Project') → exit=0; маркер только в старом turn (не последнем) → exit=2 (NEGATIVE). 6. tool_result-turns пропускаются: последний user event содержит list-of-tool_result, ранее в транскрипте реальный user prompt с маркером → exit=0 (реальный сценарий Claude Code). 7. TestSettingsGeneration: bootstrap_generate.generate_settings_claude и bootstrap_qwen.generate_settings_qwen регистрируют 'memory_pretool_block.py' под PreToolUse matcher Write|Edit|MultiEdit. 8. Все тесты проходят в tests/ без регрессий на существующих 1105 тестах.

## Plan

## Rollback

## Journal

- 2026-04-22T22:39:11Z [implementation] — AC verified: (1) tests/test_memory_pretool_block_hook.py создан, pattern _run/_setup_tausik скопирован из test_user_prompt_submit_hook.py ✓. (2) Блок-сценарии: TestBlocksMemoryWrites::test_blocks_tool_at_memory_root[Write|Edit|MultiEdit] + test_blocks_nested_subdir + test_blocks_raw_windows_backslash_path (Win32-only) + test_blocks_tilde_expanded_path — все exit=2, stderr с BLOCKED/tausik memory add/confirm: cross-project ✓. (3) Пропуск: TestAllowsNonMemoryPaths::test_allows_path_outside_memory[4 cases: README.md, sibling settings.json, plans/plan.md, ~/Documents] + test_allows_other_tool_names[Bash/Read/Grep/Glob/WebFetch] + TestAllowsOutsideTausik::test_allows_without_tausik_db + test_skip_hooks_env_var — все exit=0 ✓. (4) Graceful: TestGracefulMalformed::test_malformed_json + test_empty_stdin + test_array_instead_of_object + test_missing_tool_input + test_file_path_not_string — exit=0 ✓. (5) Bypass: TestBypassMarker::test_marker_in_last_user_turn_as_string + as_list + case_insensitive + test_marker_only_in_earlier_turn_blocks (NEGATIVE, exit=2) + test_missing_transcript_file — AC ✓. (6) tool_result: TestSkipsToolResultTurns::test_tool_result_turn_is_not_the_bypass_source + test_no_real_user_turns_only_tool_results ✓. (7) TestSettingsGeneration::test_claude_settings_registers_hook + test_qwen_settings_registers_hook — проверен matcher Write|Edit|MultiEdit ✓. (8) Регрессий нет: pre-existing 1105 тестов + 25 новых = 1130 passed в full-suite; после добавления +5 edge-cases (review gaps от sub-agent: raw Windows backslash, tilde expansion, mixed-list content, assistant-turn-ignored, corrupt JSONL) итого 30/30 зелёных в изолированном прогоне. Review через general-purpose subagent: подтвердил отсутствие tautology/fake-test патернов, правильность negative-test семантики, указал на gaps — все 5 закрыты.
