---
slug: adhd-rules-become-ours-not-a-vendored-dependency
title: "Чужой навык i-have-adhd вендорен вместо того, чтобы стать нашей дисциплиной ответа"
status: active
epic: release-110-deferred-from-19
story: deferred-110-audit-hygiene
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
  - "tests/test_response_contract_shape.py"
  - "tests/test_bootstrap_skills_coverage.py"
  - "scripts/answer_shape.py"
  - "scripts/response_contract_audit.py"
  - "docs/ru/skills.md"
  - "docs/en/skills.md"
  - "docs/ru/quickstart.md"
  - "docs/en/quickstart.md"
  - "changelog.d/adhd-rules-become-ours-not-a-vendored-dependency.md"
scope_paths:
  - "bootstrap/"
  - "harness/"
  - "docs/"
  - "scripts/"
  - "tests/"
  - "changelog.d/"
  - ".claude/"
scope_tools: []
depends_on: []
completed_at: null
resolution: null
resolution_reason: null
tracker_refs: []
started_model_id: claude-opus-5
started_model_version: null
done_model_id: null
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
