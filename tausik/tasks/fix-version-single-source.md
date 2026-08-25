---
slug: fix-version-single-source
title: "[debt] tausik_version.py дублирует pyproject version и дрейфит — single-source + doc-drift scan"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/doc_drift_scanners.py"
  - "scripts/gen_doc_constants.py"
  - "tests/test_gen_doc_constants.py"
  - "docs/_generated/constants.json"
  - README.md
  - README.ru.md
  - "docs/en/architecture.md"
  - "docs/ru/architecture.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-13T13:57:00Z"
---

## Goal

scripts/tausik_version.py хранил __version__='1.4.0' и застрял с релиза 1.4.0 (пропустил 1.4.1/1.4.2) — _get_version() читает его для CLAUDE.md/CLI. gen_doc_constants --check НЕ сканит .py __version__, поэтому drift невидим. Фикс: либо tausik_version.py читает версию из pyproject/importlib.metadata (single source), либо добавить __version__ в CROSS_FILE/doc-drift scan. Обнаружено в v15p-release-150 (бампнул вручную до 1.5.0).

## Acceptance Criteria

AC1: gen_doc_constants --check падает (exit 1) когда scripts/tausik_version.py.__version__ != pyproject project.version. Новый scanner scan_py_version_constants залит в run_main (gated by skip_cross_files).
AC2 (negative): регресс-тест — при tausik_version.py='1.4.0' и pyproject='1.5.0' (исторический drift, который раньше был невидим) scan_py_version_constants возвращает непустой список drift-сообщений. Без фикса scan отсутствует → drift молчит.
AC3: при синхронной версии (текущая 1.5.0) --check остаётся зелёным; существующие test_gen_doc_constants зелёные; ruff + mypy clean.

## Plan

## Rollback

## Journal

- 2026-06-13T13:56:40Z [implementation] — Fix: добавил scan_py_version_constants(repo_root, expected) в doc_drift_scanners.py (PY_VERSION_SCAN_TARGETS=scripts/tausik_version.py, _PY_VERSION_RE). Wired в gen_doc_constants.run_main после scan_version_refs (gated skip_cross_files) + import + __all__. Литерал остаётся (runtime .claude/scripts без pyproject), но drift теперь ловится --check. End-to-end доказано: tausik_version.py='9.9.9' → --check EXIT=1 'Python __version__ drift'. 3 теста (clean/drift-1.4.0-vs-1.5.0/missing-target). test_count 3820→3823, бейджи+constants синхронизированы. 34 passed, ruff clean.
- 2026-06-13T13:56:59Z [implementation] — AC1 ✓: scan_py_version_constants wired в run_main; end-to-end — tausik_version.py='9.9.9' → `gen_doc_constants --check` EXIT=1 с "Python __version__ drift". AC2 ✓ (negative): test_scan_py_version_flags_drift (1.4.0 vs 1.5.0 — исторический невидимый drift) возвращает непустой список с 'tausik_version.py:2' + '1.4.0'. AC3 ✓: версия синхронна (1.5.0) → --check OK; 34 passed (test_gen_doc_constants); ruff clean; mypy clean (pre-commit). Domain: scanner ловит реальный класс багов из v15p-release-150 (ручной бамп пропустил 1.4.1/1.4.2).
