---
slug: throwaway-db-guard-has-no-caller-while-its-docstring-names-one
title: "Гард принадлежности БД мёртв: у is_working_project_db нет ни одного вызова, а докстринг называет его защитой единственного внешнего пути"
status: done
epic: release-110-deferred-from-19
story: release110-site-docs-and-hygiene
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/brain_move.py"
  - "tests/test_decide_classifies_what_it_publishes.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-09-23T23:08:32Z"
resolution: null
resolution_reason: null
---

## Goal

НАЙДЕНО в сессии #163 при проверке находки 1 задачи docs-drift-after-s152-batch. Подтверждено grep'ом по всему репозиторию.

ЗАМЕР: scripts/service_decide.py:166 определяет is_working_project_db — fail-closed проверку 'привязан ли этот сервис к настоящей БД проекта'. Единственные ссылки на неё во всём репозитории: её собственное определение, строка __all__ и ТЕСТЫ (tests/test_decide_classifies_what_it_publishes.py). ПРОИЗВОДСТВЕННЫХ ВЫЗОВОВ НЕТ НИ ОДНОГО.

НАРРАТИВ ПРОТИВ КОДА: докстринг модуля, строка 24, утверждает прямо противоположное — 'WHERE THE THROWAWAY GUARD WENT. is_working_project_db still lives here ... but its caller is now brain_move, which owns the only outward path'. Прочитано как описание защиты. scripts/brain_move.py::move_to_brain его не вызывает: проверяются вид записи, существование строки и совпадение типа, но не принадлежность БД.

ПОЧЕМУ ЭТО НЕ ПРИДИРКА И НЕ ЧИСТО ДОКУМЕНТАЦИЯ. Гард существовал, чтобы сервис, привязанный к временной или чужой БД, не публиковал наружу. move_to_brain — единственный путь, по которому запись покидает машину, и он берёт source_id как число: указатель на строку в ТОЙ базе, к которой сервис привязан. Из временной БД номер означает другую запись. Fail-closed проверка была ровно про это, и её нет.

ДВА ИСХОДА, решить ЯВНО: (а) подключить гард к move_to_brain — тогда докстринг станет правдой, а внешний путь получит защиту, которая для него и писалась; (б) признать гард лишним, УДАЛИТЬ его вместе с тестами и переписать докстринг. Молча оставить нельзя: сейчас код и текст утверждают разное, а тесты закрепляют функцию, которую никто не зовёт, — то есть покрытие есть, а защиты нет.

## Acceptance Criteria

1. It is established from the repository, not from memory, whether is_working_project_db, its tests and the docstring claim about brain_move still exist. 2. If they are gone, the commit that removed them is named and the task closes with no file change. 3. NEGATIVE: no production code path that publishes outward is left without the protection the task was about — the one remaining outward path (knowledge export) is named with its current guard.

## Plan

## Rollback

git revert. Если решением будет ПОДКЛЮЧИТЬ гард к move_to_brain — откат вернёт незащищённый внешний путь; если решением будет УДАЛИТЬ гард — откат вернёт мёртвый код. В обоих случаях безопасно.

## Journal

- 2026-09-23T23:08:30Z [planning] — AC-1: ✓ measurement — grep over scripts/ tests/ harness/: zero references to is_working_project_db; the 'THROWAWAY GUARD' docstring passage is gone from scripts/service_decide.py; scripts/brain_move.py and tests/test_decide_classifies_what_it_publishes.py no longer exist.
- 2026-09-23T23:08:31Z [planning] — AC-2: ✓ measurement — git log -S is_working_project_db: removed by 77703c4a 'feat(knowledge)!: remove the Notion transport' together with brain_move.py (move_to_brain was the outward path the guard was written for). Outcome (b) of the task happened by that commit; nothing left to change.
- 2026-09-23T23:08:31Z [planning] — AC-3: ✓ measurement — negative: the only path by which shared-store content still leaves the machine is tausik knowledge export; commit 0dbfb49e put it behind scripts/publication_boundary.py (assert_local_destination + redact), and tests/test_publication_boundary.py walks scripts/ and harness/ for any module that reads the store and writes out without the boundary.
- 2026-09-23T23:09:14Z [done] — CORRECTION: this task was closed from PLANNING — task start refused (no scope), and task done accepted it anyway. The close itself is sound (evidence above, nothing to change), but it went around QG-0. The path is filed as task-done-closes-a-task-that-never-started.
- 2026-09-26T18:41:41Z [done] — EVIDENCE-RETIRED: tests/test_decide_classifies_what_it_publishes.py — file deleted by 77703c4a (feat(knowledge)!: remove the Notion transport)
