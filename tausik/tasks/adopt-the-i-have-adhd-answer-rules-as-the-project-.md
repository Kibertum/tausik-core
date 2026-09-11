---
slug: adopt-the-i-have-adhd-answer-rules-as-the-project-
title: "adopt the i-have-adhd answer rules as the project answer style"
status: done
epic: release-19-agent-effectiveness
story: context-carries-over-between-sessions
complexity: medium
role: tech-writer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "harness/skills/i-have-adhd/; shared skill-deployment manifests/templates and focused tests/docs that enumerate cross-host discovery."
scope_exclude: "Do not weaken task journals, verify receipts, acceptance evidence or docstrings; do not modify unrelated official skills; do not release, tag, push, or touch user-owned .agents/."
relevant_files:
  - "harness/skills/i-have-adhd/SKILL.md"
  - "harness/skills/i-have-adhd/LICENSE"
  - "bootstrap/bootstrap_templates.py"
  - "tests/test_bootstrap_skills_coverage.py"
  - "docs/en/skills.md"
  - "docs/ru/skills.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-09-11T13:13:44Z"
---

## Goal

Владелец просит: ответы короче, без пространных рассуждений. Источник правил — https://github.com/ayghri/i-have-adhd (SKILL.md), адаптация принципов The Adult ADHD Tool Kit под общение языковой модели.

ДЕСЯТЬ ПРАВИЛ: 1) веди с действия; 2) нумеруй многошаговое; 3) заканчивай одним конкретным шагом; 4) глуши отступления; 5) повторяй состояние каждый ход; 6) конкретные оценки времени в минутах, а не 'немного'; 7) делай выигрыши видимыми; 8) об ошибках буднично; 9) списки не длиннее 5 пунктов; 10) без преамбул, без пересказов, без закрывашек.

ЧТО ДЕЛАТЬ: вендорить SKILL.md в harness/skills/, подключить как правило для агента, назвать источник и лицензию. Проверить, не противоречит ли правилу проекта о полноте доказательств: краткость ОТВЕТА не есть краткость ЖУРНАЛА — доказательство закрытия остаётся полным.

ЭТО ДОРАБОТКА, НЕ БЛОКЕР 1.9.

## Acceptance Criteria

AC-1. SKILL.md вендорен с указанием источника и лицензии; правила не пересказаны по памяти.
AC-2. Правило подключено так, что его видит агент в любой среде, а не только в одной.
AC-3. Граница названа: краткость касается ОТВЕТА ВЛАДЕЛЬЦУ, а не журнала задачи, доказательства закрытия и docstring. Проверяется тестом или явной строкой в правиле.
AC-4. НЕГАТИВ: правило не должно сокращать то, что гейты требуют полным — проверяется тем, что закрытие с полным доказательством по-прежнему проходит.

## Plan

[{"step": "Inspect the upstream SKILL.md and license plus existing cross-host skill deployment surfaces.", "done": true}, {"step": "Vendor the source-attributed skill and connect it through the shared harness without altering evidence requirements.", "done": true}, {"step": "Add focused behavioral/documentation coverage proving every supported host sees it and that evidence remains full.", "done": true}, {"step": "Run focused tests, lint/type checks and a review; record evidence before signed verify.", "done": true}]

## Rollback

git revert of the dedicated skill adoption commit

## Journal

- 2026-09-11T13:06:02Z [implementation] — L3 review found four MEDIUM issues. Fixed: generated bootstrap inventory now names 14 always-on skills including /reason and /i-have-adhd, with /brain conditional as 15th; cross-host test now asserts deployed SKILL.md and MIT LICENSE in both Claude and Codex. Re-run: 165 focused tests PASS, ruff PASS. Remaining review item before closure: establish source-fidelity policy for condensed adaptation versus verbatim upstream skill; do not claim the shortened SKILL is a verbatim vendor copy.
- 2026-09-11T13:06:59Z [implementation] — Resolved L3 source-fidelity finding without a false verbatim claim: SKILL now identifies itself as an adapted derivative, cites upstream path/date/license, states omitted upstream rationale/examples, retained normative intent, and identifies the TAUSIK overlay. Focused suite re-run: 165 passed in 4.16s; skill_spec_conformance and git diff --check pass. Remaining before QG-2: captured real cross-host bootstrap result, final review gates, signed verify.
- 2026-09-11T13:11:37Z [implementation] — Final evidence: source verify #2408 is signed/presentable with declared scope complete, ruff=PASS and pytest=PASS in 35.5s. Review gate was re-run on all six changed carriers; no surviving process or diff-whitespace finding. L3 review #43 findings resolved: host template, cross-host MIT-copy assertion, count drift, and explicit adapted-derivative/source-fidelity record. AC-1 source+MIT; AC-2 shared bootstrap + Claude/Codex assertions; AC-3 TAUSIK boundary; AC-4 signed verify preserves full evidence.
