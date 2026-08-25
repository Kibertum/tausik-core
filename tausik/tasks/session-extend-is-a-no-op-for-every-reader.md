---
slug: session-extend-is-a-no-op-for-every-reader
title: "Продление сессии не доходит до ПОКАЗА: status печатает базовый лимит, хотя warning уже считает по продлённому"
status: done
epic: landscape-2026-h2
story: l26-provable
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 30
defect_of: null
scope: "scripts/status_view.py (читать effective_session_limit); scripts/tausik_utils.py (сериализация компактного JSON); scripts/service_session_metrics.py (если формуле нужен публичный вход); scripts/project_cli_doctor.py (комментарий-обоснование); tests/; CHANGELOG.md; CHANGELOG.ru.md"
scope_exclude: "session_capacity_calls и гейт ёмкости — отдельный лимит, не расширяем; service_session.py::session_extend — он УЖЕ считает верно, чинить надо читателей; harness/claude/mcp/** — MCP берёт статус через тот же status_view, отдельной правки не требует"
relevant_files:
  - "scripts/status_view.py"
  - "scripts/project_cli_doctor.py"
  - "tests/test_status_effective_session_limit.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-28T08:52:00Z"
---

## Goal

Обнаружено вживую в сессии #148: `tausik session extend --minutes 120` ответил «New limit: 300 min», после чего `tausik status` продолжил печатать «Session: #148 (active 61m / 180m)».  ТОЧНЫЙ объём дефекта (уточнён чтением кода, исходная формулировка была шире факта): предупреждение SENAR Rule 9.2 работает ПРАВИЛЬНО — service_session_metrics.py:113 внутри session_overrun_warning разрешает эффективный лимит через effective_session_limit, читая события продления. Ломается только ПОКАЗ: status_view.py:114 кладёт в data["session_max_minutes"] сырой base из конфига, а tausik_utils.py:234 сериализует его в компактный JSON, который читают /start и tausik_session_open.  Следствие: число, которое видит человек в status и агент в конверте /start, противоречит и сообщению самой команды extend, и порогу, по которому реально срабатывает warning. Пользователь, продливший сессию, видит «61m / 180m» и делает вывод, что продление не сработало; агент, читающий конверт, планирует остаток работы по заниженному лимиту. Это тот же класс, что status-cli-mcp-divergence и model-registry-single-source: два читателя одного факта, один из которых знает про поправку, а другой нет — только здесь расходятся не два канала, а вычисление и его отображение.  Починка: показ идёт через ту же формулу effective_session_limit, что и порог. Проверить остальных читателей session_max_minutes и записать решение по каждому: project_cli_doctor.py:298 печатает КОНФИГ-кнобы, там база уместна по смыслу (это отчёт о конфигурации, а не о текущей сессии).

## Acceptance Criteria

AC1. После `session extend --minutes N` команда `tausik status` печатает ПРОДЛЁННЫЙ лимит, а не базовый из конфига.
AC2. Предупреждение SENAR Rule 9.2 продолжает считаться от продлённого лимита — оно УЖЕ верно (session_overrun_warning -> effective_session_limit), и задача обязана это НЕ СЛОМАТЬ. Пришпилено тестом: после продления warning молчит там, где без продления сработал бы.
AC3. Компактный JSON статуса (его читают /start и tausik_session_open) везёт продлённый session_max_minutes — текстовый и машинный каналы согласованы между собой и с порогом warning.
AC4. Одна формула: показ и порог используют effective_session_limit; в презентационном коде не остаётся сырого cfg.get("session_max_minutes") для показа лимита ТЕКУЩЕЙ сессии.
AC5. Решение по остальным читателям записано комментарием: project_cli_doctor.py:298 сознательно печатает БАЗУ, потому что это отчёт о конфигурации, а не о сессии — чтобы следующий читатель не принял расхождение за баг и не «починил» его.
AC6. Тесты: (a) без продления — прежнее поведение не изменилось; (b) после продления status и компактный JSON показывают новый лимит; (c) два продления складываются; (d) warning после продления молчит.
AC7. НЕГАТИВ: продление НЕ трогает ёмкость по вызовам (session_capacity_calls) — отдельный лимит, задача его не расширяет и не отображает как продлённый.
AC8. Гейты зелёные, CHANGELOG.md + CHANGELOG.ru.md обновлены прозаической записью.

## Plan

## Rollback

git revert коммита. Изменение читающее, а не пишущее: события продления в БД уже пишутся сегодня и остаются валидными при откате — откат возвращает лишь прежнее (неверное) прочтение, данные не портятся и миграции не требуется.

## Journal

