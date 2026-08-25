---
slug: bootstrap-drift-gate-blind-to-hooks-subdir
title: "bootstrap_drift гейт слеп к scripts/hooks/** — частичный деплой ломает ВСЕ хуки ImportError'ом"
status: done
epic: null
story: null
complexity: medium
role: architect
stack: null
tier: null
call_budget: null
defect_of: null
scope: "scripts/service_doctor_drift.py, tests/test_bootstrap_drift_gate.py (или существующий тест-модуль дрейфа), CHANGELOG.md, CHANGELOG.ru.md"
scope_exclude: "bootstrap_check.check_deployed_trees и harness-фан-аут — другой комパrator и другой класс. Сам gate_bootstrap_drift.py (только потребитель, менять нечего). Список SCAFFOLD_IDES. Генерируемые файлы (settings.json/CLAUDE.md/.cursorrules) — не копии исходников, сравнение с источником бессмысленно. skills/stacks/references — config-зависимые деревья, объявленная граница задачи bootstrap-drift-harness-tree-ungated."
relevant_files:
  - "scripts/service_doctor_drift.py"
  - "tests/test_bootstrap_drift_gate.py"
  - "docs/_generated/constants.json"
  - README.md
  - README.ru.md
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-23T23:27:14Z"
---

## Goal

