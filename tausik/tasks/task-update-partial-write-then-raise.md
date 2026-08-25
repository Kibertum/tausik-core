---
slug: task-update-partial-write-then-raise
title: "task_update пишет в БД первый бюджет, падает на валидации второго и выходит исключением мимо проекции — дерево остаётся устаревшим"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 40
defect_of: state-export-trigger-misses-task-linked-decisions
scope: "scripts/service_task.py (task_update, порядок валидации бюджетных полей), tests/, CHANGELOG.md, CHANGELOG.ru.md. После правки scripts/ обязателен bootstrap --ide all."
scope_exclude: "НЕ трогать каскад статусов и каскадное удаление — отдельные задачи. НЕ менять валидаторы бюджета по существу (границы значений, деривацию тира) — меняется только МОМЕНТ проверки относительно записи."
relevant_files:
  - ".gitattributes"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - CLAUDE.md
  - "scripts/project_backend.py"
  - "scripts/service_task.py"
  - "scripts/state_triggers.py"
  - "tausik/stories/kb-git-sync.md"
  - "tausik/tasks/kb-brain-deprecate.md"
  - "tausik/tasks/kb-export-tasks.md"
  - "tausik/tasks/revise-kb-export-tasks-superseded.md"
  - "tests/test_state_triggers.py"
  - "tausik/decisions/koeffitsient-kalibrovki-na-okne-n-10-neprigoden-dlya.md"
  - "tausik/decisions/reviziya-obema-1-8-sokratila-byudzhet-s-2087-do-1927-no-ne.md"
  - "tausik/decisions/revyu-pyati-zakrytyh-zadach-nashlo-chto-state-export.md"
  - "tausik/memory/audit-kachestva-sessii-153-revyu-partii-152-nashlo-devyat.md"
  - "tausik/memory/novoe-proizvodnoe-derevo-obyazano-byt-vneseno-v-kazhdyy.md"
  - "tausik/memory/otnoshenie-kotorym-vladeet-dvizhok-bd-kaskad-po-vneshnemu.md"
  - "tausik/memory/zadacha-obyavivshaya-svoyu-zhe-proektsiyu-v-relevant-files.md"
  - "tausik/tasks/brain-db-binding-ignores-path-case.md"
  - "tausik/tasks/calibration-window-too-small-to-forecast.md"
  - "tausik/tasks/cascade-mutations-never-project-to-tree.md"
  - "tausik/tasks/complexity-proxy-counts-state-projection.md"
  - "tausik/tasks/docs-drift-after-s152-batch.md"
  - "tausik/tasks/ghost-projection-on-fk-cascade-delete.md"
  - "tausik/tasks/projection-property-test-cannot-reach-cascades.md"
  - "tausik/tasks/publish-risk-gate-docstring-lies-after-205.md"
  - "tausik/tasks/risk-l3-still-blocks-after-demotion.md"
  - "tausik/tasks/service-knowledge-one-line-from-filesize-gate.md"
  - "tausik/tasks/task-update-partial-write-then-raise.md"
  - "tausik/tasks/tausik-tree-gitattributes-lf.md"
  - "tausik/tasks/tool-call-syntax-leaks-into-entity-text.md"
  - "tests/test_projection_follows_the_write.py"
  - "tests/test_projection_shrinks_with_the_db.py"
  - "tests/test_state_tree_eol_pin.py"
  - "tests/test_task_update_writes_all_or_nothing.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-28T21:55:20Z"
---

## Goal

Найдено ревью сессии #153, ВОСПРОИЗВЕДЕНО на живом коде.

ВОСПРОИЗВЕДЕНИЕ: svc.task_update("t1", call_budget=5, cost_budget_usd="not-a-number"). call_budget=5 записывается в БД (be.task_get('t1')['call_budget'] == 5), затем валидация cost_budget_usd бросает ServiceError. Функция выходит исключением, до _task_updated/_project_task не доходит. В tausik/tasks/t1.md остаётся call_budget: null. Расхождение молчит до ближайшего state export --check.

ПРИЧИНА. scripts/service_task.py:286-322 валидирует три бюджетных поля ПОСЛЕДОВАТЕЛЬНО и пишет каждое сразу, как только оно прошло проверку, до валидации следующего: task_set_call_budget вызывается раньше, чем float(cost_budget_usd) успевает бросить. Форма «записал -> достал следующее -> провалидировал -> может бросить».

