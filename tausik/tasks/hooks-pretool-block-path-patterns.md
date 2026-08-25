---
slug: hooks-pretool-block-path-patterns
title: "MEDIUM: расширить guard на все .claude/**/memory/ paths"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: brain-decide-auto-route
scope: "scripts/hooks/memory_pretool_block.py, tests/test_memory_pretool_block_hook.py"
scope_exclude: "scripts/hooks/memory_posttool_audit.py, scripts/hooks/memory_markers.py"
relevant_files:
  - "scripts/hooks/memory_pretool_block.py"
  - "tests/test_memory_pretool_block_hook.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-24T19:49:59Z"
---

## Goal

Текущий матч только projects/&lt;slug&gt;/memory/. Silently unguarded: ~/.claude/memory/ и ~/.claude/agents/*/memory/. Broaden prefix check до .claude/**/memory/ сегмента

## Acceptance Criteria

1. _is_in_claude_memory возвращает True для любого пути, где сегмент 'memory' является parent-директорией под <home>/.claude/ (не только под projects/)
2. Регрессия: существующие пути <home>/.claude/projects/<slug>/memory/* всё ещё True
3. Новые пути блокируются: <home>/.claude/memory/foo.md, <home>/.claude/agents/<name>/memory/bar.md
4. Ошибка/граничный случай: файл с именем memory.md (не под директорией memory/) НЕ блокируется (False)
5. Ошибка/граничный случай: путь без 'memory' сегмента не блокируется: <home>/.claude/projects/slug/notes/file.md → False
6. BLOCKED stderr сообщение обновлено: отражает .claude/**/memory/ pattern
7. memory_posttool_audit автоматически расширяется (он импортирует is_in_claude_memory)
8. Тесты в test_memory_pretool_block_hook.py покрывают новые сценарии + negative cases
9. pytest tests/test_memory_pretool_block_hook.py tests/test_memory_posttool_audit_hook.py проходят; ruff clean

## Plan

## Rollback

## Journal

- 2026-04-24T19:46:28Z [implementation] — AC verified: _is_in_claude_memory расширена — prefix теперь home/.claude/ (без /projects/), матч через split + 'memory' in segments[:-1]. BLOCKED stderr + docstring обновлены на .claude/**/memory/. memory_posttool_audit автоматически подхватывает (импортирует is_in_claude_memory). 3 новых положительных теста: bare_claude_memory, agents_memory, deeply_nested_memory. 3 новых negative: memory.md (файл не папка), somememory/, memoryold/. pytest 60/60 passed (pretool + posttool). ruff clean.
