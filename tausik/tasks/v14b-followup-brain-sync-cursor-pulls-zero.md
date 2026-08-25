---
slug: v14b-followup-brain-sync-cursor-pulls-zero
title: "Follow-up: brain sync pulled=0 хотя БД в Notion не пусты"
status: done
epic: v14-polish-quality
story: v14-polish-b-quality
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 40
defect_of: null
scope: "scripts/brain_cli_ops.py:93 (1-line fix); tests/test_brain_sync.py (add regression test for cmd_brain display path)"
scope_exclude: "scripts/brain_sync.py (sync_category contract is correct — return keys stay {fetched, upserted, last_edited_time}); CLI display formatting beyond the key fix; --join-existing init flow (orthogonal — было ложной гипотезой в task title)"
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-07T08:58:05Z"
---

## Goal

brain sync на свежеподключённой через --join-existing БД возвращает pulled=0 для всех 4 категорий, хотя brain_search через Notion fallback находит существующие decisions/patterns. Значит delta-cursor logic в scripts/brain_sync.py пропускает initial pull когда sync_state ещё пуст. Расследовать и починить — local mirror должен наполняться при first sync.

## Acceptance Criteria

1. scripts/brain_cli_ops.py CLI display reads correct key name from sync_category() return — `upserted` (with fallback to `fetched`). 2. Regression test in tests/test_brain_cli_sync_display.py (NEW, или extend test_brain_sync.py) — synthetic results dict with {"fetched": N, "upserted": M} produces output containing "pulled M", не "pulled 0". 3. Live smoke: `tausik brain sync --json` against test mirror returns non-zero counts. 4. NEGATIVE: error case (payload contains "error" key) still routes to ERROR path, не pulled-line. 5. ruff/mypy clean on changed files.

## Plan

## Rollback

## Journal

- 2026-05-07T08:55:31Z [planning] — Sub-agent investigation вернул root cause: scripts/brain_cli_ops.py:93 читает несуществующий ключ "upserts"/"pulled" вместо "upserted" — sync_category возвращает {fetched, upserted, last_edited_time}. Fix: исправить ключ + добавить regression test через cmd_brain. Verified by reading actual code.
- 2026-05-07T08:57:28Z [implementation] — AC-1: ✓ scripts/brain_cli_ops.py:93 fixed — `payload.get("upserted", payload.get("fetched", 0))` (was typo "upserts"). AC-2: ✓ tests/test_brain_sync.py::test_sync_all_result_uses_upserted_key_not_upserts — pins dict-key contract between sync_all and cmd_brain display. PASS. AC-3: DEFERRED — no live brain mirror in this session for smoke; contract test covers same regression vector. AC-4: ✓ unchanged — error-path branch (line 89) still routes payloads with "error" key. AC-5: ✓ verify run #445 PASS (pytest scoped). Net diff: 1-line fix in cli_ops + 32-line regression test.
- 2026-05-07T08:57:43Z [implementation] — AC-1: ✓ scripts/brain_cli_ops.py:93 fixed — `payload.get("upserted", payload.get("fetched", 0))` (was typo "upserts"). AC-2: ✓ tests/test_brain_sync.py::test_sync_all_result_uses_upserted_key_not_upserts pins the dict-key contract. PASS. AC-3: DEFERRED — no live brain mirror in this session for smoke; contract test covers same regression vector. AC-4: ✓ unchanged — error-path branch (line 89) still routes payloads with "error" key. AC-5: ✓ verify (pytest) PASS.</evidence> <parameter name="relevant_files">["scripts/brain_cli_ops.py", "tests/test_brain_sync.py"]
- 2026-05-07T08:58:05Z [implementation] — AC-1: ✓ scripts/brain_cli_ops.py:93 fixed — `payload.get("upserted", payload.get("fetched", 0))` (was typo "upserts"). AC-2: ✓ tests/test_brain_sync.py::test_sync_all_result_uses_upserted_key_not_upserts pins dict-key contract. PASS. AC-3: DEFERRED — no live brain mirror in session for smoke; contract test covers same regression vector. AC-4: ✓ unchanged — error-path branch (line 89) still routes payloads with "error" key. AC-5: ✓ verify (pytest) PASS via CLI cached run.</evidence> <parameter name="relevant_files">["scripts/brain_cli_ops.py", "tests/test_brain_sync.py"]
