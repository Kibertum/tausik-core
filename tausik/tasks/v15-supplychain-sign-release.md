---
slug: v15-supplychain-sign-release
title: "[P2] Подпись skill/stack релизов (ed25519)"
status: done
epic: v15-evidence-attestation
story: v15-supplychain-signing
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "supply_sign.py (манифест+подпись+проверка) + CLI skill sign"
scope_exclude: "skill_manager install-флоу (verify на install = следующая задача)"
relevant_files:
  - "scripts/supply_sign.py"
  - "scripts/project_cli_skill.py"
  - "scripts/project_parser_ops.py"
  - "tests/test_supply_sign.py"
scope_paths:
  - "scripts/supply_sign.py"
  - "scripts/project_cli_skill.py"
  - "scripts/project_parser_ops.py"
  - "scripts/project_parser_errors.py"
  - "tests/*"
scope_tools: []
depends_on: []
completed_at: "2026-06-12T02:16:18Z"
---

## Goal

Подписывать артефакты skill/stack-релизов тем же ed25519-ключом (story A) при публикации; класть подпись/манифест рядом с артефактом. Основа для проверки на install.

## Acceptance Criteria

1. tausik skill sign <dir> строит детерминированный манифест tausik-skill-sig/v1 (sorted rel-пути + sha256 + size, исключая .git и сам файл подписи), подписывает проектным ключом и кладёт .tausik-signature.json рядом с артефактом. 2. supply_sign.verify_signed_dir(dir, public) -> (valid, detail): пересчёт хэшей + ed25519; валидный неизменённый каталог -> True. 3. Негативный: изменённый/добавленный/удалённый файл после подписи -> False с именем файла; повреждённый signature-файл -> False/ошибка без креша. 4. Негативный: нет проектного ключа -> понятная ошибка с tausik key init, exit 2. 5. pytest: sign/verify/tamper(3 вида)/no-key/детерминизм манифеста.

## Plan

## Rollback

git revert: подпись - новый артефакт .tausik-signature.json рядом со скиллом, install-флоу её пока не читает (v15-supplychain-verify-install), откат ничего не ломает

## Journal

- 2026-06-12T02:16:17Z [implementation] — AC verified: 1-5 OK см. лог (14 тестов, live smoke).
- 2026-06-12T02:16:17Z [implementation] — AC-1: ✓ live: tausik skill sign skills-official/pdf -> .tausik-signature.json (fingerprint 103a83a212851018, артефакт убран — подпись = шаг публикации); tests/test_supply_sign.py::TestManifest::test_deterministic_and_excludes_noise; AC-2: ✓ test_sign_then_verify_intact + test_foreign_key_rejected; AC-3 Negative: ✓ modified/added/removed detected с именами файлов + test_tampered_signature_payload + test_corrupt_signature_file_no_crash; AC-4 Negative: ✓ test_no_project_key_raises + CLI exit 2; AC-5: ✓ 14 тестов + test_resign_after_change
