---
slug: mem-pretool-hook
title: "PreToolUse hook: блок Write к ~/.claude/projects/*/memory/"
status: done
epic: memory-discipline-hardening
story: memory-pre-write-block
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/hooks/memory_pretool_block.py (новый), bootstrap/bootstrap_templates.py (добавить регистрацию hook)"
scope_exclude: "Не трогать task_gate.py и другие существующие hooks. Не менять severity/триггеры других hooks. Comprehensive-тесты — отдельная задача mem-pretool-tests."
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-22T20:34:52Z"
---

## Goal

Реализовать PreToolUse hook, который блокирует Write к путям ~/.claude/projects/*/memory/ из активного TAUSIK-проекта. Сообщение должно направлять к `tausik memory add` для проектных записей. Hook регистрируется в settings.json при bootstrap.

## Acceptance Criteria

1. Hook scripts/hooks/memory_pretool_block.py блокирует PreToolUse для Write/Edit/MultiEdit если tool_input.file_path находится под ~/.claude/projects/*/memory/. 2. Блок возвращает exit 2 + stderr с подсказкой "это проектное знание? → tausik memory add; cross-project preference? → ответь user явно с маркером `confirm: cross-project`". 3. При tool_input.file_path вне memory/ — exit 0 (allow). 4. При отсутствии .tausik/tausik.db (не-TAUSIK проект) — exit 0. 5. При ошибке парсинга stdin/JSON — exit 0 (graceful degradation, не падает). 6. Hook регистрируется в bootstrap_templates.py для settings.json PreToolUse hooks. 7. Негативный: hook НЕ блокирует если pattern `confirm: cross-project` присутствует в последнем user-промпте (см. mem-bypass-mechanism).

## Plan

## Rollback

## Journal

- 2026-04-22T20:26:32Z [implementation] — Продолжаю после краша прошлой сессии. План: (1) scripts/hooks/memory_pretool_block.py — PreToolUse hook; path-check ~/.claude/projects/*/memory/; bypass-marker 'confirm: cross-project' из transcript_path (последний user turn). (2) Регистрация в bootstrap/bootstrap_generate.py и bootstrap/bootstrap_qwen.py (scope в задаче указывает bootstrap_templates.py, но actual hook registration находится в generate.py — поправка scope по факту).
- 2026-04-22T20:31:48Z [implementation] — AC verified: (1) Write/Edit/MultiEdit к C:/Users/[вычеркнуто: local-path]/.claude/projects/d--Work-Personal-claude/memory/foo.md → exit=2, stderr с guidance ✓. (2) Message содержит 'tausik memory add' + 'confirm: cross-project' маркер ✓. (3) file_path вне memory (README.md, settings.json в projects/X/) и tool_name=Bash → exit=0 ✓. (4) CLAUDE_PROJECT_DIR=d:/tmp без .tausik/tausik.db → exit=0 ✓. (5) malformed JSON, empty stdin, array → exit=0 graceful ✓. (6) Регистрация в bootstrap/bootstrap_generate.py PreToolUse + bootstrap/bootstrap_qwen.py PreToolUse (scope задачи указывал bootstrap_templates.py, но фактическая генерация settings.json находится в *_generate.py — поправка scope) ✓. (7) Bypass маркер 'confirm: cross-project' в последнем user-turn транскрипта (плоский string + list-of-text-blocks) → exit=0; маркер только в старом turn → exit=2 ✓.
- 2026-04-22T20:31:52Z [implementation] — Gates: ruff=PASS (scripts/hooks/memory_pretool_block.py, bootstrap/bootstrap_generate.py, bootstrap/bootstrap_qwen.py). Pytest: 1105 passed, 2 skipped в 175s.
