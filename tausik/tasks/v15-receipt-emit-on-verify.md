---
slug: v15-receipt-emit-on-verify
title: "[P0] verify эмитит signed receipt"
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
  - "scripts/verify_receipt_emit.py"
  - "scripts/service_verification.py"
  - "scripts/project_cli_verify.py"
  - "scripts/project_cli_receipt.py"
  - "scripts/project_parser.py"
  - "scripts/project.py"
  - "scripts/backend_schema.py"
  - "scripts/backend_migrations.py"
  - "scripts/backend_migrations_legacy.py"
  - "scripts/project_parser_errors.py"
  - "tests/test_verify_receipt_emit.py"
  - "tests/test_service_verification.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-12T00:54:14Z"
---

## Goal

При tausik verify формировать canonical receipt по результатам гейтов и подписывать ed25519; сохранять подпись в verification_runs (или receipts). Verify-прогон становится криптографически заверенным.

## Acceptance Criteria

1. tausik verify --task <slug> после гейтов строит canonical receipt (build_receipt) и подписывает активным ключом (sign_receipt). 2. Signed envelope персистится в БД привязанным к verify-прогону и доступен для чтения через CLI. 3. Негативный: tampered payload -> verify подписи возвращает ошибку/False (fail), тест это проверяет. 4. Негативный: нет ключа в .tausik/keys -> graceful degradation: verify работает как раньше, warning, без receipt, без исключения. 5. pytest: emission + persistence + tamper + no-key fallback.

## Plan

## Rollback

git revert коммита; receipt-эмиссия аддитивна (новая колонка/таблица не ломает старые verify-прогоны); при сбое подписи verify работает как раньше (graceful degradation), миграцию вниз не требует — данные receipt можно игнорировать

## Journal

- 2026-06-12T00:41:53Z [implementation] — Side-quest done: токен-правила #131 перенесены в auto-memory (feedback_token_economy.md, Rule 2 добавлен); MEMORY.md индекс обновлён; gotcha про anchored-маркер записана
- 2026-06-12T00:49:06Z [implementation] — Impl done: миграция v29 receipt_json, verify_receipt_emit.py (emit/load), record_run эмитит, CLI receipt show, 138 tests green local
- 2026-06-12T00:51:18Z [implementation] — AC verified: 1. ✓ verify run #637 -> 'Receipt: signed (key 103a83a212851018)'; tests/test_verify_receipt_emit.py::TestEmission 2. ✓ receipt_json on verification_runs (migration v29); CLI 'tausik receipt show --task/--run' prints envelope + VALID; TestLoadReceipt 3. ✓ TestTamperDetection::test_modified_payload_fails_verification + test_modified_signature_fails_verification 4. ✓ TestNoKeyDegradation::test_record_run_survives_missing_key + test_emit_reports_no_key (no exception, receipt NULL) 5. ✓ pytest tests/test_verify_receipt_emit.py 17 passed; +test_service_verification.py 138 passed combined
- 2026-06-12T00:53:37Z [implementation] — AC verified: 1. ✓ verify run #638 -> 'Receipt: signed (key 103a83a212851018)'; tests/test_verify_receipt_emit.py::TestEmission 2. ✓ receipt_json on verification_runs (migration v29); CLI 'tausik receipt show --task/--run' prints envelope + VALID; TestLoadReceipt 3. ✓ TestTamperDetection::test_modified_payload_fails_verification + test_modified_signature_fails_verification 4. ✓ TestNoKeyDegradation::test_record_run_survives_missing_key + test_emit_reports_no_key (no exception, receipt NULL) 5. ✓ pytest tests/test_verify_receipt_emit.py 17 passed; +test_service_verification.py 138 passed combined
- 2026-06-12T00:54:14Z [implementation] — AC verified: 1. ✓ verify run #640 -> 'Receipt: signed (key 103a83a212851018)'; tests/test_verify_receipt_emit.py::TestEmission 2. ✓ receipt_json on verification_runs (migration v29); CLI 'tausik receipt show --task/--run' prints envelope + VALID; TestLoadReceipt 3. ✓ TestTamperDetection::test_modified_payload_fails_verification + test_modified_signature_fails_verification 4. ✓ TestNoKeyDegradation::test_record_run_survives_missing_key + test_emit_reports_no_key (no exception, receipt NULL) 5. ✓ pytest tests/test_verify_receipt_emit.py 17 passed; +test_service_verification.py 138 passed combined
