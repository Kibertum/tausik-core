---
slug: changelog-gate-switch-is-outside-config-trust-guards
title: "Выключатель блокирующего гейта changelog (task_done.changelog_gate.enabled) не в GUARDS: локальный false молча побеждает закоммиченный true"
status: planning
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: moderate
call_budget: 30
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

НАЙДЕНО ВНЕШНИМ L3 #38 на закрытие changelog-gate-double-registration-premise-unconfirmed, ВОСПРОИЗВЕДЕНО МОИМ ПРОГОНОМ: compose_project_tier(policy={task_done.changelog_gate.enabled: True}, local={...: False}) даёт enabled=False без Rejection, тогда как охраняемый контроль gates.changelog.enabled при тех же входах остаётся True. Причина: GUARDS в scripts/config_trust.py содержит qg0.scope_hard_gate, risk.l3_block_on_high, task_done.auto_verify и gates.*.{enabled,severity,trigger,file_extensions}, но НЕ task_done.changelog_gate.enabled — настоящий выключатель гейта (gate_changelog.py читает именно его, потому что гейт старше gates.changelog.enabled). Значит gitignored .tausik/config.json на любой машине может молча выключить гейт severity=block, закоммиченный ужесточением в tausik/policy.json (de9e027).

СЛЕДСТВИЕ ДЛЯ ЗАКРЫТОЙ ЗАДАЧИ: её вывод «дубль безвреден, при расхождении побеждает строгий» держался только на СОВПАДЕНИИ значений, а не на механизме; поправка записана в её журнал.

ЧТО СДЕЛАТЬ: добавить Guard(('task_done','changelog_gate','enabled'), _weaker_when_false, default=False (фреймворковый opt-in), note) — либо перевести выключатель на уже охраняемый путь gates.changelog.enabled, если резолвер это допускает без второго источника истины; выбрать замером того, что читает gate_changelog.changelog_gate_enabled. Тест: local false против policy true → композиция True (или Rejection); контроль — обычный неохраняемый ключ по-прежнему берётся из local.

ВНЕ ОБЪЁМА 1.9 (решение #310): слой доверия конфигурации фреймворка, не норма RENAR.

## Acceptance Criteria

## Plan

## Rollback

## Journal
