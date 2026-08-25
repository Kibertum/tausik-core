---
slug: v14b-doc-gen-cross-files
title: "B6: gen_doc_constants extension — cross-file version/test-count consistency"
status: done
epic: v14-polish-quality
story: v14-polish-b-quality
complexity: medium
role: tech-writer
stack: python
tier: light
call_budget: 25
defect_of: null
scope: "scripts/gen_doc_constants.py (modify); tests/test_gen_doc_constants.py (extend); CHANGELOG.md + CHANGELOG.ru.md (entry)"
scope_exclude: "Adding test_count to constants.json (separate follow-up — needs pytest collect at gen time); README/AGENTS/CLAUDE content edits (scanner is read-only); .claude/ tree (regenerated)"
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-06T21:29:32Z"
---

## Goal

gen_doc_constants.py --check видит только docs/_generated/constants.json. Расширить — пройти по README/AGENTS/CLAUDE/docs/{en,ru}/architecture.md и проверить что test-count badges + version refs совпадают с constants.json. Закрывает doc drift gap.

## Acceptance Criteria

1. scripts/gen_doc_constants.py extended with cross-file consistency scanner: --check now also walks README.md, README.ru.md, AGENTS.md, CLAUDE.md, docs/en/architecture.md, docs/ru/architecture.md and verifies that occurrences of tausik version refs (vX.Y.Z patterns) match constants.json tausik_version. Report lists file:line + found vs expected on mismatch.
2. New CLI flag --skip-cross-files to opt out of the new check (preserves original constants.json-only check behavior; useful when running in narrow contexts).
3. tests/test_gen_doc_constants.py extended with at least 3 new cases: (a) scanner finds drift when version ref in synthetic file differs; (b) scanner stays clean when version refs match; (c) --skip-cross-files preserves prior single-file check behavior.
4. CHANGELOG.md + CHANGELOG.ru.md entry under Unreleased v1.4.0 polish Phase B describing the new scanner, the version-ref check, and CLI flag.
5. Negative: pytest full suite green; ruff + mypy clean on scripts + tests; existing 'tausik doc constants --check' invocation in pre-commit / CI keeps working (no behavior break for the single-file path) — verified by retaining old tests untouched.
6. Negative: scanner skips fenced code blocks (avoid false positives on doc examples that mention old versions intentionally) — same convention as audit_translation_drift.
7. Negative: NOT in scope — adding test_count to constants.json (requires pytest --collect-only at gen time, separate concern); MCP tool count cross-check (regex is too noisy without careful context detection — separate follow-up). Scope strictly limited to vX.Y.Z version-ref consistency.

## Plan

## Rollback

## Journal

- 2026-05-06T21:29:27Z [implementation] — AC verified: 1. scan_version_refs walks 6 targets (README/README.ru/AGENTS/CLAUDE/architecture en+ru), regex vX.Y[.Z], line-preserving fenced strip, foreign-version filter (SENAR/Python/OWASP), 2-part vs 3-part comparison. 2. --skip-cross-files preserves legacy single-file check. 3. +7 tests covering all branches: clean, minor drift, patch drift, foreign skip, fenced skip, run_main exit-1 on cross-file drift, --skip-cross-files restores legacy. 10/10 PASS. 4. CHANGELOG entries added. 5. pytest 2910 to 2917 (+7), ruff+mypy clean on changed files. 6. Fenced code blocks stripped via line-number-preserving whitespace replacement. 7. Scope strictly version-refs (no test_count/MCP-count). Smoke: --check exit 0 after fixing 4 stale v1.3 refs in arch docs.
