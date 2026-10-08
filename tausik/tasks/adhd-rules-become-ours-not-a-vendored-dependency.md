---
slug: adhd-rules-become-ours-not-a-vendored-dependency
title: "Чужой навык i-have-adhd вендорен вместо того, чтобы стать нашей дисциплиной ответа"
status: done
epic: release-110-deferred-from-19
story: release110-owner-priorities
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "bootstrap/bootstrap_templates.py"
  - README.md
  - README.ru.md
  - QWEN.md
  - "docs/_generated/constants.json"
  - "tests/test_answer_shape_discipline.py"
  - "changelog.d/adhd-rules-become-ours-not-a-vendored-dependency.md"
scope_paths:
  - "bootstrap/"
  - "harness/"
  - "docs/"
  - "scripts/"
  - "tests/"
  - "changelog.d/"
  - ".claude/"
  - README.md
  - README.ru.md
  - QWEN.md
scope_tools: []
depends_on: []
completed_at: "2026-09-29T22:01:46Z"
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

Указание владельца, смена #278: «я не просил тебя его целиком затаскивать, а просил ВНЕДРИТЬ К НАМ, чтобы не тащить чужую зависимость». Сейчас harness/skills/i-have-adhd/ — вендоренная копия чужого SKILL.md под MIT с LICENSE, которая к тому же ОПЦИЯ: вызывается слэш-командой, а в CLAUDE.md слово adhd встречается ноль раз. То есть мы несём чужую зависимость И не получаем от неё дисциплины. Цель: принципы становятся НАШЕЙ дисциплиной ответа в всегда-поставляемом блоке, нашими словами; вендоренный каталог с LICENSE уходит; происхождение идеи записано решением, а не файлом в дереве.

## Acceptance Criteria

AC-1 Правила, которых не было в ANSWER_SHAPE, добавлены НАШИМИ словами: нумерация многошагового, потолок пунктов в группе, подавление побочных веток, оценка в минутах. ✓ tests/test_answer_shape_discipline.py
AC-2 Каталог harness/skills/i-have-adhd/ с LICENSE удалён; в дереве не остаётся вендоренной копии и упоминаний навыка как живого.
AC-3 Происхождение идеи записано решением со ссылкой на источник — мы не приписываем себе чужую мысль, но и не тащим её файлом.
AC-4 НЕГАТИВНЫЙ: рост всегда-поставляемого блока ОПЛАЧЕН замером — сказано, сколько токенов кэша он добавляет на вызов и почему это дешевле того, что экономит. Без числа рост запрещён.
AC-5 НЕГАТИВНЫЙ: граница доказательства сохранена дословно — блок по-прежнему запрещает сокращать код, вывод инструментов, доказательство критериев, журналы и решения.
AC-6 Тесты, знавшие про навык (test_bootstrap_skills_coverage, счётчики навыков, страницы docs), обновлены, а не обойдены.
AC-7 Полная лента зелёная.

## Plan

## Rollback

git revert; вендоренный навык возвращается из истории

## Journal

- 2026-09-29T20:27:03Z [implementation] — Работа готова и проверена, задача НЕ закрыта намеренно. Гейт pytest краснеет на tests/test_answer_budget_ratchet: p90 моих ответов 1410 против базы 923. Это не дефект задачи — это храповик, сработавший на авторе, и обходить его при закрытии задачи ПРО ДИСЦИПЛИНУ ОТВЕТА было бы прямым опровержением её предмета. Мера читает последние 10 транскриптов; длинные ответы уйдут из окна только со сменой сессии. Закрывать в следующей смене, когда мера зелена, — ровно как записано в AC-4 задачи answer-budget-counts-evidence-against-its-own-rule.
- 2026-09-29T20:50:46Z [implementation] — Full lane showed 9 more reds from 214cb678 (my #278 claim 'only answer_shape red' was wrong). Fix: ANSWER_SHAPE rewritten 1223->779 chars, 13->8 lines, all pinned terms + #407 rules kept, 'Never' gone; cap 779; constants regenerated (skills_core_count 13); README/README.ru IDE tables 14->13 core.
- 2026-09-29T21:07:25Z [implementation] — State: 9 reds from 214cb678 fixed, 292 passed on affected files. Remaining red: test_answer_budget_ratchet p90 1410 > 923. Not closing past it.
- 2026-09-29T21:43:15Z [implementation] — Ratchet unblocked: the measure read the OLDEST ten transcripts (fixed in answer-measure-reads-the-oldest-transcripts); newest ten p90 453 = re-measured baseline. Evidence for the 9 reds from 214cb678: tests/test_response_contract_shape.py, tests/test_instruction_tone.py, tests/test_bootstrap_generate.py, tests/test_gen_doc_constants.py, tests/test_doc_table_count_subjects.py — 292 passed.
- 2026-09-29T21:59:36Z [implementation] — AC-1: ✓ tests/test_answer_shape_discipline.py::test_the_shipped_block_carries_the_rule (6 rules). AC-2: ✓ tests/test_answer_shape_discipline.py::test_no_vendored_copy_came_back; QWEN.md regenerated, no /i-have-adhd left outside history. AC-3: ✓ decision #407 names ayghri/i-have-adhd (MIT). AC-4 Negative: ✓ growth paid: block 1223 -> 776 chars, file budgets held (tests/test_bootstrap_generate.py::TestGenerateClaudeMd::test_line_count_in_range). AC-5 Negative: ✓ tests/test_bootstrap_skills_coverage.py (KEEP BYTE-EXACT / KEEP FULL PROSE / acceptance-criteria evidence). AC-6: ✓ tests/test_response_contract_shape.py, tests/test_gen_doc_constants.py::test_constants_json_file_matches_live. AC-7: ✓ full lane 12573 passed (1 CLAUDE.md pin fixed after, 20 passed), slow lane 143 passed.
- 2026-09-29T22:00:02Z [implementation] — NO-DEAD-END: red verify runs were the answer ratchet on a mis-sliced window (fixed in its own task) and bootstrap_drift after editing scripts/ (redeployed).
