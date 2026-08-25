---
slug: task-update-half-applies-when-acl-rejects
title: "task update ВСЁ ЕЩЁ применяется наполовину: бюджеты пишутся, затем валидатор ACL двумя строками ниже бросает исключение"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: moderate
call_budget: 35
defect_of: task-update-partial-write-then-raise
scope: "scripts/service_task.py, tests/test_task_update_writes_all_or_nothing.py, tests/test_state_projection_tracks_db.py, CHANGELOG.md, CHANGELOG.ru.md"
scope_exclude: null
relevant_files:
  - "scripts/service_task.py"
  - "tests/test_task_update_writes_all_or_nothing.py"
  - "tests/test_state_projection_tracks_db.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-08-01T12:05:29Z"
---

## Goal

Найдено ревью сессии #154, ВОСПРОИЗВЕДЕНО ЖИВЫМ ПРОГОНОМ пятью независимыми ревьюерами и повторно мной. Это тот же дефект, который задача task-update-partial-write-then-raise (сессия #153) объявила закрытым. Она его СУЗИЛА, но не закрыла.

ЧТО ПОЧИНИЛИ В #153. Три бюджетных поля валидируются ДО первой записи — но только относительно ДРУГ ДРУГА. Далее идёт `for setter, value in budget_writes: setter(slug, value)` (scripts/service_task.py:325-326), и записи уходят в БД немедленно: task_set_call_budget и соседи пишут через self._ex (scripts/backend_crud.py:253-297), а task_update не открывает транзакцию вовсе.

ЧТО ОСТАЛОСЬ. Сразу ПОСЛЕ цикла записи стоит следующий валидатор — normalize_acl_json по ACL_FIELDS (scripts/service_task.py:331-336), и он бросает. Форма та же, исход тот же.

ЖИВОЙ ЗАМЕР (мой, на временной БД с включённым auto_export):
  db  before: None | file before: call_budget: null
  svc.task_update("t1", call_budget=40, scope_paths="{not-json") -> ServiceError: scope_paths: not valid JSON
  db  after: call_budget=40, tier=moderate
  file after: call_budget: null, tier: null
Строка изменилась, вызов сообщил об ошибке, выход по исключению прошёл мимо _task_updated и, значит, мимо проекции. Дополнительный ущерб: tier выведен и записан, хотя вызывающий его не называл.

ПОЧЕМУ ТЕСТ ЭТОГО НЕ ВИДИТ. tests/test_task_update_writes_all_or_nothing.py и операция _op_task_budget_rejected в порождаемом наборе сочетают бюджет ТОЛЬКО С БЮДЖЕТОМ. Ни один случай не сочетает валидный бюджет с невалидным ACL-полем, поэтому дыра невидима и новому набору тоже.

## Acceptance Criteria

