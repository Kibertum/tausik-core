---
slug: l3-dispatch-does-not-carry-the-author-model
title: "Диспетчер внешнего L3 не передаёт модель автора: разделение обязанностей держится на внимательности рецензента"
status: done
epic: release-110-deferred-from-19
story: release110-open-defects
complexity: medium
role: architect
stack: python
tier: moderate
call_budget: 60
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/review_separation.py"
  - "scripts/project_cli_review.py"
  - "scripts/project_parser_ops.py"
  - "scripts/project_parser_review.py"
  - "scripts/external_reviewer.py"
  - "harness/claude/subagents/tausik-external-reviewer.md"
  - "harness/skills/review/SKILL.md"
  - "tests/test_review_separation.py"
  - "tests/test_severity_scale.py"
scope_paths:
  - "scripts/project_cli_review.py"
  - "scripts/project_parser_ops.py"
  - "scripts/project_parser_review.py"
  - "scripts/external_reviewer.py"
  - "scripts/review_separation.py"
  - "harness/claude/subagents/*.md"
  - "harness/skills/review/SKILL.md"
  - "tests/*.py"
  - "docs/ru/*.md"
  - "docs/en/*.md"
  - "CHANGELOG*.md"
scope_tools: []
depends_on: []
completed_at: "2026-09-24T08:35:32Z"
resolution: null
resolution_reason: null
tracker_refs:
  - "github#157"
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

НАЙДЕНО САМИМ ВНЕШНИМ РЕЦЕНЗЕНТОМ в #213 (он отказался ревьюить и объяснил почему). Приглашение на L3 не несёт идентификатор модели АВТОРА. Рецензенту пришлось восстанавливать её самому: по трейлеру Co-Authored-By в коммите и по .tausik/token_metrics.jsonl (session 213, model=claude-opus-5 за минуту до коммита). Он совпал с автором и ОТКАЗАЛСЯ — правильно, SENAR Rule 4. Но рецензент, который такую проверку НЕ сделает, молча заверит собственную работу, и запись review record --type L3 закроет гейт закрытия задачи, не проведя ни одного адверсариального прохода. Это ровно тот класс, который весь релиз 1.9 вычищает: контроль, который не умеет отказать.

ЗАМЕР ДО ПРАВКИ: пройти по всем путям, откуда запускается внешнее ревью (harness/claude/subagents/tausik-external-reviewer, скилл review, любые обёртки), и предъявить, какие поля приглашение несёт сегодня и откуда рецензент берёт модель автора. Отдельно: несёт ли `tausik review record` поле модели рецензента и модели автора, или только свободные notes (сегодня — только notes).

ФОРМА ПОЧИНКИ — ВЫБОР, ПРЕДЪЯВИТЬ ЦИФРАМИ: (а) диспетчер подставляет модель автора в приглашение (дёшево, но держится на том, что подставили верно); (б) `review record` получает поля author_model/reviewer_model и ОТКАЗЫВАЕТ при совпадении (машинная проверка на записи, работает независимо от текста приглашения); (в) обе. Вариант (б) делает предмет проверяемым и даёт красную ветвь; вариант (а) без (б) остаётся объявлением.

ВНЕ ОБЪЁМА 1.9 (решение #310): машинерия ревью фреймворка, не норма RENAR.

## Acceptance Criteria

1. Замер до правки записан в лог: пути запуска внешнего ревью, поля приглашения, поля review record.
2. review record --type L3 требует --reviewer-model; модель автора берётся из --author-model, иначе из живого транскрипта автора; обе пишутся в notes (author_model=, reviewer_model=).
3. НЕГАТИВНЫЙ: L3 с reviewer того же семейства, что автор, ОТКАЗАН с кодом выхода 1 и строкой SENAR Rule 4; строка в reviews не появляется.
4. НЕГАТИВНЫЙ: L3 без --reviewer-model или при неизвестной модели автора ОТКАЗАН (fail-closed), текст называет, какой флаг дать.
5. Приглашение (подсказка делегирования L3 и субагент tausik-external-reviewer) несёт точный id модели автора и команду записи с --author-model/--reviewer-model.
6. L1/L2 не затронуты: запись без моделей проходит как раньше.

## Plan

## Rollback

git revert коммита; review record возвращается к записи без моделей

## Journal

- 2026-09-24T08:30:17Z [planning] — AC-1 measurement before: dispatch paths = risk_l3_trigger._delegation_hint (reviewer_hint names the author FAMILY only, 'Opus'), harness/claude/subagents/tausik-external-reviewer.md ('the invoking context will tell you the author model' - nothing supplies it). No review skill dispatches. review record (CLI only, no MCP tool) carries --task --type --critical --warnings --notes --reason: no model fields, no separation check; reviewer model only as free text in notes.
- 2026-09-24T08:30:24Z [implementation] — AC-1 measurement before: dispatch paths = risk_l3_trigger._delegation_hint (reviewer_hint names the author FAMILY only, 'Opus'), harness/claude/subagents/tausik-external-reviewer.md ('the invoking context will tell you the author model' - nothing supplies it). No review skill dispatches. review record (CLI only, no MCP tool) carries --task --type --critical --warnings --notes --reason: no model fields, no separation check; reviewer model only as free text in notes.
- 2026-09-24T08:33:06Z [implementation] — Also found: /review skill records L3 itself (harness/skills/review/SKILL.md step 7) - now passes both models and records L2 when agents inherited the author's model.
- 2026-09-24T08:33:06Z [implementation] — Mutation: same-family check disabled -> tests/test_review_separation.py::test_an_l3_without_shown_separation_is_refused_and_not_written[same-family] red; restored.
- 2026-09-24T08:33:06Z [implementation] — Root cause: separation of duties was enforced only when choosing the reviewer model (external_reviewer.recommend_reviewer_model); the record that satisfies the L3 gate accepted any reviewer, and the invitation carried the author's family, not its id.
- 2026-09-24T08:33:07Z [implementation] — AC-1: ✓ measurement logged above (3 dispatch paths incl. /review skill; record had notes only)
- 2026-09-24T08:33:07Z [implementation] — AC-2: ✓ tests/test_review_separation.py::test_an_l3_on_a_different_family_is_recorded_with_both_models
- 2026-09-24T08:33:07Z [implementation] — AC-3: ✓ tests/test_review_separation.py::test_an_l3_without_shown_separation_is_refused_and_not_written[same-family]
- 2026-09-24T08:33:07Z [implementation] — AC-4: ✓ tests/test_review_separation.py::test_an_l3_without_shown_separation_is_refused_and_not_written[no-reviewer], [unknown-author], [unknown-reviewer]
- 2026-09-24T08:33:08Z [implementation] — AC-5: ✓ tests/test_review_separation.py::test_the_invitation_carries_the_author_id_and_the_record_flags; subagent prompt and /review skill updated
- 2026-09-24T08:33:08Z [implementation] — AC-6: ✓ tests/test_review_separation.py::test_l1_and_l2_need_no_models; tests/test_severity_scale.py green
- 2026-09-24T08:34:35Z [implementation] — Filesize: project_parser_ops.py reached 510 -> add_review moved to scripts/project_parser_review.py (469/51).
- 2026-09-24T08:35:29Z [implementation] — NO-DEAD-END: the red verify runs were the filesize gate (project_parser_ops.py 510 > 500) and the intentional mutation; fixed by moving add_review to its own module, no approach abandoned.
