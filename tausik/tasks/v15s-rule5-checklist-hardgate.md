---
slug: v15s-rule5-checklist-hardgate
title: "[P1] SENAR Rule 5: checklist warning → hard для substantial/deep"
status: done
epic: v15-senar-hardening
story: v15s-rules
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 40
defect_of: null
scope: "scripts/gate_ac_check.py (keyword-таблицы на модульный уровень + checklist_missing/checklist_hard_block, planning-tier substantial/deep). scripts/service_task_done.py (hard-блок + escalating nudge для меньших тиров через nudge_escalation, config opt-out). tests/test_checklist_hardgate.py."
scope_exclude: "determine_checklist_tier логика, существующие AC-evidence/test-ref/negative warnings (не трогаем), check_verification_checklist возвращаемые warning-строки"
relevant_files:
  - "scripts/gate_ac_check.py"
  - "scripts/service_task_done.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-13T10:01:52Z"
---

## Goal

Rule 5 Verification Checklist сейчас 3.5/5 (warning-only). Сделать hard gate для tier substantial/deep: task done отказывает без заполненного checklist в notes; для меньших тиров — эскалирующий nudge (синергия с v15p-escalating-nudges). AC: hard-блок с понятным remediation-сообщением; тиры ниже — warning; тесты обоих путей.

## Acceptance Criteria

1. checklist_hard_block: planning-tier substantial/deep + пустой checklist -> (True, понятное remediation-сообщение со ссылкой на /review и opt-out config). 2. task done отказывает (blocking_failure) для substantial/deep без checklist; с заполненным — проходит. 3. Меньшие тиры (trivial/light/moderate/None): не блок, а эскалирующий nudge через nudge_escalation (синергия). 4. Ошибка/boundary: config task_done.checklist_hard=false -> downgrade в warning, не блок; tier=None -> не блок. 5. pytest: hard-путь (блок+проход) + nudge-путь + opt-out.

## Plan

## Rollback

git revert коммита; checklist возвращается к warning-only. Config task_done.checklist_hard=false мгновенно отключает hard-блок без отката кода.

## Journal

- 2026-06-13T10:01:39Z [implementation] — checklist_hard_block: planning-tier substantial/deep + пустой checklist -> hard-блок (config task_done.checklist_hard, default True). Меньшие тиры -> escalate() через nudge_escalation (синергия с v15p-escalating-nudges), reset при наличии checklist. Keyword-таблицы вынесены на модульный уровень (shared warning+hardgate). 9 новых + 87 regression зелёные. test_count 3786->3795.
- 2026-06-13T10:01:51Z [implementation] — AC verified: 1. ✓ checklist_hard_block substantial/deep+пустой -> (True,msg) с /review+opt-out (TestChecklistHardBlock). 2. ✓ task done блок substantial без checklist, проход с checklist (test_substantial_blocked/passes). 3. ✓ меньшие тиры -> nudge не блок (test_lower_tier_not_blocked). 4. ✓ negative: checklist_hard=false->warning, tier=None->no block (test_opt_out, test_lower_tier). 5. ✓ pytest 9 + 87 regression. Checklist verified: scope clean, no secret, edge-cases (tier None/lower) covered, no test tamper.
