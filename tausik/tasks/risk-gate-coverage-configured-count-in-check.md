---
slug: risk-gate-coverage-configured-count-in-check
title: "risk _factor_gate_coverage: хранить число сконфигурированных гейтов в чеке (verify-time), не пересчитывать из load_config на task-done"
status: done
epic: null
story: null
complexity: medium
role: architect
stack: python
tier: null
call_budget: null
defect_of: l26-config-not-repo-state-audit
scope: "scripts/crypto_receipt.py (build_receipt +configured_gates_count), scripts/verify_receipt_emit.py (передать len(gate_results)), scripts/risk_compute.py (_factor_gate_coverage читает из рецепта + legacy fallback), tests/test_crypto_receipt.py, tests/test_verify_receipt_emit.py, tests/test_risk_compute.py, CHANGELOG.md, CHANGELOG.ru.md"
scope_exclude: "schema-миграция verification_runs (выбран путь (а) — поле в подписанном рецепте, не nullable-колонка); verify_receipt_check.py (верификация version-agnostic, не трогаем); контракт crypto_sign; declared_scope-поля рецепта; RECEIPT_SCHEMA версия (не бампаем)"
relevant_files:
  - "scripts/crypto_receipt.py"
  - "scripts/verify_receipt_emit.py"
  - "scripts/risk_compute.py"
  - "scripts/verify_endpoint.py"
  - "tests/test_crypto_receipt.py"
  - "tests/test_verify_receipt_emit.py"
  - "tests/test_risk_compute.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-27T09:42:11Z"
---

## Goal

Выделено из l26-config-not-repo-state-audit (consumer 2). risk_compute._factor_gate_coverage сравнивает len(ran_gates) из подписанного рецепта (verify-time) с configured=get_gates_for_trigger('verify', load_config()) на task-done. При смене доверенного тира между verify и done это сравнение ДВУХ РАЗНЫХ множеств → gate_coverage factor машинозависим. Фикс требует сохранять число сконфигурированных гейтов В МОМЕНТ verify: либо (а) добавить поле configured_gates_count в подписанный рецепт (crypto_receipt.build_receipt → verify_receipt_emit → risk_compute чтение), либо (б) nullable-колонка verification_runs.configured_gates_count. ОБА пути security-adjacent: (а) трогает ed25519-подписанный конверт и его верификацию; (б) — schema-миграция (см. handoff-предупреждение о schema-изменениях «между делом»). Требуется отдельный фокус-проход + адверсариальное ревью + обратная совместимость со старыми рецептами (отсутствие поля → graceful fallback к текущему поведению, не None-срыв). Негативный сценарий: старые рецепты без поля закрываются как раньше.

## Acceptance Criteria

AC1. Числитель и знаменатель gate_coverage берутся из ОДНОГО verify-time источника (подписанного рецепта): crypto_receipt.build_receipt получает configured_gates_count; verify_receipt_emit передаёт len(gate_results) — полный набор сконфигурированных гейтов триггера, т.к. run_gates() кладёт по записи на КАЖДЫЙ гейт (ran+skipped). Тест: emit с 3 гейтами (2 non-skipped + 1 skipped) → receipt["configured_gates_count"]==3, receipt["gates"] длиной 2.

AC2. risk_compute._factor_gate_coverage читает configured_gates_count ИЗ рецепта (verify-time), НЕ пересчитывает из get_gates_for_trigger(load_config()) на task-done. Trust-tier независимость: рецепт count=5, ran=2 → factor==round(1-2/5,4)==0.6 ДАЖЕ когда текущий конфиг вернул бы иное (monkeypatch get_gates_for_trigger→10 не меняет результат). Больше не сравнение двух разных множеств.

AC3 (НЕГАТИВНЫЙ СЦЕНАРИЙ — обратная совместимость). Старый рецепт БЕЗ configured_gates_count закрывается как раньше: factor падает на recompute len(get_gates_for_trigger("verify", load_config())), без None-срыва. Тесты: рецепт gates=2 без поля + конфиг→4 → factor==0.5; конфиг пуст → None (нечего покрывать) без исключения; поле int<=0 → та же fallback-ветка.

AC4. Канонизация/подпись целы: configured_gates_count это int|None (допустимый canonical-тип, НЕ float); build_receipt детерминирован. Schema-версия НЕ бампается (v2 остаётся) — обоснование в комментарии: верификация ре-канонизирует хранимые байты и не ветвится на версию/набор полей; поле — вспомогательная телеметрия риск-модели, не новое утверждение рецепта о полноте покрытия (в отличие от declared_scope, который менял СМЫСЛ рецепта). Старые v2-рецепты без поля остаются валидными.

AC5. Регрессий нет: test_crypto_receipt, test_verify_receipt_emit, test_risk_compute, test_risk_model, test_risk_l3_trigger, test_bypass_telemetry зелёные.

AC6. L3 внешним ревьюером (separation of duties, ДРУГАЯ модель) — security-adjacent: трогает содержимое ed25519-подписанного конверта. tausik-external-reviewer прогон, вердикт записан.

CHANGELOG.md [Unreleased] и зеркало CHANGELOG.ru.md обновлены прозаической записью.

## Plan

## Rollback

git revert коммита: изменения изолированы в 3 scripts-файлах (crypto_receipt/verify_receipt_emit/risk_compute) + 3 тестовых + CHANGELOG. Нет миграций БД, нет изменения схемы событий/таблиц, нет бампа RECEIPT_SCHEMA. Откат: build_receipt перестаёт писать поле, risk_compute возвращается к recompute-денаминатору. Старые рецепты с полем остаются валидными (поле игнорируется читателем без knowledge о нём — просто лишний ключ в подписанном payload, подпись покрывает его, верификация ре-канонизирует). Данные не теряются.

