---
slug: stack-registry-loader
title: "scripts/stack_registry.py — built-in + user loader"
status: done
epic: v16-plugin-arch-and-docs
story: plugin-foundation
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/stack_registry.py (NEW)"
scope_exclude: "stacks/<name>/stack.json (отдельная задача Story 2), consumers (Story 3), тесты (отдельная задача stack-registry-tests)"
relevant_files:
  - "scripts/stack_registry.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-25T16:38:16Z"
---

## Goal

Implement scripts/stack_registry.py with StackRegistry class. Methods: load_builtin(stacks_dir), load_user(user_stacks_dir), all_stacks() → frozenset, signatures_for(name), extensions_for(name), gates_for(name), guide_path_for(name). Loader scans <dir>/<stack_name>/stack.json, validates via schema, accumulates into registry. User stacks deep-merge over built-in (via 'extends' field). null gate values disable. Cached on first import; explicit reload() for tests.

## Acceptance Criteria

1. scripts/stack_registry.py создан с классом StackRegistry.
2. Методы: load_builtin(stacks_dir), load_user(user_stacks_dir), all_stacks() -> frozenset[str], signatures_for(name), extensions_for(name), filenames_for(name), path_hints_for(name), gates_for(name), guide_path_for(name).
3. Loader сканирует <dir>/<stack_name>/stack.json, валидирует через stack_schema.validate_decl, накапливает в registry. Malformed JSON → log warning + skip (не crash).
4. User stacks deep-merge поверх built-in через 'extends' поле (builtin:NAME). null gate values отключают inherited gate. extensions_extra additive (не заменяет, добавляет к extends target).
5. Cache: первый импорт строит registry, повторные load_builtin/load_user обновляют. Метод reload() для тестов.
6. Unknown 'extends' target (нет такого built-in) → log warning + skip (или error — задокументировать выбор).
7. signatures_for возвращает list of {file, type, keyword} dicts (готовый формат для bootstrap_config).
8. extensions_for возвращает frozenset[str] (готовый формат для _EXT_TO_STACKS).
9. all_stacks возвращает frozenset[str] всех загруженных имён.
10. Filesize: stack_registry.py под 400 строк.

## Plan

## Rollback

## Journal

- 2026-04-25T16:38:11Z [implementation] — AC verified: 1. ✓ scripts/stack_registry.py создан, класс StackRegistry. 2. ✓ Методы: load_builtin, load_user, all_stacks, signatures_for, extensions_for, filenames_for, path_hints_for, gates_for, guide_path_for, reload, default_registry. 3. ✓ Loader сканирует <dir>/<name>/stack.json, валидирует через validate_decl, malformed → log+skip, errors аккумулируются в self.errors. 4. ✓ Deep-merge: extensions_extra additive, null gate disable, key override; smoke test {'pytest':None,'ruff':{}} + extensions_extra=['.pyi'] → gates={ruff}, ext=[.py,.pyi]. 5. ✓ _resolved кеш сбрасывается на load_*, метод reload(). 6. ✓ Unknown extends target → warning + skip, error в self.errors. 7. ✓ signatures_for возвращает list[{file,type,keyword?}]. 8. ✓ extensions_for → frozenset[str]. 9. ✓ all_stacks → frozenset[str]. 10. ✓ Filesize: 293 строки (<400). Smoke-tests 5 cases all pass.
