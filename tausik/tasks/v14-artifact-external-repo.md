---
slug: v14-artifact-external-repo
title: "Опциональная ссылка на git submodule / внешний репо"
status: done
epic: v14-brain-snippets
story: v14-brain-snippets-security
complexity: medium
role: null
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/brain_artifact_card.py"
  - "scripts/brain_mcp_write.py"
  - "scripts/brain_publish_flow.py"
  - "scripts/brain_config.py"
  - "tests/test_brain_artifact_external_repo.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-01T11:58:52Z"
resolution: null
resolution_reason: null
tracker_refs: []
started_model_id: null
started_model_version: null
done_model_id: null
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

Документированный opt-in и проверка доступности ссылки.

## Acceptance Criteria

1. Документ security/opt-in. 2. Валидация URL при сохранении. 3. Negative: битый URL при publish отклоняется.

## Plan

## Rollback

## Journal

- 2026-05-01T11:57:16Z [implementation] — AC verified: 1. ✓ docs/en + docs/ru brain-artifact-taxonomy.md — раздел External repo / безопасность / skip_external_repo_url_reachability_check. 2. ✓ validate_external_repo_url_for_store + GET reachability; scrub включает URL; stripped перед Notion. 3. ✓ pytest tests/test_brain_artifact_external_repo.py — отказ при сетевой ошибке; draft would_publish_ok false. AC-1: ✓ taxonomy doc. AC-2: ✓ tests/test_brain_artifact_external_repo.py.
- 2026-09-26T18:41:32Z [done] — EVIDENCE-RETIRED: tests/test_brain_artifact_external_repo.py — file deleted by 77703c4a (feat(knowledge)!: remove the Notion transport)
