---
slug: review-fix-c1-memory-guard-dir
title: "[C1 HIGH] Memory guard: directory-only path matched again"
status: done
epic: senar-verify-redesign
story: review-findings-fix
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/hooks/memory_pretool_block.py, tests/test_memory_pretool_block_hook.py"
scope_exclude: "scripts/hooks/memory_posttool_audit.py"
relevant_files:
  - "scripts/hooks/memory_pretool_block.py"
  - "tests/test_memory_pretool_block_hook.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-25T10:13:51Z"
---

## Goal

Multi-agent review нашёл регрессию в _is_in_claude_memory: `~/.claude/projects/abc/memory` (без trailing файла) больше НЕ блокируется — `os.path.normpath` режет trailing slash, потом split дает `['projects','abc','memory']`, и `[:-1]` исключает 'memory' из проверки. Старый guard `rest[1] == 'memory'` это ловил. Нужно: либо `'memory' in segments` (без [:-1]) с дополнительной защитой от basename 'memory' (без расширения), либо явный allowlist. Регрессия задачи hooks-pretool-block-path-patterns.

## Acceptance Criteria

1. _is_in_claude_memory возвращает True для пути-директории '~/.claude/projects/<slug>/memory' (basename = 'memory', без расширения, без trailing файла)
2. Регрессия: True для нормальных файлов '~/.claude/projects/<slug>/memory/foo.md' (path с файлом внутри memory dir)
3. Регрессия: False для файла 'memory.md' в любой точке (basename с расширением, не директория memory)
4. Регрессия: False для substring matches типа 'somememory/' и 'memoryold/' (segments check exact)
5. Новый тест: test_blocks_memory_dir_basename — file_path кончается ровно на 'memory' без расширения → блокировка
6. pytest tests/test_memory_pretool_block_hook.py + tests/test_memory_posttool_audit_hook.py зелёные
7. ruff clean

## Plan

## Rollback

## Journal

- 2026-04-25T10:13:47Z [implementation] — AC verified: ✓1 _is_in_claude_memory: 'memory' in segments (без [:-1] slice) ловит bare directory-form path ✓2 регрессия: nested file '.../memory/foo.md' всё ещё matches ✓3 'memory.md' не матчит (segment exact compare) ✓4 'somememory'/'memoryold' не матчит ✓5 test_blocks_memory_dir_basename_no_file покрывает 3 paths ✓6 pytest 61/61 passed (60→61 после +1) ✓7 ruff clean
