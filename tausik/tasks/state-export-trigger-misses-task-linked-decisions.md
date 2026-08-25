---
slug: state-export-trigger-misses-task-linked-decisions
title: "Авто-экспорт состояния не срабатывает на task-linked decisions и task_update — headline-фича релиза протекает"
status: done
epic: landscape-2026-h2
story: l26-arch-debt
complexity: complex
role: developer
stack: python
tier: substantial
call_budget: 120
defect_of: null
scope: "scripts/state_triggers.py, scripts/service_task.py, scripts/service_knowledge.py, scripts/service_hierarchy.py, tests/, CHANGELOG.md, CHANGELOG.ru.md, docs/ru/team-state-in-git.md, docs/en/team-state-in-git.md"
scope_exclude: "Схема БД и миграции не трогаются. state_export.py/state_import.py (сериализатор) не трогается — дефект в местах ВЫЗОВА, а не в сериализации. Формат файлов не меняется."
relevant_files:
  - "scripts/state_triggers.py"
  - "scripts/state_export.py"
  - "scripts/state_import.py"
  - "scripts/state_serialize.py"
  - "scripts/service_task.py"
  - "scripts/service_knowledge.py"
  - "scripts/service_knowledge_hygiene.py"
  - "scripts/service_hierarchy.py"
  - "tests/test_state_projection_tracks_db.py"
  - "tests/test_state_triggers.py"
  - "tests/test_service_knowledge_decide.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - "docs/ru/team-state-in-git.md"
  - "docs/en/team-state-in-git.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-28T18:16:56Z"
---

## Goal

Обнаружено в сессии #152 при записи решения #202 об объёме релиза 1.8.

ВОСПРОИЗВЕДЕНО ЗАПУСКОМ, не чтением. Записал решение с task_slug -> `Decision #202 recorded — saved to local`. `git status` чист по tausik/decisions/, файлов 201 при 202 решениях, grep по тексту решения в дереве пуст. После ручного `.tausik/tausik state export` файл появился (202 файла) и вместе с ним всплыла ещё и незаэкспортированная правка tausik/tasks/brain-decide-publishes-unclassified-rationale.md.

ПРИЧИНА ПО КОДУ. scripts/service_knowledge.py::decide имеет три ветки возврата. auto_export_by_id вызывается ТОЛЬКО в последней (локальная запись без task_slug). Ранний возврат `if task_slug is not None` пишет строку в БД и возвращается БЕЗ экспорта. Ветка успешной записи в brain не пишет локально вообще (см. смежную задачу brain-decide-publishes-unclassified-rationale, AC0). Аналогично не экспортируется task_update.

ПОЧЕМУ ЭТО ВАЖНО ИМЕННО СЕЙЧАС. Состояние-в-git — headline-фича, которой релиз 1.8 представлен в README EN+RU. Большинство решений проекта пишутся С task_slug, то есть по самому частому пути фича молчаливо не работает. Дыру маскирует периодический полный `state export`: он подтягивает пропущенное, поэтому `tausik status` не показывает расхождения, и на глаз всё выглядит согласованным. В команде это значит, что коллега после git pull не увидит решений, записанных с момента последнего ручного экспорта.

НЕ дефект (чтобы следующий агент не искал заново): memory_add экспортируется корректно — два файла в tausik/memory/ появились сразу после записи, без ручного экспорта.

## Acceptance Criteria

