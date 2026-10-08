---
slug: answer-budget-counts-evidence-against-its-own-rule
title: "Бюджет ответа считает доказательство, хотя конвенция ставит его на пересказ"
status: done
epic: release-110-deferred-from-19
story: release110-owner-priorities
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/answer_shape.py"
  - "tausik/gates.json"
  - "tests/test_answer_evidence_split.py"
  - "changelog.d/answer-budget-counts-evidence-against-its-own-rule.md"
scope_paths:
  - "scripts/answer_shape.py"
  - "scripts/answer_budget_ratchet.py"
  - "tests/"
  - "tausik/gates.json"
scope_tools: []
depends_on: []
completed_at: "2026-09-29T22:11:24Z"
resolution: null
resolution_reason: null
tracker_refs: []
started_model_id: claude-opus-5
started_model_version: null
done_model_id: claude-opus-5
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

Конвенция #768: бюджет ставится на ПЕРЕСКАЗ, не на доказательство — иначе он давит на дорогое. Измеритель answer_shape.final_words считает КАЖДОЕ слово итогового ответа, включая таблицы замеров и цитаты квитанций. То есть правило объявлено, а мера его не исполняет. ЗАВЕДЕНО, НО НЕ СДЕЛАНО СЕЙЧАС НАМЕРЕННО: автор в этот момент сам выше порога (p90 1325 против 923), и правка меры под собой неотличима от побега от храповика. Делать, когда мера зелена.

## Acceptance Criteria

AC-1 Измеритель отделяет пересказ от доказательства по объявленному признаку, и признак назван в коде, а не угадывается.
AC-2 База пересчитана на НОВОЙ мере и объявлена заново — старое число к новой мере не относится.
AC-3 НЕГАТИВНЫЙ: ответ без доказательства считается целиком, иначе всякий длинный ответ объявит себя доказательством.
AC-4 НЕГАТИВНЫЙ: правка НЕ делается, пока автор выше действующего порога; задача отказывается стартовать с красным answer_shape.
AC-5 Полная лента зелёная.

## Plan

## Rollback

git revert; мера считает все слова, как сейчас

## Journal

- 2026-09-29T22:10:32Z [implementation] — AC-1: ✓ declared mark in code: scripts/answer_shape.py _FENCE/_TABLE_ROW + evidence_words(); tests/test_answer_evidence_split.py::test_fenced_output_and_table_rows_are_evidence_not_retelling. AC-2: ✓ baseline declared anew on the new measure: median 162.0, p90 365 (same newest-10 window), tausik/gates.json answer_shape with provenance. AC-3 Negative: ✓ tests/test_answer_evidence_split.py::test_an_answer_with_no_evidence_is_counted_whole and ::test_an_unclosed_fence_does_not_exempt_the_rest. AC-4 Negative: ✓ started only with the measure green (p90 453 = baseline 453 before the change). AC-5: ✓ full lane 12579 passed; the 1 red (comment history refs 235>234, from comments added this session) fixed, tests/test_comment_history_refs.py 80 passed.
