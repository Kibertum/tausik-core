---
slug: full-suite-red-on-the-110-change-set
title: "Full suite red on the 1.10 change set: six tests after one full run"
status: done
epic: release-110-deferred-from-19
story: release110-verification-is-cheap
complexity: medium
role: developer
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/gate_ruff_format.py"
  - "scripts/senar_claim.py"
  - "scripts/dead_end_gate.py"
  - "scripts/gate_test_resolver.py"
  - "scripts/rule_coverage.py"
  - "tests/test_renar_citations_resolve.py"
  - "tests/test_codex_support_matrix.py"
  - CLAUDE.md
scope_paths:
  - "scripts/*.py"
  - "tests/*.py"
  - "docs/ru/*.md"
  - "docs/en/*.md"
  - CLAUDE.md
  - "harness/**"
  - "bootstrap/*.py"
  - pyproject.toml
  - "CHANGELOG*.md"
scope_tools: []
depends_on: []
completed_at: "2026-09-23T23:07:15Z"
resolution: null
resolution_reason: null
---

## Goal

The one full run of session #269 (10854 passed) found six regressions left by this release's uncommitted work; each is fixed at its cause before anything is committed.

## Acceptance Criteria

1. The six tests red in the one full run of session #269 are green again, each fixed at its cause: subprocess calls in MCP-reachable modules pass stdin=DEVNULL (gate_ruff_format, senar_claim); mypy is clean over the declared tree (dead_end_gate, gate_test_resolver); the §10.15 citation resolves or is corrected; the codex support matrix and the CLAUDE.md tool-call section agree with the rules they describe.
2. NEGATIVE: no test is weakened, skipped or re-pinned to hide a failure; where a test pins text that changed on purpose, the change is named in the journal with the decision behind it.
3. NEGATIVE: the fix introduces no new failure in the scoped verify of the touched files.

## Plan

## Rollback

git revert of the fix commit

## Journal

- 2026-09-23T23:01:42Z [implementation] — AC-1: ✓ tests/test_risk_compute_stdin.py::TestNoUnguardedSubprocessInMcpPath::test_all_top_level_subprocess_calls_set_stdin, tests/test_mypy_clean.py::test_declared_tree_is_mypy_clean, tests/test_mypy_gate_scope.py::test_conftest_no_longer_reddens_the_mypy_gate, tests/test_renar_citations_resolve.py::test_every_citation_resolves, tests/test_codex_support_matrix.py::test_codex_matrix_is_complete_and_language_paired, tests/test_plan_skill_agent_aware.py::TestClaudeMd::test_section_mentions_tool_calls — all six green, fixed at the cause.
- 2026-09-23T23:01:42Z [implementation] — AC-2: ✓ review — negative, no test weakened. Two tests changed ON PURPOSE and are named here: test_renar_citations_resolve now sets aside a citation the line attributes to SENAR ('SENAR 1.5 §10.15'); an unattributed § is still read as RENAR — the change makes it STRICTER in effect, because SENAR §8.6/§9.4 used to 'resolve' to unrelated RENAR sections of the same number. test_codex_support_matrix now expects Rule 9.2 as 'signal' (decision #376) and still pins every other row hard; rule_coverage.RULES drops 9.2 because it no longer guards an action.
- 2026-09-23T23:01:42Z [implementation] — Root cause: six independent slips of this release's uncommitted work, none caught by the scoped verifies that closed their tasks: (a) new subprocess calls in gate_ruff_format and senar_claim without stdin=DEVNULL; (b) mypy errors in dead_end_gate (Any return) and gate_test_resolver (bool-flag narrowing mypy cannot follow); (c) docs cite 'SENAR 1.5 §10.15(f)' and the RENAR citation test read every § in cli.md as RENAR; (d) decision #376 turned Rule 9.2 into a signal in model-providers.md, but rule_coverage.RULES still listed it as a refusal at tausik_task_start and the Codex matrix test still pinned it hard; (e) the #376 rewrite of CLAUDE.md dropped the only 'tool calls' mention, which pins that estimation is agent-native.
- 2026-09-23T23:01:43Z [implementation] — AC-3: ✓ measurement — related suites after the fix: 81 (codex/rule_coverage/bootstrap/doctor) + 24 (claude_md/plan_skill) + 15 (mypy/stdin) + 3 (citations) passed; scoped verify follows.
- 2026-09-23T23:03:50Z [implementation] — Verify #2826 found a SEVENTH defect, in my own ruff_format gate: _repo_root was dirname-twice, so the DEPLOYED copy (.claude/scripts) resolved to .claude/, read no frozen list and named files ../scripts/x.py — the listed legacy gate_test_resolver.py was refused. Fixed with the .git-anchored walk (as gate_test_dedupe); tests/test_gate_ruff_format.py::test_the_deployed_copy_finds_the_project_root_not_claude_dir pins it.
- 2026-09-23T23:04:55Z [implementation] — NO-DEAD-END: the red verify #2826 was a real defect found by the gate itself (deployed-root bug), fixed and pinned — not a wrong approach.
