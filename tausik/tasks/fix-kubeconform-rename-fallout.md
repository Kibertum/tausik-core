---
slug: fix-kubeconform-rename-fallout
title: "Fix test + doc fallout from kubeval→kubeconform gate rename"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: null
tier: light
call_budget: 20
defect_of: k8s-stack-kubeconform
scope: "tests/test_stack_iac.py; docs/en/architecture.md, docs/ru/architecture.md, docs/en/cli.md, docs/ru/cli.md, docs/en/mcp.md, docs/ru/mcp.md"
scope_exclude: "stacks/kubernetes/* (already correct); other stacks; scripts/*; .claude/ deployed copies."
relevant_files:
  - "tests/test_stack_iac.py"
  - "docs/en/architecture.md"
  - "docs/ru/architecture.md"
  - "docs/en/cli.md"
  - "docs/ru/cli.md"
  - "docs/en/mcp.md"
  - "docs/ru/mcp.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-26T11:24:37Z"
---

## Goal

Repair the regression the k8s-stack-kubeconform rename left behind: tests/test_stack_iac.py still hardcodes the old 'kubeval' gate key in 5 places (5 tests fail — the tree ships a red suite), and 6 source doc lines (docs/{en,ru}/{architecture,cli,mcp}.md) still enumerate 'kubeval' among the heavy IaC gates. Rename all to 'kubeconform' so the suite is green and docs match the shipped stack. Root cause: the k8s task verified with --no-tests-expected and missed that test_stack_iac.py exercises stack-gate registration.

## Acceptance Criteria

1. tests/test_stack_iac.py: all 5 'kubeval' occurrences (lines ~47,64,71,137,169 incl. the id="kubeval_runs_for_k8s_manifest" string) → 'kubeconform'; `pytest tests/test_stack_iac.py` goes fully green. 2. The 6 source doc lines (docs/en/architecture.md, docs/ru/architecture.md, docs/en/cli.md, docs/ru/cli.md, docs/en/mcp.md, docs/ru/mcp.md) list 'kubeconform' instead of 'kubeval'. 3. No 'kubeval' reference remains anywhere except CHANGELOG entries that intentionally document the deprecation. 4. NEGATIVE/EDGE: the rename must not touch other IaC gate names (ansible-lint/terraform-validate/helm-lint/hadolint stay); test assertions still check the same behavior (registration, stack-map membership, lint-only description), just under the new key.

## Plan

## Rollback

git checkout -- tests/test_stack_iac.py docs/en/architecture.md docs/ru/architecture.md docs/en/cli.md docs/ru/cli.md docs/en/mcp.md docs/ru/mcp.md

## Journal

- 2026-07-26T11:23:52Z [implementation] — AC verified: 1. ✓ tests/test_stack_iac.py 5 kubeval sites → kubeconform; `pytest tests/test_stack_iac.py` = 37 passed (was 5 failed/32 passed). 2. ✓ 6 source doc lines (docs/{en,ru}/{architecture,cli,mcp}.md) now list kubeconform. 3. ✓ No kubeval remains except CHANGELOG (intentional deprecation note) and docs/ru/research/*.md (historical archives — editing would falsify the dated record, per memory #313). 4. ✓ NEGATIVE: other IaC gates untouched (ansible-lint/terraform-validate/helm-lint/hadolint — 18 refs intact); assertions check the same behavior under the new key. ROOT CAUSE: k8s-stack-kubeconform renamed the gate key but verified with --no-tests-expected, so the pre-existing test_stack_iac.py (hardcodes gate names) never ran and its 5 kubeval assertions weren't caught. The review-every-5 adversarial pass caught it before commit. PREVENTION: when renaming a registered gate/stack/role key, grep tests/ for the old key and NEVER use --no-tests-expected if a *_iac/registry/_test exists for the changed artifact.
- 2026-07-26T11:24:54Z [done] — Root cause (regression): kubeval→kubeconform gate-key rename in stack.json broke test_stack_iac.py (5 hardcoded 'kubeval' assertions) and left 6 doc lines stale; the renaming task closed green because it verified with --no-tests-expected, so the covering registry test never ran. Prevention: when renaming any registry key (gate/stack/role), grep tests/ for the old key before closing and never declare --no-tests-expected when a *_iac/registry test exists for the changed artifact.
