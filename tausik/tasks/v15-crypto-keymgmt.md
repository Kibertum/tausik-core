---
slug: v15-crypto-keymgmt
title: "[P0] Key management — генерация/хранение ed25519 project key"
status: done
epic: v15-evidence-attestation
story: v15-crypto-foundation
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/crypto_ed25519.py (new), scripts/crypto_keys.py (new), scripts/project_parser*.py, scripts/project_cli*.py, tests/"
scope_exclude: null
relevant_files:
  - "scripts/crypto_ed25519.py"
  - "scripts/crypto_keys.py"
  - "scripts/project_cli_key.py"
  - "scripts/project_parser.py"
  - "scripts/project_parser_errors.py"
  - "scripts/project.py"
  - "tests/test_crypto_keys.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-11T23:57:31Z"
---

## Goal

Реализовать управление ed25519-ключом проекта: генерация, хранение приватного ключа в .tausik/keys/ (gitignore), публичный ключ доступен для верификации. Команда/функция инициализации ключа. Фундамент для подписи receipts/scope/releases.

## Acceptance Criteria

1. tausik key init генерирует ed25519-пару: приватный seed в .tausik/keys/project.key, публичный в project.pub (формат ed25519:<hex>). 2. Повторный init без --force отказывает (exit!=0), с --force перезаписывает. 3. tausik key show выводит публичный ключ + fingerprint (sha256/16hex), приватный НЕ выводится. 4. ed25519-ядро проходит RFC 8032 test vector 1 (seed->pub, sign(empty)->known sig). 5. Тесты + ruff/mypy зелёные.

## Plan

## Rollback

## Journal

- 2026-06-11T23:57:19Z [implementation] — crypto_ed25519.py (RFC 8032 pure-python, vectors 1+2 OK) + crypto_keys.py (init/load/fingerprint, формат ed25519:<hex>) + CLI key init/show (project_cli_key.py, parser, dispatch, EXAMPLES). 16 тестов. E2E: init→show→повторный init отказал; git check-ignore подтверждает приватник под ignore.
- 2026-06-11T23:57:31Z [implementation] — AC: 1. ✓ e2e key init создал project.key/.pub, git check-ignore подтвердил. 2. ✓ повторный init exit 1 + --force hint; tests/test_crypto_keys.py::TestKeyStorage. 3. ✓ key show: pub+fingerprint, seed не выводится (test_key_info_never_exposes_seed). 4. ✓ RFC 8032 vectors 1+2 (TestEd25519Core). 5. ✓ 16 passed, ruff+mypy clean.
