---
slug: brain-move-deletes-leave-ghost-projection
title: "brain move пишет и удаляет решения и записи памяти мимо проекции: три вызова из трёх обходят слой, который её обновляет"
status: done
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
relevant_files:
  - "scripts/brain_move.py"
  - "scripts/project_backend.py"
  - "scripts/backend_crud_knowledge.py"
  - "tests/test_brain_move_projection.py"
  - "tests/test_brain_move.py"
  - "tests/test_state_projection_tracks_db.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-08-03T09:21:52Z"
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

- 2026-08-03T09:15:41Z [implementation] — AC verified: 1. ✓ Все три пути через слой записи, не рядом с вызовом: добавлен SQLiteBackend._delete_projected_by_id (читает slug ДО удаления — после него читать неоткуда), на нём memory_delete и новый decision_delete; вставка идёт через write_local. brain_move больше не содержит ни одного сырого _ex по этим таблицам. 2. ✓ ВЫБОР МЕСТА: слой записи, а не brain_move. Список из трёх не повторит судьбу списка из восемнадцати именно потому, что гарантию даёт не список, а СВОЙСТВО — tests/test_brain_move_projection.py проверяет равенство дерева и build_tree(db) после реальных прогонов move_to_brain/move_to_local, а не перечисляет места вызова. Отсутствие decision_delete в миксине и было приглашением написать сырой DELETE. 3. ✓ КРАСНЫЕ ДО ФИКСА, проверено обратимыми пробами: возврат удаления решения к _ex — красный; удаления памяти к _ex — красный; возврата из brain к decision_add — красный. Четвёртая проба (ушедшая память с живым ребром) тоже красная. 4. ✓ (а) ребро в никуда: test_a_departing_memory_leaves_no_edge_pointing_at_nothing — краснеет на старом пути; (б) fail-open: test_a_broken_projection_does_not_roll_back_or_kill_the_move — экспорт кидает OSError, миграция завершается ok, строка удалена. 5. ✓ ИСКЛЮЧЕНИЕ ПЕРЕПИСАНО, а не оставлено: ('decisions','DELETE') больше не ссылается на закрытый дефект. Причина теперь — ОБЛАСТЬ НАБЛЮДЕНИЯ, по образцу соседней записи memory_edges. 6. ✓ ruff и mypy чистые, bootstrap пересобран, 45 тестов трёх смежных наборов зелёные. DEAD END, записан в исключении: добавление decision_delete в _OPS генератора. Новая операция сдвигает КАЖДЫЙ последующий розыгрыш, и форма start-task-in-open-story перестала достигаться — на четырёх разных наборах зёрен. Подбирать зёрна, пока форма вернётся, значит крутить выборку до согласия; отказался. ПОБОЧНАЯ ПРАВКА: _FakeBackend.decision_add в tests/test_brain_move.py имел сигнатуру УЖЕ настоящей (только text и keyword rationale). Когда вставка поехала через write_local, который передаёт task_slug позиционно как все прочие вызовы, три теста упали на ДУБЛЕ при верном коде. Дубль расширен до сигнатуры оригинала.
- 2026-08-03T09:19:03Z [implementation] — ПОПРАВКА к записи о критерии 1: публичного decision_delete НЕТ. Он был написан, и его отверг храповик поверхности класса — SQLiteBackend уже несёт 129 публичных членов, и гейт существует ровно затем, чтобы 130-й не добавляли ради одного вызывающего. Удаление решения идёт через сам помощник слоя записи: svc.be._delete_projected_by_id('decisions', id). Требование критерия было «путь на слое записи, который ПРОЕЦИРУЕТ», а не «публичный метод»; публичный метод был лишь одним способом это записать. memory_delete остаётся публичным, потому что он уже существовал, и теперь проецирует. Гейт поверхности класса зелёный (tests/test_gate_class_surface.py), 63 теста четырёх наборов зелёные, ruff и mypy чистые.
- 2026-08-03T09:19:42Z [implementation] — Root cause (missing-validation): у миксина не было метода удаления решения, а memory_delete был сырым _ex без проекции. Отсутствие метода — это приглашение: автор brain_move написал свой DELETE, он сработал, и файл остался призраком. Проекция при этом не давала сигнала, потому что полный state export перестраивает дерево с нуля и прячет расхождение. Prevention: удаление по id живёт на слое записи в _delete_projected_by_id, который читает slug ДО удаления и проецирует уход; свойство «дерево равно build_tree(db) после прогона brain move» закреплено тестом, а не перечнем мест вызова.