1. НИ ОДНО поле не записано, если ЛЮБОЕ поле того же вызова отвергнуто. Проверяется не только на паре бюджет+ACL: валидация всех полей (бюджеты, enum'ы, ACL, title/goal) завершается ДО первой записи, либо весь task_update обёрнут в begin_tx/commit_tx/rollback_tx. Если выбрана транзакция — сказано в журнале, почему она предпочтена ранней валидации, с учётом того, что очередь отложенной проекции уже умеет откатываться (_pending_projection.clear в rollback_tx).
2. ПОБОЧНАЯ ЗАПИСЬ tier ТОЖЕ ЗАКРЫТА: отвергнутый вызов не оставляет tier, выведенный из call_budget. Сегодня остаётся (замер в цели: tier=moderate при отказе).
3. ТЕСТ КРАСНЫЙ ДО ФИКСА, и это доказано прогоном, а не рассуждением: случай «валидный бюджет + невалидное ACL-поле» добавлен в tests/test_task_update_writes_all_or_nothing.py; факт красноты до фикса записан в журнал с выводом.
4. ДЫРА ЗАКРЫТА И В ПОРОЖДАЕМОМ НАБОРЕ: операция _op_task_budget_rejected в tests/test_state_projection_tracks_db.py перестаёт сочетать бюджет только с бюджетом — добавляется сочетание с ACL-полем. Иначе свойство проекции снова не увидит класс, который дважды прошёл мимо него.
5. НЕГАТИВ: (а) успешный смешанный вызов (валидный бюджет + валидное ACL-поле) по-прежнему пишет ОБА поля и проецирует — фикс не превращается в отказ от смешанных вызовов; (б) существующие тесты task_update зелёные без правки ожиданий.
6. ПРОВЕРЕНО, ЧТО КЛАСС ЗАКРЫТ, А НЕ СУЖЕН ЕЩЁ РАЗ. В журнале перечислены ВСЕ точки после первой записи в task_update, способные бросить, и для каждой сказано, почему она больше не может оставить частичную запись. Именно отсутствие такого перечня в #153 позволило дефекту пережить собственную починку.
7. Полный pytest зелёный; ruff и mypy чистые.
CHANGELOG.md [Unreleased] и зеркало CHANGELOG.ru.md обновлены прозаической записью, в которой прямо сказано, что предыдущая запись о том же дефекте описывала более узкий случай.

## Plan

## Rollback

git revert

## Journal

- 2026-08-01T11:53:28Z [implementation] — Root cause (logic-error): в #153 чинили НАЙДЕННЫЙ ОТКАЗ, а не ФОРМУ, которая его порождает. Три бюджета сгруппировали относительно друг друга — и остановились ровно там, где кончался воспроизведённый случай. Следующий валидатор (normalize_acl_json) остался ПОСЛЕ записи бюджетов, и дефект пережил собственную починку в неизменном виде. Prevention: (а) вся валидация и нормализация — до первой записи; (б) записи обёрнуты в транзакцию, что закрывает и те точки отказа, которые валидацией не предупреждаются (неизвестная колонка в _update, отказ SQLite по FK, ошибка ввода-вывода); (в) AC-6 требует ПЕРЕЧИСЛИТЬ все точки после первой записи и объяснить каждую — именно отсутствие такого перечня позволило дефекту выжить. AC-6, ПЕРЕЧЕНЬ ВСЕХ ТОЧЕК ОТКАЗА ПОСЛЕ ПЕРВОЙ ЗАПИСИ, и почему ни одна больше не оставит половину. 1. normalize_acl_json по scope_paths/scope_tools — ПЕРЕНЕСЕНА ВЫШЕ записей. Не может сработать после них по построению. 2. safe_single_line по title/goal — перенесена выше; не бросает, но порядок теперь единообразен. 3. self.be.task_update(...) -> _update -> ValueError на колонке вне белого списка _TASK_FIELDS. ВАЛИДАЦИЕЙ НЕ ПРЕДУПРЕЖДАЕТСЯ (белый список живёт в бэкенде) — закрыто транзакцией. 4. sqlite3.IntegrityError на записи story_id с несуществующим FK. Тоже не предупреждается — закрыто транзакцией. 5. Ошибка ввода-вывода или блокировка БД между двумя setter'ами. Закрыто транзакцией. Проверка enum'ов (_update_enums) и guard_notes_overwrite стоят ДО первой записи и всегда стояли — поэтому в пробе случай invalid-enum остался зелёным, и это правильный результат, а не пропуск: он никогда не был частичной записью. Записываю прямо, чтобы перечень не выглядел полнее, чем он есть. ФАЛЬСИФИЦИРУЕМОСТЬ ДОКАЗАНА ПРОГОНОМ. Проба: записи бюджетов возвращены ВЫШЕ блока ACL, транзакция убрана. Результат — tests/test_task_update_writes_all_or_nothing.py: 4 failed, 13 passed (красные: acl-not-json, acl-other-field, unknown-column, и проверка совпадения дерева с БД). tests/test_state_projection_tracks_db.py: 8 failed, 6 passed — то есть дыру видит теперь и порождаемый набор. После отката пробы: 31 passed совместно. ЗАМЕР ЖИВОГО ПОВЕДЕНИЯ ПОСЛЕ ФИКСА (временная БД, auto_export включён): call_budget=40 + scope_paths="{not-json" -> raised; db call_budget=None tier=None call_budget=7 + cost_budget_usd=-1.0 -> raised; db call_budget=None tier=None call_budget=9 + nosuchfield=1 -> raised; db call_budget=None tier=None УСПЕШНЫЙ СМЕШАННЫЙ: call_budget=12 + scope_paths='["a.py"]' -> db 12/light/["a.py"], файл tier: light, call_budget: 12. До фикса первый случай давал db call_budget=40, tier=moderate при файле с null — то есть отвергнутый вызов писал и поле, которого вызывающий не называл.
- 2026-08-01T12:05:26Z [implementation] — AC-1 ✓ вся валидация и нормализация перенесена до первой записи, записи обёрнуты в begin_tx/commit_tx/rollback_tx (_write_update_atomically); выбор ОБОИХ средств обоснован в докстринге и журнале: валидация закрывает предупреждаемые отказы, транзакция — непредупреждаемые. AC-2 ✓ tier больше не остаётся после отказа — замер: db call_budget=None tier=None во всех трёх сценариях. AC-3 ✓ ПРОГОН ПРОБЫ: возврат к записи бюджетов выше блока ACL без транзакции -> tests/test_task_update_writes_all_or_nothing.py 4 failed, 13 passed; после отката 17 passed. AC-4 ✓ _op_task_budget_rejected теперь тянет отказ из пяти разных точек метода, а не только из бюджетов; при пробе порождаемый набор даёт 8 failed. AC-5 ✓ Negative: test_the_mixed_call_still_works_when_nothing_is_refused — успешный смешанный вызов пишет ОБА поля, выводит tier и проецирует; существующие 13 тестов без правки ожиданий. AC-6 ✓ перечень ВСЕХ пяти точек отказа после первой записи в журнале, с честной пометкой, что invalid-enum никогда не был частичной записью (проверка enum стоит до записей) — поэтому в пробе он остался зелёным. AC-7 ✓ полный pytest 6544 passed, 24 skipped, 0 failed; ruff чисто; ruff format чисто; mypy Success 294 files; bootstrap drift отсутствует. CHANGELOG EN+RU, обе записи прямо говорят, что предыдущая описывала более узкий случай. Domain: воспроизводится обычной командой CLI `task update --call-budget 40 --scope-paths '{not-json'` на живом проекте и оставляет расхождение, которое `state export --check` показывает как безымянный «дрейф».