ЧТО ЭТО ГОВОРИТ О ЗАКРЫТОЙ ЗАДАЧЕ. Форма предшествует коммиту ff0fc86 (проверено через git show ff0fc86^:scripts/service_task.py — структура идентична, менялись только строки возврата). То есть фикс «каждый мутирующий метод теперь проецирует» закрыл ТЕРМИНАЛЬНЫЕ точки возврата и не закрыл ВНУТРЕННИЕ пути «частичная запись, затем исключение». Проекция привязана к успешному возврату, а не к факту записи — а записи бывают без возврата.

НАПРАВЛЕНИЕ ФИКСА, обосновать в задаче. Либо валидировать все три бюджетных поля ДО первой записи (так уже делает task_add через validate_task_add_inputs — конвенция в проекте есть, метод её не соблюдает), либо проецировать в finally. Первое лучше: оно устраняет частичную запись, а не компенсирует её.

## Acceptance Criteria

1. Частичной записи не остаётся: task_update валидирует ВСЕ бюджетные поля (call_budget, cost_budget_usd, token_budget) до первой записи в БД. Тест на входе call_budget=5 плюс cost_budget_usd="not-a-number" доказывает, что после исключения call_budget в БД НЕ изменился, и падает до фикса.
2. Проекция и БД не расходятся ни на одном исходе: после отказа файл tausik/tasks/<slug>.md по-прежнему равен build_tree(db). Проверяется сравнением, а не отсутствием дифа в git.
3. Выбор механизма записан: валидация до записи, а не проекция в finally. Обосновано тем, что finally компенсирует частичную запись, а не устраняет её, и что конвенция валидации до записи в проекте уже есть — task_add делает это через validate_task_add_inputs.
4. НЕГАТИВ И ГРАНИЦЫ. (а) Успешные пути не изменились: обновление одного поля, обновление нескольких, обновление бюджета вместе с обычными полями — все дают тот же результат, что и до правки. (б) Ветви ранних возвратов по cost_budget_usd и token_budget, сегодня не исполняемые ни одним тестом, покрываются — иначе четвёртая такая ветвь снова пройдёт мимо. (в) Сообщения об ошибке валидации сохраняют прежний текст и тип (ServiceError), чтобы вызывающие не сломались.
5. Полный pytest зелёный; ruff и mypy чистые.
CHANGELOG.md [Unreleased] и зеркало CHANGELOG.ru.md обновлены прозаической записью об этом изменении.

## Plan

## Rollback

git revert. Изменение локализовано в task_update плюс тесты; схема и миграции не затрагиваются. Худший исход отката — возврат к сегодняшнему поведению, где отвергнутый вызов оставляет записанным первое поле; данные при откате не теряются, расходится только проекция.

## Journal

