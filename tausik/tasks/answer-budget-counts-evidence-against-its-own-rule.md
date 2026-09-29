---
slug: answer-budget-counts-evidence-against-its-own-rule
title: "Бюджет ответа считает доказательство, хотя конвенция ставит его на пересказ"
status: planning
epic: release-110-deferred-from-19
story: deferred-110-audit-hygiene
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths:
  - "scripts/answer_shape.py"
  - "scripts/answer_budget_ratchet.py"
  - "tests/"
  - "tausik/gates.json"
scope_tools: []
depends_on: []
completed_at: null
resolution: null
resolution_reason: null
tracker_refs: []
started_model_id: null
started_model_version: null
done_model_id: null
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
