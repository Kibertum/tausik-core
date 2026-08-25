---
slug: v15-crypto-canonical-receipt
title: "[P0] Canonical receipt — детерминированная JSON-схема + сериализатор"
status: done
epic: v15-evidence-attestation
story: v15-crypto-foundation
complexity: medium
role: architect
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/crypto_receipt.py (new), tests/"
scope_exclude: null
relevant_files:
  - "scripts/crypto_receipt.py"
  - "tests/test_crypto_receipt.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-11T23:59:28Z"
---

## Goal

Определить каноническую детерминированную JSON-схему receipt {task_slug, git_sha, gates[], results, timestamp, scope} и сериализатор (стабильный порядок ключей, нормализация), чтобы одна и та же запись давала идентичные байты для подписи. Схема + тесты детерминизма.

## Acceptance Criteria

1. Модуль receipt: build_receipt(...) формирует dict со схемой v1 {schema, task_slug, git_sha, scope, gates[], passed, ran_at, files_hash?, key_fingerprint?} и canonical_bytes(receipt) даёт детерминированные байты (RFC 8785-стиль: sorted keys, разделители без пробелов, ensure_ascii, запрет NaN/Inf и не-JSON типов). 2. Тесты детерминизма: перестановка ключей/вложенных dict → идентичные байты; float/NaN/datetime → явная ошибка. 3. Roundtrip: canonical_bytes(json.loads(canonical_bytes(r))) == canonical_bytes(r). 4. ruff/mypy зелёные.

## Plan

## Rollback

## Journal

- 2026-06-11T23:59:28Z [implementation] — AC: 1. ✓ scripts/crypto_receipt.py (schema v1 + canonical_bytes). 2. ✓ tests/test_crypto_receipt.py::TestCanonicalBytes (key order, float/NaN/datetime/non-str-key rejected). 3. ✓ test_roundtrip_stable. 4. ✓ ruff+mypy clean, 13 passed.
- 2026-06-11T23:59:28Z [implementation] — crypto_receipt.py: build_receipt (схема tausik-receipt/v1, gates слимятся до name/passed/severity и сортируются) + canonical_bytes (sorted keys, no-ws separators, ensure_ascii, float/NaN/non-JSON -> ReceiptError). 13 тестов детерминизма/отказов. mypy fix: typing slim_gates.
