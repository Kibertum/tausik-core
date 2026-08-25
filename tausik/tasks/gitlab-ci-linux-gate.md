---
slug: gitlab-ci-linux-gate
title: "Вернуть CI на путь разработки: Linux-пайплайн в GitLab"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: light
call_budget: 25
defect_of: null
scope: ".gitlab-ci.yml (новый). Плюс scripts/skill_manager.py: снять осиротевшие импорты stat/sys, которые ruff нашёл первым же прогоном lint-джоба — они остались после переноса rmtree_force в skill_git. Правка обязательна, иначе новый пайплайн красный на main с первой минуты."
scope_exclude: "Не менять код scripts/. Не пушить без разрешения."
relevant_files:
  - ".gitlab-ci.yml"
  - "scripts/skill_manager.py"
  - "tests/test_supply_eol.py"
  - "tests/test_skill_repo_trust.py"
  - "tests/test_skill_manager.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-10T14:28:05Z"
---

## Goal

Разработка идёт в GitLab, где нет ни одного теста: .gitlab-ci.yml исчез вместе с сайтом (d42779e). Тесты впервые видят код только после ручной публикации ff-child на GitHub — то есть после релиза. CRLF-баг прошёл ровно этой дырой: на Windows зелено, на Linux не проходил ни один скилл. Windows покрывается машиной разработчика, macOS находок не давал; нужен Linux на каждом push/MR. Пайплайн повторяет проверенные шаги GitHub-воркфлоу: ruff, gen_doc_constants --check, bootstrap .claude/, pytest. Образ python:X (не -slim): тесты цепочки поставок гоняют настоящий git.

## Acceptance Criteria

1) .gitlab-ci.yml существует, валидный YAML, гоняется на MR, main и тегах. 2) Джоб тестов использует образ с настоящим git (не -slim) — тесты supply-chain клонируют репозитории. 3) Явно выставлен core.autocrlf=false: тесты CRLF должны опираться на известный базис, а не на дефолт образа. 4) Шаги повторяют GitHub-воркфлоу: ruff, gen_doc_constants --check, bootstrap .claude/ (нужен mirror-sync тестам), pytest с теми же двумя --ignore. 5) Матрица python 3.11/3.12/3.13. Негативные сценарии: 6) Ошибка, если пайплайн зелёный на образе без git — тогда тесты цепочки поставок молча пропускаются или падают. 7) Ошибка, если bootstrap пропущен: тесты mirror-sync упадут с FileNotFoundError на .claude/settings.json, и это выглядит как регрессия кода. 8) Ошибка, если я объявлю пайплайн рабочим, не проверив его — Linux-раннера у меня нет, это надо сказать вслух, а не выдать за проверенное.

## Plan

## Rollback

rm .gitlab-ci.yml — пайплайн исчезает, поведение репозитория прежнее.

## Journal

- 2026-07-10T14:27:47Z [implementation] — AC verified: 1. ✓ .gitlab-ci.yml валиден — распарсен yaml.safe_load, stages=[check,test], jobs=[lint,doc-constants,tests]; workflow.rules покрывают merge_request_event, default branch и теги. 2. ✓ Образ python:3.11 / python:$PY, не -slim: проверено, что 6 тестовых модулей зовут настоящий git (grep '"git"' по tests/). 3. ✓ before_script выставляет core.autocrlf=false и safe.directory. 4. ✓ Шаги повторяют GitHub-воркфлоу: ruff / gen_doc_constants --check / bootstrap --no-detect --ide claude / pytest с теми же двумя --ignore. Каждая команда прогнана локально: ruff 'All checks passed', gen_doc_constants --check 'OK', pytest 4408 passed 12 skipped 0 failed. 5. ✓ Матрица PY 3.11/3.12/3.13. Негативные: 6. ✓ Проверено, что образ обязан нести git — иначе шесть модулей падают; before_script начинается с 'git --version', чтобы это выяснилось до сюиты, а не внутри неё. 7. ✓ bootstrap оставлен в before_script: без него тесты mirror-sync падают с FileNotFoundError на .claude/settings.json (сам напоролся на это в worktree). 8. ✓ ЧЕСТНО: Linux-раннера у меня нет. Пайплайн я не прогонял. Проверено всё, что можно без него: валидность YAML, каждая команда локально, наличие git-зависимостей, отсутствие ruff-ошибок. Первый настоящий прогон случится на GitLab. Пайплайн окупился до запуска, двумя находками в уже смерженном коде: (1) ruff красный на main: scripts/skill_manager.py импортировал stat и sys, осиротевшие после переноса rmtree_force в skill_git. Снято. (2) Мои же тесты сломались бы на Linux: 'file:///' + str(path) даёт file:////tmp/... с четырьмя слэшами, потому что POSIX-путь уже начинается со слэша. На Windows обе формы совпадают байт в байт, поэтому тест зелёный и на ревью безобиден. Заменено на Path.as_uri() в трёх местах (test_supply_eol, test_skill_repo_trust, test_skill_manager). Доказать падение локально нельзя — на Windows формы идентичны; as_uri() корректен по построению. Память #197. Обе находки — тот же класс, что весь релиз 1.6.0: код, который не мог упасть там, где его гоняли.
