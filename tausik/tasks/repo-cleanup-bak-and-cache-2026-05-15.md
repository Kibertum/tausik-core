---
slug: repo-cleanup-bak-and-cache-2026-05-15
title: "Repo cleanup: drop 14 db backups, 3 dev scripts, 3 cache dirs; add .mypy_cache/.ruff_cache to .gitignore"
status: done
epic: null
story: null
complexity: simple
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
completed_at: "2026-05-15T12:53:29Z"
---

## Goal

Освободить ~158 MB локального места и заткнуть утечки в .gitignore. Все удаляемые файлы untracked — потерь нет.

## Acceptance Criteria

(1) 14 файлов .tausik/tausik.db.bak.* удалены (67 MB). (2) 3 dev-скрипта (.tausik/brain_research.py, brain_smoke.py, generate_v13_pdf.py) + 2 пустых _mcp_*_test.txt удалены. (3) .mypy_cache/, .ruff_cache/, .claude-project/ удалены. (4) .gitignore: добавлены .mypy_cache/ и .ruff_cache/. (5) Ни одного tracked-файла не затронуто (git status кроме .gitignore + CLAUDE.md остаётся чистым). (6) Ошибка: не должно случайно удалиться tausik.db, tausik.db-shm, tausik.db-wal — проверено через ls .tausik/ после rm.

## Plan

## Rollback

## Journal

- 2026-05-15T12:53:29Z [implementation] — AC verified: (1) ✓ 14 .tausik/tausik.db.bak.* удалены (v14-v26 + 2 named, 67 MB). (2) ✓ 3 dev-скрипта + 2 пустых .txt удалены: brain_research.py, brain_smoke.py, generate_v13_pdf.py, _mcp_stderr_test.txt, _mcp_stdout_test.txt. (3) ✓ .mypy_cache (90 MB) + .ruff_cache (178 KB) + .claude-project (1 KB) удалены через shutil.rmtree. (4) ✓ .gitignore: +2 строки .mypy_cache/ и .ruff_cache/ в секции Coverage/pytest/linter caches. (5) ✓ git status: tracked-изменения только .gitignore + CLAUDE.md (dynamic). (6) ✓ Критичные файлы целы: tausik.db, tausik.db-shm, tausik.db-wal, tausik (CLI), tausik.cmd, config.json, .session.json, .env. Total freed: 148.3 MB.
