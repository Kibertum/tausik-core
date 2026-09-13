---
slug: dev-lane-tests-are-hostage-to-the-runner-environment
title: "Лента GitLab на ветке разработки красная с 07.09: три теста читают состояние машины (реестр official, глубина клона, живая БД), а не своё"
status: done
epic: release-19-agent-effectiveness
story: verification-off-the-critical-path
complexity: medium
role: qa
stack: python
tier: moderate
call_budget: 50
defect_of: null
scope: "tests/test_code_counts.py, tests/test_renar_manifest_chain.py, tests/test_prose_arguments_are_not_redirections.py, CHANGELOG.md, CHANGELOG.ru.md"
scope_exclude: ".gitlab-ci.yml не менять (GIT_DEPTH — выбор владельца, обозначенный комментарием); хук bash_write_gate не менять; push запрещён."
relevant_files:
  - "tests/test_code_counts.py"
  - "tests/test_renar_manifest_chain.py"
  - "tests/test_prose_arguments_are_not_redirections.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - "docs/en/whats-new-1.9.md"
  - "docs/ru/whats-new-1.9.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-09-13T13:30:32Z"
---

## Goal

ЗАМЕР, смена #251, `glab ci list`: последний зелёный пайплайн v1-9-wave — #7078 (cf263bb0, 2026-09-07); с тех пор все красные, tests-full ни разу не запускался (skipped за stage). Пайплайн #7485 (e4f7380c): 14 failed. Три причины, и все — окружение раннера, не код: (1) tests/test_code_counts.py::test_the_live_tree_counts_what_it_ships: `(count_official_skills(_REPO_ROOT) or 0) >= 20` — на чистом клоне skills-official/ отсутствует по .gitignore, функция ВОЗВРАЩАЕТ None и сама документирует «NONE MEANS THE SOURCE IS NOT HERE», а тест превращает None в 0 и требует ≥20; (2) tests/test_renar_manifest_chain.py::test_the_committed_manifest_chain_resolves: докстринг обещает пропуск на shallow-клоне, но пропускает только при ПУСТОМ `git log`; при GIT_DEPTH=50 (.gitlab-ci.yml) прошлая версия манифеста за горизонтом → «git holds no manifest with that id and version; known: [(21, …)]»; сегодня v22 заменяет v21 (5707501a, >50 коммитов назад) — упадёт снова; (3) tests/test_prose_arguments_are_not_redirections.py::TestДыраНеОткрыта::test_живой_хук_по_прежнему_блокирует[12 кейсов]: хук гоняется с CLAUDE_PROJECT_DIR=_REPO против ЖИВОГО репозитория; bash_write_gate возвращает 0, если .tausik/tausik.db нет (CI после bootstrap --no-detect без единого вызова CLI) — и вернёт 0 локально, если активная задача без scope_paths (legacy freedom). Тест доказывает свойство хука через состояние чужого проекта. Починка: (1) реестр отсутствует → pytest.skip с причиной (None ≠ 0, как говорит сама функция), присутствует → ≥20; (2) `git rev-parse --is-shallow-repository` == true и предыдущая версия не найдена → skip с причиной; в полном клоне — прежний assert; (3) хук гоняется против ВРЕМЕННОГО проекта с созданной БД без активных задач (как соседние хук-тесты), и второй кейс — с активной задачей, объявившей scope_paths, не включающей zzz.txt. Проверка: полный прогон в чистом shallow-клоне (git clone --depth 50 file://…) во временный каталог с bootstrap --no-detect --ide all — та же процедура, что в .gitlab-ci.yml, на этой машине; push для проверки не делается (запрет владельца).

## Acceptance Criteria

AC-1: test_the_live_tree_counts_what_it_ships пропускается с причиной, когда реестр official отсутствует (None), и по-прежнему требует ≥20, когда он есть — оба пути доказаны (tmp без реестра / живое дерево). AC-2: НЕГАТИВ: test_the_committed_manifest_chain_resolves пропускается с причиной на shallow-клоне, где предыдущая версия за горизонтом, и по-прежнему даёт ошибку в полном клоне, если replaces указывает в пустоту (мутация: подменить replaces во временном полном клоне). AC-3: test_живой_хук_по_прежнему_блокирует гоняет хук против временного проекта со своей БД: без активной задачи — блок (Rule 1); с активной задачей и scope_paths, не покрывающим цель, — блок (Rule 2); с активной задачей без scope — пропуск (legacy freedom) назван отдельным кейсом. Ни один кейс не читает .tausik/ этого репозитория. AC-4: полный прогон в свежем shallow-клоне (--depth 50) во временном каталоге после bootstrap --no-detect --ide all — та же процедура, что .gitlab-ci.yml, — зелёный на этой машине; число passed/skipped записано в журнал. AC-5: signed verify.

## Plan

## Rollback

git revert; тесты вернутся к чтению живого окружения.

## Journal

- 2026-09-13T13:30:06Z [implementation] — AC-4 замер: свежий клон --depth 50 + bootstrap --no-detect --ide all + pytest -m '' → 10166 passed, 170 skipped, 0 failed (7:31), корневая БД не создана. В клоне глубины 5 manifest-chain и official-registry пропускаются с причиной; в полном клоне висячий replaces (v99) → failed; id, видимый под другой версией на shallow-клоне → failed, не skip (ревью). Ревью tausik-reviewer: 1 high (skip по паре версия+id прятал переиспользование id) — сужен до отсутствия id; 1 low (порог реестра дремлет на CI по построению) — принято как объявленное.
- 2026-09-13T13:30:28Z [implementation] — AC-1 ✓ tests/test_code_counts.py::test_the_official_registry_counts_when_it_is_here — в клоне без skills-official SKIPPED с причиной (журнал), на живом дереве registry=20 → passed. AC-2 ✓ (НЕГАТИВ) tests/test_renar_manifest_chain.py::test_the_committed_manifest_chain_resolves — клон --depth 5: SKIPPED «past the clone horizon»; полный клон с replaces=…@v99: FAILED «git holds no manifest»; shallow-клон с id, видимым под другой версией: FAILED, не skip (журнал). AC-3 ✓ tests/test_prose_arguments_are_not_redirections.py: фикстура hook_project (своя БД, ни одной активной задачи) — 12 кейсов IS_A_WRITE блокируются по Rule 1, 4 кейса NOT_A_WRITE проходят; ни один не читает .tausik/ репозитория; кейсы Rule 2 (scope_paths) и legacy freedom уже живут в tests/test_bash_write_gate_hook.py::TestHook::test_active_task_write_outside_scope_blocked и ::test_active_undeclared_task_write_allowed — не дублируются (правило дедупликации). AC-4 ✓ процедура .gitlab-ci.yml в свежем клоне --depth 50 на этой машине: 10166 passed, 170 skipped, 0 failed за 7:31. AC-5 ✓ verify #2597 подписан; CHANGELOG EN/RU. Domain: быстрая лента GitLab, красная с 07.09 не из-за кода, при следующем пуше зелёная на любом раннере — тесты меряют свой предмет, а не машину.
