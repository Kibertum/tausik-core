---
slug: changelog-gate-switch-is-outside-config-trust-guards
title: "Выключатель блокирующего гейта changelog (task_done.changelog_gate.enabled) не в GUARDS: локальный false молча побеждает закоммиченный true"
status: done
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
relevant_files:
  - "scripts/config_trust.py"
  - "tests/test_config_trust.py"
  - "tests/test_config_policy.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-09-04T21:56:28Z"
resolution: null
resolution_reason: null
tracker_refs: []
started_model_id: null
started_model_version: null
done_model_id: null
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

НАЙДЕНО ВНЕШНИМ L3 #38 на закрытие changelog-gate-double-registration-premise-unconfirmed, ВОСПРОИЗВЕДЕНО МОИМ ПРОГОНОМ: compose_project_tier(policy={task_done.changelog_gate.enabled: True}, local={...: False}) даёт enabled=False без Rejection, тогда как охраняемый контроль gates.changelog.enabled при тех же входах остаётся True. Причина: GUARDS в scripts/config_trust.py содержит qg0.scope_hard_gate, risk.l3_block_on_high, task_done.auto_verify и gates.*.{enabled,severity,trigger,file_extensions}, но НЕ task_done.changelog_gate.enabled — настоящий выключатель гейта (gate_changelog.py читает именно его, потому что гейт старше gates.changelog.enabled). Значит gitignored .tausik/config.json на любой машине может молча выключить гейт severity=block, закоммиченный ужесточением в tausik/policy.json (de9e027).

СЛЕДСТВИЕ ДЛЯ ЗАКРЫТОЙ ЗАДАЧИ: её вывод «дубль безвреден, при расхождении побеждает строгий» держался только на СОВПАДЕНИИ значений, а не на механизме; поправка записана в её журнал.

ЧТО СДЕЛАТЬ: добавить Guard(('task_done','changelog_gate','enabled'), _weaker_when_false, default=False (фреймворковый opt-in), note) — либо перевести выключатель на уже охраняемый путь gates.changelog.enabled, если резолвер это допускает без второго источника истины; выбрать замером того, что читает gate_changelog.changelog_gate_enabled. Тест: local false против policy true → композиция True (или Rejection); контроль — обычный неохраняемый ключ по-прежнему берётся из local.

ВНЕ ОБЪЁМА 1.9 (решение #310): слой доверия конфигурации фреймворка, не норма RENAR.

## Acceptance Criteria

AC-1: GUARDS в scripts/config_trust.py содержит запись для ('task_done','changelog_gate','enabled') с _weaker_when_false (дефолт фреймворка False — opt-in гейт) и заметкой; выбор «охранять этот путь, а не переносить выключатель на gates.changelog.enabled» обоснован в журнале замером того, что читает gate_changelog.changelog_gate_enabled.
AC-2 (negative): compose_project_tier(policy={task_done.changelog_gate.enabled: True}, local={...: False}) → True — локальный файл не может молча снять закоммиченное ужесточение (тест по образцу test_a_local_config_cannot_quietly_undo_a_committed_tightening); мутация «запись Guard снята» убивается этим тестом.
AC-3: resolve(project={task_done.changelog_gate.enabled: False}, trusted с True) → отклонение с именем ключа (Rejection), как для auto_verify; контроль: обычный неохраняемый ключ task_done.changelog_gate.files по-прежнему берётся из local.
AC-4: policy.json этого репозитория по-прежнему проходит test_this_repository_stays_strict_whatever_the_user_tier_says; CHANGELOG в обоих файлах; журнал закрытой задачи changelog-gate-double-registration уже несёт поправку.

## Plan

## Rollback

git revert коммита; без схемы и данных.

## Journal

- 2026-09-04T21:54:05Z [implementation] — ВЫБОР ФОРМЫ ЗАМЕРОМ: gate_changelog.changelog_gate_enabled (scripts/gate_changelog.py:100) и _read_changelog_gate_config читают cfg['task_done']['changelog_gate'] — это единственный путь выключателя, а gates.changelog.enabled реестр использует только для `gates status` через enabled_resolver. Перенос выключателя на gates.changelog.enabled дал бы ДВА места для одного выключателя (второй источник истины) и потребовал бы миграции policy.json и config.json на всех машинах. Поэтому охраняется ПУТЬ: Guard(('task_done','changelog_gate','enabled'), _weaker_when_false, default=False, note). Тесты: test_config_trust — ужесточение True проходит (параметризация), False под доверенным True отклоняется с ключом task_done.changelog_gate.enabled, соседний files остаётся проектным; test_config_policy — policy True / local False → True (зеркало test_a_local_config_cannot_quietly_undo_a_committed_tightening).
- 2026-09-04T21:55:34Z [implementation] — ЛЕНТА: test_config_trust + test_config_policy + test_changelog_gate + test_gate_degeneracy — 154 passed, 1 skipped; ruff/format/mypy чисто; config_trust.py 437 строк. МУТАЦИИ 3/3 после разбора выжившего: G1 запись Guard снята → убита зеркальным policy-тестом; G2 направление инвертировано (_weaker_when_true) → убита тестом отклонения под доверенным True; G3 дефолт перевёрнут в True → ВЫЖИЛА в первом проходе: все тесты проходили с охраной, которая принудительно включала бы changelog-гейт у любого проекта без доверенного тира. Разобрана ДО КОНЦА: добавлен test_the_changelog_switch_may_stay_off_where_nothing_turned_it_on (project False, trusted {} → без отклонений, False) — G3 убита им. Мутаторы удалены. Docs перечня охраняемых ключей не держат (grep пуст).
- 2026-09-04T21:56:25Z [implementation] — AC-1: ✓ scripts/config_trust.py GUARDS несёт Guard(('task_done','changelog_gate','enabled'), _weaker_when_false, False, note); выбор «охранять путь» обоснован в журнале замером gate_changelog.py:100 (единственный читатель пути). tests/test_config_trust.py::TestProjectMayOnlyTighten::test_tightening_key_passes_through (включение проходит) AC-2: ✓ tests/test_config_policy.py::test_the_changelog_switch_is_one_of_the_keys_the_local_file_cannot_undo (policy True / local False → True, files остаётся локальным). Negative: мутация G1 «запись снята» убита этим тестом AC-3: ✓ tests/test_config_trust.py::TestProjectMayOnlyTighten::test_the_changelog_switch_cannot_undercut_a_trusted_true (Rejection с ключом task_done.changelog_gate.enabled, files проектный); tests/test_config_trust.py::TestProjectMayOnlyTighten::test_the_changelog_switch_may_stay_off_where_nothing_turned_it_on (opt-in дефолт; убивает мутацию G3) AC-4: ✓ tests/test_config_policy.py::test_this_repository_stays_strict_whatever_the_user_tier_says зелёный; CHANGELOG.md и CHANGELOG.ru.md; журнал changelog-gate-double-registration-premise-unconfirmed несёт поправку Domain: слой доверия конфигурации (config_trust / config_policy), выключатель блокирующего гейта.
