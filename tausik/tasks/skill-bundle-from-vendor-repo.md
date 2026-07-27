---
slug: skill-bundle-from-vendor-repo
title: "3.5: бандлы недоступны из магазина — bundle резолвит skills-official/, которого в поднятом проекте нет"
status: planning
epic: landscape-2026-h2
story: l26-ecosystem
complexity: complex
role: architect
stack: python
tier: moderate
call_budget: 60
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
completed_at: null
---

## Goal

Подтверждено: scripts/project_cli_skill.py:158-162 ищет skills-official/ рядом с чекаутом ядра, а bundles.json не живёт в репозитории магазина. Из-за этого deck нельзя вписать в workflow-helpers, а noslop — в ru-locale; бандл ru-locale остаётся пустым placeholder'ом. Решить, откуда бандл берёт состав: из вендор-репы (bundles.json рядом с tausik-skills.json) или из ядра со ссылками на репозиторий:скилл. Первое даёт магазину владеть своими бандлами.

## Acceptance Criteria

AC1. Принято и зафиксировано через tausik decide решение об источнике состава бандла: вендор-репа (bundles.json рядом с tausik-skills.json) ИЛИ ядро со ссылками repo:skill. Первое даёт магазину владеть своими бандлами.
AC2. Резолв бандлов больше не требует наличия skills-official/ рядом с чекаутом ядра (project_cli_skill.py:158-162): бандл резолвится в поднятом проекте без вендор-каталога ядра — тест fails-then-passes.
AC3. Бандлы deck (в workflow-helpers) и noslop (в ru-locale) резолвятся; бандл ru-locale больше не остаётся пустым placeholder'ом — тест на непустой состав.
AC4. НЕГАТИВНЫЙ: отсутствующий или битый bundles.json даёт понятную ошибку, а не молча пустой бандл.
CHANGELOG.md [Unreleased] и зеркало CHANGELOG.ru.md обновлены прозаической записью об этом изменении.

## Plan

## Rollback

## Journal
