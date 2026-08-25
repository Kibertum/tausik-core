---
slug: v14-conftest-verify-first-comment
title: "Уточнить docstring и имена verify_first shim в conftest"
status: done
epic: v14-verify-integrity
story: v14-verify-conftest-clarity
complexity: medium
role: null
stack: null
tier: null
call_budget: null
defect_of: null
scope: "tests/conftest.py tests/verify_first_compat_predicate.py docs/en/verify-glossary.md docs/ru/verify-glossary.md tests/test_verify_first_contract.py"
scope_exclude: null
relevant_files:
  - "tests/conftest.py"
  - "tests/verify_first_compat_predicate.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-01T10:35:24Z"
---

## Goal

Ссылка на pytest.mark.verify_first и контракт v1.4.

## Acceptance Criteria

1. Обновлённый docstring. 2. Упоминание маркера. 3. Negative: тест с маркером verify_first не отключает enforcement ошибочно.

## Plan

## Rollback

## Journal

- 2026-05-01T10:35:24Z [implementation] — AC verified: 1. ✓ Docstring conftest + ссылка на v1.4 и маркер verify_first. 2. ✓ Маркер упомянут; fixture переименован _verify_first_autouse_compat_shim. 3. ✓ Negative: tests/verify_first_compat_predicate.py + AC-3: ✓ tested via pytest tests/test_verify_first_contract.py tests/test_qg2_gates.py tests/verify_first_compat_predicate.py.
