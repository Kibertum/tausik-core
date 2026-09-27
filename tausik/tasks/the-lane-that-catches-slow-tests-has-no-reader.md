---
slug: the-lane-that-catches-slow-tests-has-no-reader
title: "Полосу, которая ловит медленные тесты, никто не читает"
status: planning
epic: release-110-deferred-from-19
story: release110-open-defects
complexity: medium
role: architect
stack: python
tier: moderate
call_budget: 40
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

НАЙДЕНО ПРИ ПОЧИНКЕ two-tests-fail-only-under-parallel-and-hide-which-step-broke, смена #277. Это тот же тезис, который scripts/ci_lane_status.py уже формулирует про себя, применённый к нему же.

ЧТО ИЗМЕРЕНО. Два теста были сломаны ДЕТЕРМИНИРОВАННО и прожили релиз: task start отказывал по QG-0 (цель в одно слово), обработчик dead_end — по правилу 1.10 о слаге задачи. Оба файла под `pytestmark = pytest.mark.slow`, и addopts по умолчанию `-m 'not slow'` отбрасывает их целиком: `--collect-only` печатает «157 deselected» в 15 файлах.

ПОЛОСА, КОТОРАЯ ИХ ЛОВИТ, СУЩЕСТВУЕТ: .gitlab-ci.yml::tests-full гоняет `pytest tests/ -m '' -q`, отдельной стадией, на каждой ветке. Она обязана была покраснеть.

НО ЕЁ ВЕРДИКТ НЕ ЧИТАЕТ НИКТО. scripts/ci_lane_status.py показывает на чокпоинте `push-ok` состояние ОПУБЛИКОВАННОЙ полосы — GitHub Actions на main. За смену #277 он десять раз подряд отвечал «published lane Tests is GREEN (main #34799474905, 2026-09-14)», то есть говорил про main двухнедельной давности, пока вся работа шла на v1-10. Полоса GitLab на рабочей ветке не показывается нигде и ни на каком чокпоинте.

ЭТО ДОСЛОВНО ТЕЗИС ЭТОГО ЖЕ МОДУЛЯ: «гейт, красноту которого никто не читает, неотличим от выключенного». Он написан про три красных windows-latest, простоявших девять дней. Теперь тот же дефект — про сам модуль.

ГРАНИЦА, ПОСТАВЛЕННАЯ ВЛАДЕЛЬЦЕМ И ОБЯЗАТЕЛЬНАЯ: чтение CI GitLab НЕ ДОЛЖНО попасть в публичный репозиторий на GitHub. Значит решение либо не выпускается наружу, либо выпускается так, что публичная сборка его не несёт. Это условие задачи, а не пожелание.

ЧТО ПРОВЕРИТЬ ПЕРВЫМ, а не чинить сразу: действительно ли tests-full краснела на v1-10, или пайплайн там вовсе не шёл. Это два разных дефекта: «никто не читал красноту» и «полоса не запускалась». Число решает, что чинить.

## Acceptance Criteria

## Plan

## Rollback

## Journal
