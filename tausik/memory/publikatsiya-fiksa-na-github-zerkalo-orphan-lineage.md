---
slug: publikatsiya-fiksa-na-github-zerkalo-orphan-lineage
title: "Публикация фикса на github-зеркало (orphan lineage)"
type: pattern
tags: []
task: null
edges: []
---

github.com/Kibertum/tausik-core = release-зеркало на parentless-корне (f380a2e). Scrub касается ТОЛЬКО истории (сквош по релизам); дерево файлов байт-в-байт == dev (проверено: diff dev-commit против github/main пуст). origin=GitLab несёт полную историю + .gitlab-ci.yml (dev-гейт, Linux, fast-полоса -m 'not slow'). GitHub Actions = релизная верификация (матрица 3.11-3.13 + full slow lane -m ''). Рецепт публикации фикса БЕЗ утечки истории: (1) fetch github; (2) checkout -b tmp github/main; (3) cherry-pick -n dev-fix; (4) commit с АНГЛ.сообщением (конвенция: dev-коммиты рус переводятся); (5) diff --stat dev-fix против HEAD ОБЯЗАН быть пуст; (6) tausik push-ok; (7) публикация tmp в github:main одной командой; (8) вернуться на main, удалить tmp. ВНИМАНИЕ: hook git_push_gate блокирует ЛЮБУЮ Bash-команду с подстрокой 'git'+'push' — включая journal/memory с этим текстом (ложное срабатывание).
