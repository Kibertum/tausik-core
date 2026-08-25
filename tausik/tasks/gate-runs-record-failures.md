---
slug: gate-runs-record-failures
title: "gate_runs не видит падений: запись прогона привязана к пригодности для кэша"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 40
defect_of: l26-gate-results-persist
scope: null
scope_exclude: "scripts/verify_cache.py и scripts/verify_recent_lookup.py (фильтр exit_code=0 корректен и является ровно тем, что делает правку безопасной — трогать нельзя), scripts/verify_run_record.py и scripts/gate_run_record.py (слой записи верен, чинится условие ВЫЗОВА выше по стеку), схема БД и миграции (структура не меняется), scripts/service_gates.py (потребитель), .claude/ и harness/ (генерируемые зеркала), skills.json (значения пинов требуют сетевой сверки)"
relevant_files:
  - "scripts/service_verification.py"
  - "scripts/project_cli_verify.py"
  - "scripts/gate_runner.py"
  - "bootstrap/bootstrap_vendor_integrity.py"
  - "bootstrap/bootstrap_vendor.py"
  - "tests/test_requirements_bounds.py"
  - "tests/test_gate_runs_failures.py"
  - "tests/test_service_verification.py"
scope_paths:
  - "scripts/service_verification.py"
  - "scripts/project_cli_verify.py"
  - "scripts/gate_runner.py"
  - "bootstrap/bootstrap_vendor_integrity.py"
  - "bootstrap/bootstrap_vendor.py"
  - "docs/ru/vendor-skills.md"
  - "docs/en/vendor-skills.md"
  - "tests/test_requirements_bounds.py"
  - "tests/test_gate_runs_failures.py"
  - "tests/test_service_verification.py"
  - "docs/_generated/constants.json"
  - README.md
  - README.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-07-18T22:42:57Z"
---

## Goal

ДЕФЕКТ В ТОЛЬКО ЧТО ПОСТАВЛЕННОЙ ФИЧЕ, найден adversarial-ревью сессии #117, подтверждён чтением кода лично.

ГЛАВНОЕ. service_verification.run_gates_with_cache вызывает record_run (а с ним record_gate_runs) только при `passed and cache_ok and has_real_pass` (service_verification.py:325). Условие смешивает ДВА разных вопроса: годится ли прогон в КЭШ и нужно ли его НАБЛЮДАТЬ. В результате упавший гейт с этого пути не попадает в gate_runs никогда, и центральный вопрос, ради которого таблица заведена — «как часто гейт реально блокирует и растёт ли доля падений» — с него неотвечаем. Путь используется через service_gates при auto_verify.

БЕЗОПАСНОСТЬ ПРАВКИ ПРОВЕРЕНА, а не предположена: обе выборки кэша фильтруют exit_code=0 — lookup_recent_for_task (verify_recent_lookup.py:51, `AND exit_code = 0`) и lookup_any_fresh_run_for_task («any fresh exit-zero row»). Поэтому запись прогона с exit_code=1 НЕ может быть засчитана кэшем как зелёная. Путь CLI (project_cli_verify.py:130) уже пишет безусловно с `exit_code=0 if passed else 1` — то есть безопасность такой записи в проекте уже доказана практикой, расходится только сервисный путь.

СОПУТСТВУЮЩИЕ НАХОДКИ ТОГО ЖЕ РЕВЬЮ, чинятся здесь же как однородная мелочь:
1. project_cli_verify.py не передаёт trigger= в record_run, поэтому у всех строк с пути CLI trigger=NULL — колонка, ради денормализации которой она заводилась, пуста.
2. gate_runner.py: ветка стек-скоупового пропуска добавляет результат из gate_stack_dispatch.skipped_result, где duration_ms нет. Две другие ветки его получили, эта пропущена — покрытие длительностей неполное.
3. bootstrap_vendor_integrity.digest_mismatch сравнивает sha чувствительно к регистру. hexdigest() всегда нижний, а ожидаемое значение правит человек: sha в верхнем регистре даст ложное «integrity check FAILED».
4. bootstrap_vendor.sync_deps на быстрой ветке up-to-date выходит ДО проверки дайджеста. Если sha256 добавили к уже вендоренной зависимости с неизменным ref, новый пин не проверяется без --force, а документация подаёт проверку как безусловную.

ОТДЕЛЬНО, поправка к ревьюеру: он счёл ошибку ruff E741 доказательством того, что задача не могла пройти чистый verify. Это неверно — ruff НЕ входит в набор гейтов проекта (verify: hadolint, pytest; task-done: filesize, renar_drift_*). Сама ошибка реальна и чинится, вывод о гейтах — нет.

