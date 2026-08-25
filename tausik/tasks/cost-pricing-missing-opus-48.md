---
slug: cost-pricing-missing-opus-48
title: "Телеметрия стоимости пишет $0.00 для модели, которую TAUSIK сам рекомендует (opus-4-8 нет в таблице цен)"
status: done
epic: landscape-2026-h2
story: l26-arch-debt
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 45
defect_of: null
scope: "scripts/cost_pricing.py, tests/test_llm_pricing_config.py или новый tests/test_cost_pricing.py, CHANGELOG.md, CHANGELOG.ru.md"
scope_exclude: "model_profiles.py и model_routing_matrix.py (их таблицы читаются, но не правятся), project_config.lookup_llm_usd_per_million_tokens (мёртвый второй лукап — отдельная задача), hooks/posttool_usage.py, схема usage_events, пересчёт исторических строк cost_usd"
relevant_files:
  - "scripts/cost_pricing.py"
  - "tests/test_cost_pricing.py"
  - "tests/test_posttool_usage_hook.py"
  - "docs/_generated/constants.json"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-23T14:57:19Z"
---

## Goal

Живой тихий сбой (нарушение принципа «нулевая толерантность к тихим ошибкам»). scripts/cost_pricing.py хардкодит таблицу цен с claude-opus-4-7/4-6/sonnet-4-6/haiku-4-5, но БЕЗ claude-opus-4-8 — при том что scripts/model_profiles.py маппит профиль opus → claude-opus-4-8, а model_routing_matrix.py знает этот id. Проверено в рантайме: cost(1M in,100k out) для claude-opus-4-8 = 0.0 против 22.5 для 4-7. Потребители — scripts/hooks/posttool_usage.py и session_metrics.py, значит `tausik metrics` LLM-cost и каждая строка usage_events.cost_usd для сессий на Opus 4.8 (включая сессии ЭТОГО репозитория) равны нулю, а фолбэк документирован как «cost_usd=0.0 + stderr warn». Корень архитектурный: ТРИ хардкоженные таблицы моделей в трёх модулях (cost_pricing, model_profiles, model_routing_matrix) плюс ещё две (service_delegate._DEFAULT_MODEL, skill_profile_detect.VALID_MODELS) без общего источника и без drift-проверки — при том что механизм drift-проверки уже существует (gen_doc_constants + doc_drift_scanners). Смежно: project_config.lookup_llm_usd_per_million_tokens — второй, конфиг-driven лукап цен с НУЛЁМ продакшн-вызовов (только тест), при этом его нормализатор гоняется на каждой загрузке конфига: ключ llm_pricing_usd_per_million валидируется, хранится и никогда не читается. Либо подключить как override-слой в cost_pricing.get_pricing (что и предотвратило бы эту дыру), либо удалить оба.

## Acceptance Criteria

AC1. get_pricing("claude-opus-4-8") и суффиксная форма "claude-opus-4-8[1m]" возвращают ненулевые цены; calculate_cost_usd на непустых токенах даёт > 0. Тест fail-then-pass.
AC2. Таблица цен приведена в соответствие с актуальным прайсом Anthropic целиком, а не точечно: Opus 4.8/4.7/4.6 = $5/$25 (сейчас 4-7 и 4-6 стоят $15/$75 — завышение втрое), Haiku 4.5 = $1/$5 (сейчас $0.80/$4), добавлены Sonnet 5 и Fable 5/Mythos 5. Каждая строка снабжена ссылкой на источник и датой сверки.
AC3. Фантомная «премия за 1M-контекст» убрана: у Opus 4.6/4.7/4.8 и Sonnet 1M — ШТАТНЫЙ контекст по базовой цене, поэтому [1m]-форма обязана стоить столько же, сколько база. Тест на равенство base и [1m] для этих моделей.
AC4. Дрейф не повторяется механически: проверка покрытия — каждый Claude-id, на который ссылаются model_profiles.DEFAULT_FAMILIES['claude'], model_routing_matrix._PROFILE_SLUG_BY_MODEL_ID и service_delegate._DEFAULT_MODEL, обязан иметь строку в таблице цен. Тест падает при добавлении модели в роутинг без цены. Не-Claude семейства (glm) из проверки исключены явно и с объяснением.
AC5. Полный прогон pytest зелёный, без warnings.
AC6. CHANGELOG.md + CHANGELOG.ru.md обновлены прозой.

## Plan

## Rollback

git revert коммита; файл цен изолирован — git checkout -- scripts/cost_pricing.py возвращает прежнюю таблицу. Исторические строки usage_events не переписываются, так что откат не оставляет несогласованных данных.

## Journal

