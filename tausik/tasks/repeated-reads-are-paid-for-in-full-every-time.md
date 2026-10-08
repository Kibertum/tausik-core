---
slug: repeated-reads-are-paid-for-in-full-every-time
title: "Повторное чтение файла оплачивается полностью каждый раз: хук про раздутый вывод только советует"
status: done
epic: release-19-agent-effectiveness
story: context-carries-over-between-sessions
complexity: medium
role: backend
stack: null
tier: moderate
call_budget: 45
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/hooks/read_ledger.py"
  - "scripts/hooks/read_ledger_gate.py"
  - "scripts/service_token_metrics.py"
  - "scripts/service_token_metrics_render.py"
  - "bootstrap/bootstrap_hooks.py"
  - "bootstrap/bootstrap_qwen.py"
  - "tests/test_read_ledger.py"
  - README.md
  - README.ru.md
  - "docs/ru/hooks.md"
  - "docs/en/hooks.md"
  - "docs/_generated/constants.json"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - ROADMAP.md
scope_paths:
  - "scripts/hooks/read_ledger.py"
  - "scripts/hooks/read_ledger_gate.py"
  - "scripts/service_token_metrics.py"
  - "scripts/service_token_metrics_render.py"
  - "bootstrap/"
  - "tests/"
  - "docs/"
  - README.md
  - README.ru.md
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-09-07T18:15:35Z"
resolution: null
resolution_reason: null
tracker_refs: []
started_model_id: null
started_model_version: null
done_model_id: null
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

Повторное чтение неизменившегося файла в пределах сессии не стоит полного контекста, и экономия измерена, а не заявлена.

## Acceptance Criteria

1. Read-ledger на PreToolUse для Read: сессионная таблица (path, content_hash, mtime, call_no). Файл не менялся с прошлого чтения ЭТОЙ сессии — deny с сообщением «не изменён с вызова #N, содержимое уже в контексте». Механизм deny у нас освоен: memory_pretool_block и git_push_gate работают так же.
2. Сравнение по mtime И content_hash, а не по одному из них: mtime врёт при чекауте, hash дорог на больших файлах — вместе они снимают главный класс ложных отказов.
3. Строго opt-in, по умолчанию ВЫКЛЮЧЕНО.
4. Экономия считается и пишется в существующие метрики токенов (posttool_usage уже пишет usage). Заявление об экономии без счётчика ЗАПРЕЩЕНО.
5. ГЛАВНЫЙ РИСК, спроектировать ДО кода: содержимое могло выпасть из контекста после compaction, и тогда deny — это тихий обрыв данных, то есть ровно тот дефект, который фреймворк объявил нетерпимым. Смягчение: окно из N последних вызовов, за пределами окна пропускаем; аварийный обход назван прямо в тексте deny. Если окно не удаётся обосновать числом — задача закрывается как dead end, а не выпускается на авось.
6. Не тащить внешний бинарь как зависимость: у ядра ноль зависимостей, а проект-образец подостыл (последний пуш два месяца назад). Свой механизм на stdlib.
7. НЕГАТИВНЫЙ сценарий: тест на изменившийся файл — второе чтение обязано ПРОЙТИ. Тест на compaction-сценарий — чтение за пределами окна обязано пройти.
8. НЕГАТИВНЫЙ сценарий: при выключенной опции ни одного лишнего вызова и ни одной записи в ledger; проверяется прогоном, а не чтением кода.

## Plan

## Rollback

git revert коммита; механизм opt-in и по умолчанию выключен

## Journal