## Acceptance Criteria

1. Прогон, в котором гейты РЕАЛЬНО запускались, записывается в verification_runs и gate_runs независимо от вердикта: падение фиксируется с exit_code=1, успех с 0. Пригодность для кэша (passed/cache_ok/has_real_pass) продолжает управлять ТОЛЬКО кэшированием, но больше не управляет наблюдаемостью.
2. Регрессия кэша исключена: прогон с exit_code=1 НЕ удовлетворяет verify-first. Проверяется тестом, а не рассуждением — записать падение, затем убедиться, что has_fresh_verify_run возвращает False.
3. Прогон, где гейтов не было вовсе (results пуст), по-прежнему не пишется — записывать нечего.
4. Синтетическая блокировка «no-test-mapped» (service_verification.py:305-319) остаётся блокирующей и не превращается молча в записанный зелёный.
5. project_cli_verify передаёт trigger в record_run на обеих точках вызова — колонка перестаёт быть NULL на пути CLI.
6. Все ветки gate_runner отдают duration_ms, включая стек-скоуповый пропуск через skipped_result.
7. Сравнение дайджеста нечувствительно к регистру с обеих сторон; ожидаемое значение из skills.json в верхнем регистре не даёт ложного отказа.
8. Быстрая ветка up-to-date: поведение приведено в соответствие с документацией. Либо объявленный sha сверяется с записанным в .lock без сети, либо оговорка про --force явно written в docs/{ru,en}/vendor-skills.md. Молчаливого расхождения кода и доков не остаётся.
9. Ошибка ruff E741 в tests/test_requirements_bounds.py устранена; `python -m ruff check` по всем файлам задачи чист.
10. Тесты: падающий прогон пишет строки gate_runs со статусом падения; агрегаты показывают ненулевые failures/blocking_failures; кэш не принимает падение; trigger не NULL; duration_ms присутствует во всех ветках; регистр sha не влияет.
11. Полный прогон pytest зелёный, гейт 400 строк не нарушен.

## Plan

## Rollback

git revert коммита. Изменения аддитивны и не трогают схему: записываются те же таблицы, что и раньше, шире по условию. Данных не мигрируем. Главный риск отката — возврат слепоты к падениям, а не поломка. Точечный откат при неожиданном росте объёма таблицы: вернуть условие записи к прежнему, оставив исправления trigger, duration_ms и регистра sha, которые от него независимы.

## Journal

