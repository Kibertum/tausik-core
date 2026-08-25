---
slug: align-filesize-gate-research-exemption
title: "Filesize-gate: добавить docs/{en,ru}/research/ в коммиченный exempt (conv #122)"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: light
call_budget: 12
defect_of: null
scope: "scripts/gate_runner.py (_FILESIZE_EXEMPT_DIRS), tests/test_gates.py (новый тест exempt research). НЕ трогать: логику run_filesize_gate, лимит 400, прочие exempt-диры."
scope_exclude: "логику count_lines/run_filesize_gate, .tausik/config.json"
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-14T00:11:55Z"
---

## Goal

Согласовать filesize-gate с convention #122: research-дампы docs/{en,ru}/research/* должны быть exempt от лимита 400 строк. Сейчас _FILESIZE_EXEMPT_DIRS хардкодит несуществующие docs/content/ и docs/architecture/, а реальные research-диры (файлы 829/1033 строк) НЕ освобождены в коммиченном коде — exemption живёт лишь в gitignored .tausik/config.json, поэтому на свежем клоне/CI research-файлы нарушат gate. Добавить docs/en/research/ и docs/ru/research/ в коммиченный exempt-список + тест.

## Acceptance Criteria

1. docs/en/research/ и docs/ru/research/ добавлены в _FILESIZE_EXEMPT_DIRS (коммиченный gate_runner.py). 2. Существующие docs/{en,ru}/research/*.md (>400 строк) больше не нарушают gate (проверяемо: файл в этом пути с 500+ строк → run_filesize_gate passed=True). 3. Negative/boundary: файл с 500 строк ВНЕ research-дир по-прежнему нарушает (passed=False) — exemption не сверх-широкий. 4. Новый тест в test_gates.py покрывает обе ветки (research exempt vs non-research fail). 5. Поведение для прочих exempt-диров (tests/, mcp) неизменно. 6. pytest зелёный, ruff чист.

## Plan

## Rollback

## Journal

- 2026-06-14T00:11:54Z [implementation] — AC-1: ✓ docs/en/research/ + docs/ru/research/ добавлены в _FILESIZE_EXEMPT_DIRS (gate_runner.py:46-48). AC-2: ✓ реальные 9 research-файлов (829/1033 строк) → run_filesize_gate passed=True (проверено glob+вызов). AC-3: ✓ Negative: docs/ru/guide.md с 900 строк ВНЕ research → passed=False, '900 lines' — tested via tests/test_gates.py::test_filesize_gate_non_research_md_still_blocks. AC-4: ✓ обе ветки в test_gates.py (exempt research + non-research fail). AC-5: ✓ прочие exempt-диры неизменны (94 теста gate зелёные). AC-6: ✓ pytest 94 passed, ruff clean, gen_doc_constants --check CLEAN (README→4035). Domain: на свежем клоне/CI research-дампы больше не ломают gate.
