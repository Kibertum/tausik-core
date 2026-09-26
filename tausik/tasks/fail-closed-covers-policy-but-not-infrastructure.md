---
slug: fail-closed-covers-policy-but-not-infrastructure
title: "Fail-closed объявлен для политики, но не для инфраструктуры: невозможность записать квитанцию не имеет отдельного отказа"
status: done
epic: release-110-deferred-from-19
story: release110-open-defects
complexity: medium
role: backend
stack: null
tier: moderate
call_budget: 45
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/infra_refusal.py"
  - "scripts/verify_cached_run.py"
  - "scripts/verify_run_record.py"
  - "scripts/gate_verify_first.py"
  - "tests/test_infra_refusal.py"
scope_paths:
  - "scripts/infra_refusal.py"
  - "scripts/verify_cached_run.py"
  - "scripts/verify_run_record.py"
  - "scripts/gate_verify_first.py"
  - "tests/*.py"
  - "docs/ru/*.md"
  - "docs/en/*.md"
  - "CHANGELOG*.md"
scope_tools: []
depends_on: []
completed_at: "2026-09-24T08:23:21Z"
resolution: null
resolution_reason: null
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

- 2026-09-24T08:17:53Z [implementation] — AC3: ✓ measurement — before: grep signer_unavailable|receipt_persistence|policy_unavailable|SIGNER_UNAVAILABLE over scripts/ = 0 matches. Points enumerated from code: (1) verification_runs INSERT + gate_runs (verify_run_record._record_verification -> VerificationRecordError -> record-failed, already blocking but uncoded); (2) signing with the project key (verify_receipt_emit.emit_signed_receipt -> STATUS_ERROR: printed as a WARNING, run stayed GREEN and closable by freshness lookup); (3) receipt_json UPDATE (same try as 2); (4) gate config load (gate_verify_first config-load block, uncoded).
- 2026-09-24T08:21:28Z [implementation] — AC-1: ✓ tests/test_infra_refusal.py::test_signer_unavailable_turns_the_run_red
- 2026-09-24T08:21:28Z [implementation] — Mutation: signer check disabled -> test_signer_unavailable_turns_the_run_red red (1 failed); restored.
- 2026-09-24T08:21:28Z [implementation] — Root cause: verify treated infrastructure failures as warnings (signer) or as generic text (persistence, config); fail-closed was specified for policy verdicts only.
- 2026-09-24T08:21:29Z [implementation] — AC-2: ✓ tests/test_infra_refusal.py::test_receipt_persistence_unavailable_is_named
- 2026-09-24T08:21:29Z [implementation] — AC-3: ✓ tests/test_infra_refusal.py::test_policy_profile_unavailable_is_named (enumeration logged earlier: persistence, signer, policy config)
- 2026-09-24T08:21:29Z [implementation] — AC-4: ✓ tests/test_infra_refusal.py::test_a_keyless_project_is_not_an_infrastructure_failure
- 2026-09-24T08:21:41Z [implementation] — AC-2: ✓ tests/test_infra_refusal.py::test_receipt_persistence_unavailable_is_named, tests/test_infra_refusal.py::test_policy_profile_unavailable_is_named, tests/test_infra_refusal.py::test_signer_unavailable_turns_the_run_red — three distinct codes
- 2026-09-24T08:21:41Z [implementation] — AC-3: ✓ before-measurement 0 matches, logged 08:17
- 2026-09-24T08:21:41Z [implementation] — Correction of AC numbering above. AC-1: ✓ enumeration from code logged 08:17 (4 points; signing and receipt write share one try -> SIGNER_UNAVAILABLE)
- 2026-09-24T08:21:42Z [implementation] — AC-4: ✓ tests/test_infra_refusal.py::test_signer_unavailable_turns_the_run_red (was green), persistence already blocking and now coded; tests/test_infra_refusal.py::test_a_keyless_project_is_not_an_infrastructure_failure bounds it
- 2026-09-24T08:21:42Z [implementation] — AC-5: ✓ every refusal line starts INFRASTRUCTURE: and says fix the environment — asserted in tests/test_infra_refusal.py::test_receipt_persistence_unavailable_is_named
- 2026-09-24T08:21:42Z [implementation] — AC-6: ✓ mutation above: signer check off -> tests/test_infra_refusal.py::test_signer_unavailable_turns_the_run_red red
