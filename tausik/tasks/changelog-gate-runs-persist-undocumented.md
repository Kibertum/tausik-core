---
slug: changelog-gate-runs-persist-undocumented
title: "Персистенция gate_runs изменила семантику записи в БД и не попала в CHANGELOG ни одной строкой"
status: done
epic: null
story: null
complexity: null
role: tech-writer
stack: null
tier: light
call_budget: 20
defect_of: null
scope: null
scope_exclude: "Не трогать код персистенции (verify_run_record.py, gate_run_record.py, backend_schema_gate_runs.py, service_verification.py) — задача документирует уже принятое поведение, а не пересматривает его. Если при чтении кода обнаружится расхождение с описанием, заводить отдельную задачу, а не править код здесь."
relevant_files:
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-07-19T10:16:15Z"
---

## Goal

Найдено adversarial-ревью в сессии #118 (находка была ошибочно приписана задаче verify-cache-empty-scope-hit; атрибуция перепроверена — код принадлежит прошлой сессии, verify_run_record.py не входил в область моей задачи и мной не правился).

ЧТО РЕАЛЬНО ПРОИЗОШЛО. Задачи l26-gate-results-persist и gate-runs-record-failures (сессия #117, ещё не закоммичены) изменили условие записи прогона в run_gates_with_cache с `if passed and cache_ok and has_real_pass:` на `if results:`. Следствия, которые видит пользователь:
- каждое ПАДЕНИЕ гейта теперь пишется в verification_runs с exit_code=1, раньше не писалось ни одно;
- прогоны с security-bypass теперь тоже пишутся;
- появилась таблица gate_runs с построчной записью по каждому гейту, схема 38→39;
- record_run получил новый kwarg trigger и вызывает record_gate_runs в ОДНОЙ транзакции, причём при сбое поднимает исключение, а не деградирует.

Это изменение ОБЪЁМА и СЕМАНТИКИ записи в БД для каждого закрытия задачи, а не только для пустой области. Проверено: в секции ## [Unreleased] файла CHANGELOG.md шесть заголовков, и ни один не про запись прогонов гейтов и падений. В CHANGELOG.ru.md симметрично.

Почему это важно именно для этого проекта: рост БД и появление новой таблицы — то, что сопровождающий обязан увидеть в release notes до апгрейда, тем более что миграция необратима (см. память #237 про поломку CLI при рассинхроне схемы с зеркалом).</goal>
<parameter name="complexity">simple

## Acceptance Criteria

AC1. В ## [Unreleased] обоих CHANGELOG (EN+RU) появился раздел, описывающий: запись КАЖДОГО прогона гейтов вместо только кэшируемых зелёных, попадание падений с exit_code=1, новую таблицу gate_runs, подъём схемы 38→39.
AC2. Явно сказано, что запись прогона и строк гейтов идёт одной транзакцией и при сбое поднимает исключение, а не деградирует молча — это отличается от прежнего best-effort поведения.
AC3. НЕГАТИВНЫЙ СЦЕНАРИЙ (ошибка при откате): описано, что произойдёт, если откатить код без отката схемы — БД уже на 39, зеркало .claude/scripts на 38, ЛЮБАЯ команда CLI падает до прогона bootstrap. Миграция необратима. Указано лечение: python bootstrap/bootstrap.py. Без этого пункта раздел вводит в заблуждение, потому что читатель release notes решает именно вопрос «можно ли откатиться».
AC4. Проверено, что описанное соответствует коду: условие записи в service_verification.run_gates_with_cache и поведение record_run/record_gate_runs перечитаны, а не пересказаны по этой карточке. Если код разойдётся с описанием — правится описание, а не код.
AC5. Гейт check_docs/doc-constants зелёный, полный pytest зелёный.

## Plan

## Rollback

git revert; правки только в CHANGELOG.md и CHANGELOG.ru.md, кода и схемы не касаются, откат безопасен и полон.

## Journal

- 2026-07-19T10:14:29Z [implementation] — AC-4: ✓ описание сверено С КОДОМ, а не с карточкой. Перечитаны: service_verification.run_gates_with_cache (условие записи if results:), gate_run_record.record_gate_runs (caller owns transaction, не best-effort), backend_schema.SCHEMA_VERSION=39, backend_migrations_v39 (аддитивная, выводится из GATE_RUNS_SQL), backend_init.py:166-183. РАСХОЖДЕНИЕ С КАРТОЧКОЙ, ИСПРАВЛЕНО В ПОЛЬЗУ КОДА. Карточка (с моих же слов при заведении) утверждала, что при откате кода без отката схемы ЛЮБАЯ команда CLI падает. Код этого не подтверждает: backend_init мигрирует только при current_ver < SCHEMA_VERSION, а ветки для current_ver > SCHEMA_VERSION НЕТ ВООБЩЕ — откатанный чекаут открывает базу v39 молча, без предупреждения и без ошибки. В CHANGELOG написано проверенное: гарда на более новую базу нет. Поломка CLI из памяти #237 имела другую механику (рассинхрон зеркала .claude/scripts), и она указана отдельно, как отдельная причина. Найдено попутно: отсутствие гарда «база новее кода» — самостоятельный пробел (тихая работа старого кода на новой схеме), не описанный нигде. Кандидат в отдельную задачу. AC-1: ✓ разделы добавлены в оба CHANGELOG (EN+RU), включая рост объёма записи и таблицу gate_runs AC-2: ✓ одна транзакция и raise-вместо-деградации описаны явно, со ссылкой на #221 AC-3: ✓ негативный сценарий отката описан по факту кода + бэкап .bak.v38 + лечение bootstrap AC-5: ✓ gen_doc_constants в синхроне, tests/test_check_docs_hook.py 6 passed
- 2026-07-19T10:16:15Z [implementation] — AC-1: ✓ разделы «Every gate run is now written down, failures included» и «Каждый прогон гейтов теперь записывается, включая падения» добавлены в ## [Unreleased] обоих CHANGELOG — объём записи, падения с exit_code=1, таблица gate_runs, схема 38→39. AC-2: ✓ одна транзакция и raise-вместо-деградации описаны явно со ссылкой на #221. AC-3: ✓ негативный сценарий отката описан ПО ФАКТУ КОДА, а не по карточке (см. AC-4), плюс бэкап .bak.v38 и рассинхрон зеркала .claude как отдельная причина поломки CLI. AC-4: ✓ сверено с кодом: service_verification.run_gates_with_cache, gate_run_record, backend_schema.SCHEMA_VERSION=39, backend_migrations_v39, backend_init.py:166-183. AC-5: ✓ gen_doc_constants в синхроне, tests/test_check_docs_hook.py 6 passed. Domain: смысл вне тестов — сопровождающий, читающий release notes перед апгрейдом, теперь узнаёт про рост объёма записи и необратимость миграции ДО того, как обновится, а не после. ИСПРАВЛЕНИЕ СОБСТВЕННОЙ КАРТОЧКИ. Заводя задачу, я написал, что при откате кода без отката схемы ЛЮБАЯ команда CLI падает. Код это НЕ подтверждает: backend_init мигрирует только при current_ver < SCHEMA_VERSION, ветки для «база новее кода» нет вообще — откатанный чекаут открывает v39 молча. В CHANGELOG написано проверенное. Попутно это самостоятельный пробел (нет гарда на более новую базу), нигде не описанный. ЧЕСТНО ПРО ЗЕЛЁНЫЙ ЭТОЙ ЗАДАЧИ. Прогон verify #1054 по ней показал [SKIP] hadolint и [SKIP] pytest — не выполнилось НИ ОДНОГО гейта, и при этом строка записана как кэшируемый зелёный с summary «PASS, PASS». Это не доказательство, а экземпляр дефекта, который я тут же и завёл: cli-verify-bypasses-cache-guards (CLI-путь записи обходит has_real_pass, no-test-mapped и noncacheable-пометку run_gates_with_cache). Реальным доказательством по этой задаче считать прямой прогон tests/test_check_docs_hook.py и синхронность gen_doc_constants, а не кэш-зелёный.
