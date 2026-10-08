---
slug: severity-scale-is-documented-and-used-by-review
title: "Шкала severity документирована: что покрывают CRITICAL/HIGH/MEDIUM у нас, кто присваивает, CRITICAL — с причиной (SENAR 1.5 §10.15(f))"
status: done
epic: release-110-deferred-from-19
story: release110-senar-15-claimed-honestly
complexity: simple
role: docs
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "docs/en/severity-scale.md"
  - "docs/ru/severity-scale.md"
  - "harness/skills/review/SKILL.md"
  - "harness/claude/subagents/tausik-reviewer.md"
  - "harness/claude/subagents/tausik-external-reviewer.md"
  - "scripts/project_cli_review.py"
  - "scripts/risk_l3_trigger.py"
  - "tests/test_severity_scale.py"
scope_paths:
  - "docs/ru/*.md"
  - "docs/en/*.md"
  - "docs/README.md"
  - "harness/skills/review/SKILL.md"
  - "harness/claude/subagents/*.md"
  - "scripts/project_cli_review.py"
  - "scripts/risk_l3_trigger.py"
  - "scripts/project_parser*.py"
  - "tests/*.py"
  - "CHANGELOG*.md"
scope_tools: []
depends_on: []
completed_at: "2026-09-23T19:03:46Z"
resolution: null
resolution_reason: null
tracker_refs:
  - "github#180"
started_model_id: claude-opus-5-5
started_model_version: null
done_model_id: null
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

SENAR 1.5 §10.15(f): шкала severity ДОЛЖНА быть документирована — иначе блок коммита по (d) и числитель ADR неразрешимы; присвоение CRITICAL записывается с причиной. /review, tausik-reviewer и tausik-external-reviewer выдают critical/high/medium/low по собственному разумению, документа шкалы нет, review record причину CRITICAL не требует. Цель: одна страница шкалы в docs, скиллы и агенты ревью ссылаются на неё, review record хранит причину для CRITICAL.

## Acceptance Criteria

1. docs/ru+en/severity-scale.md: определения CRITICAL/HIGH/MEDIUM/LOW в контексте проекта, кто присваивает (агент ревью — предварительно, владелец/супервайзер — окончательно), отличие от уровня риска изменения (8.7) и тира чеклиста — как требует 1.5.
2. Скилл review и оба reviewer-агента цитируют страницу (тест на ссылку в тексте скилла и агентов).
3. НЕГАТИВНЫЙ: tausik review record --critical N (N>0) отказывает, если причина CRITICAL не передана через --reason; с причиной — она пишется в запись и видна в review list.
4. CHANGELOG EN+RU.

## Plan

## Rollback

git revert.

## Journal

- 2026-09-23T18:39:17Z [implementation] — Сделано: docs/en|ru/severity-scale.md (4 уровня, три шкалы SENAR разведены, кто предлагает/решает, §10.15(a) для L3), индекс docs/README.md; review record --reason, отказ при --critical>0 без причины (ничего не пишется), причина в notes с префиксом 'CRITICAL reason: ' и строкой в review list; скилл review, tausik-reviewer, tausik-external-reviewer и подсказка risk_l3_trigger ссылаются на шкалу/--reason; cli.md en/ru. tests/test_severity_scale.py 9 зелёных, 60 тестов ревью зелёные.
- 2026-09-23T19:03:42Z [implementation] — AC verified: 1. ✓ docs/en|ru/severity-scale.md; test_the_page_defines_the_levels_and_says_which_scale_it_is 2. ✓ test_the_review_skill_and_both_reviewers_cite_the_page 3. ✓ НЕГАТИВНЫЙ test_critical_without_a_reason_is_refused_and_nothing_is_written; test_critical_with_a_reason_is_recorded_and_listed; test_zero_critical_needs_no_reason 4. ✓ CHANGELOG EN+RU. Verify #2742 зелёный.