- 2026-09-07T17:48:19Z [implementation] — ЗАМЕР ДО КОДА, СМЕНА #229, ВСЕ 42 ТРАНСКРИПТА ПРОЕКТА. AC5 требует обосновать окно числом или закрыть задачу как dead end — числа получены, и они меняют не окно, а ОЦЕНКУ ЦЕННОСТИ механизма. ЧЕРЕЗ ИНСТРУМЕНТ Read: 285 вызовов с путём на весь корпус. Повторов пути в том же разговоре 111 (38.9%), из них 43 после правки файла (законные). Кандидатов на экономию — 68, то есть 23.9% чтений. ПОТОЛОК ВЫИГРЫША ПО Read ЖЁСТКИЙ И МАЛЫЙ. Прибор релиза относит Read 370 213 токенов прироста контекста из 17 896 506 — 2.07%. Значит даже полное устранение ВСЕХ чтений через Read дало бы 2.07%, а цель предложенного механизма (68 из 285) — около 88 332 токенов, то есть 0.49%. Для сравнения Bash даёт 66.4%. КОРПУС СМЕЩЁН, И СМЕЩЕНИЕ ИЗМЕРЕНО, А НЕ ПРЕДПОЛОЖЕНО. Этот харнесс велит агенту читать файлы через Bash (cat/sed -n/head), а не инструментом Read. Разбор 10 024 вызовов Bash даёт 2196 НАСТОЯЩИХ чтений файла — то есть 88% чтений идут мимо Read. Повторов 754, из них без правки между чтениями 604. ПЕРВАЯ ВЕРСИЯ ЭТОГО ЗАМЕРА БЫЛА НЕВЕРНА, И ОШИБКА ТА САМАЯ, ЧТО Я ИЩУ В ДРУГИХ. Я считал вхождение слова head в команду и получил 8477 «чтений» из 10 024 (84.6%). Но `| head -20` — это КРЫШКА на чужой вывод, а не чтение файла. Проверялось НАЛИЧИЕ ИМЕНИ, а не факт. После уточнения (глагол должен стоять в начале команды и брать путь аргументом, а не после конвейера) осталось 2196. ОКНО ОБОСНОВАНО ЧИСЛОМ, КАК ТРЕБУЕТ AC5. Разрыв между повторами: по Read медиана 4, p75 58, p90 187; по Bash медиана 6, p75 37, p90 148. Окно в 20 вызовов покрывает 69.4% повторов Read и 65.6% повторов Bash, окно в 50 — 73.9% и 78.5%. То есть окно не выдумывается: две трети повторов происходят в пределах двадцати вызовов, и остаток за окном пропускается, чем и снимается риск compaction. СЛЕДСТВИЕ ДЛЯ ПРОЕКТИРОВАНИЯ. Механизм, описанный в AC1 (ledger + deny на PreToolUse для Read), покрывает 0.28-0.49% прироста. Настоящая величина повторных чтений около 3.1% (604 повтора Bash по медиане 848 токенов плюс 68 повторов Read), но 88% её течёт через Bash, где deny потребовал бы РАЗБОРА ПРОИЗВОЛЬНОЙ КОМАНДЫ ОБОЛОЧКИ для решения о блокировке. У проекта уже есть заблокированная задача write-gate-reads-prose-arguments-as-redirections — доказательство, что разбор оболочки ради гейта здесь ошибается. Поэтому строится РОВНО то, что заказано (Read), а не то, что соблазнительно, и потолок построенного называется числом, а не замалчивается.
- 2026-09-07T18:06:41Z [implementation] — AC-1 (ledger на PreToolUse для Read, deny по образцу memory_pretool_block): ✓ tests/test_read_ledger.py::TestOffByDefaultMeansNothingHappens::test_when_on_it_denies_the_second_identical_read AC-2 (mtime И content_hash, а не один из них): ✓ tests/test_read_ledger.py::TestMtimeAndHashAreBothConsulted::test_same_hash_but_different_mtime_counts_as_unchanged AC-2: ✓ tests/test_read_ledger.py::TestMtimeAndHashAreBothConsulted::test_same_mtime_but_different_hash_counts_as_changed AC-2: ✓ tests/test_read_ledger.py::TestMtimeAndHashAreBothConsulted::test_one_side_unhashed_is_not_demonstrated AC-3 (строго opt-in, по умолчанию ВЫКЛЮЧЕНО): ✓ tests/test_read_ledger.py::TestOffByDefaultMeansNothingHappens::test_absent_config_is_off AC-4 (экономия считается, заявление без счётчика запрещено): ✓ tests/test_read_ledger.py::TestTheSavingIsCountedNotClaimed::test_each_refusal_increments_a_counter_in_the_ledger — счётчик выводится в tausik metrics tokens, и там же прямо сказано, что СТОИМОСТЬ отказанного чтения НЕ оценивается AC-5 (окно обосновано числом; за окном пропускаем; обход назван в тексте deny): ✓ tests/test_read_ledger.py::TestTheWindowIsAMeasuredNumber::test_the_default_window_matches_what_was_measured — в тесте закреплена и сама арифметика покрытия, чтобы правка окна не оставила обоснование позади AC-5: ✓ tests/test_read_ledger.py::TestTheDecisionRefusesOnlyWhatItCanProve::test_beyond_the_window_passes AC-5: ✓ tests/test_read_ledger.py::TestOffByDefaultMeansNothingHappens::test_the_override_lets_one_call_through_and_says_so AC-6 (без внешних зависимостей, свой механизм на stdlib): ✓ scripts/hooks/read_ledger.py импортирует только hashlib, json, os, sys, typing — стандартную библиотеку AC-7 (негативный: изменившийся файл ПРОХОДИТ; за окном ПРОХОДИТ): ✓ tests/test_read_ledger.py::TestOffByDefaultMeansNothingHappens::test_a_changed_file_is_allowed_on_the_second_read AC-7: ✓ tests/test_read_ledger.py::TestTheDecisionRefusesOnlyWhatItCanProve::test_a_changed_file_passes AC-8 (при выключенной опции ни одного лишнего вызова и ни одной записи; прогоном, а не чтением кода): ✓ tests/test_read_ledger.py::TestOffByDefaultMeansNothingHappens::test_when_off_no_ledger_file_is_ever_created — три прогона настоящего хука подпроцессом, файл ledger не создаётся Negative: каждая неопределённость решается в пользу ПРОПУСКА, и это проверено поштучно, а не заявлено. Нет отпечатка — пропуск. Файла нет в ledger — пропуск. Файл изменился — пропуск. Расстояние за окном — пропуск. Частичное чтение (offset/limit) — пропуск, потому что срез в контекст и не попадал. Чужой инструмент — не трогаем. Испорченный stdin (пустой, не-JSON, список, без tool_input) — код 0, вызов не сломан. Граница окна проверена с обеих сторон: расстояние 20 отказывает, 21 пропускает. Отдельно проверено, что запрет НЕ стена: переменная TAUSIK_READ_LEDGER_OVERRIDE названа в самом тексте отказа и действительно пропускает вызов. Domain: механизм осмыслен вне тестов, и его ПОТОЛОК назван числом, а не умолчан. Read даёт 2.07% прироста контекста, значит устранение всех чтений через Read дало бы 2.07%, а этот механизм целится в 0.49%. Настоящая величина повторных чтений около 3.1%, но 88% её течёт через Bash (2196 чтений файла внутри команд против 285 через инструмент Read), и покрыть её значило бы блокировать вызов после разбора произвольной оболочки — у проекта есть открытый дефект write-gate-reads-prose-arguments-as-redirections, доказывающий, что этот разбор здесь ошибается. Поэтому построено ровно заказанное, а не соблазнительное, и граница записана в docstring модуля, в шапке теста и в CHANGELOG. Попутно исправлена собственная ошибка замера: первая версия считала вхождение слова head и давала 84.6% «чтений», тогда как `| head -20` — это крышка на чужой вывод, а не чтение файла; после уточнения осталось 2196 из 10 024.
