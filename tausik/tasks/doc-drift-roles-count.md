---
slug: doc-drift-roles-count
title: "Add roles-count drift pattern + fix stale '5 роли' in architecture.md"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: null
tier: moderate
call_budget: 30
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/code_counts.py"
  - "scripts/doc_drift_common.py"
  - "scripts/gen_doc_constants.py"
  - "docs/en/architecture.md"
  - "docs/ru/architecture.md"
  - "docs/_generated/constants.json"
  - "tests/test_doc_drift_scanners.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-26T11:57:26Z"
---

## Goal

Close a drift blind-spot exposed while adding the devops role: doc_drift_common._CODE_COUNT_PATTERNS covers stacks/hooks/review-agents but NOT roles, so 'N roles'/'N ролей' references drift silently. architecture.md already went stale — line 115 lists '5 ролей (developer, architect, qa, tech-writer, ui-ux)' and the harness/ tree comment says '5 ролей', both missing devops (now 6). Add a roles_count to constants + a roles-count regex pattern, and reconcile the stale architecture.md references (note: they sit in a ```fence so the scanner won't auto-fix — fix as literals).

## Acceptance Criteria

1. gen_doc_constants.py computes roles_count by counting harness/roles/*.md; constants.json gains "roles_count": 6. 2. doc_drift_common._CODE_COUNT_PATTERNS gains a roles-count pattern (EN "N roles" + RU "N ролей/роли/роль"), narrow enough to dodge false positives, ignoring fenced blocks like the others. 3. architecture.md:115 (EN+RU) fixed literally 5→6 with devops added (in-fence, scanner won't auto-fix); EN:114 "12 core"→"13" reconciled to skills_core_count. 4. A behavioral test asserts the roles-count pattern flags a stale "5 roles" and passes on "6 roles". 5. python -m pytest tests/test_doc_drift_scanners.py green; doc-drift --check passes.

## Plan

## Rollback

## Journal

- 2026-07-26T11:52:49Z [implementation] — Added count_roles() to code_counts.py + roles_count:6 to constants.json (regenerated). Added roles-count EN+RU patterns to doc_drift_common._CODE_COUNT_PATTERNS (fence-blind by design). Fixed architecture.md:115 EN+RU 5→6 roles +devops, and EN:114 12→13 core skills (reconciled to skills_core_count). Added TestRolesCount (5 cases) to test_doc_drift_scanners.py — 12 passed. gen_doc_constants --check: matches.
- 2026-07-26T11:56:18Z [implementation] — AC verified: 1. ✓ code_counts.count_roles() counts harness/roles/*.md; constants.json regenerated with roles_count:6 (gen_doc_constants --check: matches) 2. ✓ doc_drift_common._CODE_COUNT_PATTERNS gained EN 'N roles' + RU 'N рол(ь|и|ей)' patterns, fence-blind via scan_code_counts _strip_fenced_blocks 3. ✓ architecture.md:115 EN+RU 5->6 roles +devops; EN:114 12->13 core; grep '5 roles|5 ролей' across docs/README/AGENTS/CLAUDE = none 4. ✓ tests/test_doc_drift_scanners.py::TestRolesCount 5 cases (stale EN/RU flagged, clean on 6, fenced ignored, role-scoped no-FP) 5. ✓ tausik verify --task doc-drift-roles-count: pytest PASS over test_gen_doc_constants.py+test_doc_drift_scanners.py (12 passed); gen_doc_constants --check matches
- 2026-07-26T11:56:47Z [implementation] — AC verified: 1. ✓ code_counts.count_roles() counts harness/roles/*.md; constants.json regenerated roles_count:6 (gen_doc_constants --check matches); bootstrap --ide all redeployed to 5 profiles 2. ✓ doc_drift_common._CODE_COUNT_PATTERNS gained EN 'N roles' + RU 'N рол(ь|и|ей)' patterns, fence-blind via _strip_fenced_blocks 3. ✓ architecture.md:115 EN+RU 5->6 roles +devops; EN:114 12->13 core; grep '5 roles|5 ролей' across docs/README/AGENTS/CLAUDE = none 4. ✓ tests/test_doc_drift_scanners.py::TestRolesCount 5 cases green 5. ✓ tausik verify --task: pytest PASS over test_gen_doc_constants.py+test_doc_drift_scanners.py; bootstrap_drift now clean after redeploy
- 2026-07-26T11:57:24Z [implementation] — AC verified: 1. ✓ count_roles() + roles_count:6 in constants.json; bootstrap --ide all redeployed (Roles: 6 copied) 2. ✓ _CODE_COUNT_PATTERNS EN+RU roles patterns, fence-blind 3. ✓ architecture.md:115 EN+RU 5->6 +devops; EN:114 12->13; grep residual '5 roles' = none 4. ✓ TestRolesCount 5 cases green 5. ✓ verify --task: pytest PASS scoped over test_gen_doc_constants+test_doc_drift_scanners; bootstrap_drift clean
