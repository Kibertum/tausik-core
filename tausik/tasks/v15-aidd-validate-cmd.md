---
slug: v15-aidd-validate-cmd
title: "tausik aidd validate — drift between conventions.md claims and repo"
status: done
epic: v15-cross-ide-parity
story: v15-aidd-ai-validation
complexity: complex
role: developer
stack: python
tier: substantial
call_budget: 120
defect_of: null
scope: "scripts/project_cli_aidd_validate.py (new), scripts/project_parser_aidd.py (validate subparser + help), scripts/project_cli.py (cmd_aidd validate branch), tests/test_aidd_validate.py, docs/{en,ru}/cli.md, README.md, docs/_generated/constants.json"
scope_exclude: "scripts/project_cli_aidd_autogen.py (reused read-only), harness/aidd-templates/*, .claude/* (generated)"
relevant_files:
  - "scripts/project_cli_aidd_validate.py"
  - "scripts/project_parser_aidd.py"
  - "scripts/project_cli.py"
  - "tests/test_aidd_validate.py"
  - "docs/en/cli.md"
  - "docs/ru/cli.md"
  - README.md
  - "docs/_generated/constants.json"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-14T17:05:48Z"
---

## Goal

Add `tausik aidd validate`: parse machine-checkable claims from conventions.md (language version pin, lint/format tool, testing framework, max file-size limit) and compare against actual repo state (config files present, file sizes, detected tooling). Report each claim as ok/drift/unverifiable; exit non-zero when any hard drift is found. Stdlib-only, no LLM call. Acceptance: matching repo → exit 0 all-ok; a claim contradicted by repo → exit 1 + drift line naming the claim; unparseable/blank claim → reported unverifiable, never crashes; missing conventions.md → clear error exit 2.

## Acceptance Criteria

AC1: `tausik aidd validate` parses machine-checkable claims from conventions.md (language version pin, lint/format tool, testing framework, max file-size limit) and reports each as ok/drift/unverifiable. AC2: A repo matching all claims → exit 0, all-ok summary. AC3: A claim contradicted by the repo (e.g. max-file-size claim but a source file exceeds it) → exit 1 + a drift line naming the claim. AC4: Blank/unparseable claim → reported unverifiable (not drift), never crashes. AC5: Missing conventions.md → clear error, exit 2. AC6: Covered by tests in tests/test_aidd_validate.py; full bootstrap; filesize <400; gen_doc_constants --check green.

## Plan

## Rollback

git revert the commit; validate is a read-only additive subcommand (no writes, no schema change), removal restores prior CLI surface.

## Journal

- 2026-06-14T16:54:20Z [implementation] — Created project_cli_aidd_validate.py: parse conventions.md ## Code bullets → claims (lang_version/lint_tool/test_framework/max_filesize); per-claim verifiers vs repo (requires-python, tool config files+deps, _detect_test_framework reuse, file-line scan). Exit 1 on drift, 2 missing conventions.md, 0 else; per-claim try/except so bad claim → unverifiable never crash. Reuses _DENY_DIRS/_EXT_LANG/_detect_test_framework/_read.
- 2026-06-14T17:04:50Z [implementation] — Adversarial review on SEPARATE model (sonnet): found 2 real false-ok bugs + tool-matching issues. Fixed: (1) version compare numeric tuple (_minor_version) — '3.1' no longer substring-matches '>=3.11'; (2) test-framework + lint-claim word-boundary (\b) — detected 'ava' no longer matches 'javascript'; (3) _tool_present: pyproject deps via _dep_names_tool, flat files line-start regex, package.json parsed dep keys — 'flake8-bugbear' no longer satisfies 'flake8'; (4) section heading exact '== code' (not startswith); (5) circuit-breaker counts ALL visited files + early-exit line count; (6) log type annotation; (7) parent help mentions validate. Dismissed CRITICAL-1 (tomllib.TOMLDecodeError crash) as false-positive: guard returns before except. Added 6 regression tests. 27 tests green, ruff+mypy clean, 295 lines.
- 2026-06-14T17:05:16Z [implementation] — AC1: ✓ parses 4 claim types from conventions.md ## Code, each reported ok/drift/unverifiable — TestParsing + TestCmdAiddValidate. AC2: ✓ matching repo → exit 0 all-ok — test_all_ok_exits_0 + CLI smoke. AC3: ✓ contradicted claim → exit 1 + drift line naming claim — test_drift_exits_1_and_names_claim + CLI smoke (lang/lint/filesize drifts). AC4: ✓ blank/unparseable → unverifiable not drift, never crashes — test_blank_claims_unverifiable_not_drift, test_non_utf8_conventions_does_not_crash, per-claim try/except. AC5: ✓ missing conventions.md → exit 2 — test_missing_conventions_exits_2 + CLI smoke. AC6: ✓ tests 4233 green; full bootstrap; filesize 295<400; gen_doc_constants --check green + README synced; ruff+mypy clean. Adversarial review (sonnet) fixed 2 false-ok bugs (version-prefix substring, framework/tool word-boundary) + regression tests. Negative: '3.1+' vs '>=3.11' → drift (no false-ok); 'flake8-bugbear' does NOT satisfy 'flake8'; detected 'ava' does NOT match 'javascript' claim; '## Code of conduct' bullets ignored; non-utf8 conventions.md → no crash.
- 2026-06-14T17:05:48Z [implementation] — AC1: ✓ parses 4 claims from conventions.md ## Code, each ok/drift/unverifiable (TestParsing+TestCmdAiddValidate). AC2: ✓ matching repo→exit 0 (test_all_ok_exits_0+CLI). AC3: ✓ contradicted→exit 1+drift line naming claim (test_drift_exits_1_and_names_claim+CLI). AC4: ✓ blank/unparseable→unverifiable not drift, never crash (test_blank_claims_unverifiable_not_drift, test_non_utf8, per-claim try/except). AC5: ✓ missing conventions.md→exit 2 (test_missing_conventions_exits_2+CLI). AC6: ✓ 4233 tests green; bootstrap; filesize 295<400; gen_doc_constants green+README synced; ruff+mypy clean. Adversarial review (sonnet) fixed 2 false-ok bugs + 6 regression tests; knowledge #168. Negative: '3.1+'≠'>=3.11'→drift; 'flake8-bugbear'≠'flake8'; 'ava'≠'javascript'; '## Code of conduct' ignored; non-utf8→no crash.
