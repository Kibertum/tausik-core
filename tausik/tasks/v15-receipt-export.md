---
slug: v15-receipt-export
title: "[P1] Экспорт receipt как переносимого артефакта"
status: done
epic: v15-evidence-attestation
story: v15-signed-receipts
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "receipt export/verify CLI + модуль receipt_export"
scope_exclude: "crypto_* модули (заморожены), service_gates.py"
relevant_files:
  - "scripts/receipt_export.py"
  - "scripts/project_cli_receipt.py"
  - "scripts/project_parser.py"
  - "scripts/project_parser_errors.py"
  - "tests/test_receipt_export.py"
scope_paths:
  - "scripts/receipt_export.py"
  - "scripts/project_cli_receipt.py"
  - "scripts/project_parser.py"
  - "scripts/project_parser_errors.py"
  - "tests/*"
scope_tools: []
depends_on: []
completed_at: "2026-06-12T01:24:51Z"
---

## Goal

Команда экспорта подписанного receipt в .tausik/receipts/<task>-<sha>.json (или stdout) для прикрепления к PR / показа внешнему аудитору. Receipt самодостаточен и проверяем по публичному ключу вне SQLite.

## Acceptance Criteria

1. tausik receipt export --task <slug> пишет self-contained артефакт tausik-receipt-export/v1 (envelope + embedded public key) в .tausik/receipts/<task>-<sha8>.json; --stdout печатает JSON. 2. tausik receipt verify <file> проверяет подпись по embedded ключу БЕЗ SQLite/keystore (и --pub для внешнего ключа); валидный -> exit 0 VALID. 3. Негативный: tampered экспорт -> ошибка, exit 1 INVALID; битый/не-export JSON -> ошибка exit 2. 4. Негативный: нет receipt у задачи -> ошибка exit 2 с подсказкой про tausik verify. 5. pytest: build/write/verify/tamper/no-receipt + fingerprint embedded ключа совпадает с signature.key_fingerprint.

## Plan

## Rollback

git revert: команды export/verify аддитивны (read-only к БД, пишут только в .tausik/receipts/ который gitignored через .tausik/); существующие receipt show/verify-флоу не меняются

## Journal

- 2026-06-12T01:24:34Z [implementation] — AC-1: ✓ live export run #649 -> .tausik/receipts/v15-scope-rule2-hardgate-1587b1c4.json; AC-2: ✓ live offline verify rc=0 VALID (embedded key, без БД); AC-3 Negative: ✓ live tampered rc=1 INVALID + tests/test_receipt_export.py::TestVerify (swapped-key, garbage->ExportError rc=2); AC-4 Negative: ✓ _cmd_export exit 2 c подсказкой (no receipt); AC-5: ✓ 14 тестов, fingerprint match проверен
- 2026-06-12T01:24:50Z [implementation] — AC verified: 1. OK live export. 2. OK offline verify rc=0. 3. OK tamper rc=1, garbage rc=2. 4. OK no-receipt exit 2. 5. OK 14 тестов.
