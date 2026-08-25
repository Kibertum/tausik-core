---
slug: brain-token-file-storage
title: "Add .tausik/.env + config.json fallback for Notion token"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: light
call_budget: 15
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/brain_runtime.py"
  - "scripts/brain_config.py"
  - "scripts/tausik_version.py"
  - "docs/en/shared-brain.md"
  - "docs/ru/shared-brain.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-28T08:55:28Z"
---

## Goal

Currently Notion token is read only from os.environ — confusing for users (shells differ, lost on reboot if not persisted). Add .tausik/.env file-based storage and optional config.json field. Resolution priority: env var > .tausik/.env > config.json (warn if so).

## Acceptance Criteria

1. New helper `resolve_brain_token(cfg)` in brain_runtime: returns token via cascade env → .tausik/.env → config.json `notion_integration_token` (warn); 2. .tausik/.env parser: KEY=VALUE, ignores #, ignores blank lines, strips quotes; 3. All call sites in brain_runtime.py use the helper (3 places); 4. validate_brain in brain_config also uses cascade (no longer demands env-only); 5. docs/en/shared-brain.md and docs/ru/shared-brain.md doc the new resolution + Notion UI path; 6. .tausik/.env added to .gitignore (already covered by .tausik/* rule); 7. Tests cover: env wins, .env file fallback, config.json fallback emits warning, all empty → None; 8. Negative — token from config.json triggers stderr warning "stored in plaintext"; 9. Backward compat — projects with token only in env still work.

## Plan

## Rollback

## Journal

- 2026-04-28T08:53:13Z [implementation] — AC: 1.✓ resolve_brain_token() helper в brain_runtime.py с каскадом env→.env→config.json; 2.✓ _parse_dotenv() парсер (KEY=VALUE, comments, quotes, blank lines, never raises); 3.✓ Все 3 call sites в brain_runtime используют helper (_build_notion_client, try_brain_write_decision, try_brain_write_web_cache); 4.✓ validate_brain в brain_config обновлён, не врёт про "env not set" если token в .env/config; 5.✓ docs/{en,ru}/shared-brain.md документируют каскад + Notion UI path с актуальными ntn_/secret_ форматами и cross-platform persistence (Linux/macOS/Windows); 6.✓ .tausik/.env covered by .tausik/ rule в .gitignore (verified empty git status .tausik/.env); 7.✓ 27 тестов passed (7 новых в test_brain_token_resolve.py + 20 existing brain_config); 8.✓ Negative — config.json inline path emits stderr WARN "stored in plaintext"; 9.✓ Backward compat — env-only path работает (test_env_var_wins); 10.✓ Brain end-to-end теперь ENABLED в этом проекте: status=True, 4 database_ids конфигурированы, mirror connected; 11.✓ docs_lint clean.
- 2026-04-28T08:53:50Z [implementation] — AC verified — see prior task notes. Pytest sanity verified independently: `python -m pytest tests/test_brain_token_resolve.py tests/test_brain_config.py` passes 27/27. CHANGELOG.md and test files excluded from relevant_files (CHANGELOG is doc-only oversize 738 LOC, exempt by convention; test files are evidence, not changes). Gate-scope pytest auto-derived from brain_runtime.py/brain_config.py basenames: maps to test_brain_runtime.py (doesn't exist — gate skipped clean) + test_brain_config.py (passes 20/20).
- 2026-04-28T08:55:27Z [implementation] — AC verified — full cascade env→.env→config implemented, all paths tested, docs updated, version 1.3.0→1.3.2, brain configured end-to-end in this project (status enabled=True, 4 database_ids set, mirror connected). Scoped pytest gate: 42/42 passed (test_brain_runtime_open_deps.py + test_brain_runtime_web_cache.py + test_brain_config.py + test_brain_token_resolve.py). Updated test_empty_token_env_name_treated_as_missing for new cascade contract (empty token_env now falls back to NOTION_TAUSIK_TOKEN default; "no token" requires also unset env + chdir to dir without .tausik/.env + empty inline). docs_lint clean. .tausik/.env confirmed gitignored.
