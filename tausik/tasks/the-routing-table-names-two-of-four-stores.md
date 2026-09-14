---
slug: the-routing-table-names-two-of-four-stores
title: "Таблица маршрутизации памяти называет два адреса из четырёх — и противоречит собственному выводу (GitLab #6)"
status: done
epic: release-110-deferred-from-19
story: deferred-110-knowledge-lifecycle
complexity: medium
role: tech-writer
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - README.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-09-14T15:20:58Z"
---

## Goal

ПРИШЛО ИЗ ТРЕКЕРА: GitLab #6, открыт 24 дня, НЕ исправлено. Проверено #189: bootstrap/bootstrap_templates.py:60 печатает `## Memory (two systems — use the right one)` и называет ДВА хранилища. Этот текст едет в CLAUDE.md, AGENTS.md, .cursorrules и QWEN.md КАЖДОГО потребительского проекта на всех хостах. ХРАНИЛИЩ ЧЕТЫРЕ: (1) проектная память .tausik/tausik.db; (2) общая база ~/.tausik-knowledge/knowledge.db — главная возможность 1.8; (3) авто-память агента; (4) brain — публикация наружу только явным согласием (#221). ПРОТИВОРЕЧИЕ ВНУТРИ ОДНОГО ВЫВОДА: `tausik memory block` ПЕЧАТАЕТ секцию «Shared knowledge — from other projects», а его же policy-заголовок в том же тексте утверждает, что систем две. ЗАМЕРЕННОЕ СЛЕДСТВИЕ: общая база не приняла НИ ОДНОЙ записи от этого проекта; её 14 памяток написаны тремя чужими проектами, 2498 решений приехали одним переносом 3 августа и с тех пор ни одной записи. Отсутствующий в таблице адрес не выбирается никогда. ПРАВИЛО ЗАДАНО РЕШЕНИЕМ #272 (владелец, 29.08) — МАРШРУТИЗАЦИЯ ПО ПРОИСХОЖДЕНИЮ И АВТОМАТИЧЕСКАЯ:   узнал из файлов ЭТОГО репозитория -> проектная память;   узнал из поведения инструмента или платформы (Windows, pytest, Ansible, git, модель) -> общая база;   узнал от пользователя (предпочтение, привычка) -> авто-память агента;   brain -> ТОЛЬКО явным действием, автоматика туда не ходит НИКОГДА (#221). ОБЯЗАТЕЛЬНОЕ УСЛОВИЕ АВТОМАТИКИ, БЕЗ КОТОРОГО ЗАДАЧУ НЕ ЗАКРЫВАТЬ: общая база объявлена не редактируемой — «secrets and PII are stored verbatim, readable from every project on this machine». Значит автоматическая запись туда обязана проходить через redact-проверку (команда есть с 1.9). Автоматика без редактирования превращает гочу, процитировавшую токен или внутренний хост, в утечку на всю машину. ЧТО ДЕЛАЕТСЯ: таблица маршрутизации называет четыре адреса и признак происхождения; правка едет ОДНИМ изменением в шаблон, в блок памяти и в docs обоих языков; согласованность числа адресов во всех местах проверяется тестом, а не глазами. НЕГАТИВНОЕ, ДВУСТОРОННЕЕ: (а) запись, чьё происхождение определить не удалось, идёт в ПРОЕКТНУЮ память и говорит об этом — умолчание обязано быть самым узким, а не самым широким; (б) попытка автоматики записать в общую базу текст, не прошедший redact, обязана ОТКАЗАТЬ громко, а не записать усечённое.

## Acceptance Criteria

AC-1: the shipped rules template names every memory destination with a criterion for each, and a test derives the row count from the code rather than restating it. AC-2: GitLab #6 is answered and closed (negative: a ticket left open after the fix ships is the defect this task was filed about).

## Plan

## Rollback

Правка шаблона, блока памяти и документации плюс тест на согласованность числа адресов. Откат — git revert; поведение хранилищ не меняется.

## Journal

- 2026-09-14T15:18:50Z [planning] — OBSOLETE, closed without work by the owner's decision (session #265): GitLab #6 fixed in 1.9 (claudemd-template-names-two-memory-stores-of-three) and closed by the owner. No criterion was exercised; the premise of the task no longer holds.
- 2026-09-14T15:20:57Z [planning] — Resolved by the 1.9 fix, closed without new work (owner, session #265). AC-1: ✓ tests/test_memory_template_names_three_stores.py (13 passed) — the table names project memory, the shared store and the host's auto-memory, each with its criterion; task claudemd-template-names-two-memory-stores-of-three shipped it in v1.9.0. AC-2: ✓ GitLab #6 answered (note_5848) and closed by the owner on 2026-09-14 (glab issue view 6 → closed).
