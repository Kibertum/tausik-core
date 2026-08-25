---
slug: github-scrub-site
title: "Вычистить сайт из GitHub orphan-снапшота"
status: done
epic: site-standalone-agent-ready
story: core-github-cleanup
complexity: complex
role: devops
stack: null
tier: moderate
call_budget: 60
defect_of: null
scope: "github remote (tausik-core): branch main (orphan rebuild), tag v1.5.6, gh release"
scope_exclude: "gitlab core (уже почищен); рабочее дерево (не менять)"
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-28T13:08:52Z"
---

## Goal

Пересобрать orphan-снапшот GitHub без сайтовых файлов (site/, Dockerfile, .dockerignore, .gitlab-ci.yml, nginx.conf), force-push через +refspec (паттерн memory #181), провести leak-аудит — на GitHub остаётся только фреймворк. Обновить тег v1.5.6 при необходимости.

## Acceptance Criteria

1. github/main пересобран как single orphan-commit из чистого core HEAD (без site/, Dockerfile, .dockerignore, .gitlab-ci.yml). 2. force-push выполнен через +refspec. 3. LEAK-АУДИТ: git ls-tree -r github/main не содержит site/, Dockerfile, .dockerignore, .gitlab-ci.yml и confidential (docs/audit, _archive, _internal). 4. Тег v1.5.6 и gh release не содержат site-файлов (re-tag/edit при необходимости). 5. ГРАНИЧНЫЙ/негативный: ни один framework-файл НЕ пропал — comm(core HEAD, github/main) по framework-файлам пуст (force-push не уронил трекаемые файлы, memory #180). Старый github main SHA 6b1fe05 сохранён для отката.

## Plan

## Rollback

Сохранён прежний github main SHA 6b1fe05 (и тег 26c3afd). Откат: git push github +6b1fe05:main и восстановить тег. Локальная ветка-orphan удаляется, рабочее дерево/HEAD core не затрагиваются.

## Journal

- 2026-06-28T13:08:23Z [implementation] — AC verified: 1. ✓ orphan f380a2e собран из чистого core HEAD (commit-tree, parentless). 2. ✓ force-push +refspec: github main 6b1fe05→f380a2e, tag v1.5.6 26c3afd→f419df3→f380a2e. 3. ✓ leak-audit: git ls-tree github/main и tag — site/Dockerfile/.gitlab-ci/_archive/_internal отсутствуют (grep пусто). 4. ✓ тег v1.5.6 и gh release указывают на чистый f380a2e (release source следует за тегом). 5. ✓ no framework drop: 816 файлов, comm(new orphan, github/main)=0 added / только 15 site удалены. Откат-SHA 6b1fe05 сохранён. verify #927.
- 2026-06-28T13:08:51Z [implementation] — AC verified: 1. ✓ orphan f380a2e (commit-tree, parentless). 2. ✓ force-push +refspec: main 6b1fe05→f380a2e, tag 26c3afd→f380a2e. 3. ✓ leak-audit чист (site/Dockerfile/_archive/_internal отсутствуют). 4. ✓ tag v1.5.6 + gh release на чистом f380a2e. 5. ✓ 816 файлов, 0 framework dropped, только 15 site удалены. Откат 6b1fe05. verify #927. Знание: memory #185.
