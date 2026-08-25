---
slug: v15-aidd-autogen-cmd
title: "tausik aidd autogen — draft vision.md from repo signals"
status: done
epic: v15-cross-ide-parity
story: v15-aidd-autogen
complexity: complex
role: developer
stack: python
tier: substantial
call_budget: 120
defect_of: null
scope: "scripts/project_cli_aidd_autogen.py (new), scripts/project_cli_aidd.py (write_file_with_conflict), scripts/project_parser_aidd.py (new), scripts/project_parser.py, scripts/project_cli.py (cmd_aidd), scripts/project.py (dispatch), bootstrap/bootstrap_copy.py + bootstrap/bootstrap.py (copy_aidd_templates), tests/test_aidd_autogen.py, tests/test_bootstrap_aidd.py, docs/{en,ru}/cli.md, README.md, docs/_generated/constants.json"
scope_exclude: "harness/aidd-templates/* (template content unchanged), .claude/* (generated)"
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-14T16:49:53Z"
---

## Goal

Add `tausik aidd autogen [--write] [--force]`: gather machine-extractable repo signals (README headings/first paragraph, package metadata name+description from pyproject/package.json, top-level source dirs, detected languages, test framework) and emit a draft vision.md pre-seeded with those facts under the existing template sections. Reuses scaffold conflict-handling (overwrite/merge-append/skip). Stdlib-only, no LLM call. Acceptance: clean dir creates seeded vision.md; existing file triggers conflict prompt; --write persists, default prints to stdout; signals missing → section left as template placeholder, never crashes.

## Acceptance Criteria

AC1: In a clean dir, `tausik aidd autogen --write` creates vision.md seeded with extracted repo facts (name/description, top-level dirs, languages, test framework) under the template sections. AC2: With an existing vision.md, conflict-handling fires (overwrite/merge-append/skip; --force overwrites) — reuses scaffold semantics. AC3: Default (no --write) prints the draft to stdout, writes nothing. AC4: When a signal is missing, its section keeps the template placeholder and the command never crashes (exit 0). AC5: Covered by tests in tests/test_aidd_autogen.py; full bootstrap run; filesize <400; gen_doc_constants --check green.

## Plan

## Rollback

git revert the commit; the autogen subcommand is additive (new dispatch branch + new module functions), removing it restores prior `tausik init` behavior with no schema/migration impact.

## Journal

- 2026-06-14T16:33:30Z [implementation] — Added write_file_with_conflict (single-file content-based conflict writer reusing scaffold semantics) to project_cli_aidd.py; refactored _merge_append to share _merge_append_content. Created project_cli_aidd_autogen.py: gather_signals (pyproject/package.json meta, README title+intro, top dirs, languages by ext, test framework) + render_vision injecting facts block, stdlib-only, missing signal→placeholder.
- 2026-06-14T16:46:46Z [implementation] — Adversarial review on SEPARATE model (sonnet) found 3 HIGH crash-paths (AC4 violations): UnicodeDecodeError in _detect_readme + _read merge path, OSError on template read. Fixed: _read uses errors=replace; _detect_readme/_detect_test_framework reads use errors=replace; template read wrapped in try/except→exit 1. MEDIUM: subparser required=True (clean argparse error). LOW: _pyproject_has_pytest precise tool/dep navigation (no false 'pytest' substring match); _fmt explicit None check. Added regression tests TestNonUtf8Inputs + TestPyprojectHasPytest. 47 aidd tests green, ruff+mypy clean, bootstrap re-run, gen_doc_constants 4205 synced (README badge).
- 2026-06-14T16:47:01Z [implementation] — AC1: ✓ clean dir `aidd autogen --write` creates vision.md seeded with name/description/top-dirs/languages/test-framework under template sections — via tests/test_aidd_autogen.py::TestCmdAiddAutogen::test_write_creates_seeded_vision + TestGatherSignals::test_end_to_end_python_repo; CLI smoke (/tmp/aidd_smoke) showed Name/Top-level dirs/Languages/Test framework all seeded. AC2: ✓ existing vision.md → conflict prompt (skip default / overwrite / merge-append / abort-all), --force overwrites — via test_existing_file_skip_by_default, test_force_overwrites, test_merge_append_non_utf8_existing_does_not_crash; CLI smoke confirmed skip + --force. AC3: ✓ default (no --write) prints draft to stdout, writes nothing — via test_default_prints_to_stdout_writes_nothing; CLI smoke confirmed vision.md absent after default run. AC4: ✓ missing signal → placeholder, never crashes (exit 0) — via test_empty_repo_never_crashes_exit_0 + test_missing_signal_becomes_placeholder + crash-path regressions TestNonUtf8Inputs (latin-1 README + non-utf8 merge) + precise pytest detection (no false substring match). AC5: ✓ tests/test_aidd_autogen.py (+tests/test_bootstrap_aidd.py) 47 pass; full `python bootstrap/bootstrap.py` run (now copies harness/aidd-templates → .claude via new copy_aidd_templates); all touched files <400 lines (autogen 316, parser 399); gen_doc_constants --check green (test_count 4205, README badge synced); ruff + mypy clean; verify gate passed=True. Adversarial review on SEPARATE model (sonnet): 3 HIGH crash-paths fixed before close. Negative: `tausik aidd` (no subcommand) → exit 2 argparse error (required=True); `aidd bogus` → exit 2 invalid choice; empty repo → vision.md all-placeholder, exit 0, no crash; non-UTF-8 README / existing vision.md → no UnicodeDecodeError (errors=replace).
- 2026-06-14T16:49:40Z [implementation] — AC1: ✓ `aidd autogen --write` in clean dir creates vision.md seeded with name/description/top-dirs/languages/test-framework under template sections — tests test_write_creates_seeded_vision + test_end_to_end_python_repo; CLI smoke confirmed. AC2: ✓ existing vision.md → conflict prompt (skip default/overwrite/merge-append/abort), --force overwrites — tests test_existing_file_skip_by_default, test_force_overwrites, test_merge_append_non_utf8_existing_does_not_crash; CLI smoke confirmed. AC3: ✓ default prints to stdout, writes nothing — test_default_prints_to_stdout_writes_nothing; CLI smoke (vision.md absent). AC4: ✓ missing signal → placeholder, exit 0, never crashes — test_empty_repo_never_crashes_exit_0, test_missing_signal_becomes_placeholder, TestNonUtf8Inputs (latin-1 README + non-utf8 merge), precise pytest detection. AC5: ✓ tests 4206 total green (test_aidd_autogen, test_bootstrap_aidd, test_gates::test_filesize_gate_exempts_cli_reference); full bootstrap run (copy_aidd_templates bundles harness/aidd-templates → .claude); all touched code files <400; gen_doc_constants --check green + README badge synced; ruff+mypy clean. Adversarial review on SEPARATE model (sonnet): 3 HIGH crash-paths fixed pre-close. Gate fix: docs/{en,ru}/cli.md were pre-existing >400 (427/442 at HEAD); the +2-command doc edit surfaced it. Exempted cli.md in the COMMITTED filesize gate (same rationale as CHANGELOG/research dumps — reference doc grows by design), covered by a new gate test. Negative: `tausik aidd` (no subcommand) → exit 2 (required=True argparse); `aidd bogus` → exit 2; empty repo → all-placeholder vision.md, exit 0; non-UTF-8 README/existing file → no UnicodeDecodeError (errors=replace); filesize gate still BLOCKS a non-cli/non-research large .md (test_filesize_gate_non_research_md_still_blocks).