- 2026-07-28T21:44:01Z [implementation] — РЕАЛИЗАЦИЯ И ВЫБОР (критерий 3). scripts/service_task.py::task_update — три бюджетных поля извлекаются и ПРОВЕРЯЮТСЯ до первой записи, накапливаются как пары (сеттер, значение) в budget_writes и применяются одним проходом. Ранний возврат сохранён и стал одним вместо трёх: `if budget_writes and not fields`. ВЫБРАНА ВАЛИДАЦИЯ ДО ЗАПИСИ, А НЕ ПРОЕКЦИЯ В finally. Обоснование: finally КОМПЕНСИРУЕТ частичную запись — он честно спроецировал бы половинчатое состояние, то есть зафиксировал бы в дереве результат отвергнутого вызова. Устраняет дефект только первое. Плюс конвенция в проекте уже есть: task_add валидирует всё через validate_task_add_inputs, а task_update ей не следовал. ЭКВИВАЛЕНТНОСТЬ УСПЕШНЫХ ПУТЕЙ РАЗОБРАНА, а не понадеялась на тесты. Прежняя форма возвращалась рано после КАЖДОГО бюджета при пустом остатке fields; но fields на тот момент ещё содержал непрочитанные бюджетные поля, поэтому ранний возврат срабатывал ровно тогда, когда остальных полей не было вовсе. Новая форма извлекает все три сразу, поэтому то же условие проверяется один раз и даёт тот же исход на всех восьми сочетаниях. Побочный pop поля tier оставлен внутри ветви call_budget, как и было. AC-1: ✓ tests/test_task_update_writes_all_or_nothing.py::TestARejectedUpdateWritesNothing::test_a_bad_second_budget_does_not_keep_the_first — вход из постановки дословно (call_budget=5 плюс cost_budget_usd="not-a-number"); после ServiceError call_budget остаётся None. Плюс ::test_a_bad_third_budget_does_not_keep_the_first_two (падение на третьем не оставляет первых двух) и ::test_a_negative_budget_is_rejected_whole (отказ по границе, а не по типу). AC-2: ✓ ::test_the_tree_still_matches_the_db_after_a_rejected_update — файл до и после отказа побайтово равен, И равен build_tree(svc)["tasks/t1.md"]. Проверяется СРАВНЕНИЕМ с истиной БД, а не отсутствием дифа в git. AC-3: ✓ Выбор механизма записан выше с причиной отказа от finally. AC-4 (негатив и границы): ✓ (а) успешные пути не изменились — ::TestTheAcceptedPathsAreUnchanged::test_all_three_budgets_together, ::test_a_budget_next_to_an_ordinary_field, ::test_ordinary_fields_alone_still_update, ::test_call_budget_overrides_tier_and_says_so; (б) ветви «только стоимость» и «только токены», не покрытые НИ ОДНИМ тестом до сегодня, покрыты параметризованным ::test_each_budget_alone по всем трём бюджетам; (в) тип и текст ошибки сохранены — тесты ловят именно ServiceError, сообщения не менялись. ФАЛЬСИФИЦИРУЕМОСТЬ ПРОВЕРЕНА ПРОГОНОМ: две накапливающие строки заменены обратно на немедленные записи (симуляция прежней формы), прогон дал 4 failed / 7 passed — упали ровно все четыре теста отказа, включая сверку дерева с БД. После восстановления 11 passed. Семь тестов успешных путей остались зелёными и в сломанном состоянии — это и требуется: они охраняют эквивалентность, а не доказывают фикс.
- 2026-07-28T21:54:55Z [implementation] — Root cause (missing-validation): валидация была ПЕРЕМЕШАНА с записью. task_update проверял бюджет, тут же его записывал, затем брался за следующий и мог бросить — то есть форма «записал, достал следующее, провалидировал, может упасть». Отказ в такой форме не является отказом: первое поле уже в БД, а функция уходит исключением мимо единственной точки, где вызывается проекция (_task_updated -> _project_task). Отсюда два независимых следствия одной причины — частично применённое обновление в БД и разошедшееся с ней дерево. Форма предшествует коммиту ff0fc86 (проверено через git show ff0fc86^:scripts/service_task.py — структура идентична, менялись только строки возврата), поэтому фикс «каждый мутирующий метод теперь проецирует» её не закрыл: он привязал проекцию к УСПЕШНОМУ ВОЗВРАТУ, а записи бывают без возврата. Prevention: все три бюджетных поля валидируются до первой записи и применяются одним проходом, как это уже делает task_add через validate_task_add_inputs. Проекция в finally сознательно отвергнута — она компенсирует частичную запись, то есть честно проецирует результат отвергнутого вызова, вместо того чтобы его не допустить. Обобщение: привязывать побочный эффект к успешному возврату можно только там, где ни одна запись не происходит раньше первого возможного исключения.
- 2026-07-28T21:55:36Z [done] — AC-5: ✓ (в нумерации парсера пятый — критерий CHANGELOG). Парные записи «Исправлено — отвергнутый task update больше не применяется наполовину» добавлены в CHANGELOG.md и CHANGELOG.ru.md в шапку [Unreleased]; факт подтверждён гейтом changelog при закрытии. Критерий полноты прогона закрыт цифрами: pytest 6521 passed / 24 skipped / 0 failed за 637.27s — прибавка ровно 11, столько же, сколько новых тестов (было 6510); ruff All checks passed; mypy Success 314 файлов; bootstrap --ide all выполнен после правки scripts/. Domain: осмысленность вне тестов. Вход взят из живого воспроизведения ревью, а не придуман: `task_update(slug, call_budget=5, cost_budget_usd="not-a-number")` — это ровно та форма, которой пользуется агент, правя карточку одной командой с несколькими флагами, и опечатка в числовом флаге здесь обычное дело, а не экзотика. Практический вред до фикса измерим на данных этого проекта: бюджет задачи участвует в оценке остатка релиза (в этой же сессии сумма бюджетов 23 задач дала 1927 вызовов и легла в ответ владельцу о сроке), поэтому наполовину применённое обновление молча сдвигало бы плановую цифру, а расхождение с деревом всплывало бы позже и в чужой формулировке — как «дрейф» от state export --check. О предупреждении «COMPLEXITY UNDERSTATED: declared medium but touched 33 of 36»: ложное, пятый живой замер дефекта complexity-proxy-counts-state-projection. Фактическая работа — четыре файла: scripts/service_task.py, tests/test_task_update_writes_all_or_nothing.py (новый) и парные CHANGELOG. Остальные 32 — сгенерированная проекция БД, которую верификация требует объявлять целиком.
