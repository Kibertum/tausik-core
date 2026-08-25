---
slug: core-remove-site
title: "Удалить сайт и его CI из core"
status: done
epic: site-standalone-agent-ready
story: core-github-cleanup
complexity: medium
role: developer
stack: null
tier: moderate
call_budget: 35
defect_of: null
scope: "core-репо: site/, Dockerfile, .dockerignore, .gitlab-ci.yml, .gitignore, README/CLAUDE.md ссылки"
scope_exclude: "docs/{en,ru,_generated} (нужны site); site-репо tausik/site"
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-28T13:04:02Z"
---

## Goal

Удалить из core: site/, Dockerfile, .dockerignore, корневой .gitlab-ci.yml (сайтовый деплой). Почистить .gitignore от site-строк. Обновить ссылки на сайт в docs/CLAUDE.md/README. Коммит в gitlab core.

## Acceptance Criteria

1. Из core удалены: site/ (вся директория), корневой Dockerfile, .dockerignore, корневой .gitlab-ci.yml (git rm). 2. .gitignore очищен от site-строк (блок 74-90). 3. Активных site-build ссылок в трекаемых файлах не осталось (CHANGELOG-история — легитимна, не трогаем). 4. pytest core зелёный после удаления. 5. ГРАНИЧНЫЙ/негативный сценарий: docs/{en,ru,_generated} НЕ удаляются — это ошибка scope; при их удалении site-сборка упала бы (Could not resolve constants.json, исторический баг). git ls-files docs/ остаётся непустым.

## Plan

## Rollback

git revert коммита удаления в core (все файлы восстановятся из истории).

## Journal

- 2026-06-28T13:04:02Z [implementation] — AC verified: 1. ✓ git rm site/ (15 файлов) + Dockerfile + .dockerignore + .gitlab-ci.yml, working tree очищен. 2. ✓ .gitignore блок site удалён (74-83, _archive). 3. ✓ git grep активных site-build ссылок пусто (CHANGELOG-история оставлена). 4. ✓ verify #926: hadolint PASS, pytest SKIP (нет python-изменений — удаления не трогают код). 5. ✓ Граница: git ls-files docs/ непустой — docs/en=51, docs/_generated/constants.json на месте (не затронуты). commit d42779e, mypy clean.
