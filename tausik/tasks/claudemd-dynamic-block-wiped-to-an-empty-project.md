---
slug: claudemd-dynamic-block-wiped-to-an-empty-project
title: "Динамический блок CLAUDE.md и AGENTS.md затирается состоянием ПУСТОГО проекта — и ни один гейт этого не видит"
status: planning
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 60
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

ЗАМЕР #190, ПРЯМОЙ. В ходе сессии #190 блок между DYNAMIC:START и DYNAMIC:END в CLAUDE.md и AGENTS.md был перезаписан на «Session: none | Branch: v1-9-wave | Version: 1.8.0 / Tasks: 0/1 done, 0 active, 0 blocked». Снесено 42 строки в каждом файле: весь хвост памяти (5 context, 5 decisions, 5 conventions, 3 dead ends) и весь блок общего знания из других проектов (11 записей).

ДАННЫЕ ЦЕЛЫ, СЛОМАНА ГЕНЕРАЦИЯ. Проверено сразу: .tausik/tausik status в тот же момент отдавал «1235/1446 done, Session: #190 (active 46m)». То есть «0/1 done» и «Session: none» — не состояние проекта, а состояние ПУСТОЙ или изолированной базы, записанное в РЕАЛЬНЫЕ файлы репозитория.

ВРЕМЯ УСТАНОВЛЕНО, ВИНОВНИК — НЕТ. mtime обоих файлов 2026-08-30 19:33:00.578952900 — секунда в секунду одна и та же, то есть один вызов писал оба (resolve_sibling_targets). Это РАНЬШЕ первой моей правки кода (19:46:47) и раньше первого прогона тестов, то есть тесты исключены: в тот момент работали только старт сессии, task show/update/start и чтения. Кандидаты на осмотр: scripts/claudemd_writer.py, scripts/project_cli_extra.py, scripts/doc_drift_common.py, scripts/service_doctor_drift.py и путь MCP-сервера tausik-project. Тест tests/test_update_claudemd_agents.py осмотрен и чист — он изолирован через tmp_path целиком.

ЧТО ДЕЛАЕТСЯ: воспроизвести запись пустого состояния, найти вызов, который берёт путь к CLAUDE.md репозитория, но данные из другой (пустой) базы, и закрыть его. НЕГАТИВНОЕ: запись блока при нулевом числе задач обязана быть ОТКАЗОМ, а не записью. Пустая база — это признак того, что писатель смотрит не туда, и молча соглашаться с ней нельзя: цена ошибки — потеря всего контекста, который следующий агент читает первым.

СМЕЖНОЕ И ХУДШЕЕ: claudemd-drift-gates-do-not-notice-an-emptied-dynamic-block. Порча пережила ТРИ полных зелёных прогона подряд.

## Acceptance Criteria

## Plan

## Rollback

## Journal
