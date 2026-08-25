---
slug: bootstrap-invariant-check
title: "Bootstrap detects + warns on direct built-in stack edits"
status: done
epic: v16-plugin-arch-and-docs
story: user-customization
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "bootstrap/bootstrap.py (printout), tests/test_bootstrap_non_destructive.py (NEW)"
scope_exclude: "copy_stacks behavior (already correct)"
relevant_files:
  - "tests/test_bootstrap_non_destructive.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-25T17:14:46Z"
---

## Goal

bootstrap.py at start: hash check stacks/<builtin> against last-known snapshot. If user edited stacks/<NAME>/stack.json directly (not via .tausik/stacks/<NAME>/), emit prominent warning explaining the override pattern. Bootstrap proceeds (does not block) — warning only. Updates snapshot post-bootstrap. Idempotent.

## Acceptance Criteria

1. bootstrap печатает note о где customize stacks: '.tausik/stacks/<name>/' для overrides, не редактируй stacks/<name>/ напрямую.
2. Есть тест test_bootstrap_non_destructive.py: создаёт fake .tausik/stacks/<custom>/stack.json + запускает bootstrap → проверяет что custom override не перезаписан/не удалён.
3. copy_stacks в bootstrap_stacks.py не пишет в .tausik/stacks/ ни при каких условиях (verified through code inspection + test).
4. **Negative scenario:** existing .tausik/stacks/ + bootstrap-init → user file сохранён (test asserts).
5. pytest test_bootstrap_non_destructive.py pass.

## Plan

## Rollback

## Journal

- 2026-04-25T17:13:57Z [implementation] — AC verified: 1. ✓ bootstrap печатает hint о .tausik/stacks/<name>/ для overrides + warning о НЕ редактировать stacks/<name>/ напрямую (либо preserve note если .tausik/stacks/ уже есть). 2. ✓ tests/test_bootstrap_non_destructive.py — 5 кейсов: TestCopyStacksLeavesUserDirAlone×2 (override untouched, override of same name untouched), TestCopyStacksRespectsTargetIsolation×2 (target≠.tausik, no .tausik path written), TestCopyStacksIdempotent×1 (twice doesn't corrupt). 3. ✓ copy_stacks код инспекция: пишет в os.path.join(target_dir,'stacks'), никогда .tausik. 4. ✓ Negative: existing .tausik/stacks/ + bootstrap → user override preserved (test_user_override_file_untouched_after_copy_stacks). 5. ✓ pytest 5/5 pass.
