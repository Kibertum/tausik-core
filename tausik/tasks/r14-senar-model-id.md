---
slug: r14-senar-model-id
title: "SENAR Rule 10.13: record AI model id+version per session (mandatory all configurations)"
status: done
epic: rel-14-readiness
story: rel-14-audit-fixes
complexity: medium
role: null
stack: null
tier: moderate
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-01T00:59:09Z"
---

## Goal

Release 1.4 readiness: r14-senar-model-id

## Acceptance Criteria

1. sessions table has model_id and model_version columns (migration v20). 2. session_start reads TAUSIK_AGENT_MODEL > CLAUDE_MODEL > ANTHROPIC_MODEL > OPENAI_MODEL > CURSOR_MODEL chain and stores in model_id; TAUSIK_AGENT_MODEL_VERSION goes to model_version. 3. backend_schema.SCHEMA_VERSION bumped to 20. 4. Negative scenario: with no env vars set, session_start completes successfully and stores NULL in both columns - never blocks the user.

## Plan

## Rollback

## Journal

- 2026-05-01T00:59:08Z [implementation] — Schema migration v20 in scripts/backend_migrations.py adds model_id + model_version + idx_sessions_model. backend_schema.py SCHEMA_VERSION bumped to 20 and CREATE TABLE sessions includes the new columns for fresh databases.
- 2026-05-01T00:59:08Z [implementation] — Tests: tests/test_session_model_id.py covers (1) columns exist, (2) no env => NULL rows, (3) TAUSIK_AGENT_MODEL takes precedence over host envs, (4) fallback to CLAUDE_MODEL when only host env set. 4/4 pass plus 28 existing session tests still green.
- 2026-05-01T00:59:08Z [implementation] — backend_crud.session_start now reads env-var chain (TAUSIK_AGENT_MODEL > CLAUDE_MODEL > ANTHROPIC_MODEL > OPENAI_MODEL > CURSOR_MODEL) plus TAUSIK_AGENT_MODEL_VERSION. Insert statement carries model_id+model_version into sessions row.
- 2026-05-01T00:59:09Z [implementation] — AC verified: 1. sessions has new columns ✓ (PRAGMA table_info confirms). 2. session_start picks env-var chain ✓ (test_session_start_picks_tausik_env_first). 3. SCHEMA_VERSION = 20 ✓. 4. Negative - no env vars => NULL/NULL, no error ✓ (test_session_start_with_no_env).
