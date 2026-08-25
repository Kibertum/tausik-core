---
slug: fix-hook-cp1252-unicode-crash
title: "Fix SessionStart/hook crash: force UTF-8 decode of TAUSIK CLI output (Windows cp1252)"
status: done
epic: null
story: null
complexity: null
role: null
stack: python
tier: light
call_budget: 20
defect_of: null
scope: "scripts/hooks/{session_start,_common,auto_format,task_done_verify,session_metrics,check_docs}.py + scripts/{project_cli_extra,project_cli_renar,pytest_test_count,service_session,verify_git_diff}.py — add encoding='utf-8', errors='replace' to every text=True subprocess reader"
scope_exclude: null
relevant_files:
  - "scripts/hooks/session_start.py"
  - "scripts/hooks/_common.py"
  - "scripts/hooks/auto_format.py"
  - "scripts/hooks/task_done_verify.py"
  - "scripts/hooks/session_metrics.py"
  - "scripts/hooks/check_docs.py"
  - "scripts/project_cli_extra.py"
  - "scripts/project_cli_renar.py"
  - "scripts/pytest_test_count.py"
  - "scripts/service_session.py"
  - "scripts/verify_git_diff.py"
  - pyproject.toml
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-06T11:42:12Z"
---

## Goal

Hook subprocess readers of TAUSIK CLI output use text=True without encoding, so on Windows they decode with cp1252 and crash (UnicodeDecodeError -> stdout=None -> AttributeError on .strip()) whenever CLI output contains Cyrillic/non-cp1252 (e.g. memory block, task titles). Force encoding='utf-8', errors='replace' on all affected hook subprocess calls to match the correct session_cleanup_check.py pattern.

## Acceptance Criteria

1) Every core hook subprocess that captures TAUSIK CLI stdout as text passes encoding='utf-8', errors='replace' (session_start.py, _common.py, auto_format.py, task_done_verify.py, session_metrics.py). 2) Running session_start.py hook against a project whose memory block contains Cyrillic exits 0 and emits valid JSON with no traceback. 3) gitlab-tracker deployed .tausik-lib copies patched so its SessionStart hook runs clean.

## Plan

## Rollback

git revert the commit; single-line encoding args, no behavioral change beyond decoding.

## Journal

- 2026-07-06T11:36:15Z [implementation] — Root cause: subprocess.run(text=True) in hooks/scripts decoded child stdout with Windows locale codec (cp1252); UTF-8 Cyrillic bytes (0x81 undefined) -> UnicodeDecodeError in reader thread -> stdout=None -> AttributeError on .strip(), outside caught tuple -> SessionStart hook aborted, no context injected. Fixed 12 subprocess sites with encoding='utf-8', errors='replace'. Verified patched session_start.py exits 0 + valid JSON against gitlab-tracker Cyrillic DB. Bumped 1.5.6->1.5.7 (pyproject.toml SoT + tausik_version.py + regenerated constants.json + README badges EN/RU + CHANGELOG EN/RU). Doc-drift check green.
- 2026-07-06T11:42:11Z [implementation] — AC1 ✓ — all 12 text=True subprocess readers now pass encoding='utf-8', errors='replace' (grep sweep of scripts/ returns zero unencoded readers; py_compile OK for all 11 files). AC2 ✓ — patched scripts/hooks/session_start.py run against gitlab-tracker's Cyrillic memory DB (CLAUDE_PROJECT_DIR override) exits 0 and emits valid JSON, no traceback; full suite 4313 passed / 12 skipped / 0 failed. AC3 — gitlab-tracker deployed .tausik-lib rollout pending (submodule bump after core push).
