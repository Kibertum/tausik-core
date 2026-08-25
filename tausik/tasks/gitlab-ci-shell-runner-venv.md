---
slug: gitlab-ci-shell-runner-venv
title: "Пайплайн под реальные раннеры: shell executor, venv, один python3"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: light
call_budget: 25
defect_of: gitlab-ci-linux-gate
scope: ".gitlab-ci.yml. Плюс тесты, которые первый Linux-прогон вскрыл как привязанные к машине: tests/test_doctor_auto_verify_hint.py (вычищает 2 CI-маркера из 10; на GitLab выживает GITLAB_CI), tests/test_bootstrap_extension_skills.py (требует gitignored skills-official/, на чистом клоне его нет)."
scope_exclude: "Не менять код scripts/ и tests/. Не поднимать docker-раннер — это админская работа на сервере пользователя."
relevant_files:
  - ".gitlab-ci.yml"
  - "tests/test_doctor_auto_verify_hint.py"
  - "tests/test_bootstrap_extension_skills.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-10T15:18:45Z"
---

## Goal

Первый прогон (pipeline 3624, sha fd803f3) упал. Причина, вычитанная в трейсе: 'Preparing the "shell" executor' — раннер common исполняет shell, а не docker, поэтому image: python:3.11 игнорируется. Джоб шёл на системном Debian-python 3.12, где pip install заблокирован PEP 668 (externally-managed-environment). Проверено, что docker-executor'а на инстансе нет вообще: чужой джоб с тегом docker-services (momlora, job 2119) в шапке трейса тоже даёт 'shell' executor. Значит матрица по образам python была фикцией. Переписать: venv на каждый джоб (обход PEP 668), системный python3, без матрицы — нам нужен был Linux, а версии python покрывает GitHub перед релизом. gen_doc_constants на stdlib, ему venv не нужен вовсе. GIT_CLEAN_FLAGS=-ffdx: shell-раннер переиспользует рабочий каталог, .tausik/ и .ci-venv обязаны исчезать между прогонами.

## Acceptance Criteria

1) Пайплайн зелёный на GitLab — проверено через glab, а не предположено. 2) Ни один джоб не полагается на image:. 3) pip ставится в venv, PEP 668 не срабатывает. 4) Рабочий каталог чистится между прогонами (GIT_CLEAN_FLAGS=-ffdx), иначе .tausik/ от прошлого джоба искажает bootstrap. 5) git-конфиг задаётся job-локально (GIT_CONFIG_GLOBAL в файл внутри рабочего каталога), а не в ~/.gitconfig раннера — иначе испортим чужие пайплайны на общем shell-раннере. Негативные сценарии: 6) Ошибка, если объявить пайплайн рабочим, не посмотрев статус через glab. 7) Ошибка, если venv-модуль на раннере отсутствует — тогда падать явно, а не тихо ставить пакеты в систему через --break-system-packages. 8) Ошибка, если тесты гоняются без bootstrap: mirror-sync упадёт с FileNotFoundError на .claude/settings.json.

## Plan

## Rollback

git revert коммита с пайплайном; либо rm .gitlab-ci.yml — репозиторий возвращается к состоянию без CI.

## Journal

- 2026-07-10T15:18:33Z [implementation] — AC verified: 1. ✓ Пайплайн 3626 (sha fcc3e5f) — status=success, все три джоба зелёные; проверено через glab api, а не предположено. 2. ✓ image: удалён полностью. 3. ✓ pip ставится в venv (/tmp/tausik-ci-venv-$CI_JOB_ID, подтверждено в трейсе), PEP 668 не срабатывает. 4. ✓ GIT_CLEAN_FLAGS=-ffdx. 5. ✓ GIT_CONFIG_GLOBAL указывает на /tmp/tausik-ci-gitconfig-$CI_JOB_ID — ~/.gitconfig раннера не трогается. 6. ✓ (негативный) Статус смотрел через glab; предыдущие два прогона (3624 failed, 3625 failed) разобраны по трейсам. 7. ✓ (негативный) `python3 -m venv --help || exit 1` — при отсутствии venv падаем явно, --break-system-packages не используется. 8. ✓ (негативный) bootstrap остался в before_script. Прогон на Linux: 4299 passed, 121 skipped, 108 deselected. Сумма собранных совпала с Windows (4408+12=4420 = 4299+121), значит расхождения счётчика больше нет. Root cause (config-error): пайплайн был написан под docker-executor, которого на инстансе нет. 'Preparing the "shell" executor' в трейсе 3624; чужой джоб с тегом docker-services (momlora, job 2119) даёт то же. image: игнорируется молча — GitLab не считает это ошибкой. Prevention: перед тем как опираться на image:, прочитать шапку трейса существующего джоба; для shell-раннера venv обязателен, а всё, что создаётся внутри рабочего каталога, попадает под инструменты, которые ходят по дереву. Первый Linux-прогон окупил себя четырежды, и все четыре — один класс «зелено благодаря машине»: (1) джоб doc-constants не мог упасть: count_tests при отсутствии pytest ловит исключение и подставляет значение с диска, сравнивая файл сам с собой; (2) test_count зависел не от платформы, а от установленных пакетов — 4540-4504=36 = 15+21 тестов в двух модулях с importorskip('yaml'); (3) test_ble001_enforced зовёт `python -m ruff`, локально проходил на системном ruff; (4) test_doctor_auto_verify_hint чистил 2 CI-маркера из 10, GITLAB_CI выживал — тест был привязан к GitHub Actions. Плюс test_no_recommendation_is_a_phantom требует gitignored skills-official/ (теперь skip с объяснением), и ruff поймал pytest.skip в файле без import pytest — ветка локально не исполняется, на CI дала бы NameError. Domain: пайплайн проверен там, где он живёт — на GitLab, тремя последовательными прогонами (3624 failed -> 3625 failed -> 3626 success), каждый разобран по трейсу.
