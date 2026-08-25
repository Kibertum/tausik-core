---
slug: r18-en-sessions-missing-from-generated-bundles
title: "docs/en/sessions.md не попал в сгенерированные бандлы оснастки — новый документ 1.8 отсутствует у всех IDE"
status: done
epic: landscape-2026-h2
story: l26-narrative
complexity: simple
role: developer
stack: null
tier: light
call_budget: 20
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "bootstrap/bootstrap.py"
scope_paths:
  - ".claude/*"
  - ".cursor/*"
  - ".kilo/*"
  - ".opencode/*"
  - ".qwen/*"
  - "bootstrap/*"
scope_tools: []
depends_on: []
completed_at: "2026-08-03T14:44:12Z"
---

## Goal

Найдено ревью партии. docs/ru/sessions.md есть в бандлах .claude/, .cursor/, .kilo/, .opencode/, .qwen/, а docs/en/sessions.md — нет: файл создан в сессии #161, позже последней синхронизации. Выпуск в таком виде оставит англоязычный документ 1.8 вне каждой оснастки, при том что whats-new-1.8.md на него ссылается.

## Acceptance Criteria

AC1: docs/en/sessions.md присутствует во ВСЕХ пяти бандлах (.claude, .cursor, .kilo, .opencode, .qwen) наравне с ru-версией.
AC2: tausik doctor не выдаёт предупреждение bootstrap drift.
AC3 (негативный): файл не докладывается в бандлы вручную — это скрыло бы причину. Если после штатной регенерации он там не появился, задача НЕ закрывается, а превращается в дефект генератора с указанием, почему en-документ не подхватывается.

## Plan

## Rollback

Регенерация бандлов; git revert одного коммита.

## Journal

- 2026-08-03T14:43:42Z [implementation] — ВЕРИФИКАЦИЯ: AC-1: ✓ find по пяти бандлам -> .claude/docs/en/sessions.md, .cursor/docs/en/sessions.md, .kilo/docs/en/sessions.md, .opencode/docs/en/sessions.md, .qwen/docs/en/sessions.md, каждый рядом со своим docs/ru/sessions.md. Было: только ru во всех пяти. AC-2: ✓ tausik doctor -> 'OK Bootstrap drift: none — deployed scripts match source'. Было: WARN про 10 разошедшихся файлов. AC-3 (негативный): ✓ соблюдён. Файл НЕ копировался руками — выполнена штатная регенерация python bootstrap/bootstrap.py --ide all, и документ подхватился сам. Значит генератор исправен, а расхождение было лишь возрастом бандлов: docs/en/sessions.md создан позже последней синхронизации. Дефекта генератора нет, и выдумывать его не понадобилось. Тестов нет по существу: задача про содержимое сгенерированных бандлов; доказательство — состояние доктора и наличие файлов до и после регенерации. Domain: результат осмыслен вне тестов — англоязычная страница whats-new-1.8.md ссылается на sessions.md, и теперь эта ссылка разрешается внутри каждой оснастки, а не только в исходном дереве.
