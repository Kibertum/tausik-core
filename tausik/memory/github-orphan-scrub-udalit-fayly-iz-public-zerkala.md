---
slug: github-orphan-scrub-udalit-fayly-iz-public-zerkala
title: "GitHub orphan-scrub: удалить файлы из public-зеркала"
type: pattern
tags:
  - force-push
  - github
  - leak-audit
  - orphan
  - release
  - site
task: github-scrub-site
edges: []
---

Чтобы убрать файлы (напр. site/) из github orphan-снапшота, НЕ редактируя историю поштучно: 1) `TREE=$(git rev-parse HEAD^{tree}); NEW=$(git commit-tree "$TREE" -m "<тот же message>")` — создаёт parentless orphan-коммит из ТЕКУЩЕГО чистого дерева (site уже удалён из core). 2) Перед push — leak-audit дельты: `comm -23 <(git ls-tree -r --name-only github/main|sort) <(git ls-tree -r --name-only $NEW|sort)` должен показать ТОЛЬКО намеренно удаляемые файлы, а `comm -13 ...` (added) = пусто (memory #180: force-push не должен ронять framework-файлы). 3) push-ok (тикет привязан к core HEAD, цель push'а не проверяется) затем `git push github +$NEW:refs/heads/main`. 4) Дуальный тег: github v1.5.6 и main указывали на один orphan-коммит. Re-point через ВРЕМЕННЫЙ annotated-тег чтобы не трогать локальный/gitlab тег: `git tag -f -a _tmp $NEW -m ...; git push github +_tmp:refs/tags/vX; git tag -d _tmp`. 5) gh release source-архив следует за тегом — отдельно править не нужно (если нет вручную загруженных ассетов). 6) Финальный аудит: re-fetch, `git ls-tree -r github/main | grep -iE "site/|Dockerfile|_archive|_internal"` пусто. gh аутентификация — keyring (gh auth status). Пример: site-extraction, 6b1fe05→f380a2e, 816 файлов.