- 2026-07-23T14:47:10Z [implementation] — Реализовано. Root cause шире заявленного в задаче: отсутствовал не только claude-opus-4-8 — вся таблица разошлась с прайсом. Opus стоял $15/$75 против опубликованных $5/$25 (завышение втрое на КАЖДОЙ записанной Opus-сессии), Haiku 4.5 — $0.80/$4 против $1/$5, а строки [1m] несли двукратную «премию за длинный контекст», экстраполированную с устаревшего тарифа Sonnet: на текущих тарифах Opus/Sonnet 1M — штатное окно по базовой цене. Добавлены Sonnet 5, Fable 5/Mythos 5. Цены сверены через skill claude-api (не по памяти — правило харнесса про LLM-прайсинг). ОТДЕЛЬНО ВАЖНО: существующие тесты в tests/test_cost_pricing.py УТВЕРЖДАЛИ дефект — и $15/$75, и фантомную премию, — поэтому набор был зелёным над счётчиком, ошибавшимся в обе стороны; их ожидания исправлены с объяснением в докстринге, чтобы правка не читалась как подгонка. Механическая защита от повтора: cost_pricing.routed_claude_model_ids() читает ТРИ реальные таблицы роутинга (model_profiles.DEFAULT_FAMILIES['claude'], model_routing_matrix._PROFILE_SLUG_BY_MODEL_ID, service_delegate._DEFAULT_MODEL), models_missing_pricing() возвращает непокрытые, тест падает при добавлении модели в роутинг без цены; есть fail-then-pass тест, что гейт реально срабатывает (не пустое множество из-за того, что он никуда не смотрит), и тест, что он читает НАСТОЯЩИЕ таблицы, а не свою копию (conv #266). Не-Claude семейства (glm) исключены явно: не тарифицируются по ставкам Anthropic, выдуманная цена хуже отсутствующей. Побочно: get_pricing теперь возвращает КОПИЮ строки — тарифы шарятся одним dict между id и суффиксными формами, и мутация у одного вызывающего перетарифицировала бы всю линейку. Интро-цена Sonnet 5 ($2/$10 до 2026-08-31) сознательно НЕ кодируется: статическая таблица не выражает «до даты», а протухшая скидка занижала бы расход — завышение в интро-окно безопаснее.
- 2026-07-23T14:57:17Z [implementation] — AC1 ✓ get_pricing('claude-opus-4-8') и '[1m]'-форма дают ненулевые цены; calculate_cost_usd > 0 (TestTheDefect). AC2 ✓ таблица сверена целиком по актуальному прайсу через skill claude-api: Opus 4.8/4.7/4.6 = 5/25 (было 15/75 — завышение втрое), Haiku 4.5 = 1/5 (было 0.80/4), добавлены Sonnet 5 и Fable 5/Mythos 5; в докстринге источник и дата сверки 2026-07-23. AC3 ✓ фантомная 1M-премия убрана — [1m] равен базе для Opus 4.6/4.7/4.8, Sonnet 5/4.6, Fable 5 (TestNoPhantomLongContextPremium, 6 параметров). AC4 ✓ models_missing_pricing() читает ТРИ реальные таблицы роутинга; тест падает при модели без цены; отдельный тест доказывает, что гейт СРАБАТЫВАЕТ (fail-then-pass), отдельный — что он читает настоящие таблицы, а не свою копию (conv #266); проверено вручную: при удалении строки claude-opus-4-8 гейт возвращает ровно {'claude-opus-4-8'}, то есть поймал бы исходный дефект. Не-Claude семейства исключены явно. AC5 ✓ полный прогон 5398 passed / 23 skipped, без warnings; единственное падение (test_check_docs_hook) — устаревший счётчик тестов в constants.json после добавления тестов, перегенерирован gen_doc_constants --write. AC6 ✓ прозаические записи в CHANGELOG.md и CHANGELOG.ru.md. Побочно: get_pricing возвращает копию строки — тарифы шарятся одним dict между id и суффиксными формами, мутация у вызывающего перетарифицировала бы всю линейку; исправлены ожидания в tests/test_cost_pricing.py и test_posttool_usage_hook.py, утверждавшие дефект.
- 2026-07-23T14:57:17Z [implementation] — Root cause (missing-validation): таблица цен поддерживалась ПАМЯТЬЮ, а не механизмом — ничего не связывало её с таблицами роутинга, которые решают, какая модель реально запустится, поэтому добавление claude-opus-4-8 в model_profiles прошло без цены и счётчик молча обнулился; сопутствующие ошибки (5/5 вместо /5, фантомная 1M-премия, Haiku /usr/bin/bash.80/) — того же происхождения: цифры однажды записали и больше ни с чем не сверяли, а тесты закрепили их как ожидания. Prevention: (1) покрытие цен выведено из РЕАЛЬНЫХ таблиц роутинга (models_missing_pricing), падает при добавлении модели без цены — обязанность обновлять таблицу переложена с памяти на сборку; (2) проверено, что гейт ловит именно исходный дефект: при удалении строки claude-opus-4-8 он возвращает ровно этот id (не только monkeypatch-набор); (3) у таблицы теперь есть дата сверки и указание источника, чтобы 'проверено когда-то' было отличимо от 'проверено тогда-то'; (4) урок про тесты: набор из 5385 зелёных тестов не заметил счётчика, ошибавшегося втрое, потому что тесты утверждали ту же ошибку — числовой факт из внешнего мира нельзя фиксировать только тестом, ему нужен источник и дата.
