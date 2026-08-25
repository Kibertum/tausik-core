---
slug: mypy-baseline-debt-precommit-hook-lies
title: "mypy: 16 ошибок в baseline — pre-commit хук фреймворка не прошёл бы на самом фреймворке"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 50
defect_of: null
scope: "pyproject.toml (mypy overrides), ~10 scripts/*.py (mechanical no-any-return), scripts/hooks/pre-commit если нужно уточнить сообщение"
scope_exclude: "Реальные arg-type/assignment фиксы (state_import/export, service_knowledge/task, graph_mermaid и др.) — вынести в follow-up, здесь только ignore_errors-маркер"
relevant_files:
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - CLAUDE.md
  - pyproject.toml
  - "scripts/backend_crud_knowledge.py"
  - "scripts/cli_push_ok.py"
  - "scripts/gate_bootstrap_drift.py"
  - "scripts/gate_registry.py"
  - "scripts/skill_deps.py"
  - "scripts/supply_eol.py"
  - "scripts/verify_envelope.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-26T17:47:31Z"
---

## Goal

`python -m mypy` даёт 16 ошибок в 11 файлах на чистом main. При этом `scripts/hooks/pre-commit`, который фреймворк предлагает установить (docs/en/hooks.md, docs/ru/hooks.md: `git config core.hooksPath scripts/hooks`), блокирует коммит при ненулевом mypy. То есть документированный путь установки собственного хука ЗАВЕДОМО заблокировал бы любой коммит в этом репозитории — рекомендация, которую сам проект не исполняет. Это тот же класс, что конвенция #282 (сообщение-инструкция — это код): документированная команда обязана работать. Либо ошибки чинятся, либо mypy-шаг хука честно объявляется warn-only с указанием причины, либо в pyproject фиксируется baseline-исключение — но молчаливого расхождения между доком и поведением быть не должно.

## Acceptance Criteria

1. `python -m mypy` даёт 0 ошибок (было 28/17 файлов; премиса 16 устарела) — документированный pre-commit хук (core.hooksPath scripts/hooks) больше не блокировал бы каждый коммит. Молчаливого расхождения док↔поведение нет. 2. import-not-found (7): ignore_missing_imports оверрайды в pyproject для hooks-модулей, импортируемых из scripts/ (bootstrap_venv, tools, hook_supervision, token_rows, _common) — паттерн memory_markers. 3. Механические no-any-return (~10: skill_deps, gate_registry×2, supply_eol×2, cli_push_ok, backend_crud_knowledge×2, verify_envelope, gate_bootstrap_drift) починены cast/аннотацией, НЕ подавлением. 4. Остаток arg-type/assignment (state_import, state_export, service_knowledge, service_task, gate_post_scope, service_gates, graph_mermaid) — per-module ignore_errors в pyproject с маркером-комментарием как ОТСЛЕЖИВАЕМЫЙ долг + follow-up задача на un-exclude (реальный фикс типов). 5. Полная суита зелёная, 0 failed.

## Plan

## Rollback

git revert; изменения — mypy-оверрайды в pyproject (аддитивно) + локальные cast'ы. Откат восстанавливает прежний baseline.

## Journal

- 2026-07-26T17:47:29Z [implementation] — AC verified: 1. ✓ `python -m mypy` -> 'Success: no issues found in 278 source files' (was 28 errors/17 files). Pre-commit hook (scripts/hooks/pre-commit, exit 1 on mypy!=0) now honest & blocking. 2. ✓ pyproject.toml ignore_missing_imports override for bootstrap_venv/bootstrap_check/bootstrap_config/tools/hook_supervision/token_rows/_common (memory_markers pattern) 3. ✓ 10 no-any-return fixed at value: cast in skill_deps/gate_registry×2/verify_envelope/gate_bootstrap_drift; bool()/str() in supply_eol×2/cli_push_ok; _add_slugged annotated -> int with int() wrap (fixes backend_crud_knowledge×2). Not suppressed. 4. ✓ 7 residual modules get per-module disable_error_code naming the SPECIFIC code (arg-type/assignment) — narrower than ignore_errors, still catches other classes; follow-up task mypy-residual-argtype-untangle created (defect_of this) 5. ✓ full suite 6031 passed, 24 skipped, 0 failed (type-cleanup behaviour-preserving: cast is runtime no-op, int()/str()/bool() at boundaries). scoped verify pytest PASS. 6. ✓ Domain: mypy=0 means the documented `git config core.hooksPath scripts/hooks` install now works instead of blocking every commit — the doc-vs-code lie is closed.
