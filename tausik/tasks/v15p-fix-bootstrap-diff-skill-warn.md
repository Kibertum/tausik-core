---
slug: v15p-fix-bootstrap-diff-skill-warn
title: "[P2] Defect: bootstrap трижды пишет «skills not found: diff»"
status: done
epic: v15-polish
story: v15p-defects
complexity: simple
role: developer
stack: python
tier: light
call_budget: 25
defect_of: null
scope: "bootstrap/bootstrap_config.py (detect_extension_skills .git→diff mapping + ALL_EXTENSION_SKILLS), skills.example.json (official skill_dirs), tests/ (regression)"
scope_exclude: "other phantom catalog entries (onboard/init) — separate follow-up; copy_skills warning semantics unchanged; registry.json content"
relevant_files:
  - "bootstrap/bootstrap_config.py"
  - skills.example.json
  - "tests/test_bootstrap_extension_skills.py"
  - README.md
  - "docs/_generated/constants.json"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-14T17:30:13Z"
---

## Goal

Найдено quality sweep 2026-06-12: bootstrap --ide all детектит extension skills «diff, docs», но затем 3 раза (по разу на IDE) предупреждает «skills not found: diff» — рассинхрон detect-каталога и фактического набора skills. AC: root cause найден (детектор vs каталог); предупреждение либо устранено (skill добавлен/детект исправлен), либо даунгрейднуто с объяснением; bootstrap --ide all чистый.

## Acceptance Criteria

AC1: root cause identified — why the detect step lists 'diff' as an extension skill but copy_skills reports it missing (detector vs catalog/source mismatch). AC2: the spurious "skills not found: diff" warning is eliminated (skill source added, or detector corrected, or the list reconciled) OR downgraded with a clear explanation if genuinely optional. AC3: `python bootstrap/bootstrap.py --ide all` runs clean (no repeated skills-not-found warning). AC4: covered by a test; filesize<400.

## Plan

## Rollback

## Journal

- 2026-06-14T17:29:59Z [implementation] — Root cause: skills-official/registry.json has 20 skills (incl docs) but NOT diff; detect_extension_skills mapped .git→diff and diff was in ALL_EXTENSION_SKILLS + skills.example.json — phantom (no source in registry/builtin; git covered by builtin commit/review). copy_skills filter only drops registry skills, so phantom diff survived → 3× 'skills not found: diff'. Fix: removed .git→diff mapping, removed diff from ALL_EXTENSION_SKILLS + skills.example.json. Regression test tests/test_bootstrap_extension_skills.py asserts no detector output is a phantom (all resolve to registry∪builtin). Reproduced clean: 'Extension skills detected: docs', no warning.
- 2026-06-14T17:30:13Z [implementation] — AC1: ✓ root cause — detect_extension_skills mapped .git→'diff' + 'diff' in ALL_EXTENSION_SKILLS/skills.example.json, but skills-official/registry.json (20 skills) has no 'diff' and no builtin source; copy_skills filter only drops registry skills so the phantom survived→missing→3× warning. AC2: ✓ eliminated — removed the phantom 'diff' from detector + ALL_EXTENSION_SKILLS + skills.example.json (git workflow covered by builtin commit/review). AC3: ✓ bootstrap --ide all clean — reproduced: 'Extension skills detected: docs', zero 'skills not found'. AC4: ✓ tests/test_bootstrap_extension_skills.py (3 tests) incl regression guard 'no detector output is a phantom (resolves to registry∪builtin)'; bootstrap_config.py 341<400. Negative: a real .git+docs+.env repo still detects docs+security (only the phantom diff removed); test_no_recommendation_is_a_phantom fails loudly if any future detector output lacks a source.
