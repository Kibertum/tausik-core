---
slug: v15-receipt-check-on-done
title: "[P0] task_done проверяет подпись + свежесть receipt"
status: done
epic: v15-evidence-attestation
story: v15-signed-receipts
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/verify_receipt_check.py"
  - "scripts/service_gates.py"
  - "tests/test_verify_receipt_check.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-12T00:59:14Z"
---

## Goal

QG-2 task_done дополнительно к существующей verify-first проверке валидирует ed25519-подпись cached receipt и его свежесть/привязку к git_sha. Невалидная подпись = блок закрытия. Tamper-evidence для proof-of-done.

## Acceptance Criteria

1. task_done при fresh verify run с receipt_json проверяет ed25519-подпись envelope (verify_receipt); валидная -> закрытие как раньше. 2. Негативный: tampered/невалидная подпись -> blocking failure 'receipt-signature', task done заблокирован, remediation в выводе. 3. Привязка: receipt.task_slug != слаг задачи -> блок (ошибка); git_sha receipt != HEAD -> warning, не блок. 4. Негативный/graceful: receipt_json NULL (pre-v29 или keyless) или нет публичного ключа -> закрытие НЕ блокируется, warning в notes. 5. pytest: valid/tampered/slug-mismatch/null-receipt/no-key.

## Plan

## Rollback

git revert коммита — проверка read-only (без миграций БД); при инцидентах деградация уже встроена: keyless-проект/NULL receipt_json (pre-v29 строки) не блокируются, т.е. откат ключа тоже не ломает закрытие задач

## Journal

- 2026-06-12T00:58:57Z [implementation] — Impl: verify_receipt_check.check_receipt_for_hit + wiring в _enforce_verify_first (gate receipt-signature); decision #91 (drift=warn); 26+188 tests green
- 2026-06-12T00:59:14Z [implementation] — AC verified: 1. ✓ check_receipt_for_hit wired into _enforce_verify_first cache-hit branch; tests/test_verify_receipt_check.py::TestValid::test_valid_receipt_allows_close; live: closing THIS task goes through the check 2. ✓ TestTamperBlocks::test_tampered_payload_blocks + test_corrupt_json_blocks -> gate 'receipt-signature' blocking failure 3. ✓ TestTamperBlocks::test_slug_mismatch_blocks + test_ran_at_mismatch_blocks (блок); TestValid::test_git_sha_drift_warns_but_allows (warning, не блок; decision #91) 4. ✓ TestGracefulDegradation: null receipt / no public key / missing row -> ok_to_close=True with warning note 5. ✓ pytest tests/test_verify_receipt_check.py 9 passed; -k 'gates or task_done' 188 passed (no regression)
- 2026-06-12T00:59:54Z [done] — Поправка к AC1 evidence: MCP task_done использовал stale service_gates (модуль загружен до правок) — note без receipt-статуса. Логика подтверждена unit-тестами (9 passed); живая проверка wiring отложена до следующего task done через CLI (CLI перечитывает модули). До рестарта IDE: task done/verify только через CLI.
- 2026-06-12T01:05:39Z [done] — Live wiring подтверждён: закрытие v15-scope-declare через CLI -> note 'Verify-First: cache hit (run #644) | receipt: VALID ed25519 signature' — AC1 живое evidence получено
