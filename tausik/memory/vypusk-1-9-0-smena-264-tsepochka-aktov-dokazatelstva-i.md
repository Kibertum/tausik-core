---
slug: vypusk-1-9-0-smena-264-tsepochka-aktov-dokazatelstva-i
title: "Выпуск 1.9.0 (смена #264): цепочка актов, доказательства и ловушка credential-manager при push из безголовой сессии"
type: context
tags:
  - credential
  - github
  - gitlab
  - publishing
  - release-1.9
task: null
edges: []
---

Выпуск 1.9.0, смена #264, по указанию владельца «когда будешь уверен — выпускай согласно договорённостям». Доказательства перед тегом: пайплайн GitLab #7726 на релизном коммите 0cfccd89 зелёный во всех четырёх работах, включая tests-full (первая зелёная полная лента в опубликованном CI за недели: до этого #7719 нашёл два Linux-only дефекта тестов — «Memory tail» из общей базы автора и communicate() после закрытого stdin, оба не воспроизводимы на Windows; это и есть довод за полную ленту в CI, а не локально). Акты по docs/ru/publishing.md: разрез CHANGELOG → релизный коммит → CI → аннотированный v1.9.0 на линии разработки (origin) → publish snapshot 03f1531b (1329 файлов, 3121 исключено, 0 утечек) → publish verify OK → refspec-push github main и refs/tags/v1.9.0 (lightweight) → published_tags.json → GitHub Release → PR #5 закрыт со ссылкой. Ловушка: `git push github` из безголовой сессии повис на `git credential-manager get` (скрытое окно) на 8 минут; выход — разовое `-c credential.helper='!gh auth git-credential'` без изменения конфига. Тикеты GitLab #5/#6/#14 остаются открытыми для владельца (#366).
