---
slug: pypi-package-uvx-tausik-init
title: "Пакет на PyPI: uvx tausik init вместо сабмодуля и bootstrap"
status: planning
epic: visibility-stream
story: entry-barrier
complexity: complex
role: backend
stack: null
tier: moderate
call_budget: 55
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths:
  - "bootstrap/**"
  - "scripts/**"
  - pyproject.toml
  - "tests/*.py"
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

Установка TAUSIK в чужой проект занимает одну команду и меньше минуты, а не три шага, два из которых человек делает руками вне агента.

## Acceptance Criteria

1. Имя tausik на PyPI занято нами (проверено: сейчас свободно, HTTP 404). Пакет stdlib-only, wheel собирается без зависимостей.
2. `uvx tausik init` в корне чужого проекта делает всё, что сегодня делают сабмодуль плюс bootstrap: вендорит файлы, инициализирует .tausik, пишет конфиги IDE.
3. Измерено на ЧИСТОЙ машине: время от `git clone` чужого проекта до первого успешного `task start` — меньше 60 секунд. Число названо, а не заявлено.
4. Обновление работает: `tausik upgrade` переносит на новую версию без ручной правки.
5. НЕГАТИВНЫЙ сценарий: два канала распространения (сабмодуль и PyPI) НЕ имеют права разойтись по версиям молча. Расхождение обнаруживается проверкой и называется вслух, иначе мы производим ровно тот тихий дрейф, против которого построены.
6. НЕГАТИВНЫЙ сценарий: установка в проект, где TAUSIK уже стоит сабмодулем, НЕ ломает существующую установку и не затирает .tausik.

## Plan

## Rollback

Пакет депубликуется; путь через сабмодуль остаётся рабочим

## Journal
