---
slug: v15mr-subagent-model-hints
title: "[P2] Model-подсказки для сабагентов (research=haiku)"
status: done
epic: v15-model-routing
story: v15mr-phase-routing
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "harness/skills/review/SKILL.md, harness/skills/ship/SKILL.md, harness/skills/debug/SKILL.md, docs/ru/research/model-routing-matrix.md, tests/*"
scope_exclude: "skills-official/ (external deep-research, not vendored), .claude/ .cursor/ .qwen/ (bootstrap-generated)"
relevant_files:
  - "harness/skills/review/SKILL.md"
  - "harness/skills/ship/SKILL.md"
  - "harness/skills/debug/SKILL.md"
  - "docs/ru/research/model-routing-matrix.md"
  - "tests/test_subagent_model_hints.py"
  - README.md
  - "docs/_generated/constants.json"
scope_paths:
  - "harness/skills/review/SKILL.md"
  - "harness/skills/ship/SKILL.md"
  - "harness/skills/debug/SKILL.md"
  - "docs/ru/research/model-routing-matrix.md"
  - "tests/*"
  - README.md
  - "docs/_generated/constants.json"
scope_tools: []
depends_on: []
completed_at: "2026-06-14T15:23:38Z"
---

## Goal

Зафиксировать выбор модели для сабагентов Agent-tool в skills: search/exploration -> haiku, код-ревью -> sonnet, reasoning-синтез -> opus/fable. Согласовано с token-economy правилом (auto-memory #131: sonnet для поиска, opus только где reasoning).

## Acceptance Criteria

1. Skills c Agent-вызовами (review, explore, deep-research и др.) документируют model= для сабагентов по фазе (research=haiku, code-review=sonnet, synthesis=opus|fable). 2. Гайд-страница соответствия фаза -> модель сабагента (docs или references). 3. Негативный: отсутствие model= в вызове НЕ ошибка (подсказка/гайд, не блок) — grep-тест дрейфа skills не падает на легаси. 4. pytest/grep-тест на наличие подсказок в целевых SKILL.md.

## Plan

## Rollback

git revert: только skills-доки и гайд, поведение кода не меняется

## Journal

- 2026-06-14T15:23:37Z [implementation] — AC verified: 1. ✓ review/ship/debug SKILL.md document per-phase subagent model via 'Subagent model (phase=code-review)' callouts + concrete model="sonnet" in Agent examples (critic->Opus 4.8) — tests/test_subagent_model_hints.py::TestSkillHints 2. ✓ Guide page: docs/ru/research/model-routing-matrix.md '## Сабагенты (Agent-tool)' table maps search/exploration->Haiku, code-review->Sonnet, synthesis->Opus|Fable — TestGuidePage::test_matrix_doc_has_subagent_section 3. ✓ Negative: model= is advisory, not required — doc states 'подсказка, не требование'; legacy end/SKILL.md spawns subagent without the hint and is allowed — TestAdvisoryNotMandatory (2 tests) 4. ✓ grep-test tests/test_subagent_model_hints.py 6 passed; bootstrap propagated hints to .claude skill copies; doc-constants 4135 in sync (gen_doc_constants --check OK)
