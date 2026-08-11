---
slug: doctor-drift-compares-the-host-scripts-root-not-the-libs
title: "doctor и гейт bootstrap_drift сравнивают с корнем scripts ХОСТА, а не с тем, откуда копирует bootstrap"
status: planning
epic: landscape-2026-h2
story: l26-narrative
complexity: medium
role: backend
stack: null
tier: moderate
call_budget: 40
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths:
  - "scripts/service_doctor_drift.py"
  - "scripts/*.py"
  - "tests/*.py"
scope_tools: []
completed_at: null
---

## Goal

Проверка дрейфа сравнивает ровно то дерево, из которого копирует bootstrap_copy: в потребительском проекте это .tausik-lib/scripts, а не собственные скрипты проекта.

## Acceptance Criteria

1. Источник разрешается ТАК ЖЕ, как его разрешает копировщик bootstrap_copy.copy_scripts (bootstrap/bootstrap_copy.py:254), а не переписывается вторым правилом. Тикеты: GitHub #7 и GitLab #3 — ОДИН дефект, заведённый дважды; закрывать оба.
2. Вендоренная раскладка ПОБЕЖДАЕТ: в потребительском репозитории существуют оба каталога, и <project>/scripts — это скрипты проекта, а не харнесса.
3. Тест-фикстура из тикета: .tausik-lib/scripts/a.py плюс посторонний scripts/deploy.sh; deploy.sh НИКОГДА не появляется в списке дрейфа, а правка развёрнутой копии a.py — появляется.
4. Разобрана ирония, названная в тикете: докстринг этого модуля ссылается на конвенцию #266 про вторую копию правила и совершает ровно этот дефект уровнем выше — на корне источника. Правка обязана не создать третью копию.
5. НЕГАТИВНЫЙ сценарий: ложное срабатывание на скриптах проекта считается провалом критерия — это симптом, с которого тикет начинается.
6. НЕГАТИВНЫЙ сценарий: слепота проверена отдельно от ложной тревоги. Полуприехавший деплой в .tausik-lib/scripts обязан быть НАЙДЕН; сегодня он рапортует чисто, и это вторая, более опасная половина дефекта.

## Plan

## Rollback

git revert коммита; правка в одной функции разрешения источника

## Journal