## Journal

- 2026-07-23T21:10:36Z [planning] — Контекст от gate-registry-single-source: post-scope гейты (verify_first, changelog) теперь объявлены в GATE_REGISTRY и НЕ попадают в get_gates_for_trigger — значит знаменатель _factor_gate_coverage ('verify'-триггер) ими не затронут и остаётся корректным. Но теперь есть gate_runs-строки с trigger='task-done' и verification_run_id=NULL: при реализации этой задачи не считать их в покрытие verify-прогона, это другая фаза.
- 2026-07-27T09:30:03Z [implementation] — Реализовано (путь (а) — поле в подписанном рецепте, БЕЗ schema-бампа). crypto_receipt.build_receipt: +configured_gates_count int|None. verify_receipt_emit: configured_gates_count=len(gate_results) (полный набор, run_gates кладёт по записи на каждый гейт). verify_endpoint.handle_verify: len(gates) — паритет HTTP-пути. risk_compute._factor_gate_coverage: читает count из рецепта; legacy fallback (нет поля / int<=0) → recompute get_gates_for_trigger, без None-срыва/деления на 0. Ключевой тест: рецепт count=5,ran=2 → 0.6 даже когда конфиг вернул бы 10 (trust-tier independence). Тесты: 121 (crypto_receipt/verify_receipt_emit/risk_compute/risk_model/risk_l3/bypass) + 25 (crypto_sign/receipt_export) + 24 (verify_endpoint) зелёные. Обоснование no-bump: верификация version-agnostic (ре-канонизирует байты), поле — телеметрия, не утверждение о полноте (в отличие от declared_scope v1→v2). Root cause (config-error): знаменатель пересчитывался из ТЕКУЩЕГО конфига на done, числитель — из verify-time рецепта; при смене тира между verify/done сравнивались два разных множества. Prevention: фиксировать оба конца ratio в одном подписанном источнике.
- 2026-07-27T09:41:35Z [implementation] — AC verified: 1. ✓ build_receipt +configured_gates_count (crypto_receipt.py); verify_receipt_emit передаёт len(gate_results). test_verify_receipt_emit.py::test_configured_gates_count_is_the_full_run — 3 гейта (2 ran + 1 skipped) → receipt[configured_gates_count]==3, receipt[gates] длиной 2, подпись валидна. 2. ✓ risk_compute._factor_gate_coverage читает count из рецепта. test_risk_compute.py::test_uses_receipt_count_not_current_config — рецепт count=5,ran=2 → 0.6 при monkeypatch get_gates_for_trigger→10 (recompute дал бы 0.8). Trust-tier независимость доказана. 3. ✓ НЕГАТИВНЫЙ: test_legacy_receipt_without_count_falls_back_to_recompute (нет поля,конфиг→4 → 0.5); test_legacy_receipt_no_config_returns_none (нет поля,конфиг пуст → None без исключения); test_zero_or_bad_count_falls_back (count=0 → fallback → 0.75). Guard isinstance(int) and >0. 4. ✓ int|None, не float — build_receipt: int(x) if not None else None. test_configured_gates_count_is_signable_int/defaults_none — canonical_bytes не падает. Schema НЕ бампнут: обоснование в докстринге crypto_receipt.py:72-81; L3-ревьюер подтвердил верификация version-agnostic. 5. ✓ Регрессий нет: 121 (risk/receipt/crypto/bypass) + 25 (crypto_sign/receipt_export) + 24 (verify_endpoint) + широкий свип 1396 passed/0 failed (risk|receipt|crypto|verify|gate|task_done|state_export|import|roundtrip). 6. ✓ L3 external review записан (review #2): tausik-external-reviewer на opus (separation of duties, read-only) → APPROVE 0 critical/0 high/0 medium, 2 informational nits (pre-existing/out-of-scope). Все 5 фокус-точек: подпись/канон/backward-compat/знаменатель/malicious-path — cleared. Подтвердил len(gate_results)==configured через gate_runner трассу. 7. ✓ CHANGELOG.md + CHANGELOG.ru.md [Unreleased] — прозаическая запись про фиксацию знаменателя gate_coverage в verify-time рецепте. Domain: реальный риск-скор закрытия теперь воспроизводим между verify и done независимо от смены доверенного тира конфига.
- 2026-07-27T09:42:09Z [implementation] — AC verified: 1. ✓ build_receipt +configured_gates_count; verify_receipt_emit передаёт len(gate_results). test_configured_gates_count_is_the_full_run — 3 гейта (2 ran+1 skipped) → receipt[configured_gates_count]==3, gates длиной 2, подпись валидна. 2. ✓ _factor_gate_coverage читает count из рецепта. test_uses_receipt_count_not_current_config — count=5,ran=2 → 0.6 при monkeypatch get_gates_for_trigger→10 (recompute дал бы 0.8). Trust-tier независимость. 3. ✓ НЕГАТИВНЫЙ: legacy без поля+конфиг→4 → 0.5; legacy+конфиг пуст → None без исключения; count=0 → fallback → 0.75. Guard isinstance(int) and >0, div-by-zero невозможен. 4. ✓ int|None не float; canonical_bytes не падает. Schema НЕ бампнут (обоснование в докстринге); L3 подтвердил верификацию version-agnostic. 5. ✓ Регрессий нет: 121+25+24 таргет + широкий свип 1396 passed/0 failed. bootstrap --ide all redeployed (drift устранён). 6. ✓ L3 external review #2: opus (separation of duties, read-only) → APPROVE 0 crit/0 high/0 med, 2 informational nits (pre-existing). Все 5 фокус-точек cleared. 7. ✓ CHANGELOG ×2. Domain: риск-скор закрытия воспроизводим между verify/done независимо от смены доверенного тира.
