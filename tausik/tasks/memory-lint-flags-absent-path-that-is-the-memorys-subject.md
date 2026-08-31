---
slug: memory-lint-flags-absent-path-that-is-the-memorys-subject
title: "Два детектора (memory lint и audit evidence) считают ПРИМЕР-ЗАГЛУШКУ настоящей ссылкой: 43% ложных в одном, заглушки в счётчике 'выдумано' у другого"
status: planning
epic: release-19-renar-conformance
story: renar-debt-implemented-wrong
complexity: complex
role: developer
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
---

## Goal

НАЙДЕНО АУДИТОМ SENAR 9.5 В #199. ДВА НЕЗАВИСИМЫХ ДЕТЕКТОРА ОШИБАЮТСЯ ОДИНАКОВО, И ПРИЧИНА У НИХ ОДНА: они не отличают ССЫЛКУ от УПОМИНАНИЯ-ПРИМЕРА. Задача чинит корень, а не два симптома.  ДЕТЕКТОР 1 — memory lint (stale_file). После --apply остаётся 7 находок; каждый путь проверен на диске — отсутствуют все семь, но ТРИ ложны. #322 «Разделение durable/runtime стейта» ссылается на 'tausik/tausik.db' — память УТВЕРЖДАЕТ, что БД там не лежит; это её предмет. #463 «44 нерезолвящихся цитаты» ссылается на 'tests/test_does_not_exist.py' — иллюстрация несуществующей цитаты внутри памяти О несуществующих цитатах. #65 ссылается на '.claude/settings.local.json' — файл в .gitignore (строка 32), отсутствует ЗАКОННО и машинно-локально. Ложных 3 из 7 — 43%.  ДЕТЕКТОР 2 — tausik audit evidence. Замер: 1267 закрытых задач, 3041 цитата, 1107 уникальных, резолвятся 1063, ROTTED 19, NEVER_EXISTED 25. Но в NEVER_EXISTED лежат ЯВНЫЕ ЗАГЛУШКИ: tests/test_does_not_exist.py, tests/test_foo.py(::test_bar), tests/test_x.py, tests/test_X.py, tests/x.py, tests/test_a.py, tests/test_real.py::test_a, tests/test_file.py, tests/foo.py, tests/integration/test_foo.py, tests/unit/scoped/test_bar.py, tests/../scripts/prod.py. Цитируют их задачи, чей ПРЕДМЕТ — поддельные и сгнившие цитаты: rule5-checklist-keyword-theater, closure-evidence-references-rot-and-nothing-notices, memory-lint-stale-file-mostly-false-positives, checklist-detector-is-red-on-its-own-test, review-mlow-resolver-recursive.  ПОЧЕМУ ЭТО НЕ КОСМЕТИКА. Число «25 выдуманных доказательств» ПУГАЕТ вместо того, чтобы УКАЗЫВАТЬ: настоящих среди них меньшинство, и они тонут в заглушках. Контроль, который в заметной доле случаев кричит на здоровое, обучает агента пролистывать свой вывод — то есть отключается руками читателя. Это ровно дефект из решения #288: контроль, исполняемый формально, по всем прочим признакам выглядит здоровым.  ЧТО ДЕЛАТЬ (варианты, выбор за исполнителем, но корень чинить ОДИН). (1) Отличать упоминание-пример от ссылки: путь внутри текста, который сам утверждает его отсутствие/поддельность, ссылкой не считать. (2) Дать явный способ ОБЪЯВИТЬ путь примером, чтобы оба детектора его пропускали. (3) Учитывать .gitignore: игнорируемый путь отсутствует законно. (4) Разделить вывод audit evidence на «настоящие» и «заглушки» с ОТДЕЛЬНЫМИ счётчиками, чтобы число в шапке не врало. ОБЯЗАТЕЛЬНО: у починки нужна НЕГАТИВНАЯ ветвь — заведомо НАСТОЯЩАЯ сгнившая цитата обязана остаться найденной. Иначе «ложных срабатываний больше нет» станет достигаться отключением детектора. ГДЕ СМОТРЕТЬ: поиск по 'stale_file' и по реализации audit evidence в scripts/.

## Acceptance Criteria

## Plan

## Rollback

## Journal
