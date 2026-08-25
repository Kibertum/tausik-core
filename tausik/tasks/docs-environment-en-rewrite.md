---
slug: docs-environment-en-rewrite
title: "Environment.md (EN) full rewrite — document 25+ TAUSIK env vars"
status: done
epic: null
story: null
complexity: medium
role: tech-writer
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
completed_at: "2026-05-15T13:41:05Z"
---

## Goal

docs/en/environment.md сейчас — generic shell/venv/Docker гайд, НЕ документирует TAUSIK env vars. Переписать: собрать 25+ env vars через grep os.environ/os.getenv в scripts/ (TAUSIK_VERIFY_FULL, TAUSIK_SKIP_HOOKS, TAUSIK_QUIET, TAUSIK_HOOK_FAIL_SECURE, TAUSIK_SECRET_SCAN_STRICT, etc.) и задокументировать. RU stub (27 строк) тоже расширить или переадресовать на EN правильно.

## Acceptance Criteria

(1) docs/en/environment.md содержит секцию TAUSIK env vars. (2) Список собран из реальных os.environ / os.getenv в scripts/. (3) RU mirror в синхронизации. (4) pnpm build clean. (5) Ошибка: env vars, используемые в коде, не должны остаться недокументированными.

## Plan

## Rollback

## Journal

- 2026-05-15T13:41:04Z [implementation] — AC verified: docs/en/environment.md получил полную TAUSIK env vars секцию (50+ переменных) собранную через grep os.environ/os.getenv по scripts/. Разбита на Workflow control / Push+memory / Project+IDE detection / Model selection / Brain+Notion. RU mirror тоже обновлён (стал самостоятельным, не редиректом). Shell rules секция сохранена. pnpm build 4.75s clean.
