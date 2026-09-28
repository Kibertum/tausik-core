---
slug: full-suite-runs-only-in-ci-and-ci-has-not-run
title: "Полный прогон живёт только в CI, а CI не запускался 13 дней и 11 коммитов"
status: done
epic: release-110-deferred-from-19
story: deferred-110-audit-hygiene
complexity: medium
role: qa
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths:
  - "scripts/gate_*.py"
  - ".github/workflows/*.yml"
  - "tests/*.py"
  - "docs/ru/agent-contract.md"
  - "docs/en/agent-contract.md"
scope_tools: []
depends_on: []
completed_at: "2026-09-14T15:18:48Z"
resolution: null
resolution_reason: null
tracker_refs: []
started_model_id: null
started_model_version: null
done_model_id: claude-opus-5
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 1
token_budget: null
cost_budget_usd: null
---

## Goal

ЗАМЕР АУДИТА #177-#181 (память #414). Полный прогон в проекте есть и он в CI: .github/workflows/tests.yml гоняет pytest tests/ по матрице в двух полосах. CI запускается по push. Push не делался: последний коммит на GitHub 4 августа, на GitLab origin/main 12 августа, голова ветки 25 августа и впереди origin/main на 11 коммитов. Тринадцать дней страховочная сеть натянута и отключена от розетки. Цена измерена, а не предположена: tests/test_redact.py стоял красным с сессии #180 (страж, который он нарушает, старше его на 73 коммита), задача была закрыта поверх красного дерева, и обнаружилось это только первым за долгое время ручным полным прогоном в #181 — вместе с восемью другими отказами, из которых ни один не мог быть виден ни одному срезу.
ПОЧЕМУ СРЕЗ ЭТОГО НЕ ЛОВИТ ПО УСТРОЙСТВУ: область скоупного прогона выводится из relevant_files задачи, а сломавшиеся стражи (счётчик инструментов MCP, храповик поверхности классов, реестр cross-cutting тестов, миграционные цепочки) читают ВСЁ дерево и не принадлежат ничьей relevant_files. Квитанция при этом не лжёт — она печатает 'NOT the full suite'. Честность о пробеле не есть его покрытие.
ЧТО РЕШИТЬ В ЗАДАЧЕ, назвать явно: (а) локальный полный прогон становится условием закрытия ПАРТИИ задач (не каждой задачи — 23 минуты на закрытие убьют темп); (б) прогон вешается на предпуш-ворота; (в) оба. Побочный вопрос той же природы: .github/workflows/test-coverage.yml запускает pytest с '|| true', то есть задание не может отказать никогда и в зелёном виде неотличимо от полностью сломанного прогона — вырожденный контроль класса памяти #404.
НЕГАТИВНЫЙ СЦЕНАРИЙ, обязательный: доказательство должно быть предъявлено ОТКАЗОМ, а не успехом. Внесённая красная поломка ВНЕ relevant_files любой открытой задачи обязана заблокировать выбранные ворота; если она проходит, ворота не стерегут.

## Acceptance Criteria

## Plan

## Rollback

git revert коммита; ворота вводятся конфигурацией гейта и выключаются gates disable

## Journal

- 2026-09-14T15:18:48Z [planning] — OBSOLETE, closed without work by the owner's decision (session #265): CI runs on every push since 2026-09-14 (GitLab #7722, #7726 green including tests-full); the 13-day gap the task measured is over. No criterion was exercised; the premise of the task no longer holds.