Ревью s128 (META, pre-existing, но обострено этой сессией). service_doctor_drift.scripts_drift_names (:187) делает os.listdir(scripts) НЕрекурсивно и сравнивает только scripts/*.py — scripts/hooks/**/*.py (и scripts/providers/**) НЕ проверяются гейтом, хотя деплоятся в .{ide}/scripts/hooks/. Сессия #128 ввела ПЕРВУЮ cross-file зависимость внутри hooks/: _common.py импортирует hook_supervision.py. Если развёрнутая копия _common.py обновится без hook_supervision.py рядом, КАЖДЫЙ хук, импортирующий _common, упадёт module-level ImportError на каждом tool-call до передеплоя — а гейт этого не увидит. Сейчас hook_supervision.py корректно развёрнут во все 5 профилей (проверено), немедленной поломки нет. Фикс: scripts_drift_names обходит scripts/ РЕКУРСИВНО (os.walk, относительные пути .{ide}/scripts/<relpath>), покрывая hooks/ и providers/. ВНИМАНИЕ: проверить, что ВСЕ подкаталоги scripts/ реально деплоятся во все профили — иначе рекурсия даст false-positive drift на не-деплоящихся каталогах; при необходимости whitelist/skip. Гейт чувствительный (сам механизм enforcement) — отдельная верификация + тесты на false-positive.

## Acceptance Criteria

1. `service_doctor_drift.scripts_drift_names` обходит `scripts/` РЕКУРСИВНО и потому видит дрейф в `scripts/hooks/**` и `scripts/providers/**`; относительный путь репортится как `.{ide}/scripts/<relpath>` с forward-slash.
2. Набор сравниваемых файлов совпадает с тем, что реально деплоит `bootstrap_copy.copy_dir` (единственный производитель): рекурсивно ВСЕ файлы, кроме `__pycache__/`, `.git/` и `*.pyc`. Не `.py`-only — иначе компаратор судит по другому правилу, чем копировщик, и разъедется с ним (conv #266).
3. NEGATIVE — нет false-positive: чистое дерево после `bootstrap --ide all` даёт пустой список; отсутствующий профиль по-прежнему пропускается (не дрейф); отсутствующий `scripts/` по-прежнему даёт `None`, а не `[]` (два разных пустых, каллеры реагируют по-разному).
4. NEGATIVE — файл, лежащий ТОЛЬКО в профиле (`vendor_seo/`, `.pyc`), не считается дрейфом: гейт ловит «правка не доехала», а не «в профиле есть лишнее».
5. Тест, доказывающий ИМЕННО закрытую дыру: расхождение подставляется в `.{ide}/scripts/hooks/<файл>.py` и обязано быть найдено (на старом коде тест падает).
6. Тест, механически связывающий правила игнора компаратора с правилами `copy_dir`, — чтобы расхождение с копировщиком ловилось сборкой, а не следующим инцидентом.
7. CRLF→LF нормализация сохранена (кросс-платформенный чекаут не должен давать ложный дрейф).
8. Все гейты зелёные; полный прогон pytest зелёный.
CHANGELOG.md [Unreleased] и зеркало CHANGELOG.ru.md обновлены прозаической записью об этом изменении.

## Plan

## Rollback

git revert коммита — изменение локализовано в scripts_drift_names (одна функция) плюс тесты. Гейт bootstrap_drift независимо выключается через .tausik/config.json -> gates.bootstrap_drift.enabled=false, если рекурсия даст неожиданный false-positive у потребителя.

## Journal

- 2026-07-23T23:17:02Z [implementation] — Реализовано. Ключевое решение: набор сравниваемых файлов выведен не «рекурсивно все .py», а «ровно то, что деплоит copy_dir» — рекурсивно ВСЁ, минус __pycache__/, .git/, *.pyc. Компаратор, судящий по правилу УЖЕ, чем у копировщика, которого он проверяет, — это та же «вторая копия правила» (conv #266) этажом ниже; scripts/hooks/pre-commit (shell) — тоже цель деплоя, и старый .py-фильтр его не видел. Проверка на живом дереве до передеплоя: 287 файлов в сравнении (было ~255 верхнего уровня), из них 30 в hooks/, не-.py — README.md и hooks/pre-commit. Дрейф после `bootstrap --ide all` = []. False-positive от vendor_seo/ нет (обход идёт от ИСХОДНИКА, лишнее в профиле не считается). Перевёрнут существующий тест test_non_py_files_are_ignored: он утверждал, что устаревший не-.py файл сообщать НЕ надо, — то есть закреплял ровно узкое правило, которое и было дефектом. Не удалён, а переписан с обоснованием, чтобы следующий читатель понял, почему прежнее утверждение было ошибочным. Новый тест test_comparator_ignore_rules_match_the_real_copier связывает правила игнора ПОВЕДЕНЧЕСКИ: запускает настоящий bootstrap_copy.copy_dir во временную цель и сравнивает множество файлов. Не сравнение строк — изменение копировщика уронит сборку, а не сожмёт проверку молча. Доказательство неваккуумности: прогон новых тестов против застэшенной старой реализации — 5 падают, на новой все 19 зелёные.
- 2026-07-23T23:27:12Z [implementation] — AC1 ✓ scripts_drift_names обходит scripts/ рекурсивно через новый _deployed_relpaths (os.walk); путь репортится как .{ide}/scripts/<relpath> с forward-slash. Живая проверка: 287 файлов в сравнении против ~255 верхнего уровня, из них 30 в hooks/. AC2 ✓ Набор файлов = ровно то, что деплоит bootstrap_copy.copy_dir: рекурсивно ВСЁ, минус __pycache__/, .git/, *.pyc. НЕ .py-only — иначе компаратор судит по более узкому правилу, чем копировщик, которого проверяет (conv #266); scripts/hooks/pre-commit — shell-файл и тоже цель деплоя, старый фильтр его не видел. AC3 NEGATIVE ✓ После bootstrap --ide all дрейф = [] на реальном дереве (проверено вживую). test_absent_profile_is_not_drift, test_no_profiles_at_all_is_clean_not_none, test_missing_source_dir_is_none — два разных пустых сохранены. AC4 NEGATIVE ✓ test_profile_only_file_is_not_drift (vendor_seo/) и test_pycache_and_git_are_not_compared. Обход идёт от ИСХОДНИКА, поэтому лишнее в профиле структурно не может стать дрейфом. AC5 ✓ test_drift_inside_hooks_subdir_is_found + test_missing_file_inside_a_subdir_is_found (именно сценарий _common.py без hook_supervision.py) + test_nested_providers_subdir_is_covered. ДОКАЗАНО неваккуумными: прогон против застэшенной старой реализации — 5 новых тестов падают, на новой все 19 зелёные. AC6 ✓ test_comparator_ignore_rules_match_the_real_copier — связь ПОВЕДЕНЧЕСКАЯ, а не сравнение строк: запускает настоящий copy_dir во временную цель и требует равенства множества файлов. Изменение копировщика уронит сборку, а не сожмёт проверку молча. AC7 ✓ CRLF→LF нормализация сохранена; test_crlf_normalisation_is_not_drift зелёный. AC8 ✓ Полный прогон 5554 passed / 23 skipped / 0 failed; ruff All checks passed; verify #1229 подписан. CHANGELOG ✓ [Unreleased] EN + RU-зеркало. Domain: вопрос гейта — «доехала ли правка исходника до исполняемой копии». Компаратор теперь спрашивает у того же производителя (copy_dir), что именно должно было доехать, поэтому ответ осмыслен вне тестов: на реальном дереве до передеплоя он назвал ровно отредактированный файл в 5 профилях и ничего лишнего, после передеплоя — пусто. Root cause: компаратор и копировщик были двумя независимыми формулировками одного правила; узкая (os.listdir + .py) отставала от широкой (copy_dir всего дерева) молча, потому что расхождение ничем не проверялось. Устранено не расширением узкой формулы, а привязкой её к производителю тестом.
