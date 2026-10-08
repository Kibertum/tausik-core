---
slug: two-pricing-models-and-neither-counts-the-cache
title: "Две модели цены, и ни одна не считает главный поток токенов"
status: done
epic: release-110-deferred-from-19
story: deferred-110-audit-hygiene
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/token_price.py"
  - "tests/test_token_price_cache.py"
  - "tests/test_token_price.py"
  - "changelog.d/two-pricing-models-and-neither-counts-the-cache.md"
scope_paths:
  - "scripts/token_price.py"
  - "scripts/cost_pricing.py"
  - "scripts/service_token_cost.py"
  - "scripts/service_token_metrics.py"
  - "tests/"
  - "changelog.d/"
  - "tests/test_token_price.py"
scope_tools: []
depends_on: []
completed_at: "2026-09-29T19:54:57Z"
resolution: null
resolution_reason: null
tracker_refs: []
started_model_id: claude-opus-5
started_model_version: null
done_model_id: claude-opus-5
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

Замер по последним 10 сменам: cache_read 3 044 531 708 токенов против 3 922 523 выхода — в 776 раз больше. Но цены живут в ДВУХ независимых местах, и ни одно не даёт ответа. cost_pricing несёт встроенную таблицу {input, output} и кэш не оценивает вовсе — оттуда usage_events.cost_usd, который поэтому занижает на порядок. token_price умеет cache_read и cache_create, но берёт ставки ТОЛЬКО из config.json, которого никто не заполнил, — оттуда metrics tokens печатает UNPRICED и молчит о 5953 вызовах. Цель: одна встроенная ставка, из неё выводятся кэшевые по опубликованным множителям, и metrics tokens считает из коробки.

## Acceptance Criteria

AC-1 token_price падает на встроенную таблицу cost_pricing, когда в config нет записи: metrics tokens печатает цену без правки конфига. ✓ tests/test_token_price_cache.py
AC-2 Кэшевые ставки ВЫВОДЯТСЯ из входной по опубликованным множителям (чтение 0,1x, запись 1,25x), а не заводятся второй таблицей, которая разойдётся.
AC-3 Множители названы вместе с их источником, и тест закрепляет арифметику на разобранном примере.
AC-4 НЕГАТИВНЫЙ: модель без цены по-прежнему даёт ОТСУТСТВИЕ, а не ноль — ни одна строка не объявляет работу бесплатной.
AC-5 НЕГАТИВНЫЙ: запись в config ПЕРЕБИВАЕТ встроенную, а не складывается с ней; проект, объявивший свою цену, получает свою.
AC-6 Вывод говорит, какая доля счёта — кэш: без этой строки читатель повторит мою же ошибку и примет выход за счёт.
AC-7 usage_events.cost_usd остаётся входом плюс выходом, и это НАЗВАНО причиной: payload хука не несёт кэшевых счётчиков, они приходят из транскрипта. Два числа не выдаются за одно.
AC-8 Полная лента зелёная.

## Plan

## Rollback

git revert; token_price снова только из config, metrics tokens снова UNPRICED

## Journal

- 2026-09-29T19:54:53Z [implementation] — AC-1 ✓ metrics tokens печатает цену БЕЗ правки конфига: было UNPRICED, стало total 1700,06. ✓ tests/test_token_price_cache.py::TestTheCacheRatesAreDerivedNotListed::test_a_shipped_model_prices_all_four_kinds и парный ::test_a_shipped_model_prices_without_any_config в старом наборе. AC-2 ✓ кэшевые ставки ВЫВОДЯТСЯ множителями от входной — ::test_the_cache_rates_are_the_published_multiples_of_input. AC-3 ✓ множители названы с источником, арифметика закреплена разобранным примером: вход Opus 5,0 -> чтение 0,50, запись 6,25 (::test_the_arithmetic_on_a_named_example). AC-4 ✓ НЕГАТИВНЫЙ: четыре формы неизвестной модели дают None, и непроценённые вызовы названы числом и именем. AC-5 ✓ НЕГАТИВНЫЙ: запись конфига перебивает целиком, чужие ключи не протекают — ::test_the_config_overrides_the_shipped_table. AC-6 ✓ строка доли: «cache is 94,2% of this bill and output is 5,8%», и отдельный тест требует, чтобы при нулевом счёте доли НЕ было. AC-7 ✓ докстрока называет, почему usage_events.cost_usd остаётся входом плюс выходом (хук не видит кэшевых счётчиков, они приходят из транскрипта), и тест читает это утверждение. AC-8 лента 12 546 passed, 34 skipped при одном явно снятом answer_shape. ЗАМЕР: кэш 3 044 531 708 токенов против 3 922 523 выхода — в 776 раз; в деньгах кэш 94,2% счёта. НАЙДЕНО: суффикс с датой лишал модель цены — claude-haiku-4-5-20251001 это id, который сообщает хост, а таблица ключуется без даты; хвостовые числовые сегменты теперь отбрасываются, и одно это вернуло в счёт 984 вызова. ПОБОЧНО: два старых теста закрепляли «без конфига — не оценено»; предмет переставлен на модель, которой таблица не знает, и добавлен парный положительный.
