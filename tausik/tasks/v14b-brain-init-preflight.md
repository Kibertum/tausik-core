---
slug: v14b-brain-init-preflight
title: "B-brain-1: brain init pre-flight — verify integration access before databases_create/search"
status: done
epic: v14-polish-quality
story: v14-polish-b-quality
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/brain_notion_client.py, scripts/brain_init.py, tests/test_brain_init.py"
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-03T22:11:24Z"
---

## Goal

Dead-end #72: brain init --join-existing fails when integration not shared with workspace BRAIN DBs. Wizard падает на search() без понятной диагностики — пользователь не понимает что нужно сделать в Notion UI. Код корректный (find_workspace_brain_databases есть), но UX сломан. Цель: pre-flight check в run_wizard — (a) users.me() для проверки что токен валиден; (b) при --join-existing без explicit ids — поиск + если 0 матчей → emit explicit guide "Go to Notion → BRAIN page → Connections → add your integration. Then re-run."

## Acceptance Criteria

1. NotionClient gains a `users_me()` method that performs GET /v1/users/me and returns the bot user dict. 2. `run_wizard` calls `users_me()` immediately after the Notion client is constructed; on NotionAuthError it raises WizardError with a clear "Token is invalid" message including the env var name and integration-creation URL. 3. In the --join-existing branch, when find_workspace_brain_databases() returns 0 matches AND no explicit IDs were passed, the wizard raises a WizardError with an explicit guide: "Go to Notion → BRAIN page → Connections → add your integration. Then re-run." (instead of the generic "could not resolve all 4" message). 4. NEGATIVE: when search() returns >0 partial matches, the existing partial-match error path is preserved (no regression). 5. NEGATIVE: with explicit IDs supplied, the discovery-empty guide does NOT fire (explicit-mode short-circuits pre-flight). 6. NEGATIVE: when users_me() raises a generic NotionError (network / 5xx), preflight surfaces the cause without false-positive "token invalid" text. 7. Existing brain init tests still pass; new tests cover users_me success, users_me 401, join-existing-empty discovery, and explicit-id bypass. 8. pytest tests/test_brain_init.py (or equivalent) PASS. 9. tausik verify --task &lt;slug&gt; PASS.

## Plan

## Rollback

## Journal

- 2026-05-03T22:11:24Z [implementation] — AC verified: 1.✓ NotionClient.users_me() added (GET /v1/users/me) returning bot dict. 2.✓ users_me() called pre-flight in run_wizard — test_run_wizard_calls_users_me_before_search. 3.✓ NotionAuthError → WizardError 'Notion token is invalid' with env var name + integration URL — test_run_wizard_users_me_401_raises_token_invalid_message. 4.✓ Empty discovery + no explicit ids → Connections-guide WizardError — test_run_wizard_join_existing_empty_discovery_emits_connections_guide. 5.✓ Partial-explicit-ids on empty workspace → legacy 'could not resolve' preserved — test_run_wizard_join_existing_partial_explicit_ids_falls_to_could_not_resolve. 6.✓ All-explicit-ids skip pre-flight + Connections guide — test_run_wizard_join_existing_with_all_explicit_ids_skips_preflight_guide. 7.✓ Generic NotionError on users.me() does NOT print 'token invalid' — test_run_wizard_users_me_generic_error_does_not_falsely_say_token_invalid. 8.✓ pytest tests/test_brain_init.py 59/59 PASS in 0.38s. 9.✓ tausik verify exit=0.
