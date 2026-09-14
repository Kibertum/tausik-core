---
slug: pr5-was-promised-a-merge-and-planned-as-a-reimplementation
title: "Внешнему автору публично обещан МЕРЖ его коммитов, а запланирован ПЕРЕНОС чужими руками — обещанию 25 дней, PR открыт"
status: done
epic: release-110-deferred-from-19
story: deferred-110-outward-loop-and-test-authorship
complexity: complex
role: architect
stack: null
tier: moderate
call_budget: 50
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - README.md
scope_paths: []
scope_tools: []
depends_on:
  - github-is-primary-by-decision-and-gitlab-is-primary-in-practice
completed_at: "2026-09-14T15:21:04Z"
---

## Goal

РАСХОЖДЕНИЕ МЕЖДУ ПУБЛИЧНЫМ ОБЕЩАНИЕМ И СОБСТВЕННЫМ ПЛАНОМ, НАЙДЕНО ПРИ РАЗБОРЕ ТИКЕТОВ GITHUB В СЕССИИ #189.

ЧТО ОБЕЩАНО ПУБЛИЧНО. Комментарий владельца к github.com/Kibertum/tausik-core PR #5 от 2026-08-04, четыре пронумерованных пункта:
  1. открывается ветка release/1.9, «This PR is retargeted onto it and merged there — your commits, with your authorship, not a re-implementation»; maintainerCanModify включён, ребейз делаем мы, если автор не предпочтёт сам;
  2. устаревшие части (пин mcp, PowerShell и NotebookEdit в матчерах, правки README/бейджей) отпадают при ребейзе, остальное сохраняется;
  3. те же изменения портируются на рабочий remote, где гоняется полная лента и линуксовый пайплайн;
  4. tests/test_hook_tool_coverage.py приезжает КАК НАПИСАН.

ЧТО ЕСТЬ ПО ФАКТУ, ЗАМЕРЕНО СЕГОДНЯ (2026-08-29, то есть 25 дней спустя):
  PR #5 — OPEN, mergeable, один комментарий: то самое обещание. Ответа автору с тех пор не было.
  github/release/1.9 — ветка СУЩЕСТВУЕТ, но её голова 623fb4e относится к выпуску 1.8; коммитов PR #5 в ней нет.
  tests/test_hook_tool_coverage.py — в дереве ОТСУТСТВУЕТ (пункт 4 не выполнен).
  scripts/autoloop/ из состава PR — отсутствует.
  scripts/service_doctor_mcp.py — отсутствует.

ГЛАВНОЕ РАСХОЖДЕНИЕ, И ОНО НЕ В СРОКАХ. Наша собственная задача port-external-pr5-hook-coverage (статус planning) в AC4 планирует ровно то, что обещание ИСКЛЮЧАЕТ: «перенесено... автор PR #5 указан соавтором в коммите; PR закрыт ссылкой на перенос». Это и есть re-implementation с указанием соавтора — а автору обещали мерж ЕГО коммитов, «not a re-implementation». Два плана противоречат друг другу, и внешний участник видит только один из них — публичный.

СВЯЗЬ С РЕШЕНИЕМ О ВЫКЛАДКЕ. poryadok-vykladki-zerkala-popravlen-dlya-vypuskov-s требует: 1.9 ложится на main МЕРЖЕМ ветки release/1.9 либо squash-ом с Co-Authored-By автора; «молчаливый squash без атрибуции ЗАПРЕЩЁН». То есть механика выкладки уже рассчитывает на то, что коммиты автора окажутся в release/1.9. Если вместо мержа будет перенос, это решение тоже надо переписать, а не тихо исполнить иначе.

БЛОКИРУЮЩАЯ ЗАВИСИМОСТЬ: пункт 1 требует операций на GitHub, а место разработки сейчас является открытым вопросом — см. github-is-primary-by-decision-and-gitlab-is-primary-in-practice. Пока он не решён, ребейз PR на release/1.9 делать нельзя: непонятно, чем эта ветка станет.

ЧТО НАДО РЕШИТЬ (владельцу, не выбирать в одиночку): (А) исполнить обещание буквально — ребейз коммитов автора на release/1.9 и мерж, наш порт становится добавкой ПОВЕРХ, а не заменой; (Б) изменить обещание — но тогда написать автору РАНЬШЕ, чем сделать иначе, а не после; (В) гибрид: мерж того, что переживает ребейз, порт остального с Co-Authored-By. Ни один не выбран.

НЕЗАВИСИМО ОТ ВЫБОРА И БЕЗ ОЖИДАНИЯ: автору 25 дней никто ничего не написал. Это отдельная стоимость и она платится уже сейчас.

## Acceptance Criteria

AC-1: the author's finding ships on the development line with their Co-Authored-By. AC-2: the PR thread carries the answer (what was taken, what was not and why) and the PR is closed with the release link — not left open (negative: an open PR after the tag would break the public promise).

## Plan

## Rollback

Исход задачи — либо мерж коммитов автора, либо явное объяснение автору, почему перенос. Откат мержа — git revert коммитов с сохранением авторства (Co-Authored-By остаётся в истории). Откат объяснения не требуется: сказанное автору не отзывается, а дополняется.

## Journal

- 2026-09-14T15:18:49Z [planning] — OBSOLETE, closed without work by the owner's decision (session #265): PR #5 was ported with the author's Co-Authored-By (1a32c19d), answered in its thread and closed with the 1.9.0 release link. No criterion was exercised; the premise of the task no longer holds.
- 2026-09-14T15:20:56Z [planning] — Resolved by events, closed without new work (owner, session #265). AC-1: ✓ commit 1a32c19d 'fix(hooks): guards see every tool their action is reachable with — GitHub PR #5 ported, not merged', Co-Authored-By the author, in tag v1.9.0. AC-2: ✓ PR #5 answered (issuecomment-5657649753: what landed, what was not taken and why) and closed with the v1.9.0 release link (issuecomment-5658194173); gh pr view 5 → CLOSED. Negative held: the PR did not outlive the tag.
