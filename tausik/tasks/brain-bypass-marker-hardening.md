---
slug: brain-bypass-marker-hardening
title: "HIGH: harden 'confirm: cross-project' bypass detection"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: brain-decide-auto-route
scope: "scripts/hooks/_common.py, scripts/hooks/memory_pretool_block.py, scripts/hooks/brain_search_proactive.py, tests/test_hooks_common.py (new), tests/test_memory_pretool_block_hook.py (update), tests/test_brain_search_proactive_hook.py (update)"
scope_exclude: "UserPromptSubmit хуки (не используют bypass markers), будущие hooks — фикс наследуется через helper автоматически"
relevant_files:
  - "scripts/hooks/_common.py"
  - "scripts/hooks/memory_pretool_block.py"
  - "scripts/hooks/brain_search_proactive.py"
  - "tests/test_hooks_common.py"
  - "tests/test_memory_pretool_block_hook.py"
  - "tests/test_brain_search_proactive_hook.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-24T11:04:39Z"
---

## Goal

Закрыть substring-ловушку: bypass должен срабатывать только когда marker на отдельной строке в последнем user-turn, не внутри fenced code блока (чтобы цитирование текста хука не отключало guard случайно)

## Acceptance Criteria

AC1: Helper в scripts/hooks/_common.py: last_user_prompt_text(transcript_path) — возвращает текст последнего user-turn или ''.
AC2: Helper в scripts/hooks/_common.py: marker_present_anchored(text, marker) — True только если marker найден как отдельная строка (не substring) И не внутри fenced code блока (```).
AC3: memory_pretool_block.py использует helper — старый substring-поиск удалён.
AC4: brain_search_proactive.py использует helper — тот же bypass pattern защищён.
AC5: Тест: marker внутри fenced ```code``` блока → False.
AC6: Тест: marker как substring внутри обычного текста → False.
AC7: Тест: marker на отдельной строке → True (с leading/trailing whitespace, mixed case).
AC8: Регрессия: все тесты test_memory_pretool_block_hook.py + test_brain_search_proactive_hook.py зелёные.
AC9: ruff + mypy scripts/ clean.

## Plan

## Rollback

## Journal

- 2026-04-24T11:01:17Z [implementation] — Root cause: оригинальный _bypass_present() в обоих хуках был substring-поиском `_BYPASS_MARKER in prompt.lower()`. Пользователь, цитирующий текст ошибки хука в своём вопросе (даже как объяснение, что это такое), автоматически отключал guard на следующий ход. Особо уязвим сценарий когда user вставляет hook stderr в fenced ```code``` блок чтобы показать что он получил — substring match не отличает чистый вопрос от намеренного обхода.
- 2026-04-24T11:01:22Z [implementation] — AC verified: 1. scripts/hooks/_common.last_user_prompt_text() extracted ✓ 2. marker_present_anchored() — line-by-itself outside fences ✓ 3. memory_pretool_block.py uses helper, old _last_user_prompt deleted ✓ 4. brain_search_proactive.py uses same helper — same vuln class covered ✓ 5. Fenced ```code``` с marker → False (test_marker_inside_fenced_code_block_does_NOT_bypass) ✓ 6. Substring в тексте → False (test_substring_marker_does_NOT_bypass) ✓ 7. Marker на отдельной строке + whitespace + mixed case → True (22 теста в test_hooks_common.py) ✓ 8. Регрессия 96/96 (test_hooks_common + test_memory_pretool_block_hook + test_brain_search_proactive_hook + test_memory_posttool_audit_hook) ✓ 9. ruff + mypy scripts/ clean ✓