- 2026-07-18T22:42:10Z [implementation] — AC-1: ✓ прогон с реально запускавшимися гейтами пишется независимо от вердикта, падение с exit_code=1 — tests/test_gate_runs_failures.py::TestFailuresAreRecorded::test_blocking_failure_lands_in_gate_runs AC-2: ✓ регрессия кэша исключена ТЕСТОМ, а не рассуждением: записанное падение не удовлетворяет verify-first — tests/test_gate_runs_failures.py::TestRecordedRunsAreNotReplayedAsGreen::test_failure_does_not_satisfy_verify_first AC-3: ✓ пустой набор результатов не пишется — наблюдать нечего — tests/test_gate_runs_failures.py::TestFailuresAreRecorded::test_no_gates_ran_records_nothing AC-4: ✓ синтетическая блокировка no-test-mapped сохранена и не стала записанным зелёным — tests/test_gate_runs_failures.py::TestRecordedRunsAreNotReplayedAsGreen::test_all_skipped_with_declared_files_still_blocks AC-5: ✓ trigger передаётся на обеих точках вызова CLI, колонка больше не NULL — tests/test_gate_runs_failures.py::TestTriggerAndDuration::test_trigger_is_persisted_not_null AC-6: ✓ duration_ms добавлен в третью ветку (стек-скоуповый пропуск), покрытие полное — tests/test_gate_runs_failures.py::TestTriggerAndDuration::test_duration_survives_to_the_row AC-7: ✓ сравнение дайджеста нечувствительно к регистру с обеих сторон — tests/test_vendor_lock_integrity.py::TestPureHelpers::test_no_expected_digest_is_not_a_mismatch AC-8: ✓ быстрая ветка up-to-date сверяет объявленный sha с записанным в .lock без сети; доки обеих локалей приведены в соответствие, дрейфа нет (exit 0) — tests/test_vendor_lock_integrity.py::TestLockBecomesMeaningful::test_matching_lock_short_circuits_without_network AC-9: ✓ ruff E741 устранён, `python -m ruff check tests/ scripts/ bootstrap/` — All checks passed — tests/test_requirements_bounds.py::TestUpperBounds::test_mcp_range_admits_the_version_we_ship_against AC-10: ✓ покрыты падение, агрегаты, отказ кэша, trigger, duration, регистр sha — tests/test_gate_runs_failures.py::TestFailuresAreRecorded::test_failure_shows_up_in_aggregates AC-11: ✓ полный прогон 4861 passed / 21 skipped / 0 failed; bootstrap_vendor.py 400, service_verification.py 369, gate_runner.py 338 — все под гейтом — tests/test_gate_runs_failures.py::TestFailuresAreRecorded::test_failed_run_is_recorded_with_nonzero_exit Negative: прогон, прошедший, но НЕ пригодный для кэша (все гейты пропущены, файлы не объявлены), обязан быть записан и при этом не давать попадания — exit_code там 0, поэтому охраняет префикс команды — tests/test_gate_runs_failures.py::TestRecordedRunsAreNotReplayedAsGreen::test_all_skipped_pass_does_not_satisfy_verify_first Negative: настоящий зелёный обязан по-прежнему давать попадание в кэш — иначе фикс сломал бы Verify-First — tests/test_gate_runs_failures.py::TestRecordedRunsAreNotReplayedAsGreen::test_real_pass_still_satisfies_verify_first Domain: до правки вопрос «как часто гейт реально блокирует» был неотвечаем именно для тех прогонов, ради которых таблица заводилась: сервисный путь писал только успешные и кэшируемые прогоны. Теперь блокировка попадает в gate_runs и в агрегаты. Безопасность правки не предполагалась, а проверена в коде: обе выборки кэша фильтруют exit_code=0 (verify_recent_lookup.py:51 и «any fresh exit-zero row»), а путь CLI уже годами пишет падения безусловно — то есть практика такой записи в проекте уже была, расходился только сервисный слой. Для прохода, который не годится в кэш при exit_code=0, введён префикс команды noncacheable|, который не матчится ни строгой выборкой (точное совпадение command), ни ослабленной (префикс trigger=verify|). Checklist: scope — ACL расширялся явно по мере обнаружения; тесты — 10 новых плюс два существующих теста приведены к заявленному контракту; security — security-чувствительный прогон теперь наблюдаем, но по-прежнему не переиспользуем (двойная защита: is_cache_allowed отказывает до запроса, плюс префикс команды); rollback — аддитивно, схема не тронута. НАХОДКА В ЧУЖИХ ТЕСТАХ, важная для оценки первопричины: test_cache_misses_on_red_run содержал ДВА противоречащих комментария — сначала «record_run still happens but exit_code != 0 → lookup_recent returns None» (описание ЗАМЫСЛА, ровно то, что я реализовал), затем «record_run is NOT called for red» (описание РЕАЛИЗАЦИИ), и утверждение было подогнано под второе. То есть тест писался под фактическое поведение, а не под намерение, и тем самым законсервировал дефект. Оба теста переписаны на заявленный контракт с сохранением главной проверки — отсутствия попадания в кэш. ПОПРАВКА К РЕВЬЮЕРУ, заявляю явно: он счёл ошибку ruff доказательством того, что задача pin-mcp-major-bound не могла пройти чистый verify. Это неверно — ruff НЕ входит в набор гейтов проекта (verify: hadolint, pytest; task-done: filesize, renar_drift_*), что проверено через get_gates_for_trigger. Сама ошибка реальна и исправлена, вывод о гейтах — нет. Отдельно: его тревога про отсутствие фильтра exit_code была снята чтением verify_recent_lookup.py — фильтр есть, и именно он делает правку безопасной.
- 2026-07-18T22:42:28Z [implementation] — Root cause (logic-error): одно условие 'passed and cache_ok and has_real_pass' управляло ДВУМЯ независимыми вопросами — годится ли прогон для переиспользования из кэша и нужно ли его записать для наблюдаемости. Условие писалось для первого (не кэшировать all-skipped как проверенное), а второе получило его как побочный эффект, из-за чего падения гейтов не записывались никогда и главный вопрос новой таблицы стал неотвечаем именно на тех прогонах, ради которых она заведена. Prevention: при добавлении наблюдаемости к существующему коду проверять, не привязана ли запись к условию, введённому для другой цели; признак — булево, чьё имя (cacheable) не совпадает с тем, что оно охраняет (recorded). Тест, фиксирующий 'строк нет', обязан объяснять ПОЧЕМУ их нет — здесь комментарий теста описывал замысел 'записываем, но exit_code!=0 не даёт попадания', а утверждение проверяло противоположное, и расхождение между комментарием и assert законсервировало дефект.
- 2026-07-18T22:42:56Z [implementation] — AC-1: ✓ прогон с реально запускавшимися гейтами пишется независимо от вердикта — tests/test_gate_runs_failures.py::TestFailuresAreRecorded::test_blocking_failure_lands_in_gate_runs AC-2: ✓ записанное падение НЕ удовлетворяет verify-first, проверено тестом — tests/test_gate_runs_failures.py::TestRecordedRunsAreNotReplayedAsGreen::test_failure_does_not_satisfy_verify_first AC-3: ✓ пустой набор результатов не пишется — tests/test_gate_runs_failures.py::TestFailuresAreRecorded::test_no_gates_ran_records_nothing AC-4: ✓ синтетическая блокировка no-test-mapped сохранена — tests/test_gate_runs_failures.py::TestRecordedRunsAreNotReplayedAsGreen::test_all_skipped_with_declared_files_still_blocks AC-5: ✓ trigger не NULL на пути CLI — tests/test_gate_runs_failures.py::TestTriggerAndDuration::test_trigger_is_persisted_not_null AC-6: ✓ duration_ms во всех трёх ветках gate_runner — tests/test_gate_runs_failures.py::TestTriggerAndDuration::test_duration_survives_to_the_row AC-7: ✓ сравнение sha нечувствительно к регистру — tests/test_vendor_lock_integrity.py::TestPureHelpers::test_no_expected_digest_is_not_a_mismatch AC-8: ✓ быстрая ветка сверяет пин с .lock без сети, доки обеих локалей синхронны (drift exit 0) — tests/test_vendor_lock_integrity.py::TestLockBecomesMeaningful::test_matching_lock_short_circuits_without_network AC-9: ✓ ruff чист по tests/ scripts/ bootstrap/ — tests/test_requirements_bounds.py::TestUpperBounds::test_mcp_range_admits_the_version_we_ship_against AC-10: ✓ падения, агрегаты, отказ кэша, trigger, duration, регистр — tests/test_gate_runs_failures.py::TestFailuresAreRecorded::test_failure_shows_up_in_aggregates AC-11: ✓ 4861 passed / 21 skipped / 0 failed, все файлы под гейтом 400 — tests/test_gate_runs_failures.py::TestFailuresAreRecorded::test_failed_run_is_recorded_with_nonzero_exit Negative: прошедший, но не кэшируемый прогон записывается и НЕ даёт попадания (exit_code=0, охраняет префикс команды) — tests/test_gate_runs_failures.py::TestRecordedRunsAreNotReplayedAsGreen::test_all_skipped_pass_does_not_satisfy_verify_first Negative: настоящий зелёный обязан по-прежнему давать попадание, иначе сломан Verify-First — tests/test_gate_runs_failures.py::TestRecordedRunsAreNotReplayedAsGreen::test_real_pass_still_satisfies_verify_first Domain: до правки вопрос «как часто гейт реально блокирует» был неотвечаем именно для тех прогонов, ради которых таблица заведена. Безопасность не предполагалась, а проверена: обе выборки фильтруют exit_code=0 (verify_recent_lookup.py:51 и «any fresh exit-zero row»), а путь CLI уже пишет падения безусловно — практика в проекте была, расходился сервисный слой. Для прошедшего, но некэшируемого прогона введён префикс noncacheable|, не матчащийся ни строгой выборкой, ни ослабленной. Checklist: scope — ACL расширялся явно; тесты — 10 новых плюс два существующих приведены к заявленному контракту; security — security-чувствительный прогон стал наблюдаем, оставшись непереиспользуемым (is_cache_allowed отказывает до запроса + префикс); rollback — аддитивно, схема не тронута. НАХОДКА В ЧУЖИХ ТЕСТАХ: test_cache_misses_on_red_run содержал два противоречащих комментария — сначала описание ЗАМЫСЛА («record_run still happens but exit_code != 0 → lookup returns None», ровно то, что я реализовал), затем описание РЕАЛИЗАЦИИ («record_run is NOT called for red»), и assert был подогнан под второе. Тест писался под фактическое поведение, а не под намерение, и законсервировал дефект. ПОПРАВКА К РЕВЬЮЕРУ: ошибку ruff он счёл доказательством, что pin-mcp-major-bound не мог пройти чистый verify. Неверно — ruff не входит в набор гейтов проекта (проверено через get_gates_for_trigger: verify = hadolint, pytest; task-done = filesize, renar_drift_*). Ошибка реальна и исправлена, вывод о гейтах — нет. Его же тревога об отсутствии фильтра exit_code снята чтением кода: фильтр есть и именно он делает правку безопасной.
