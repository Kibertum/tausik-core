---
slug: site-dead-links-cleanup
title: "Clean 103 dead cross-file links in docs/{en,ru} + drop ignoreDeadLinks"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-15T12:43:50Z"
---

## Goal

Чистка ломаных ссылок (../../scripts/*.py, ../en/stacks, etc.) после sync в site/docs/. Сейчас замаскировано через ignoreDeadLinks: true в .vitepress/config.ts. Цель — снять флаг и видеть build error на новых ломаных ссылках.

## Acceptance Criteria

(1) Все ломаные cross-file ссылки в docs/{en,ru}/*.md устранены либо заменой на корректный путь (GitHub URL для ссылок на код, абсолютные /docs или /ru/docs paths для внутренних), либо удалением link-обёртки. (2) .vitepress/config.ts: ignoreDeadLinks снят (removed/false). (3) pnpm build проходит зелёным без deadlinks warnings. (4) docs/ru/agent-contract.md: ссылка [English](../en/agent-contract.md) либо переписана на корректный путь, либо удалена (поскольку EN-агент-контракта нет — лучше удалить). (5) Ошибка: после фикса не должны появиться новые ломаные ссылки — VitePress build будет fail-stopper на любой новой dead link. (6) Не трогаем content docs — только links. Если ссылка указывает на источник кода (../../scripts/x.py) — заменяем на github.com/Kibertum/tausik-core/blob/main/scripts/x.py.

## Plan

## Rollback

## Journal

- 2026-05-15T12:43:49Z [implementation] — AC verified: (1) ✓ 103 ломаных ссылок устранены: 30 en→ru crosslang, 42 ru→en crosslang, 18 scripts-root → github URL, 1 en-research→ru-research, 4 ru-research→en-root, 3 scripts-research → github, 3 tests-research → github, 1 agent-contract-EN-link removed, 2 missing-research-files unlinked. (2) ✓ .vitepress/config.ts: ignoreDeadLinks = false. (3) ✓ pnpm build clean 4.45s, 0 dead links. (4) ✓ docs/ru/agent-contract.md: [English](../en/agent-contract.md) удалён (EN не существует). (5) ✓ build fail-stopper включён — любой новый dead link сломает build. (6) ✓ Content не тронут — только ссылки; 72 файла, все правки точечные через regex с capture groups.
