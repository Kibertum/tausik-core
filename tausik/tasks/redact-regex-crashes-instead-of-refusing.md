---
slug: redact-regex-crashes-instead-of-refusing
title: "redact --regex с неверным шаблоном падает сырым трейсбеком вместо именованного отказа"
status: planning
epic: release-19-renar-conformance
story: github-primary-gitlab-mirror
complexity: simple
role: backend
stack: null
tier: trivial
call_budget: null
defect_of: nothing-can-redact-the-memory-the-framework-publishes
scope: null
scope_exclude: null
relevant_files: []
scope_paths:
  - "scripts/redact_engine.py"
  - "scripts/project_cli_redact.py"
  - "tests/test_redact.py"
  - "docs/ru/cli.md"
scope_tools: []
completed_at: null
---

## Goal

ВОСПРОИЗВЕДЕНИЕ, сессия #181: tausik redact --regex --pattern '<неверное регулярное выражение>' печатает трейсбек re._compiler через redact_engine._compiled и падает. Пользователь видит семь кадров стека внутренностей Python и строку 'unterminated character set at position 5' — то есть ответ есть, но он адресован автору команды, а не тому, кто её вызвал. Соседний случай в той же команде сделан правильно: нулевое совпадение имеет ОТДЕЛЬНУЮ формулировку и не выдаётся за успех (её собственный AC7). Значит расхождение не в незнании правила, а в том, что правило применили к одному входу и не применили к другому. Класс: отказ, не названный словами, неотличим от поломки инструмента.

## Acceptance Criteria

## Plan

## Rollback

git revert коммита; правка локальна в redact_engine._compiled

## Journal
