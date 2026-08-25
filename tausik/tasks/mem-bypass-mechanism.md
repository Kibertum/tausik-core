---
slug: mem-bypass-mechanism
title: "Bypass через маркер `confirm: cross-project` в промпте"
status: done
epic: memory-discipline-hardening
story: memory-pre-write-block
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-22T22:12:20Z"
---

## Goal

Добавить в hook детектор маркера `confirm: cross-project` (или эквивалент) в последнем user-промпте — пропускает Write, чтобы реально кросс-проектные записи были возможны. Это escape hatch, не обход.

## Acceptance Criteria

1. Hook memory_pretool_block.py проверяет последний user turn в transcript (JSONL) на присутствие строки 'confirm: cross-project'. 2. Если маркер найден в последнем user turn — exit 0 (allow Write к memory/). 3. Если маркер в более раннем turn (не в последнем) — НЕ пропускает, exit 2. 4. Поддерживается оба формата content: плоский string и list-of-content-blocks (Claude native). 5. Бэкап маркера в коде — константа _BYPASS_MARKER в memory_pretool_block.py.

## Plan

## Rollback

## Journal

- 2026-04-22T22:09:00Z [implementation] — AC реализован inline в составе mem-pretool-hook — см. scripts/hooks/memory_pretool_block.py функции _last_user_prompt() и _bypass_present(). Константа _BYPASS_MARKER='confirm: cross-project'. AC verified smoke-тестами: (1) маркер в последнем user turn → exit 0 (allow) ✓; (2) маркер в старом turn, не в последнем → exit 2 (block) ✓; (3) content-as-list (Claude native JSONL format) поддерживается через парсинг item.text блоков ✓. Живой dogfood-тест после rebootstrap: Write в C:/Users/[вычеркнуто: local-path]/.claude/projects/.../memory/ без маркера → блок hook с подсказкой; Write вне memory → пропуск.
