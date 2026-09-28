---
slug: this-repos-strictness-lives-in-a-gitignored-file
title: "Строгость этого репозитория живёт в gitignored файле и не переживает клонирование"
status: done
epic: release-19-renar-conformance
story: evidence-primitives
complexity: medium
role: architect
stack: python
tier: moderate
call_budget: 50
defect_of: a-foreign-projects-config-weakens-qg2-in-our-own-repo
scope: "Носитель строгости — по решению AC1: tausik/ (отслеживаемое дерево), либо .gitignore, либо дефолты в scripts/project_config.py / scripts/config_trust.py. tests/ — новый тест на временном HOME. tests/test_config_trust.py — только докстринг класса TestBuiltinGateCommandOverride по AC4. CHANGELOG.md и CHANGELOG.ru.md. При выборе AC1(в) — bootstrap/, чтобы генератор не расходился с дефолтом."
scope_exclude: "~/.tausik/config.json — НЕ ТРОГАТЬ ни при каком варианте: тир общий для машины, ключи стоят под записанные причины другого проекта (vaflower, сессия #11; дедэнд #126). Правило слоёв и функции разрешения (project < user < managed, _weaker_*, Guard) не меняются — замером #193 доказано, что они исправны в обе стороны; предмет задачи в том, ГДЕ живёт проектное значение, а не в том, как оно разрешается. Утверждение модели угрозы в TestBuiltinGateCommandOverride по существу не пересматривается — уточняется только его область действия. .tausik/tausik.db и производные остаются gitignored при любом исходе."
relevant_files:
  - "scripts/config_policy.py"
  - "scripts/config_trust.py"
  - "scripts/project_config.py"
  - "scripts/gate_command_policy.py"
  - "scripts/gate_verify_first.py"
  - "tausik/policy.json"
  - "tests/test_config_policy.py"
  - "tests/test_config_trust.py"
  - "tests/test_gate_command_neutering.py"
  - "tests/test_opencode_bootstrap.py"
  - "docs/en/config-trust-tiers.md"
  - "docs/ru/config-trust-tiers.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-08-31T14:31:35Z"
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

ЗАМЕР #193, ПРЯМОЙ. Задача a-foreign-projects-config-weakens-qg2-in-our-own-repo вернула репозиторию строгость двумя ключами в .tausik/config.json (task_done.auto_verify=false, gates.bootstrap_drift.enabled=true). `git check-ignore -v` отвечает: `.gitignore:25:.tausik/`. То есть ужесточение НЕ ВЕРСИОНИРУЕТСЯ и не существует ни для кого, кроме этой рабочей копии.
СЛЕДСТВИЕ, НЕ ПРЕДПОЛОЖЕНИЕ: агент на другой машине, в CI или в свежем клоне получает конфигурацию из СВОЕГО ~/.tausik/config.json. Если там стоит auto_verify=true — как стоит на этой машине ради проекта vaflower, — он закрывает задачи в обход подписанной квитанции и не узнает об этом: doctor скажет «no project-scope key weakens enforcement». Строгость релиза, заявленного как релиз про доказательства, держится на локальном файле одной рабочей копии.
BOOTSTRAP ЭТИ КЛЮЧИ НЕ ВОСПРОИЗВОДИТ, ЗАМЕРЕНО: bootstrap/bootstrap_templates.py упоминает auto_verify только в тексте документации, как ОПЦИЮ ОТКАЗА для CI (строки 30 и 132). Ни один генератор не пишет строгих значений — свежесозданный .tausik/config.json их не получит.
ВТОРАЯ ПОЛОВИНА НАХОДКИ, ТРЕБУЕТ РЕШЕНИЯ, А НЕ ТОЛЬКО ПРАВКИ: tests/test_config_trust.py:154 строит модель угрозы на прямо противоположном утверждении — «`.tausik/config.json` travels with the repo, so a clone could point `ruff.command` at any binary». Для проектов-потребителей, где .tausik/ закоммичен, это верно. Для ЭТОГО репозитория — нет. Одно и то же предложение описывает два несовместимых мира, и ни один машинный признак их не различает.

