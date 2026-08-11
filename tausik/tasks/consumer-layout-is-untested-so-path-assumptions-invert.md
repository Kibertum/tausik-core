---
slug: consumer-layout-is-untested-so-path-assumptions-invert
title: "Потребительская раскладка не покрыта тестами, поэтому каждое допущение о путях в ней переворачивается"
status: planning
epic: landscape-2026-h2
story: l26-narrative
complexity: complex
role: architect
stack: null
tier: substantial
call_budget: 65
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths:
  - "tests/**"
  - "scripts/*.py"
  - "docs/ru/*.md"
  - "docs/en/*.md"
scope_tools: []
completed_at: null
---

## Goal

Существует фикстура ПОТРЕБИТЕЛЬСКОГО проекта — TAUSIK сабмодулем в .tausik-lib, собственные scripts/ у проекта, тесты не в <root>/tests — и ключевые проверки прогоняются на ней, а не только на репозитории разработки.

## Acceptance Criteria

1. Названа ПРИЧИНА класса: TAUSIK разрабатывается там, где project_dir и lib_dir — один каталог, а ставится туда, где это два разных каталога. Каждое допущение о путях, верное в репозитории разработки, в потребительском переворачивается молча.
2. Фикстура воспроизводит потребительскую раскладку: TAUSIK в .tausik-lib, собственные scripts/ у проекта, тесты не в <root>/tests, сабмодуль без содержимого.
3. На фикстуре прогоняются проверки ЧЕТЫРЁХ уже найденных дефектов этого класса: hooks-point-into-a-submodule, pytest-gate-no-ops, doctor-drift-compares-the-host-scripts-root, sibling-mcp-detector. Каждый обязан падать на фикстуре ДО своей правки.
4. Гарантия даётся СВОЙСТВОМ: тест перечисляет из кода места, читающие project_dir как корень харнесса, и требует, чтобы каждое было покрыто фикстурой (конвенция #354).
5. НЕГАТИВНЫЙ сценарий: фикстура, на которой всё зелено с первого дня, бесполезна — критерий 3 требует, чтобы она сначала КРАСНЕЛА на живых дефектах.
6. НЕГАТИВНЫЙ сценарий: фикстура не должна требовать сети и настоящего сабмодуля — иначе она не переживёт CI и будет отключена.

## Plan

## Rollback

git revert коммита; фикстура и её тесты удаляются одним куском

## Journal
