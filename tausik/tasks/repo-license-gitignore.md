---
slug: repo-license-gitignore
title: "LICENSE, .gitignore, cleanup мусора"
status: done
epic: public-release
story: repo-hygiene
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - LICENSE
  - ".gitignore"
  - README.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-05T13:19:41Z"
---

## Goal

Репозиторий чист для публичного клона: есть LICENSE, .gitignore полный, нет мусорных файлов

## Acceptance Criteria

1. LICENSE файл BSL 1.1 в корне (Licensor: Yumashev, Change Date: 2030-04-05, Change License: Apache 2.0). 2. .gitignore содержит паттерны *.bak*, *.tar.gz. 3. Untracked мусор удалён. 4. README обновлён: BSL 1.1 вместо MIT. 5. Ошибка если LICENSE не содержит Change Date или Licensor — валидация grep подтверждает наличие обоих полей.

## Plan

[{"step": "\u0421\u043e\u0437\u0434\u0430\u0442\u044c LICENSE \u0444\u0430\u0439\u043b (MIT, 2024-2026, Yumashev)", "done": true}, {"step": "\u041e\u0431\u043d\u043e\u0432\u0438\u0442\u044c .gitignore: \u0434\u043e\u0431\u0430\u0432\u0438\u0442\u044c *.bak*, *.tar.gz", "done": true}, {"step": "\u0423\u0434\u0430\u043b\u0438\u0442\u044c untracked \u043c\u0443\u0441\u043e\u0440 (.frai/*.bak.*, claude-code-main.tar.gz)", "done": true}, {"step": "\u041f\u0440\u043e\u0432\u0435\u0440\u0438\u0442\u044c git status \u2014 \u0434\u043e\u043b\u0436\u0435\u043d \u0431\u044b\u0442\u044c \u0447\u0438\u0441\u0442\u044b\u043c", "done": true}]

## Rollback

## Journal

- 2026-04-05T13:17:30Z [implementation] — AC verified: LICENSE BSL 1.1 создан, .gitignore обновлён, мусор удалён, README обновлён. Все 5 критериев пройдены.
