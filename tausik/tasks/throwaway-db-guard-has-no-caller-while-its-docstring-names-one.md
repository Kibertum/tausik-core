---
slug: throwaway-db-guard-has-no-caller-while-its-docstring-names-one
title: "Гард принадлежности БД мёртв: у is_working_project_db нет ни одного вызова, а докстринг называет его защитой единственного внешнего пути"
status: planning
epic: landscape-2026-h2
story: l26-narrative
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

НАЙДЕНО в сессии #163 при проверке находки 1 задачи docs-drift-after-s152-batch. Подтверждено grep'ом по всему репозиторию.

ЗАМЕР: scripts/service_decide.py:166 определяет is_working_project_db — fail-closed проверку 'привязан ли этот сервис к настоящей БД проекта'. Единственные ссылки на неё во всём репозитории: её собственное определение, строка __all__ и ТЕСТЫ (tests/test_decide_classifies_what_it_publishes.py). ПРОИЗВОДСТВЕННЫХ ВЫЗОВОВ НЕТ НИ ОДНОГО.

НАРРАТИВ ПРОТИВ КОДА: докстринг модуля, строка 24, утверждает прямо противоположное — 'WHERE THE THROWAWAY GUARD WENT. is_working_project_db still lives here ... but its caller is now brain_move, which owns the only outward path'. Прочитано как описание защиты. scripts/brain_move.py::move_to_brain его не вызывает: проверяются вид записи, существование строки и совпадение типа, но не принадлежность БД.

ПОЧЕМУ ЭТО НЕ ПРИДИРКА И НЕ ЧИСТО ДОКУМЕНТАЦИЯ. Гард существовал, чтобы сервис, привязанный к временной или чужой БД, не публиковал наружу. move_to_brain — единственный путь, по которому запись покидает машину, и он берёт source_id как число: указатель на строку в ТОЙ базе, к которой сервис привязан. Из временной БД номер означает другую запись. Fail-closed проверка была ровно про это, и её нет.

ДВА ИСХОДА, решить ЯВНО: (а) подключить гард к move_to_brain — тогда докстринг станет правдой, а внешний путь получит защиту, которая для него и писалась; (б) признать гард лишним, УДАЛИТЬ его вместе с тестами и переписать докстринг. Молча оставить нельзя: сейчас код и текст утверждают разное, а тесты закрепляют функцию, которую никто не зовёт, — то есть покрытие есть, а защиты нет.

## Acceptance Criteria

## Plan

## Rollback

git revert. Если решением будет ПОДКЛЮЧИТЬ гард к move_to_brain — откат вернёт незащищённый внешний путь; если решением будет УДАЛИТЬ гард — откат вернёт мёртвый код. В обоих случаях безопасно.

## Journal
