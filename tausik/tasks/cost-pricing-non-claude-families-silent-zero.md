---
slug: cost-pricing-non-claude-families-silent-zero
title: "$0.00-телеметрия остаётся для не-Claude семейств (GLM/кастом): гейт покрытия цен исключает их сознательно"
status: done
epic: landscape-2026-h2
story: l26-arch-debt
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 45
defect_of: cost-pricing-missing-opus-48
scope: "scripts/cost_pricing.py (override-слой в get_pricing, warn-once в calculate_cost_usd, config в models_missing_pricing); tests/test_cost_pricing.py (override/warn/coverage); CHANGELOG.md + CHANGELOG.ru.md; README при овер-клейме"
scope_exclude: "scripts/project_config.py (lookup/normalize уже корректны — только ПОДКЛЮЧАЕМ, не меняем); схема БД cost_usd (остаётся NOT NULL REAL — None невозможен, поэтому B реализуется как warning); ставки GLM НЕ выдумываем"
relevant_files:
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - CLAUDE.md
  - "docs/en/model-providers.md"
  - "scripts/audit_orphan_files.py"
  - "scripts/cost_pricing.py"
  - "scripts/hooks/_common.py"
  - "scripts/hooks/posttool_usage.py"
  - "scripts/hooks/session_metrics.py"
  - "scripts/hooks/session_start.py"
  - "tests/test_audit_orphan_files.py"
  - "tests/test_cost_pricing.py"
  - "tests/test_doctor_multi_ide.py"
  - "tests/test_posttool_usage_hook.py"
  - "tests/test_session_metrics_parse.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-23T19:32:24Z"
---

## Goal

cost-pricing-missing-opus-48 починил тихий ноль стоимости для семейства Claude и завёл гейт models_missing_pricing, который ЯВНО исключает не-Claude семейства (cost_pricing.py: фильтр startswith('claude'), обоснование — GLM не тарифицируется по ставкам Anthropic, выдуманная цена хуже отсутствующей). Следствие, отмеченное продуктовым ревью #130: для проекта, поднятого на GLM/кастомной модели (model_profiles.families в конфиге), get_pricing вернёт None и вся телеметрия стоимости запишет $0.00 — ровно тот дефект, который батч героически чинит для Claude, но для другого семейства он остаётся. Это подрывает нарратив линии «works on any model»: адаптируемость по IDE и оболочке доведена, по МОДЕЛИ — только для Claude. Варианты (выбрать в задаче): (A) дать проекту способ ЗАДАТЬ цены своих моделей в конфиге — тот самый мёртвый project_config.lookup_llm_usd_per_million_tokens / ключ llm_pricing_usd_per_million, который сейчас нормализуется на каждой загрузке конфига и НИКОГДА не читается, подключить как override-слой в get_pricing (это и предотвратило бы исходную дыру Opus); (B) если у семейства нет цены и нет конфиг-override — не молчать: посчитать cost как None (не 0.0) и один раз предупредить, чтобы «неизвестно» отличалось от «бесплатно». Не выдумывать цены GLM. Заодно решить, не сузить ли формулировку в CHANGELOG (сейчас «модель этого проекта», не «любая модель» — переовер-клейма нет, но стоит проверить README/нарратив линии).

## Acceptance Criteria

1. Конфиг-override (вариант A): get_pricing(model_id, config) при промахе встроенной таблицы читает project_config.lookup_llm_usd_per_million_tokens(config, model_id) и возвращает {input: r, output: r} для плоской ставки r. Ранее мёртвый ключ llm_pricing_usd_per_million (нормализуется, но никогда не читался) подключён. Тест: get_pricing('glm-4.6', config={llm_pricing_usd_per_million:{'glm-4.6':2.0}}) == {input:2.0,output:2.0}; calculate_cost_usd → ненулевой.
2. Override закрывает и Claude-класс дыры: models_missing_pricing(config) НЕ флагает routed Claude id, если он оценён через config-override (get_pricing вызывается с config). Тест: fail-then-pass.
3. Неизвестное СЛЫШНО (вариант B в рамках схемы cost_usd NOT NULL): calculate_cost_usd для непустого model_id без цены и без override пишет 0.0 (schema-compatible), НО эмитит one-time stderr-предупреждение «unknown ≠ free» с подсказкой про llm_pricing_usd_per_million. Повторный вызов того же id — без повторного шума.
4. lazy-load конфига только на промахе встроенной таблицы (горячий Claude-путь не грузит конфиг); при config=None calculate_cost_usd подгружает эффективный конфиг перед объявлением модели неоценённой.
5. Нарратив: проверить README/CHANGELOG на овер-клейм «works on any model»; при необходимости сузить до «этого проекта/сконфигурированных моделей». CHANGELOG [Unreleased] + ru-зеркало обновлены.
6. Полный набор гейтов зелёный (pytest test_cost_pricing, hadolint), ноль новых warnings.
НЕГАТИВ/ГРАНИЦА: (а) config без llm_pricing_usd_per_million или не-dict → override не срабатывает, get_pricing=None (падает на 0.0+warn); (б) отрицательная/NaN ставка отфильтрована normalize_llm_pricing_config → override None; (в) пустой model_id → без warn (нечего тарифицировать).

## Plan

## Rollback

git revert коммита. Изменения аддитивны: новый override-слой (при отсутствии config-ключа поведение идентично прежнему), warn-once (только stderr, не влияет на данные), config-параметр в models_missing_pricing (default None = прежнее поведение). Откат возвращает мёртвый ключ и тихий ноль.

## Journal

- 2026-07-23T19:31:21Z [implementation] — AC1-6 pass: verify #1212 pytest PASS scope=high (67 cost+posttool tests); TestConfigPricingOverride (override/lazy/hot-path/invalid), TestUnpricedWarning (once/zero/empty/priced/explicit-0.0), test_override_covers_a_claude_gap_in_the_guard fail-then-pass; narrative — нет cost-овер-клейма, ключ задокументирован; ASCII-warning переживает не-UTF-8 pipe. Negative: negative/NaN/non-dict override→None; empty model→no warn. Domain: проект на GLM/Ollama теперь метрит реальную стоимость через config, unknown слышно вместо тихого нуля.
- 2026-07-23T19:31:21Z [implementation] — Root cause (missing-validation): cost-pricing-missing-opus-48 починил тихий /usr/bin/bash.00 только для Claude-семейства; для GLM/кастом get_pricing возвращал None→0.0 молча, а мёртвый конфиг-ключ llm_pricing_usd_per_million нормализовался, но никогда не читался (абстракция без потребителя). Prevention: (A) get_pricing читает override при промахе таблицы (питает и models_missing_pricing — закрыл бы и исходную дыру Opus); (B) неоценённая непустая модель предупреждает once-per-id (ASCII, unknown is not free), cost_usd остаётся 0.0 из-за схемы NOT NULL. Документировано в model-providers.md.
- 2026-07-23T19:31:50Z [implementation] — AC verified: 1. ✓ config-override get_pricing(glm,config)={input:2,output:2} 2. ✓ models_missing_pricing override covers Claude-gap (fail-then-pass) 3. ✓ warn-once unknown-is-not-free, cost 0.0 4. ✓ lazy-load только на промахе, hot Claude path не грузит config 5. ✓ нарратив без cost-овер-клейма, ключ в model-providers.md 6. ✓ verify #1212 pytest PASS scope=high, 67 tests, ноль warnings. Negative: negative/NaN/non-dict→None, empty model→no warn.
