---
slug: v15-failclosed-gate-audit
title: "[P2] Аудит warning-only гейтов → fail-closed"
status: done
epic: v15-evidence-attestation
story: v15-failclosed-audit
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "аудит-док + hardening root-cause для defect-задач"
scope_exclude: "уже hard гейты (Rule 2/6, L3-trigger, receipt) не трогать"
relevant_files:
  - "scripts/service_task_done.py"
  - "docs/ru/research/failclosed-gates-audit.md"
  - "tests/test_failclosed_root_cause.py"
  - "tests/test_senar.py"
scope_paths:
  - "docs/ru/research/failclosed-gates-audit.md"
  - "scripts/service_task_done.py"
  - "tests/*"
scope_tools: []
depends_on: []
completed_at: "2026-06-12T02:05:19Z"
---

## Goal

Аудит warning-only гейтов (Rule 2/5/7 и пр.) на fail-open поверхности; перевести в hard где FP-риск приемлем; задокументировать единую fail-closed-by-default политику. Заимствует принцип Walko.

## Acceptance Criteria

1. Аудит-документ: инвентарь всех warning-only гейтов (QG-0/QG-2/hooks) с оценкой FP-риска и вердиктом (harden/keep-warn/opt-in-strict) + единая политика fail-closed-by-default с критериями исключений. 2. Негативный: defect-задача (defect_of) без задокументированного root cause -> blocking failure на task done (было warning), remediation в сообщении. 3. Root cause залогирован -> закрытие проходит; не-defect задачи не затронуты. 4. Негативный: config task_done.root_cause_hard=false -> warning как раньше. 5. pytest: блок/проход/не-defect/opt-out.

## Plan

## Rollback

git revert; мгновенный opt-out: config task_done.root_cause_hard=false возвращает warning; аудит-документ — чистое добавление

## Journal

- 2026-06-12T02:05:18Z [implementation] — AC verified: 1-5 OK см. лог (аудит-док 23 гейта, Rule 7 hard, 159 regression green).
- 2026-06-12T02:05:18Z [implementation] — AC-1: ✓ docs/ru/research/failclosed-gates-audit.md — 23 гейта в инвентаре, 3 основания для warn (adoption/high-FP/availability), кандидаты будущего ужесточения; AC-2 Negative: ✓ tests/test_failclosed_root_cause.py::test_defect_without_root_cause_blocked (status active после блока); AC-3: ✓ test_defect_with_root_cause_closes + test_russian_keyword_accepted + test_non_defect_task_unaffected; AC-4 Negative: ✓ test_opt_out_downgrades_to_warning; AC-5: ✓ 6 тестов + regression senar/done 159 passed (test_senar Rule8-пин дополнен root cause)
