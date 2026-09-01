---
slug: three-preexisting-write-gate-gaps-from-review-6
title: "Три предсуществующих пробоя гейта записи из ревью #6: обёртка env, тильда в пути скрипта, непокрытая ветка диалекта"
status: planning
epic: release-19-renar-conformance
story: gates-declare-what-they-prevent
complexity: medium
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

ТРИ ЗАМЕЧАНИЯ РЕВЬЮ #6, НЕ ВОШЕДШИЕ В ПОЧИНКУ РЕГРЕССИИ ПО РЕШЕНИЮ ВЛАДЕЛЬЦА (чинили только то, что стало ХУЖЕ прежнего). Все три ПРЕДСУЩЕСТВУЮТ, ни одно не внесено в #205.

ОДИН. ОБЁРТКА env НЕ РАЗВОРАЧИВАЕТСЯ. Замерено мной: env -C КАТАЛОГ python helper.py не блокируется НИ с полем cwd, НИ без него, то есть и до правок #205 тоже. Причина не в каталоге, а в том, что команда в позиции команды есть env, и python внутри обёртки разбору не виден вовсе. Тот же класс, что timeout 10 bash -c, для которого _mentions_interpreter уже смотрит ВСЕ токены, а _script_file_writes — только первый.

ДВА. НЕТ expanduser НА ПУТИ СКРИПТА. bash_write_parse резолвит путь скрипта без разворачивания тильды, поэтому python ~/helper.py даёт несуществующий путь и fail-soft пустоту — скрипт невидим гейту, тогда как тот же скрипт по абсолютному пути виден. Из пяти мест, резолвящих пришедший извне путь, ЧЕТЫРЕ разворачивают тильду (bash_write_gate, memory_pretool_block, scope_write_gate, memory_posttool_audit) и одно нет.

ТРИ. ВЕТКА ПО ТОЖДЕСТВУ ДИАЛЕКТА В shell_channel НЕ ПОКРЫТА НИ ОДНИМ ТЕСТОМ. Ревью показало, что снятие ветки оставляет 457 целевых тестов зелёными: ни один тест не зовёт shell_channel.write_targets напрямую с не-Bash именем инструмента. Сама ветка есть перечисление диалекта, против которого этот модуль и заведён (его же docstring). Направление: единая сигнатура у всех диалектов, тогда ветка исчезает, и заодно решается протяжка близнеца.

НАЧАТЬ С ЦИФРЫ: сколько форм запуска интерпретатора через обёртку (env, timeout, nice, xargs, стандартные оболочечные обёртки) разбор видит СЕЙЧАС — матрицей, а не примером. Числа в этом заголовке нет сознательно: их надо измерить.

## Acceptance Criteria

## Plan

## Rollback

git revert коммита задачи.

## Journal
