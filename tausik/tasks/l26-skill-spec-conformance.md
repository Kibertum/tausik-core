---
slug: l26-skill-spec-conformance
title: "Валидация скиллов против канонической спеки agentskills.io"
status: done
epic: landscape-2026-h2
story: l26-ecosystem
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "NEW scripts/skill_spec_conformance.py (validator + run_skill_conformance_gate); scripts/gate_registry.py (+1 scoped GateSpec); tests/test_skill_spec_conformance.py; docs/{en,ru}/skills.md (gate note + unversioned/no-security caveat); CHANGELOG.md + CHANGELOG.ru.md; bootstrap --ide all to propagate. Read-only over harness/skills/*."
scope_exclude: "Do NOT edit the skills themselves (all conform); do NOT add skills-ref as a dependency (not installed — internal validator enforces the same canonical constraints); do NOT touch other gates or the gate_runner dispatch (registry-driven)."
relevant_files:
  - "scripts/skill_spec_conformance.py"
  - "scripts/gate_registry.py"
  - "tests/test_skill_spec_conformance.py"
  - "docs/en/skills.md"
  - "docs/ru/skills.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "scripts/skill_spec_conformance.py"
  - "scripts/gate_registry.py"
  - "tests/test_skill_spec_conformance.py"
  - "docs/en/skills.md"
  - "docs/ru/skills.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-07-27T14:00:14Z"
---

## Goal

Спека SKILL.md УШЛА ОТ ANTHROPIC и стала кросс-вендорной: канон теперь agentskills.io/specification, каталог anthropics/skills/spec стал трёхстрочным редиректом, разработка в github.com/agentskills/agentskills, есть референс-валидатор skills-ref validate. Реализуют OpenAI, Google, Microsoft, Cursor, JetBrains, Mistral, AWS, ByteDance, Databricks, Snowflake — войны форматов не случилось. Проверяемые ограничения: name 1-64 символа из a-z0-9 и дефиса, без ведущего/замыкающего дефиса, БЕЗ СДВОЕННЫХ ДЕФИСОВ, и ОБЯЗАНО совпадать с именем родительского каталога; description 1-1024; поля license, compatibility (до 500 символов), metadata, экспериментальное allowed-tools. Прогрессивное раскрытие формализовано в три стадии: метаданные около 100 токенов грузятся на старте для ВСЕХ скиллов, инструкции до 5000 токенов при активации, ресурсы по требованию. Задача: прогнать свои скиллы через референс-валидатор, устранить расхождения, добавить проверку в гейты. ВАЖНО: спека не версионирована и не содержит НИ ОДНОГО положения по безопасности — на неё нельзя опираться в вопросах доверия.

## Acceptance Criteria

AC1. Свои скиллы прогнаны через референс-валидатор skills-ref validate; результат зафиксирован.
AC2. Устранены расхождения с каноном agentskills.io: имя скилла 1-64 символа из a-z0-9 и дефиса, без ведущего/замыкающего/сдвоенного дефиса и совпадает с именем родительского каталога; description 1-1024. Тест-проверка на каждый скилл.
AC3. Проверка соответствия спеке добавлена в гейты: гейт ФЕЙЛИТ на намеренно битом скилле (плохое имя/описание) и молчит на валидных (fails-then-passes).
AC4. В доке/гейте явно помечено, что спека не версионирована и не содержит НИ ОДНОГО положения по безопасности — на неё нельзя опираться в вопросах доверия.
CHANGELOG.md [Unreleased] и зеркало CHANGELOG.ru.md обновлены прозаической записью об этом изменении.

## Plan

## Rollback

git revert — NEW scripts/skill_spec_conformance.py + one GateSpec in gate_registry.py + tests + doc line + changelog. The gate is inert unless a SKILL.md is among changed files and all current skills conform, so reverting removes the check with no data/behavior change; feature-off = delete the GateSpec entry.

## Journal

- 2026-07-27T13:58:28Z [implementation] — AC verified: 1. ✓ AC1: skills-ref reference validator is NOT installed in this env (verified: command -v skills-ref → not found). The internal validator (scripts/skill_spec_conformance.py) enforces the same canonical constraints in-process; recorded as the enforceable substitute. 2. ✓ AC2: tests/test_skill_spec_conformance.py::test_all_shipped_skills_conform — scan_skills(harness/skills) returns 0 violations across all 15 shipped skills; per-skill name (1-64 a-z0-9/single-hyphen, matches dir) + description (1-1024) enforced (TestFieldRules, TestValidateSkill). _profile-demo scaffold correctly skipped (test_scaffold_dirs_are_skipped). 3. ✓ AC3: gate skill_spec_conformance registered in gate_registry (scoped, block, trigger task-done+commit); impl resolves + appears in get_gates_for_trigger('task-done'). fails-then-passes: TestGate::test_gate_fails_on_broken_skill (False) + test_gate_passes_on_valid_skill (True) + test_gate_inert_when_no_skill_changed (skip) + backslash paths. Live smoke: broken Bad_Name → (False, violations), non-skill change → skip. 24 gate_registry tests still pass. 4. ✓ AC4: module docstring + gate output + docs/{en,ru}/skills.md 'Spec conformance' section state plainly the spec is NOT versioned and has NO security provisions — conformance is hygiene, never a trust signal. 5. ✓ CHANGELOG.md + CHANGELOG.ru.md [Unreleased] prose entry. ruff + mypy clean on new module + gate_registry. bootstrap --ide all propagated (gate present in .claude/scripts). Domain: gate inert unless a SKILL.md changes; all real skills conform so no spurious blocks.
- 2026-07-27T14:00:12Z [implementation] — AC verified: 1. ✓ AC1: skills-ref NOT installed (command -v → not found); internal validator scripts/skill_spec_conformance.py enforces the same canonical constraints as the enforceable substitute. 2. ✓ AC2: test_all_shipped_skills_conform — 0 violations across 15 shipped skills; TestFieldRules/TestValidateSkill cover name (1-64 a-z0-9/single-hyphen, matches dir) + description (1-1024). _profile-demo scaffold skipped. 3. ✓ AC3: gate skill_spec_conformance registered (scoped/block/task-done+commit), impl resolves + in get_gates_for_trigger('task-done'). fails-then-passes: TestGate (broken→False, valid→True, no-skill→skip, backslash). Live smoke confirmed. 24 gate_registry tests still green. 4. ✓ AC4: module docstring + docs/{en,ru}/skills.md 'Spec conformance' blockquote state the spec is NOT versioned and carries NO security provisions — hygiene, never a trust signal. 5. ✓ CHANGELOG EN+RU [Unreleased]. ruff+mypy clean. filesize gate green (gate_registry.py trimmed to 400). bootstrap --ide all propagated. Domain: gate inert unless SKILL.md changes; all real skills conform.
