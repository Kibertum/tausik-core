---
slug: fail-closed-covers-policy-but-not-infrastructure
title: "Fail-closed объявлен для политики, но не для инфраструктуры: невозможность записать квитанцию не имеет отдельного отказа"
status: planning
epic: landscape-2026-h2
story: l26-narrative
complexity: medium
role: backend
stack: null
tier: moderate
call_budget: 45
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths:
  - "scripts/**"
  - "tests/*.py"
  - "docs/en/*.md"
  - "docs/ru/*.md"
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

Отказ инфраструктуры — не записалась квитанция, недоступен ключ, не читается конфиг гейтов — приводит к ГРОМКОМУ отказу с собственным кодом, а не к тихому продолжению.

## Acceptance Criteria

1. Перечислены ВСЕ точки, где верификация зависит от инфраструктуры: запись строки verification_runs, чтение ключа из .tausik/keys, чтение конфига гейтов, запись квитанции. Форма закрывается перечислением из кода, а не найденным случаем (конвенция #361).
2. По каждой точке отказ имеет СОБСТВЕННЫЙ код и текст, называющий, что именно недоступно. Приём заимствован у HELM AI Kernel: там INBOX_SIGNER_UNAVAILABLE, INBOX_POLICY_PROFILE_UNAVAILABLE, INBOX_RECEIPT_PERSISTENCE_UNAVAILABLE — три разных отказа вместо одного общего.
3. Замер зафиксирован ДО правки: сегодня grep по signer_unavailable, receipt_persistence, policy_unavailable в scripts/ не даёт НИ ОДНОГО совпадения.
4. НЕГАТИВНЫЙ сценарий: при недоступности любой из точек прогон НЕ имеет права завершиться успехом. Тест на каждую точку: сделать её недоступной и убедиться, что вердикт — отказ, а не зелёное.
5. НЕГАТИВНЫЙ сценарий: отказ инфраструктуры отличим от отказа гейта в ВЫВОДЕ. Пользователь, увидевший красное, должен понимать, чинить ему код или окружение — это разные следующие шаги, как в задаче refusal-does-not-separate-stale-from-failed.
6. НЕГАТИВНЫЙ сценарий: тесты обязаны падать на текущем коде, иначе правка не доказана.

## Plan

## Rollback

git revert коммита; коды отказа снимаются вместе с обработчиками

## Journal