- 2026-07-28T08:45:55Z [implementation] — ПОПРАВКА К ФОРМУЛИРОВКЕ ЗАДАЧИ по факту чтения кода. Исходная цель утверждала, что предупреждение SENAR Rule 9.2 считается от НЕПРОДЛЁННОГО лимита. Это неверно: service_session_metrics.py:113 внутри session_overrun_warning вызывает effective_session_limit(be, current["id"], base), то есть warning УЖЕ учитывает продления. status_view.py:98 передаёт туда base, но это корректно — база и есть ожидаемый вход, эффективный лимит разрешается внутри. Фактический дефект уже: он ТОЛЬКО в показе. status_view.py:114 кладёт в data["session_max_minutes"] сырой base из конфига, поэтому `tausik status` печатает «/180m» после продления до 300, и tausik_utils.py:234 сериализует ту же базу в компактный JSON, который читают /start и session_open. То есть число, которое видит человек и агент, противоречит и сообщению session extend, и тому, по которому реально срабатывает warning. Следствие для объёма: AC2 в исходной редакции проверял бы несуществующий баг. Переписываю AC2 в «warning уже верен — пришпилить это тестом, чтобы починка показа его не сломала», AC1/AC3 остаются. Заявленный масштаб («session extend — операция без последствий») тоже был преувеличен: последствие есть, оно просто не доходит до показа.
- 2026-07-28T08:51:57Z [implementation] — AC1 ✓ ЖИВОЙ ПРОГОН: до правки `tausik status` печатал «Session: #148 (active 64m / 180m)» при продлении до 300; после — «active 67m / 300m». AC2 ✓ Предупреждение Rule 9.2 было и осталось верным. Пришпилено test_warning_fires_without_an_extension_and_goes_quiet_with_one: при ОДНОМ И ТОМ ЖЕ активном времени 200 мин warning срабатывает без продления (200 > 180) и молчит с продлением (200 < 300). То есть тест различает лимиты, а не просто вызывает функцию. AC3 ✓ Компактный JSON (его читают /start и tausik_session_open) везёт 300 — проверено вживую `tausik status --compact` и тестом test_compact_json_carries_the_extended_limit. AC4 ✓ Одна формула: оба пути показа идут через effective_session_limit. Сырого cfg.get("session_max_minutes") для показа лимита ТЕКУЩЕЙ сессии в презентационном коде не осталось — оба view-словаря (compact-ветка и rich-ветка) отдают effective_max. AC5 ✓ Решение по третьему читателю записано КОММЕНТАРИЕМ у самой строки project_cli_doctor.py: база показывается СОЗНАТЕЛЬНО, потому что doctor отчитывается о конфигурации, а не о состоянии открытой сессии. Пришпилено test_doctor_reports_the_configured_base_on_purpose, который требует и наличия обоснования, и отсутствия effective_session_limit в doctor. AC6 ✓ 11 тестов зелёные: (a) без продления поведение прежнее; (b) текстовый канал и компактный JSON показывают новый лимит; (c) два продления складываются (240 -> 300); (d) warning после продления молчит. Плюс параметризованный кейс на битое событие продления. AC7 ✓ НЕГАТИВ: test_capacity_is_not_extended — продление времени не расширяет и не отображает как расширенную ёмкость по вызовам; событие продления говорит только о минутах. AC8 ✓ ruff «All checks passed»; scoped pytest PASS над 7 из 357 файлов; CHANGELOG.md + CHANGELOG.ru.md — прозаические записи-зеркала; bootstrap --ide all прогнан. Negative: помимо AC7 отработаны: (1) битое/пустое событие session_extend — параметризованный test_unparsable_extend_event_falls_back_to_base на трёх формах ("{not json", "", "{}"): лимит откатывается к базе, а не крашит статус и не выдумывает число; (2) отказ разрешения лимита — обёрнут в try/except с откатом на базу, статус не падает никогда; (3) ПОЛОВИНЧАТАЯ ПОЧИНКА — реальный негативный случай, случившийся на практике: два view-словаря имеют разный отступ, правка одним движением дошла только до rich-ветки, и живой CLI показал «300», создав видимость успеха. Поймали именно тесты, поэтому test_both_channels_agree утверждает равенство каналов ДРУГ ДРУГУ, а не равенство каждого числу 300 — проверка на согласованность ловит половинчатость, проверка на константу не ловила бы. Domain: результат осмыслен вне тестов — команда, которую пользователь вызвал в этой самой сессии («расширь сессию»), теперь имеет наблюдаемое последствие в обоих каналах, а агент, читающий конверт /start, планирует остаток работы по тому же числу, по которому сработает порог.
- 2026-07-28T08:52:15Z [done] — Verification checklist (SENAR Rule 5) — каждый AC с указанием теста в форме path::name. AC-1: ✓ tests/test_status_effective_session_limit.py::test_text_renderer_shows_the_extended_limit + ручной прогон `.tausik/tausik status` (до: «active 64m / 180m», после: «active 67m / 300m»). AC-2: ✓ tests/test_status_effective_session_limit.py::test_warning_fires_without_an_extension_and_goes_quiet_with_one AC-3: ✓ tests/test_status_effective_session_limit.py::test_compact_json_carries_the_extended_limit + ручной прогон `.tausik/tausik status --compact` (session_max_minutes: 180 -> 300). AC-4: ✓ tests/test_status_effective_session_limit.py::test_both_channels_agree AC-5: ✓ tests/test_status_effective_session_limit.py::test_doctor_reports_the_configured_base_on_purpose AC-6: ✓ tests/test_status_effective_session_limit.py::test_without_an_extension_nothing_changes; ::test_successive_extensions_accumulate; ::test_unparsable_extend_event_falls_back_to_base (параметризован тремя формами битого события) AC-7: ✓ tests/test_status_effective_session_limit.py::test_capacity_is_not_extended AC-8: ✓ зелёный verification_run (scoped pytest PASS над 7 из 357 файлов, отображённых из relevant_files) + ruff «All checks passed» + gates на task done: filesize/class_surface/bootstrap_drift/memory_route все PASS. Полный файл: 11 тестов, все зелёные (0.16 s).
