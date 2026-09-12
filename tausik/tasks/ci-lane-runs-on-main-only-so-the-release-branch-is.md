---
slug: ci-lane-runs-on-main-only-so-the-release-branch-is
title: "[SUPERSEDED] GitHub trigger for unpublished development branch"
status: done
epic: release-19-renar-conformance
story: release19-proof-integrity
complexity: null
role: developer
stack: null
tier: trivial
call_budget: 5
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "tausik/tasks/ci-lane-runs-on-main-only-so-the-release-branch-is.md"
scope_paths:
  - ".github/workflows/tests.yml"
  - "tests/test_ci_lanes_are_honest.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - ROADMAP.md
scope_tools: []
depends_on: []
completed_at: "2026-09-12T13:33:37Z"
---

## Goal

Исходная правка GitHub trigger НЕ выполняется: замер установил, что v1-9-wave намеренно не публикуется на GitHub, а GitLab уже проверяет рабочую ветку. Терминальный результат — документированная отмена ложной предпосылки; возможный pre-merge release/* workflow остаётся отдельным 1.10 процессным улучшением, если будет выбран владельцем.

## Acceptance Criteria

AC-1: решения #260/#267 и измерение GitLab development pipeline записаны. AC-2: GitHub workflow не меняется мёртвым trigger-правилом. AC-3 (negative): задача не заявляет, что исходные AC о v*-wave выполнены.

## Plan

## Rollback

## Journal

- 2026-09-08T19:58:50Z [implementation] — ПРЕМИСА ЭТОЙ ЗАДАЧИ ОПРОВЕРГНУТА ЗАМЕРОМ. Правка сделана и ОТКАЧЕНА, потому что не дала бы ничего. ЧТО Я СОБИРАЛСЯ СДЕЛАТЬ: добавить 'v*-wave' в триггер push у .github/workflows/tests.yml, чтобы лента видела релизную ветку. ПОЧЕМУ ЭТО НЕ РАБОТАЕТ. Решение #260: рабочая ветка НАМЕРЕННО не уходит на GitHub. Проверено 'git branch -r': на github есть main, release/1.8-batch-s126, release/1.9 и release/v1.8.0-snapshot, и НЕТ v1-9-wave. Триггер на ветку, которая туда не пушится, — мёртвая строка конфигурации. ЧТО НА САМОМ ДЕЛЕ. Веток две линии, и они делают разное: GitLab (origin) — линия разработки, решение #267. Её workflow.rules содержит 'if: $CI_COMMIT_BRANCH', то есть пайплайн идёт на ЛЮБОЙ ветке. v1-9-wave проверяется непрерывно. Половина условия выпуска 4 «лента гоняется на ветке разработки» УЖЕ ВЫПОЛНЕНА, просто не той лентой, о которой я думал. GitHub — опубликованная лента, та самая, чей значок красный. Она гоняется на main и на pull_request в main. ПОЧЕМУ ЗНАЧОК КРАСНЫЙ. github/main стоит на faaa10f4, а рабочая ветка ушла на 651 коммит вперёд от github/release/1.9. Последний прогон на main — 25.08. Лента красная не потому, что смотрит не туда, а потому что на main с тех пор не пушили. СЛЕДСТВИЕ, И ОНО МЕНЯЕТ ОТВЕТ ВЛАДЕЛЬЦУ. Опубликованная лента НЕ МОЖЕТ позеленеть никакой правкой триггера: она позеленеет, когда 1.9 приедет на main. То есть условие выпуска 4 — не препятствие ПЕРЕД выпуском, а его СЛЕДСТВИЕ. Шесть смен подряд оно выносилось как «решение о ленте», и это была моя ошибка чтения: я мерил не ту ленту. ЧТО ОСТАЁТСЯ НАСТОЯЩИМ ВОПРОСОМ: хочет ли владелец промежуточной проверки — гонять опубликованную ленту на ветке release/* ДО слияния в main, чтобы зелёное было видно раньше. github/release/1.9 существует, но отстал на 651 коммит, то есть этот путь однажды использовали и бросили. Это выбор процесса, а не дефект, и заводить его правкой втихую я не стал.
- 2026-09-12T10:44:09Z — SUPERSEDED terminal disposition: premise refuted by decisions #260/#267 and branch measurement. Original GitHub trigger AC are retired, not implemented; optional release/* pre-merge visibility is a distinct 1.10 process choice.
- 2026-09-12T10:44:19Z — AC verified for terminal disposition: 1) decisions #260/#267 and GitLab branch evidence are recorded; 2) no dead GitHub trigger was added; 3) original v*-wave trigger AC are explicitly retired, not claimed.
