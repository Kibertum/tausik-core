---
slug: v15-supplychain-verify-install
title: "[P2] Проверка подписи на skill install"
status: done
epic: v15-evidence-attestation
story: v15-supplychain-signing
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "supply_verify_install.py + trust-pin в skill_repos + проверка в install_skill + CLI repo trust"
scope_exclude: "supply_sign.py (заморожен), copy_skill логика копирования"
relevant_files:
  - "scripts/supply_verify_install.py"
  - "scripts/skill_manager.py"
  - "scripts/skill_repos.py"
  - "scripts/project_cli_skill.py"
  - "scripts/project_parser_ops.py"
  - "tests/test_supply_verify_install.py"
scope_paths:
  - "scripts/supply_verify_install.py"
  - "scripts/skill_manager.py"
  - "scripts/skill_repos.py"
  - "scripts/project_cli_skill.py"
  - "scripts/project_parser_ops.py"
  - "tests/*"
scope_tools: []
depends_on: []
completed_at: "2026-06-12T02:20:28Z"
---

## Goal

tausik skill install проверяет ed25519-подпись/манифест артефакта против доверенного публичного ключа; mismatch = warn/block. Закрывает аудит-дыру: install тянет произвольный код без верификации.

## Acceptance Criteria

1. tausik skill repo trust <repo> <ed25519:hex> пиннит публичный ключ издателя в config (skill_repos[name].pubkey); list показывает trust-статус. 2. skill install: подписанный скилл + pinned key -> verify_signed_dir перед копированием; валидный -> установка с отметкой verified. 3. Негативный: подписанный + pinned + НЕ валидный (tamper/чужой ключ) -> установка ЗАБЛОКИРОВАНА (SkillManagerError), файлы не скопированы; битый pinned ключ -> блок (fail-closed). 4. Adoption-warnings: unsigned скилл -> warning, установка идёт; signed без pinned key -> warning с подсказкой repo trust. 5. pytest: trust-pin CRUD + 4 install-сценария (verified/blocked/unsigned-warn/unpinned-warn).

## Plan

## Rollback

git revert; поведение по умолчанию мягкое (unsigned/unpinned = warning, существующие репо без подписей не ломаются), блок только signed+pinned+invalid — откат не меняет данные

## Journal

- 2026-06-12T02:20:27Z [implementation] — AC-1: ✓ tests/test_supply_verify_install.py::TestTrustPin (pin/unknown-repo/bad-key) + repo list показывает [trusted key pinned]; AC-2: ✓ test_signed_pinned_verified (verify ДО copy_skill); AC-3 Negative: ✓ test_tampered_skill_blocked_nothing_copied + test_foreign_signature_blocked + test_corrupt_pinned_key_blocks (fail-closed); AC-4: ✓ test_unsigned_warns_but_installs + test_signed_unpinned_warns_but_installs (adoption); AC-5: ✓ 14 тестов + skill_manager regression 91 passed
- 2026-06-12T02:20:28Z [implementation] — AC verified: 1-5 OK см. лог (TOFU trust-pin, fail-closed на tamper/foreign/rotten key, 91 тест).