## Acceptance Criteria

AC1. РЕШЕНИЕ ПРИНЯТО И ЗАПИСАНО, А НЕ ВЫВЕДЕНО ИЗ УДОБСТВА. Выбрать одно из трёх и обосновать замером, а не вкусом: (а) версионировать строгость отдельным файлом, который .tausik/ не покрывает (например tausik/policy.json в уже отслеживаемом дереве); (б) снять .tausik/config.json из-под .gitignore, оставив gitignored только tausik.db и производные; (в) перенести строгость в код — сделать эти значения дефолтами фреймворка для случая lib_dir == project_dir. Отвергнутые варианты записать с причинами.
AC2. СТРОГОСТЬ ПЕРЕЖИВАЕТ КЛОНИРОВАНИЕ. Замер, а не рассуждение: в СВЕЖЕЙ рабочей копии (git clone или git worktree во временный каталог) при пользовательском тире с auto_verify=true эффективное значение обязано быть False. Сегодня оно True — предъявить обе цифры, до и после.
AC3. РЕШЕНИЕ НЕ ЛОМАЕТ ПРОЕКТЫ-ПОТРЕБИТЕЛИ. Свежий `tausik init` в чистом каталоге по-прежнему работает, и ни один из его сценариев не начинает требовать файла, которого генератор не создаёт. Замерить прогоном, а не чтением кода.
AC4. ПРОТИВОРЕЧИЕ С ТЕСТОМ РАЗРЕШЕНО ЯВНО. tests/test_config_trust.py:154 утверждает «`.tausik/config.json` travels with the repo». Либо утверждение уточняется (оно верно для потребителей, но не для этого репозитория, и тогда так и написано), либо становится верным здесь по AC1(б). Молча оставить два несовместимых мира под одним предложением нельзя: на этом утверждении держится модель угрозы проверки исполняемых файлов.
AC5. Строгость закреплена ТЕСТОМ, а не только файлом. Тест утверждает, что в этом репозитории auto_verify эффективно False и bootstrap_drift эффективно включён — при ЛЮБОМ содержимом пользовательского тира. Тест обязан работать на временном HOME и не читать настоящий ~/.tausik/config.json ни при каком исходе. Именно этого теста не хватало: закрытие a-foreign-projects-config-weakens-qg2-in-our-own-repo получило замечание «tier=high requires test-ref evidence — none found», и оно было справедливым.
AC6. НЕГАТИВНЫЙ СЦЕНАРИЙ: удаление принятого носителя строгости (файла, дефолта или записи — смотря что выбрано в AC1) обязано красить тест из AC5. Мутация по реальным байтам, возврат побайтовой копией со сверкой sha256, git checkout запрещён. Без этого AC5 доказывает лишь то, что файл лежит на диске.
AC7. Полная лента зелёная: `pytest -q` из PATH, 0 failed (память #450).

## Plan

## Rollback

git revert коммита. При исходе AC1(а) или AC1(в) правка добавляет отслеживаемый файл или дефолтные значения — откат возвращает нынешнее состояние, где строгость держится на локальном .tausik/config.json, и он от отката не страдает, потому что git о нём не знает. При исходе AC1(б) откат возвращает строку в .gitignore; уже закоммиченный к тому моменту config.json придётся снять из индекса отдельной командой, и это записывается в план заранее, а не выясняется при откате. Ни схемы, ни данных, ни продуктового поведения задача не трогает.

## Journal

- 2026-08-31T14:15:13Z [implementation] — Инвентарь прочтением (память #461 — прогоню живьём отдельно). Цепь: project_config.load_config -> config_trust.resolve(load_project_config()) -> enforce_project_tier + deep_merge(cleaned, trusted) + _restore_project_tightenings. Проектный тир = РОВНО один файл .tausik/config.json, и он gitignored (.gitignore:25 `.tausik/`). Пользовательский тир этой машины прочитан: task_done.auto_verify=true (ради vaflower), gates.bootstrap_drift.enabled=false (дедэнд #126). Значит в свежем клоне оба ужесточения исчезают. ПРЕЦЕДЕНТ УЖЕ ЕСТЬ И НАЙДЕН: tausik/gates.json — закоммиченный, branch-coupled носитель политики, его собственный _comment говорит дословно «Lives in the non-dotted tausik/ projection (NOT the gitignored .tausik/) so a fresh clone carries it». Но читают его ad-hoc отдельные гейты (gate_filesize._resolve_exempts, gate_class_surface), а не загрузчик конфига — то есть образец есть, обобщения нет.
- 2026-08-31T14:24:23Z [implementation] — ЗАМЕРЫ. AC2 до: свежий worktree HEAD при пользовательском тире auto_verify=true -> auto_verify=True, bootstrap_drift=False, отклонений 0. AC2 после: та же свежая копия с tausik/policy.json (и БЕЗ .tausik/ вовсе) -> auto_verify=False, bootstrap_drift=True. Рабочая копия: тоже False/True. AC3 живьём: tausik init в пустом каталоге отработал, tausik/ не создаёт, ни один сценарий файла не требует; doctor там печатает ровно наоборот — ослабление пользовательского тира IN EFFECT, что и должно быть у потребителя. AC6: 4 мутации по каждому исправленному месту отдельно (носитель, load_policy, restore_tightenings в compose, проводка в load_config_with_rejections) — 4/4 KILLED, SETUP-FAIL 0, RESTORE-FAIL 0 (сверка sha256, git checkout не применялся). ЧЕСТНАЯ ГРАНИЦА, ЗАМЕРЕНА: враждебный policy.json с auto_verify=true на ЭТОЙ машине НЕ отклоняется — baseline берётся из доверенного тира, где auto_verify уже true, и кандидат не слабее baseline. Ровно то же происходит при той же записи в .tausik/config.json. То есть переезд даёт ОХВАТ, а не власть; поведение охранника не изменилось ни в какую сторону. qg0.scope_hard_gate=false из policy.json отклоняется, потому что доверенный тир молчит. РАСШИРЕНИЕ SCOPE ЯВНОЙ ЗАПИСЬЮ (память #451, как в #196). Утверждение «.tausik/config.json travels with the repo» найдено grep-ом в 8 местах, а не в одном, названном AC4: scripts/config_trust.py (докстринг модуля), gate_command_policy.py:149, gate_verify_first.py:328, project_config.py:367, tests/test_config_trust.py:154, tests/test_gate_command_neutering.py:7, tests/test_opencode_bootstrap.py:393, плюс таблицы тиров в docs/{en,ru}/config-trust-tiers.md. Правлю все: оставить семь копий ложного предложения и починить восьмую значит ровно тот дефект, который AC4 запрещает.
- 2026-08-31T14:31:32Z [implementation] — AC1 pass — решение #287 записано с обоснованием ЗАМЕРОМ. Выбран вариант (а): закоммиченный tausik/policy.json как ВТОРАЯ ПОЛОВИНА проектного тира. Отвергнутые с причинами: (в) строгость в дефолты фреймворка — НЕВОЗМОЖНО МЕХАНИЧЕСКИ, auto_verify=False уже дефолт (config_trust.GUARDS), а дефолт проигрывает доверенному тиру; по строгости с доверенными сравнивается ТОЛЬКО проектный тир. (б) снять .tausik/config.json из-под .gitignore — файл генерируемый (_meta.generated_at, _meta.lib_commit, installed_skills, brain.database_ids), дерево пачкалось бы каждым bootstrap. Прецедент найден в дереве, а не изобретён: tausik/gates.json, его _comment дословно «so a fresh clone carries it». | AC2 pass — ОБЕ ЦИФРЫ ПРЕДЪЯВЛЕНЫ. ДО: свежий git worktree HEAD при пользовательском тире task_done.auto_verify=true даёт auto_verify=True, gates.bootstrap_drift.enabled=False, отклонений 0 (отсутствующему проектному тиру нечего отклонять). ПОСЛЕ: та же свежая копия, .tausik/ нет вовсе, только tausik/policy.json — auto_verify=False, bootstrap_drift=True. Закреплено тестом tests/test_config_policy.py::test_a_fresh_copy_with_no_local_config_is_still_strict. | AC3 pass — ЗАМЕРЕНО ПРОГОНОМ, не чтением кода: tausik init в пустом каталоге отработал (Project 'freshinit' initialized), каталог tausik/ не создаёт, status и doctor работают; doctor там печатает ослабление пользовательского тира как IN EFFECT — то есть у проекта-потребителя поведение прежнее. FAIL-ы того doctor — «no .claude/skills/ — run bootstrap», к правке отношения не имеют. Тест: test_a_project_with_no_policy_resolves_exactly_as_before. | AC4 pass — противоречие разрешено ЯВНО и во ВСЕХ местах. grep нашёл утверждение «.tausik/config.json travels with the repo» в ВОСЬМИ местах, а не в одном названном в AC4 (память #451): scripts/config_trust.py (докстринг модуля), gate_command_policy.py, gate_verify_first.py, project_config.py, tests/test_config_trust.py:154, tests/test_gate_command_neutering.py, tests/test_opencode_bootstrap.py, плюс таблицы тиров в docs/en/config-trust-tiers.md и docs/ru/config-trust-tiers.md. Все теперь называют ТИР, а не один из двух его файлов; в test_config_trust.py:154 два мира разведены поимённо — верно для потребителей, ЛОЖНО здесь, и почему. Расширение scope записано в журнал задачи явной строкой, а не молча. | AC5 pass — новый tests/test_config_policy.py, 16 тестов. Ядро: test_this_repository_stays_strict_whatever_the_user_tier_says параметризован ЧЕТЫРЬМЯ пользовательскими тирами (молчащий, auto_verify=on, drift=off, оба ослаблены) и требует auto_verify is False и bootstrap_drift is True; test_the_managed_tier_cannot_relax_them_either закрывает managed-тир. Фикстура sealed_home перенаправляет TAUSIK_USER_CONFIG И HOME/USERPROFILE, поэтому настоящий ~/.tausik/config.json недостижим ни на одном пути, включая fallback при снятом env. test_the_policy_is_tracked_by_git утверждает то, чего значения выразить не могут: носитель отслеживается git и не попадает под .gitignore. | AC6 pass — 4 мутации, по КАЖДОМУ исправленному месту отдельно (память #449): M1 носитель (auto_verify false->true в tausik/policy.json), M2 загрузчик (load_policy перестаёт находить файл), M3 арбитраж (restore_tightenings в compose_project_tier снят), M4 проводка (load_config_with_rejections возвращается к локальному файлу). 4/4 KILLED, SETUP-FAIL 0 (якорь в ОДНУ строку, харнесс требует count==1, память #457), RESTORE-FAIL 0 — возврат побайтовой копией со сверкой sha256, git checkout не применялся. | AC7 pass — полная лента pytest из PATH с -p no:cacheprovider (память #450): 7493 passed, 24 skipped, 0 failed за 80.65 с; было 7477, прирост ровно на 16 новых. mypy и ruff по затронутым файлам чисто. Квитанция: verification_run #1902, signed, key 103a83a212851018, scope=high. | ЧЕСТНАЯ ГРАНИЦА, ЗАМЕРЕНА И НЕ СКРЫТА: враждебный policy.json с auto_verify=true на ЭТОЙ машине НЕ отклоняется — baseline берётся из доверенного тира, где ключ уже true, и кандидат не слабее baseline. Ровно то же происходит при той же записи в .tausik/config.json, то есть поведение охранника не изменилось ни в какую сторону: переезд даёт ОХВАТ, а не власть. Тест test_policy_may_not_weaken_a_guarded_key закрепляет отклонение там, где доверенный тир молчит (qg0.scope_hard_gate).
