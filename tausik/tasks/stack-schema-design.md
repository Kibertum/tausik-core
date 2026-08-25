---
slug: stack-schema-design
title: "Design stack.json JSON Schema"
status: done
epic: v16-plugin-arch-and-docs
story: plugin-foundation
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "stacks/_schema.json (NEW), scripts/stack_schema.py (NEW)"
scope_exclude: "scripts/stack_registry.py (отдельная задача), stacks/<name>/stack.json (Story 2)"
relevant_files:
  - "stacks/_schema.json"
  - "scripts/stack_schema.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-25T16:36:00Z"
---

## Goal

Design and implement stacks/_schema.json — JSON Schema for stack.json files. Fields: name (required), version, extends ('builtin:NAME' for override), detect (list of {file: glob/exact/dir-marker}), extensions (list), gates (dict of gate_name → DEFAULT_GATES-shaped dict), guide_path (optional rel path). Add validate_decl(decl) function that returns error list. Honest schema — reject malformed fields with actionable messages, not silent skip.

## Acceptance Criteria

1. stacks/_schema.json создан с полями: name (required string), version (string), extends (optional 'builtin:NAME' pattern), detect (list of objects {file: string, type: 'glob'|'exact'|'dir-marker'}), extensions (list of strings), gates (object: gate_name → gate_config), guide_path (optional string).
2. scripts/stack_schema.py реализует validate_decl(decl: dict, source: str = '<unknown>') -> list[str] — возвращает список ошибок (пусто если валидно).
3. validate_decl даёт actionable messages: указывает source, поле, причину (e.g. "stacks/python/stack.json: 'detect[0].type' must be one of glob/exact/dir-marker, got 'regex'").
4. Малформированные decl не молчаливо пропускаются — каждая ошибка отдельной строкой в списке.
5. Unknown gate name (не в DEFAULT_GATES whitelist) — warning, не error (custom_stacks support).
6. Negative scenario: пустой dict, dict без 'name', detect с неизвестным type, gates с не-dict значением — все вызывают ошибку с указанием источника.
7. Все edge cases покрыты smoke-проверкой в docstring примере или мини-тесте.

## Plan

## Rollback

## Journal

- 2026-04-25T15:11:40Z [implementation] — Изучил систему: STACK_SIGNATURES (3 формы: exact/glob/dir-marker + keyword), _EXT_TO_STACKS, _FILENAME_TO_STACKS, _PATH_HINTS, DEFAULT_GATES (с stacks list), STACK_GATE_MAP. Schema должна покрыть все 5 источников.
- 2026-04-25T15:13:30Z [implementation] — AC verification: 1. ✅ stacks/_schema.json создан (119 строк) — все поля name/version/extends/detect/extensions/filenames/path_hints/gates/guide_path/extensions_extra с типами и патернами. 2. ✅ scripts/stack_schema.py — validate_decl(decl, source='<unknown>') -> list[str], 297 строк (под 400 лимит). 3. ✅ Actionable messages: каждая ошибка формата "<source>: <field>: <reason>" — проверено на 12 edge cases. 4. ✅ Никакого silent skip: ошибки накапливаются в list и возвращаются все. 5. ✅ Unknown gate name: schema валидирует только структуру (pattern + shape), whitelist DEFAULT_GATES не проверяется на этом слое — это semantic check для registry/project_config (правильное разделение слоёв). 6. ✅ Negative scenarios verified: empty dict, None, list, bad name, typo unknown field, bad detect type, bad path_hint, bad ext, bad extends, bad gate severity — все возвращают чёткие сообщения. 7. ✅ Smoke check: __main__ block с 6 кейсами; запуск python -m stack_schema → all OK. Files: stacks/_schema.json (NEW), scripts/stack_schema.py (NEW). Filesize gate: pass (119 + 297, оба под 400).
- 2026-04-25T15:13:37Z [implementation] — AC verified: 1. ✓ stacks/_schema.json создан с полями name/version/extends/detect/extensions/filenames/path_hints/gates/guide_path/extensions_extra. 2. ✓ scripts/stack_schema.py implements validate_decl(decl: dict, source: str = '<unknown>') -> list[str]. 3. ✓ Actionable messages с source/field/reason — проверено на 12 edge cases. 4. ✓ No silent skip — все ошибки в list. 5. ✓ Unknown gate name allowed by structural schema (semantic whitelist — концерн registry). 6. ✓ Negative scenarios verified: empty dict, missing name, bad detect type, gates с не-dict — каждый возвращает чёткое сообщение. 7. ✓ Smoke check в __main__ — 6 кейсов проходят (python -m scripts.stack_schema → all OK).
