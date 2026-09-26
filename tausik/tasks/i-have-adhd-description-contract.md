---
slug: i-have-adhd-description-contract
title: "Описание навыка i-have-adhd нарушает контракт каталога: 110 символов и без trigger-сигнала"
status: done
epic: release-19-agent-effectiveness
story: release19-effective-context
complexity: simple
role: tech-writer
stack: python
tier: light
call_budget: 12
defect_of: adopt-the-i-have-adhd-answer-rules-as-the-project-
scope: null
scope_exclude: null
relevant_files:
  - "harness/skills/i-have-adhd/SKILL.md"
  - "tests/test_skill_descriptions_length.py"
scope_paths:
  - "harness/skills/i-have-adhd/SKILL.md"
  - "tausik/tasks/i-have-adhd-description-contract.md"
  - "tausik/stories/release19-effective-context.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-09-12T13:30:19Z"
resolution: null
resolution_reason: null
---

## Goal

Полный прогон (смена #244, 10590 passed / 3 failed) красный на tests/test_skill_descriptions_length.py для harness/skills/i-have-adhd/SKILL.md: description 110 символов при пороге 60 и не содержит имени навыка, поэтому каталог навыков теряет discoverability. Сократить description до ≤60 символов с именем навыка в тексте, не меняя тело навыка, лицензию и атрибуцию источника; переразвернуть профили.

## Acceptance Criteria

AC-1: tests/test_skill_descriptions_length.py::test_skill_description_length[i-have-adhd] green (≤60 chars). AC-2: test_skill_description_contains_a_trigger_signal[i-have-adhd] green — the folder name appears in the description. AC-3 (negative): body, license and metadata.source/copyright of SKILL.md are byte-identical (git diff shows only the description line). AC-4: bootstrap --check clean after redeploy; focused pytest and signed verify pass.

## Plan

## Rollback

git revert одного коммита с описанием.

## Journal

- 2026-09-12T13:29:44Z [implementation] — Root cause (documentation): the skill was adopted with a 110-char description that the ≤60-char catalog contract (tests/test_skill_descriptions_length.py) rejects and that never names the skill folder, so the trigger-signal test had nothing to match; the adopting task's scoped lane did not map to that test. Prevention: description now 54 chars and starts with the folder name; the catalog tests sit in the full lane and were run before this closure.
- 2026-09-12T13:29:45Z [implementation] — AC verified: AC-1 ✓ test_skill_description_length[i-have-adhd] green (54 chars). AC-2 ✓ test_skill_description_contains_a_trigger_signal[i-have-adhd] green — 'i-have-adhd' is the first token. AC-3 ✓ Negative: git diff shows one line changed; body, license: MIT, metadata.source and copyright untouched. AC-4 ✓ bootstrap --ide all redeployed, bootstrap --check clean; 33/33 in the catalog test file; signed verify below. Domain: the deployed catalog line for /i-have-adhd now reads like its 13 siblings (name — what it does).
