---
slug: brain-move-deletes-leave-ghost-projection
title: "brain move пишет и удаляет решения и записи памяти мимо проекции: три вызова из трёх обходят слой, который её обновляет"
status: planning
epic: brain-hardening
story: brainh-core
complexity: simple
role: developer
stack: python
tier: moderate
call_budget: 30
defect_of: projection-property-test-cannot-reach-cascades
scope: "scripts/brain_move.py, scripts/project_backend.py, tests/"
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
completed_at: null
---

## Goal

Найдено при работе над projection-property-test-cannot-reach-cascades (сессия #154), подтверждено чтением. Уже ССЫЛАЕТСЯ на эту задачу код: tests/test_state_projection_tracks_db.py, словарь _UNREACHABLE, запись ("decisions","DELETE") — исключение из храповика путей записи обосновано именно этим дефектом, поэтому пока он жив, храповик несёт дыру с именем.

ТРИ МЕСТА, все в scripts/brain_move.py.
(1) Строка 159: svc.be._ex("DELETE FROM decisions WHERE id = ?") — сырой DELETE мимо _delete_projected. Файл tausik/decisions/<slug>.md остаётся ПРИЗРАКОМ: описывает строку, которой в БД больше нет.
(2) Строка 161: svc.be._ex("DELETE FROM memory WHERE id = ?") — то же для памяти. Хуже: memory_edges полиморфна, у ссылавшихся на неё записей останется ребро в никуда (механизм тот же, что чинил _reproject_orphaned_edge_sources, но он висит на УХОДЕ через export_one, а этот путь export_one не зовёт вовсе).
(3) Строка 219: svc.be.decision_add(...) напрямую, минуя KnowledgeMixin._decision_local. Докстринг _decision_local прямо говорит, зачем он существует: «Три из четырёх точек вызова раньше звали decision_add напрямую и пропускали проекцию». Четвёртая — вот эта, её тогда не заметили. Новая строка в БД без файла в дереве.

ПОЧЕМУ ЭТО НЕ ТЕОРИЯ. brain move --to-local / --to-brain — команда миграции, она работает ПАРТИЯМИ, поэтому одна её пробежка оставляет столько призраков и пропусков, сколько строк перенесла. Полный `state export` их прячет (перестраивает дерево с нуля), так что `status` расхождения не покажет — ровно тот механизм сокрытия, который описан в state-git-triggers.

ПОЧЕМУ ЭТО НЕ ЛОВИТСЯ СУЩЕСТВУЮЩИМ ТЕСТОМ. Свойство проекции гоняется через ProjectService; brain_move — отдельный модуль поверх svc.be, и в порождаемый набор мутаций он не входит. Это и есть граница, названная в _UNREACHABLE.

## Acceptance Criteria

1. Все три пути в scripts/brain_move.py проецируются: удаление решения и удаление записи памяти снимают свой файл (через _delete_projected или эквивалент на слое записи, НЕ добавлением ещё одного ручного вызова экспорта рядом), а создание локального решения проходит через ту же единственную точку, что и остальные три вызова (KnowledgeMixin._decision_local или её преемник после разреза service_knowledge).
2. ВЫБОР МЕСТА ПОЧИНКИ ОБОСНОВАН В ЖУРНАЛЕ. Правка на слое записи (backend) закрывает и будущие вызовы; правка в brain_move закрывает только эти три. Если выбран второй вариант — сказано, почему список из трёх не повторит судьбу списка из восемнадцати, с которого начинался state-git-triggers.
3. ПРОВЕРКА ТЕСТОМ, КРАСНЫМ ДО ФИКСА: прогон brain move на временной БД с включённым state.auto_export оставляет дерево равным build_tree(db) — то же свойство, что и в tests/test_state_projection_tracks_db.py, применённое к этому модулю. Тест обязан краснеть на текущем коде; факт красноты до фикса записан в журнал.
4. НЕГАТИВ: (а) удаление записи памяти, на которую есть живое ребро, не оставляет у источника ребра в никуда — та же проверка, что дал _reproject_orphaned_edge_sources, но по пути brain_move, который export_one не зовёт; (б) fail-open сохранён: ошибка сериализации или IO не откатывает и не роняет саму миграцию (gotcha #271).
5. ИСКЛЮЧЕНИЕ СНИМАЕТСЯ. Запись ("decisions","DELETE") удаляется из _UNREACHABLE в tests/test_state_projection_tracks_db.py, ЛИБО её причина переписана на ту, что стала истинной. Оставить обоснование, ссылающееся на закрытый дефект, нельзя — храповик проверяет исключения на равенство и молча пропустит путь, который снова достижим.
6. Полный pytest зелёный; ruff и mypy чистые; bootstrap drift отсутствует.
CHANGELOG.md [Unreleased] и зеркало CHANGELOG.ru.md обновлены прозаической записью об этом изменении.

## Plan

## Rollback

git revert

## Journal
