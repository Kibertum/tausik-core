---
slug: commit-per-closed-task
title: "Коммит на закрытие задачи: state_roundtrip запрещает частичный коммит и делает работу пакетной"
status: planning
epic: release-110-deferred-from-19
story: deferred-110-audit-hygiene
complexity: complex
role: architect
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
resolution: null
resolution_reason: null
tracker_refs:
  - "github#147"
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

МЕХАНИКА, ДЕЛАЮЩАЯ РАБОТУ ПАКЕТНОЙ (замер #189, живой случай): гейт state_roundtrip отказывается принимать ЧАСТИЧНЫЙ коммит производного дерева tausik/ — «State not staged: tausik/ matches the DB, but 15 change(s) are unstaged». Поэтому сессия физически не может уехать двумя коммитами, и работа накапливается до конца дня. В #188 это уже привело к тому, что задуманные два коммита стали одним (память #428).
ПОЧЕМУ ЭТО ГЛАВНЫЙ ВИНОВНИК: у LangGraph чекпойнт пишется на КАЖДОМ шаге, и именно это делает возможным возобновление после прерывания, таймаута или перезапуска. У нас сброс в БД непрерывен, а сброс в git — раз в день, и разрыв между ними и есть та единица, которую владелец называет сессией.
ЧТО ДЕЛАЕТСЯ: постановка производного дерева ПО СУЩНОСТЯМ — закрытие задачи собирает свои файлы (задача, её память, её решения) и коммитится отдельно, а гейт проверяет согласованность СОБРАННОГО подмножества с БД, а не всего дерева.
НЕГАТИВНОЕ, И ОНО ГЛАВНОЕ: гейт заведён против расхождения экспорта с БД. Ослабление обязано ловить ровно тот случай, ради которого он стоит, — файл, изменённый мимо БД, обязан по-прежнему блокировать. Доказывать ДВУСТОРОННЕ: (а) частичный коммит согласованного подмножества проходит; (б) правка файла руками мимо БД блокирует по-прежнему.

## Acceptance Criteria

## Plan

## Rollback

Правка гейта state_roundtrip плюс режим постановки. Откат — git revert; гейт возвращается к проверке всего дерева, что строго строже.

## Journal
