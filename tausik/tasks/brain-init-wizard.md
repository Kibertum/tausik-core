---
slug: brain-init-wizard
title: "tausik brain init — interactive opt-in wizard"
status: done
epic: shared-brain
story: brain-onboarding-docs
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/brain_notion_client.py (add databases_create), scripts/brain_init.py (new), scripts/project_cli_ops.py (add cmd_brain), scripts/project_parser.py (add brain subparser), scripts/project.py (add brain dispatch entry), tests/test_brain_init.py (new), docs/en/shared-brain.md (extend setup section), docs/ru/shared-brain.md (extend setup section)"
scope_exclude: "scripts/brain_config.py (stable — new config fields only added via save_config), scripts/brain_sync.py (stable), scripts/brain_search.py (stable), scripts/brain_scrubbing.py (stable), agents/claude/mcp/brain/** (stable), bootstrap/** (no bootstrap changes — wizard invoked post-bootstrap)"
relevant_files:
  - "scripts/brain_notion_client.py"
  - "scripts/brain_init.py"
  - "scripts/project_config.py"
  - "scripts/project_cli_ops.py"
  - "scripts/project_parser.py"
  - "scripts/project_parser_ops.py"
  - "scripts/project.py"
  - "tests/test_brain_init.py"
  - "docs/en/shared-brain.md"
  - "docs/ru/shared-brain.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-23T14:28:14Z"
---

## Goal

tausik brain init CLI subcommand (interactive + non-interactive via args). Flow: confirm opt-in → request Notion token env name → confirm token is set → request Notion parent page id → call databases.create ×4 for decisions/web_cache/patterns/gotchas with correct schemas → merge brain section into .tausik/config.json (enabled=true, database_ids filled, token env stored). All steps idempotent and recoverable: re-running on an already-configured project reports "already configured" and offers to recreate. Token never written to config. Scrubbing-blocklist fields (current_project_name, project_names, private_url_patterns) accepted via args or left default.

## Acceptance Criteria

1) scripts/brain_notion_client.py gets databases_create(parent, title, properties) using POST /v1/databases with existing retry/throttle.
2) scripts/brain_init.py (new) exposes: db_schema(category) for 4 categories producing valid Notion property dicts; create_brain_databases(client, parent_page_id, project_hash_seed) → {category: db_id}; run_wizard(inputs, io, client_factory, config_ops) — pure-ish orchestration; merge_brain_config(existing_cfg, updates) — pure.
3) DB property schemas match what brain_sync._map_* reads: decisions needs Name/Context/Decision/Rationale/Tags/Stack/Date/Source Project Hash/Generalizable/Superseded By; web_cache needs Name/URL/Query/Content/Fetched At/TTL Days/Domain/Tags/Source Project Hash/Content Hash; patterns needs Name/Description/When to Use/Example/Tags/Stack/Source Project Hash/Date/Confidence; gotchas needs Name/Description/Wrong Way/Right Way/Tags/Stack/Source Project Hash/Date/Severity/Evidence URL.
4) CLI: `tausik brain init` accepts --parent-page-id X --token-env Y --project-name Z --yes. When TTY and flag missing → prompt via input(). Non-interactive + missing args → exit with clear error.
5) Idempotency: if config already has brain.enabled=true AND non-empty database_ids → wizard reports existing setup and requires --force to overwrite.
6) Config file written atomically (write-then-rename). Token is NEVER persisted — only the env var NAME is stored.
7) ≥15 tests in tests/test_brain_init.py: each DB schema shape, create_brain_databases happy path (with FakeClient), merge_brain_config pure, run_wizard interactive (stdin/stdout mocks), non-interactive success, non-interactive missing args fails, already-configured without --force fails, --force overwrites, notion databases.create network error surfaces cleanly.
8) docs/en/shared-brain.md + docs/ru/shared-brain.md: update "Setup" section to use `tausik brain init` with non-interactive flag examples.
9) mypy + ruff clean on new files; full pytest passes; no regressions.
10) Out of scope: brain-project-registry (global ~/.tausik-brain/projects.json — future task), writing project_name to brain.project_names blocklist from a registry (future), revoking a previously configured brain (just edit config manually).

## Plan

[{"step": "Add databases_create to brain_notion_client (scope extension, documented in AC)", "done": true}, {"step": "Write scripts/brain_init.py: 4 db_schema funcs, create_brain_databases, merge_brain_config, run_wizard with injectable io + client_factory + config_ops", "done": true}, {"step": "Write tests/test_brain_init.py \u2014 \u226515 tests", "done": true}, {"step": "Wire CLI: add brain subparser, cmd_brain dispatcher, register in project.py dispatch dict", "done": true}, {"step": "Update docs/{en,ru}/shared-brain.md setup section to use tausik brain init", "done": true}, {"step": "Run mypy + ruff + full pytest", "done": true}, {"step": "Log AC evidence; task done", "done": true}]

## Rollback

## Journal

- 2026-04-23T14:13:58Z [implementation] — /review-fixes applied: H1 doc renumbering (7→6) in EN+RU; M2 atomic save moved into project_config.save_config (single writer); M3 WizardIO+ConfigOps Protocols; L1 full parent_page_id в log. cmd_brain упрощён: _ConfigOps теперь просто вызывает save_config. 148 config/save/gate tests green. Полный pytest в фоне.
- 2026-04-23T14:17:32Z [implementation] — AC verified: 1. databases_create добавлен в brain_notion_client.py (POST /v1/databases) ✓ 2. scripts/brain_init.py: db_schema, create_brain_databases, merge_brain_config, run_wizard с Protocol-типизацией WizardIO+ConfigOps ✓ 3. Schemas для 4 категорий матчат brain_sync._map_*; свойства проверены: Name/Context/Decision/Rationale/Tags/Stack/Date/Source Project Hash/Generalizable/Superseded By для decisions; Name/URL/Query/Content/Fetched At/TTL Days/Domain/Tags/Source Project Hash/Content Hash для web_cache; +patterns с Confidence опциями; +gotchas с Severity+Evidence URL ✓ 4. CLI `tausik brain init --parent-page-id/token-env/project-name/yes/force/non-interactive`; TTY fallback на input(); non-interactive+missing → WizardError ✓ 5. _has_existing_brain + --force: test_run_wizard_already_configured_without_force_raises + test_run_wizard_force_overwrites_existing ✓ 6. save_config стал атомарным (temp+os.replace) в project_config; token никогда не пишется в конфиг: test_run_wizard_token_never_persisted ✓ 7. 25 тестов (>=15 требовалось): 6 schema + 4 create + 5 merge + 10 wizard — все PASS ✓ 8. docs/en + docs/ru переписаны на wizard-based flow, секция 6 восстановлена ✓ 9. 1434 pass in 196s; mypy scripts/ 57 files clean; ruff clean ✓ 10. OOS: brain-project-registry, project_names blocklist от registry, revocation — не тронуто ✓
