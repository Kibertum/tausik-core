---
slug: mem-posttool-markers
title: "Regex-набор для project markers в auto-memory записях"
status: done
epic: memory-discipline-hardening
story: memory-post-write-audit
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/hooks/memory_markers.py (новый)"
scope_exclude: "Не писать hook здесь — это отдельная задача mem-posttool-hook. Не писать тесты — mem-posttool-tests. Не трогать существующие hooks."
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-22T22:54:54Z"
---

## Goal

Compile regex-набор, детектирующий: пути (C:\Work\, /home/X/, ./src/), slug'и (3+ kebab-parts task-like), domain'ы проекта, имена из brain.project_names blocklist (переиспользовать с brain scrubbing). Список вынести в отдельный модуль для shared использования.

## Acceptance Criteria

1. scripts/hooks/memory_markers.py создан, stdlib-only, экспортирует detect_markers(text: str) -> list[Match] и список PATTERNS. Match — NamedTuple с полями (kind, match, span). 2. Паттерны: (a) abs_path — абсолютные FS-пути с project-indicator частями (Windows drive + Work/Projects/Users/src, Unix /Users|home|opt|srv|var/); (b) slug — kebab-case с >=3 частями (e.g. mem-pretool-hook, gate-false-positives-ruff-filesize); (c) tausik_cmd — .tausik/tausik(.cmd)? И tausik_<command>_* identifiers; (d) src_file — scripts/*.py, tests/*.py, bootstrap/*.py references с типичными code-extensions. 3. Positive: detect_markers находит markers в текстах типа 'path [вычеркнуто: local-path]/scripts/project.py:42', 'task mem-pretool-hook done', 'run .tausik/tausik status'. 4. Negative (false-positive guard): detect_markers возвращает [] или пропускает на cross-project preferences: 'user prefers Russian responses', 'likes pytest and python 3.11', 'uses VS Code', 'prefers concise commit messages'. 5. Уникальность: повторяющиеся matches одного kind с тем же текстом дедуплицируются. 6. Производительность: на 10 КБ текста < 50 ms. 7. Модуль отдельный (в scripts/hooks/) — не встраивается в hook-файл, чтобы brain-scrubbing (epic brain-tausik-integration) мог его переиспользовать.

## Plan

## Rollback

## Journal

- 2026-04-22T22:52:13Z [implementation] — AC verified: (1) scripts/hooks/memory_markers.py stdlib-only, экспортирует detect_markers + Match(NamedTuple kind,match,span) + PATTERNS list ✓. (2) 4 паттерна: abs_path (Windows C:\Work\, Unix /home/X/), slug (kebab 3+ parts), tausik_cmd (.tausik/tausik + tausik_*_* identifiers), src_file (scripts|tests|bootstrap/*.ext) ✓. (3) Positive: '[вычеркнуто: local-path]/scripts/project.py:42' → 2 matches (abs_path+src_file); '/home/alice/...' → 1; 'mem-pretool-hook' → 1 slug; '.tausik/tausik status' → 1; 'scripts/hooks/session_start.py' → 1 src_file ✓. (4) Negative (false-positive guard): 'user prefers Russian', 'likes pytest and python 3.11', 'uses VS Code', 'prefers concise commit messages', 'format code with prettier', 'uses Docker' — все 0 matches ✓. (5) Dedup: текст с 3 повторами 'mem-pretool-hook' → 1 match ✓. (6) Perf: 47 КБ текста → 3.1 ms (budget 50 ms) ✓. (7) Отдельный модуль, hook будет импортировать через sys.path.insert ✓.
