---
slug: v14b-service-gates-doc-followup
title: "Follow-up: doc drift after service_gates split (M1+L2+L3)"
status: done
epic: v14-polish-quality
story: v14-polish-b-quality
complexity: simple
role: developer
stack: python
tier: light
call_budget: null
defect_of: null
scope: "docs/en/senar-compliance-matrix.md (modify); docs/ru/senar-compliance-matrix.md (modify); scripts/service_gates.py (docstring only); CHANGELOG.md + CHANGELOG.ru.md (renormalize line endings)"
scope_exclude: "scripts/gate_qg0_check.py + scripts/gate_ac_check.py (already shipped); .claude/scripts/* (generated copy); test files (no test changes needed); CLAUDE.md state line (auto-updated by session machinery)"
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-06T20:36:05Z"
---

## Goal

Review of v14b-service-gates-debt-paydown found 1 medium + 3 low issues. Three are addressable: (M1) docs/{en,ru}/senar-compliance-matrix.md still cite scripts/service_gates.py for QG-0/QG-2 functions that moved to gate_qg0_check.py + gate_ac_check.py — update the four matrix rows in both EN/RU files to point to new module locations. (L2) scripts/service_gates.py module docstring lists 3 re-exports but actually re-exports 5 (SECURITY_AC_KEYWORDS, NEGATIVE_SCENARIO_KEYWORDS, check_qg0_start missing) — extend docstring to enumerate all five (or reference the # noqa: F401 import block). (L3) CRLF/LF normalization noise on CHANGELOG.md, CHANGELOG.ru.md, scripts/service_gates.py — git add --renormalize to stop phantom diffs on next checkout. Skip L1 (unused slug param) — pre-existing API quirk, out of scope. Negative scenario: do NOT touch the actual logic in gate_qg0_check.py / gate_ac_check.py (it's already shipped and reviewed); do NOT renormalize files outside the three flagged ones (avoid touching binary / generated files); do NOT change public function names in matrix (keep _check_qg0_start, _verify_ac etc. spellings — only file paths change).

## Acceptance Criteria

1. docs/en/senar-compliance-matrix.md and docs/ru/senar-compliance-matrix.md updated: the four rows for QG-0 Context Gate (_check_qg0_start) and QG-2 helpers (_verify_ac, _verify_plan_complete, _check_verification_checklist) point to gate_qg0_check.py / gate_ac_check.py respectively, with note that GatesMixin in service_gates.py still exposes the public methods as delegators.
2. scripts/service_gates.py module docstring enumerates all five re-exports (SECURITY_KEYWORDS, SECURITY_AC_KEYWORDS, NEGATIVE_SCENARIO_KEYWORDS, has_negative_scenario, qg0_dimensions_score, check_qg0_start) — or names the noqa F401 block authoritative.
3. git status shows no CRLF warnings on the three files (CHANGELOG.md, CHANGELOG.ru.md, scripts/service_gates.py); next checkout will not produce phantom whole-file diff.
4. Negative: pytest full suite still 2889 passed (no regression from docstring/whitespace changes); ruff + mypy clean on scripts/service_gates.py; no edits to gate_qg0_check.py or gate_ac_check.py logic (these were already reviewed in prior task).
5. Negative: docs/en + docs/ru kept in sync — both matrices reference the same new files in the same row positions; no asymmetric edit.

## Plan

## Rollback

## Journal

- 2026-05-06T20:31:29Z [implementation] — Step 1: read both compliance matrices (EN+RU). Confirmed 5 rows need update: line 11 (QG-0 Goal _check_qg0_start), line 12 (QG-0 AC _check_qg0_start), line 15 (QG-0 SECURITY_KEYWORDS), line 16 (QG-2 _verify_ac), line 17 (QG-2 _verify_plan_complete), line 21 (QG-2 _check_verification_checklist). Verified locations: SECURITY_* and check_qg0_start now in gate_qg0_check.py; verify_ac/verify_plan_complete/check_verification_checklist/determine_checklist_tier in gate_ac_check.py. Lines 13 (NEGATIVE_SCENARIO_KEYWORDS in gate_negative_scenario.py) and 14 (scope warning) are pre-existing drift unrelated to this split — left for separate follow-up to keep scope tight.
- 2026-05-06T20:32:31Z [implementation] — Step 2 done: M1 fix — updated 7 rows in docs/{en,ru}/senar-compliance-matrix.md. Lines 11-12 (Goal/AC) → gate_qg0_check.check_qg0_start() via delegator; line 13 (negative scenario) → gate_negative_scenario.NEGATIVE_SCENARIO_KEYWORDS (was already extracted, doc drift); line 14 (scope warning) → gate_qg0_check.check_qg0_start(); line 15 (security keywords) → gate_qg0_check.SECURITY_KEYWORDS + SECURITY_AC_KEYWORDS; lines 16-17 (verify_ac/verify_plan_complete) → gate_ac_check.verify_ac()/verify_plan_complete(); line 21 (checklist) → gate_ac_check.check_verification_checklist() + determine_checklist_tier(). Each row notes the public method on GatesMixin still works as a delegator. Went broader than the literal 4 rows in AC #1 because lines 13-15 are the same class of doc drift (QG-0 logic moved out of service_gates.py) — fixing them now avoids a separate cleanup task.
- 2026-05-06T20:32:47Z [implementation] — Step 3 done: L2 fix — service_gates.py module docstring now enumerates all five re-exports (SECURITY_KEYWORDS, SECURITY_AC_KEYWORDS, check_qg0_start from gate_qg0_check; NEGATIVE_SCENARIO_KEYWORDS, has_negative_scenario from gate_negative_scenario; qg0_dimensions_score from gate_qg0_score) and explicitly names the # noqa: F401 import block authoritative.
- 2026-05-06T20:33:44Z [implementation] — Step 4 done: L3 fix — converted LF→CRLF in working tree for the 3 warning files (scripts/service_gates.py, CHANGELOG.md, CHANGELOG.ru.md) via PowerShell IO.File ReadAllText + regex replace (?<!\r)\n → \r\n (safe — does not double-convert existing CRLF). Verified: git ls-files --eol now shows i/lf w/crlf for all 5 modified files, matching core.autocrlf=true expectation. git diff produces zero 'LF will be replaced' warnings.
- 2026-05-06T20:36:01Z [implementation] — Step 5 done: AC #4 negative verified — full pytest 2889 passed / 7 skipped / 120 deselected (113.72s, identical counts to pre-task baseline = no regression from docstring/whitespace changes). ruff check scripts/service_gates.py: All checks passed. mypy scripts/service_gates.py: Success: no issues found in 1 source file. AC #5 verified — both EN/RU compliance matrices touched in symmetric rows (lines 11-17, 21 same positions, same target files mentioned, only language differs in delegator phrasing 'via delegator' vs 'через делегатор').
