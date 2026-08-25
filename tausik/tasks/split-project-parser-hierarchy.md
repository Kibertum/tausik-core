---
slug: split-project-parser-hierarchy
title: "Filesize: project_parser.py 413→<400 (извлечь epic/story парсеры)"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: light
call_budget: 15
defect_of: null
scope: "Новый scripts/project_parser_hierarchy.py; scripts/project_parser.py (заменить inline epic/story блок на вызов+импорт). НЕ трогать: прочие парсеры, аргументы команд."
scope_exclude: "прочие project_parser_*.py, семантику CLI-аргументов"
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-14T00:27:17Z"
---

## Goal

project_parser.py = 413 строк, нарушает hard-лимит 400. Извлечь inline epic+story argparse-блоки (~32 строки) в новый project_parser_hierarchy.py как build_hierarchy_subparsers(sub) — зеркалит остальные build_*_subparsers и service_hierarchy split. build_parser вызывает функцию; дерево команд CLI неизменно.

## Acceptance Criteria

1. project_parser.py < 400 строк (было 413). 2. project_parser_hierarchy.py с build_hierarchy_subparsers(sub); build_parser вызывает её. 3. CLI-дерево неизменно: epic add/list/done/delete и story add/list/done/delete парсятся идентично (build_parser() OK + parse_args на sample). 4. Negative/boundary: неизвестная subcommand epic даёт argparse-ошибку как раньше. 5. filesize-gate проходит. 6. pytest (parser-тесты) зелёный, ruff чист.

## Plan

## Rollback

git checkout scripts/project_parser.py + rm scripts/project_parser_hierarchy.py. Чистое перемещение argparse-кода — откат тривиален.

## Journal

- 2026-06-14T00:27:15Z [implementation] — AC-1: ✓ project_parser.py 413→383 (<400). AC-2: ✓ project_parser_hierarchy.py (45 строк) build_hierarchy_subparsers; build_parser вызывает её + импорт. AC-3: ✓ epic add/list/done/delete + story add/list/done/delete парсятся идентично (parse_args smoke по 6 кейсам). AC-4: ✓ Negative: argparse-валидация subcommand сохранена. AC-5: ✓ filesize-gate проходит. AC-6: ✓ pytest 280 passed (parser/cli/epic/story), ruff clean. Domain: CLI-дерево неизменно.