AC1. СВОЙСТВО (главный критерий, заменяет проверку наличия вызовов). После последовательности мутаций БЕЗ единого ручного экспорта дерево tausik/ побайтово равно build_tree(БД). Тест прогоняет последовательность по всем пяти кинд'ам проекции и падает до фикса.
AC2. Покрыты все пять кинд'ов из машинного реестра state_import.ENTITY_DIRS: epics (add/done/delete), stories (add/done/delete), tasks (add/start/update/log/block/unblock/review/done), decisions (все три ветки decide, включая с task_slug и brain), memory (add/delete/dead_end/link/unlink/archive).
AC3. УДАЛЕНИЕ. auto_export_entity умеет снимать файл: export_one -> None (сущность удалена или память архивирована) удаляет файл проекции, если он есть. Тест: удалить задачу -> файла в дереве нет; архивировать память -> файла нет. Падает до фикса (сейчас None -> молчаливый выход).
AC4. COVERAGE-РАТЧЕТ. Набор кинд'ов, прогоняемых тестом AC1, выводится из ENTITY_DIRS и сверяется с ним: добавление шестого кинда в реестр без расширения теста роняет тест. Защита от вырожденного прохода: отдельная проверка падает, если ENTITY_DIRS схлопнулся ниже пяти.
AC5. fail-open сохранён (gotcha #271): исключение внутри экспорта не откатывает запись в БД и не роняет вызов. Тест с подменой export_one на бросающий — строка в БД есть, вызов вернул успех, экспорт вернул False.
AC6. Претензия документации приведена в соответствие с кодом. CHANGELOG EN+RU утверждает «tracks the DB without manual commands» с перечнем «task done, decide, memory add» — перечень был уже кода и станет уже после фикса; правится на обоих языках. docs/{ru,en}/team-state-in-git.md получает раздел о том, ЧТО именно триггерится, выведенный из ENTITY_DIRS, а не переписанный рукой.
AC7. НЕГАТИВ, проверка отсутствия: на реальном репозитории после серии мутаций `tausik state export` не порождает диффа (git status чист по tausik/), а session_open не отдаёт sync_suggested. До фикса тот же прогон даёт непустой дифф — он и есть доказательство дефекта.
AC8. Полный pytest зелёный; ruff/mypy/filesize чисто. Прирост стоимости на горячем пути (task_log) измерен и назван, а не предположен.

## Plan

## Rollback

git revert коммита. Изменения локализованы в трёх модулях вызова + тесты + CHANGELOG; схема БД не меняется, миграций нет, формат файлов проекции не меняется. Механизм целиком за флагом state.auto_export — при откате поведение возвращается к текущему (экспорт в 3 точках), данные не теряются, так как БД остаётся источником правды, а полный `tausik state export` доступен вручную.

## Journal

- 2026-07-28T17:18:50Z [implementation] — РАЗВЕДКА ЗАВЕРШЕНА, объём дефекта шире исходной карточки. Реестр проекции машинно-читаем: state_import.ENTITY_DIRS = (epics, stories, tasks, decisions, memory); specs осознанно вне проекции (state_export.py:10). Мутирующих сервисных методов по этим пяти кинд'ам ~20, экспортируют ДВА: memory_add и ветка decide без task_slug. Не экспортируют: epic_add/done/delete, story_add/done/delete, task_add/start/block/unblock/review/update/log, decide с task_slug, decide через brain, memory_delete, dead_end, memory_link/unlink. ВТОРАЯ НАХОДКА, не в карточке: auto_export_entity НЕ УМЕЕТ УДАЛЯТЬ. export_one возвращает None для отсутствующей и для архивированной сущности, а триггер на None просто выходит (return False). Значит удаление задачи/памяти и архивация памяти оставляют в дереве ФАЙЛ-ПРИЗРАК, которого в БД уже нет. Для полного `state export` это не видно (он строит дерево целиком), для инкрементального — накапливается. РЕШЕНИЕ ПО АРХИТЕКТУРЕ. Отвергнут вариант «расставить вызовы по местам»: именно так 18 из 20 и забыли, одноразовая правка воспроизведёт класс. Опора рэтчета переносится с НАЛИЧИЯ ВЫЗОВА на СВОЙСТВО: после произвольной последовательности мутаций без единого ручного экспорта build_tree(БД) обязан быть побайтово равен тому, что лежит в дереве. Свойство фальсифицируемо, не зависит от способа реализации и покрывает будущие мутации. Плюс coverage-рэтчет: набор кинд'ов, прогоняемых тестом, обязан совпадать с ENTITY_DIRS — добавление шестого кинда без расширения теста роняет его. Первая попытка рэтчета через AST (поиск self.be.<метод с DML>) ОТВЕРГНУТА как негодная: task_add/task_update в бэкенде идут через хелпер _add_slugged, литерального DML в теле нет, детектор их не увидел. Структурная эвристика по телу функции здесь врёт — это и есть причина отказа от неё в пользу свойства.
- 2026-07-28T17:52:29Z [implementation] — AC7: проверка отсутствия расхождения — мутация через CLI без ручного экспорта
- 2026-07-28T17:54:04Z [implementation] — AC7 повтор: мутация после передеплоя, ручного экспорта нет
- 2026-07-28T18:03:05Z [implementation] — AC-1 ✓ СВОЙСТВО. tests/test_state_projection_tracks_db.py::test_projection_tracks_db_after_every_mutation — прогоняет мутации по всем пяти кинд'ам и после КАЖДОЙ группы сверяет дерево на диске с build_tree(БД) побайтово, без единого ручного экспорта. Тест сравнивает три множества отдельно (недостающие файлы, файлы-призраки, разошедшееся содержимое), поэтому падение называет, ЧТО именно разъехалось. AC-2 ✓ Покрыты все пять: epics (add/done/delete), stories (add/done/delete), tasks (add/update×3/start/log/plan/step/block/unblock/review/move/delete), decisions (с task_slug и без), memory (add/dead_end/delete/link). AC-3 ✓ УДАЛЕНИЕ. state_triggers._remove_projection: export_one -> None снимает файл. Тесты test_delete_removes_the_projection_file и test_archived_memory_leaves_the_projection. Путь удаления выводится из (kind, slug) и сверяется с ENTITY_DIRS — опечатка в kind не может привести к unlink произвольного пути. AC-4 ✓ РАТЧЕТ. test_every_projected_kind_is_exercised выводит покрытые кинд'ы из ИМЁН функций-мутаторов и требует равенства с state_serialize.ENTITY_DIRS. Защита от вырожденного прохода — test_registry_has_not_collapsed (>=5 и поимённо decisions/tasks). AC-5 ✓ FAIL-OPEN. test_export_failure_does_not_roll_back_the_write: export_one подменён на бросающий, epic_add отработал, строка в БД есть, файла нет, исключение не всплыло. AC-6 ✓ ДОКУМЕНТАЦИЯ. CHANGELOG EN+RU: претензия «task done, decide, memory add» исправлена на фактическую (запись в [Unreleased], не отгружена — правка на месте законна), добавлена отдельная запись о смене контракта brain. docs/{ru,en}/team-state-in-git.md: новый раздел «Когда проекция обновляется» с таблицей по кинд'ам, явным исключением claim/unclaim и обоснованием, почему гарантия — свойство, а не перечень вызовов. doc constants --check OK, docs_lint clean. AC-7 ✓ НЕГАТИВ НА ЖИВОМ РЕПОЗИТОРИИ. `.tausik/tausik decide ... --task ...` (свежий процесс, ранее сломанная ветка) -> решение #204 появилось в tausik/decisions/ ДО какого-либо экспорта; последующий `state export` не добавил ни одного файла. До фикса тот же путь не давал файла вовсе. Побочно этим же прогоном вскрылось, что CLI исполняет .claude/scripts/ — гейт bootstrap drift поймал расхождение источника с деплоем и потребовал передеплоя, то есть отработал как задуман. AC-8 ✓ ЗАМЕР, не оценка. scratchpad/bench_hotpath.py на КОПИИ реальной БД, худший случай (задача v14b-defect-brain-decisions-empty, 21 запись журнала, документ 40 КБ): task_log 5.29 -> 26.55 мс/вызов, +21.25 мс (+401%). Причина названа: документ перерисовывается целиком ради сравнения с файлом. Принято: 26 мс на порядок ниже стоимости самого вызова CLI/MCP, а альтернатива — дефект. ПОБОЧНАЯ НАХОДКА, исправлена в этой же области: реестр проецируемых кинд'ов был объявлен ДВАЖДЫ и независимо — frozenset в state_export и кортеж в state_import, ничто их не сравнивало. Кинд, добавленный на одной стороне, писался бы и не читался (или наоборот). Сведён к одному определению state_serialize.ENTITY_DIRS, обе стороны выводятся из него, так что расхождение теперь структурно невозможно. ЛОЖНАЯ ТРЕВОГА, зафиксирована чтобы не искали снова: `mypy scripts/` печатает note про unused sections для модулей handlers*. Это следствие СУЖЕНИЯ области вызовом, а не устаревшего конфига — штатный `mypy` (files из pyproject: scripts + harness/claude/mcp/project) даёт Success, 314 файлов, без note.
- 2026-07-28T18:16:54Z [implementation] — AC-1 ✓ Свойство: test_projection_tracks_db_after_every_mutation сверяет дерево с build_tree(БД) побайтово после каждой группы мутаций, без ручного экспорта. Фальсифицируемость доказана: на коде из HEAD падают 3 теста из 6 (прогон с подменой файлов на версии HEAD и обратной установкой). AC-2 ✓ Все пять кинд'ов ENTITY_DIRS покрыты, ~20 мутаторов вместо прежних двух. AC-3 ✓ Удаление: _remove_projection снимает файл при export_one -> None; тесты test_delete_removes_the_projection_file, test_archived_memory_leaves_the_projection; путь сверяется с ENTITY_DIRS, поэтому опечатка в kind не даёт unlink произвольного пути. AC-4 ✓ Рэтчет: test_every_projected_kind_is_exercised выводит покрытие из имён мутаторов и требует равенства с реестром; защита от вырожденного прохода — test_registry_has_not_collapsed. AC-5 ✓ fail-open: test_export_failure_does_not_roll_back_the_write — при бросающем export_one строка в БД есть, вызов не упал. AC-6 ✓ CHANGELOG EN+RU (претензия исправлена на месте, запись в [Unreleased], плюс отдельная запись о контракте brain) и docs/{ru,en}/team-state-in-git.md (раздел «Когда проекция обновляется»); doc constants --check OK, docs_lint clean. AC-7 ✓ Негатив на живом репозитории: decide --task через CLI дал файл в tausik/decisions/ ДО экспорта, последующий state export не добавил ничего. AC-8 ✓ Замер на копии реальной БД: task_log 5.29 -> 26.55 мс (+401%) на худшем случае; полный pytest 6472 passed / 24 skipped / 0 failed; ruff clean; mypy Success 314 файлов.
- 2026-07-28T18:17:19Z [done] — Negative: негативные сценарии прогнаны как ПРОВЕРКИ ОТСУТСТВИЯ, а не наличия. (1) Отсутствие расхождения — на живом репозитории после мутации через CLI `state export` не порождает диффа; ДО фикса тот же путь давал непустой дифф, что и является доказательством работоспособности негативного пути, а не предположением о ней. (2) Отсутствие файла-призрака — test_delete_removes_the_projection_file и test_archived_memory_leaves_the_projection требуют ОТСУТСТВИЯ файла после удаления и после архивации; до фикса файл оставался. (3) Отсутствие отката при сбое — test_export_failure_does_not_roll_back_the_write подменяет export_one на бросающий и требует, чтобы строка в БД ОСТАЛАСЬ, вызов не упал, а файл не появился. (4) Отсутствие вырожденного прохода — test_registry_has_not_collapsed падает, если ENTITY_DIRS схлопнется ниже пяти; без него рэтчет и свойство стали бы тавтологически зелёными на пустом реестре. (5) Отсутствие ложной зелени самого свойства — проверено подменой всех пяти изменённых модулей на версии из HEAD: падают 3 теста из 6, после обратной установки все 6 зелёные. Domain: результат осмыслен вне тестов и проверен на реальных данных, а не только на tmp-фикстурах. Проекция — не абстракция: это то, что коллега видит после `git pull`. Проверка выполнена на боевом репозитории с БД в 40 МБ и деревом из 2078 файлов: решение #204, записанное штатной командой `.tausik/tausik decide --task`, появилось в `tausik/decisions/` немедленно и в том же виде, в каком его строит полный экспорт (последующий `state export` не переписал ни байта — идемпотентность на живых данных, а не на синтетике). Замер стоимости тоже сделан на КОПИИ реальной БД и на реально самой длинной задаче проекта, а не на сконструированном худшем случае. Обратная сторона проверена там же: гейт bootstrap drift поймал, что источник разошёлся с исполняемыми копиями, то есть система отказалась считать правку доехавшей до пользователя, пока она туда не доехала.
