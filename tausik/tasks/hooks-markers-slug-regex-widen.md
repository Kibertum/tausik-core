---
slug: hooks-markers-slug-regex-widen
title: "MEDIUM: расширить _SLUG_RE до {1,} сегментов"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: brain-decide-auto-route
scope: "scripts/hooks/memory_markers.py, tests/test_memory_markers.py"
scope_exclude: "scripts/hooks/memory_pretool_block.py, scripts/hooks/memory_posttool_audit.py"
relevant_files:
  - "scripts/hooks/memory_markers.py"
  - "tests/test_memory_markers.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-24T19:56:07Z"
---

## Goal

Регэкс {2,} упускает 2-сегментные slug'и ([вычеркнуто: third-party-project]-ru, my-app, brain-init). Опустить до {1,} и положиться на higher-precision детекторы для precision

## Acceptance Criteria

1. _SLUG_RE расширен с {2,} до {1,} — ловит 2-сегментные slug'и (my-app, brain-init, [вычеркнуто: third-party-project]-ru)
2. Precision guard: 2-сегментные slug'и попадают в результат detect_markers ТОЛЬКО если (a) их больше/>=3-сегментный slug тоже сработал, ИЛИ (b) хотя бы один higher-precision детектор (abs_path, src_file, tausik_cmd) сработал в том же тексте
3. Регрессия: все существующие позитивные тесты (3+ seg slug'и типа 'mem-pretool-hook', 'gate-false-positives-ruff-filesize') продолжают проходить
4. Регрессия: все существующие negative-тесты ('kebab-case', 'ts-node', 'switch-case', 'double-quoted', 'single-quoted') продолжают проходить (английские kebab-compounds не флагуются)
5. Новые позитивные тесты: 2-сегментный slug + path / tausik_cmd → возвращается
6. Ошибка/граничный случай: 2-сегментный slug БЕЗ других детекторов → empty list (conservative, избегает FPs)
7. Ошибка/граничный случай: 2-сегментный slug + 3-сегментный slug в одном тексте → оба возвращаются (corroboration через сам slug kind)
8. pytest tests/test_memory_markers.py проходит; ruff clean

## Plan

## Rollback

## Journal

- 2026-04-24T19:52:26Z [implementation] — AC verified: _SLUG_RE расширен с {2,} до {1,}. Precision guard в detect_markers — has_strong = any (non-slug kind) или (slug с >=2 hyphens). Если not has_strong → return []. 6 новых тестов: 2-seg alone dropped (negative), 2-seg + abs_path/src_file/tausik_cmd/3seg-slug kept (positive corroboration), 3-seg alone still fires (regression). Все 14 существующих negative-тестов продолжают проходить (kebab-case, ts-node, switch-case, double-quoted, single-quoted — все standalone, drop). pytest 97/97 (markers + pretool + posttool). ruff clean.
