---
slug: mypy-and-bandit-are-unpinned-in-ci-like-ruff-was
title: "mypy и bandit в CI стоят без пина — тот же класс, что уронил гейт ruff в день выпуска"
status: done
epic: release-110-deferred-from-19
story: release110-site-docs-and-hygiene
complexity: simple
role: backend
stack: null
tier: light
call_budget: 25
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - ci-constraints.txt
  - ".github/workflows/tests.yml"
  - ".github/workflows/security-review.yml"
  - ".gitlab-ci.yml"
  - CONTRIBUTING.md
  - "tests/test_ci_tool_pins.py"
  - "tests/test_ci_lanes_are_honest.py"
scope_paths:
  - ".github/workflows/*.yml"
  - ".gitlab-ci.yml"
  - ci-constraints.txt
  - CONTRIBUTING.md
  - "tests/*.py"
  - "CHANGELOG*.md"
scope_tools: []
depends_on: []
completed_at: "2026-09-23T23:12:40Z"
resolution: null
resolution_reason: null
tracker_refs:
  - "github#87"
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

Вердикт каждого статического инструмента в CI определяется конфигом репозитория, а не тем, что вышло накануне — как уже сделано для ruff.

## Acceptance Criteria

1. ruff, mypy and bandit are pinned with == in ONE constraints file (ci-constraints.txt) at the versions the local gates run today (ruff 0.16.5 on PATH, mypy 1.20.2, bandit 1.9.4), and every CI install of them — GitHub tests.yml, security-review.yml, .gitlab-ci.yml — and the CONTRIBUTING install line go through it with -c. 2. NEGATIVE: a test reads every install line in those files and fails on a bare install of any of the three tools (checked on a synthetic 'pip install ruff' line too, so the test can fail). 3. NEGATIVE: the lane-honesty ratchet (tests/test_ci_lanes_are_honest.py) stays green and its tokenizer no longer mistakes the file after -c for a package. 4. The task title's premise is corrected in the journal: ruff was NOT pinned either.

## Plan

## Rollback

git revert правки конфигов CI

## Journal

- 2026-09-23T23:12:20Z [implementation] — AC-1: ✓ tests/test_ci_tool_pins.py::test_the_pin_file_pins_every_tool_exactly and tests/test_ci_tool_pins.py::test_no_ci_install_of_a_pinned_tool_is_bare — ci-constraints.txt pins ruff==0.16.5 mypy==1.20.2 bandit==1.9.4 (ruff --version on PATH, venv mypy 1.20.2, venv bandit 1.9.4); tests.yml x3, security-review.yml, .gitlab-ci.yml and CONTRIBUTING.md x2 install with -c ci-constraints.txt; each GitHub job checks out before installing.
- 2026-09-23T23:12:21Z [implementation] — AC-2: ✓ tests/test_ci_tool_pins.py::test_the_reader_can_fail — negative, synthetic bare line refused; mutation (dropping -c from .gitlab-ci.yml) turned test_no_ci_install_of_a_pinned_tool_is_bare red: 1 failed, 10 passed; restored.
- 2026-09-23T23:12:21Z [implementation] — AC-3: ✓ tests/test_ci_lanes_are_honest.py::TestEveryInstallSatisfiesAddopts — negative, all 24 lane tests green including slow ones; the tokenizer now skips the file after -c/--constraint like after -r.
- 2026-09-23T23:12:21Z [implementation] — AC-4: ✓ review — premise corrected: git log -S 'ruff==' finds nothing in any branch; ruff was never pinned in CI. The title's 'like ruff was' referred to nothing that existed; all three are pinned now.
- 2026-09-23T23:12:37Z [implementation] — AC-3: ✓ tests/test_ci_lanes_are_honest.py::TestEveryLaneInstallsWhatTheAddoptsDemand::test_every_install_of_pytest_also_installs_what_addopts_needs — CORRECTION of the class name in the earlier AC-3 line (it was written from memory and was wrong); negative: all 24 lane tests green, the tokenizer skips the file after -c/--constraint.
- 2026-09-26T18:44:28Z [done] — EVIDENCE-UNPROVEN: tests/test_ci_lanes_are_honest.py::TestEveryInstallSatisfiesAddopts — git never carried this path or member under any directory
