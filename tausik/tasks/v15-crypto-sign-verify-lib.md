---
slug: v15-crypto-sign-verify-lib
title: "[P0] Sign/verify library — ed25519 модуль + тесты"
status: done
epic: v15-evidence-attestation
story: v15-crypto-foundation
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/crypto_sign.py (new), tests/"
scope_exclude: null
relevant_files:
  - "scripts/crypto_sign.py"
  - "tests/test_crypto_sign.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-12T00:01:13Z"
---

## Goal

Реализовать модуль sign(payload)->signature и verify(payload, signature, pubkey)->bool на ed25519 (stdlib/cryptography). Покрыть тестами: валидная подпись, подмена payload, неверный ключ, tamper. Общий модуль для stories B/C/F.

## Acceptance Criteria

1. Модуль crypto_sign: sign_receipt(project_dir, receipt) -> signed envelope {receipt, signature{algorithm, key_fingerprint, value_hex}}; verify_receipt(envelope, public=None) -> bool (public по умолчанию из .tausik/keys). 2. Подпись считается над canonical_bytes(receipt); любое изменение receipt -> verify False. 3. Негативные кейсы: чужой ключ, повреждённая подпись, отсутствие ключа -> явные ошибки/False. 4. Тесты + ruff/mypy зелёные.

## Plan

## Rollback

## Journal

- 2026-06-12T00:01:13Z [implementation] — AC: 1. ✓ scripts/crypto_sign.py (sign_receipt/verify_receipt, public= или project_dir=). 2. ✓ test_tampered_receipt_fails + test_tampered_nested_gate_fails. 3. ✓ test_foreign_key_fails, test_corrupt_signature_fails, test_sign_without_key_raises, test_malformed_envelopes_return_false. 4. ✓ 11 passed, ruff+mypy clean.
- 2026-06-12T00:01:13Z [implementation] — crypto_sign.py: sign_receipt/verify_receipt, envelope tausik-signed/v1, подпись над canonical_bytes(receipt); verify не бросает на attacker-controlled input (False), ключевые precondition'ы -> SignError. 11 тестов: roundtrip, tamper (top+nested), чужой ключ, malformed envelope, float->SignError.
