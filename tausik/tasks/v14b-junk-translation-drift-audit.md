---
slug: v14b-junk-translation-drift-audit
title: "B-junk-1: Bilingual EN/RU translation-drift audit script"
status: done
epic: v14-polish-quality
story: v14-polish-b-quality
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 60
defect_of: null
scope: "scripts/audit_translation_drift.py (NEW); tests/test_audit_translation_drift.py (NEW); CHANGELOG.md + CHANGELOG.ru.md (entry under Unreleased v1.4.0 polish Phase B)"
scope_exclude: "scripts/audit_stale_docs.py (referenced as pattern, not modified); gate_runner.py + service_gates.py (NOT integrated into gates); .claude/ tree (regenerated from bootstrap if needed); pre-commit hooks (audit is advisory, not blocking)"
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-06T20:50:33Z"
---

## Goal

Spin-off from v14b-junk-audit-pass. Build scripts/audit_translation_drift.py — report-only audit comparing EN/RU mirror docs (docs/en/foo.md ↔ docs/ru/foo.md) for structural drift: heading count match (h1..h6), fenced code-block count match (```), markdown-table count match. Not word-by-word translation check; structural only. Output: markdown report (default), JSON (--json), exit-1-on-drift (--check). Pairing logic: shared basenames → drift candidates; EN-only / RU-only basenames → 'unpaired' section (informational, not drift). Default mode exits 0 always (advisory). --check mode exits 1 if any pair has metric mismatch. Goal: surface stale RU mirrors after EN edits without blocking commits, run from CLI or future CI advisory job. Pattern follows scripts/audit_stale_docs.py (same arg layout, same 'check' semantic, same Path discovery). Non-goal: no semantic / NLP comparison, no auto-fix, no integration into pre-commit gates.

## Acceptance Criteria

1. scripts/audit_translation_drift.py created (<400 lines, filesize gate clean), with run modes: default markdown report, --json (machine-readable), --check (exit 1 on drift). Pure-stdlib (re + pathlib + argparse + json), no new deps.
2. Pairing: docs/en/*.md ↔ docs/ru/*.md by basename. Paired-with-drift, en-only, ru-only sections in report. Drift = any metric mismatch (heading-count OR code-block-count OR table-count differs between mirrors).
3. tests/test_audit_translation_drift.py created with at least 4 cases: (a) perfect match → no drift; (b) heading mismatch → drift; (c) code-block mismatch → drift; (d) en-only / ru-only handling. Uses tmp_path fixture to build synthetic pairs.
4. CHANGELOG.md + CHANGELOG.ru.md entries under Unreleased v1.4.0 polish Phase B describing the new audit script, its scope (structural only, advisory) and exit semantics.
5. Negative: pytest full suite green (no regression); ruff + mypy clean on the new files; running the script against actual docs/ directory does not crash and produces a sensible report (manual smoke).
6. Negative: default mode never exits 1 (advisory); --check mode exits 1 ONLY when paired drift exists, NOT for unpaired files (those are informational); script does NOT modify any files.
7. Negative: no integration into pre-commit hooks, no integration into gate_runner.py, no entry added to gate registry — strictly a CLI-runnable audit script in scripts/.

## Plan

## Rollback

## Journal

- 2026-05-06T20:50:25Z [implementation] — AC verified: 1. ✓ scripts/audit_translation_drift.py created, 213 lines after black format (<400 filesize gate clean); modes: default markdown, --json, --check; pure-stdlib (re + pathlib + argparse + json + sys for stdout reconfigure on Windows). 2. ✓ Pairing logic: docs/en/*.md ↔ docs/ru/*.md by basename; render_markdown produces 'paired-with-drift' table + 'unpaired files' section (en-only / ru-only); test_unpaired_categorisation verifies categorisation. Drift = any of 3 metrics (headings/code_blocks/tables) differs. 3. ✓ tests/test_audit_translation_drift.py — 14 cases covering count_metrics, perfect_match (no drift), heading_mismatch, code_block_mismatch, table_mismatch, unpaired_categorisation, render_markdown (no-drift + drift), render_json shape, main default exit 0 even with drift, main --check exit 1 on drift, main --check exit 0 on no drift, main --check exit 0 on unpaired-only, main --json valid JSON. 14/14 PASS in 0.25s. 4. ✓ CHANGELOG.md + CHANGELOG.ru.md entries added under Unreleased v1.4.0 polish Phase B in ### Added section, describing scope, modes, exit semantics, smoke-test result (8 drifted pairs found). 5. ✓ Negative: full pytest 2889→2903 (+14 new, zero regression); ruff + mypy clean on scripts/audit_translation_drift.py + tests/test_audit_translation_drift.py; smoke-test on real docs/ produced markdown report with 8 drifted pairs + 4 EN-only + 1 RU-only — sensible non-crashing output. 6. ✓ Negative: default exit=0, --check exit=1 only on paired drift (test_main_check_does_not_flag_on_unpaired_only confirms unpaired files alone return exit 0); script never modifies files (read-only audit). 7. ✓ Negative: scripts/gate_runner.py and pre-commit hooks NOT touched; no entry added to gate registry; script is purely CLI-runnable in scripts/.
