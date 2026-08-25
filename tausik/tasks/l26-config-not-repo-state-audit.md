---
slug: l26-config-not-repo-state-audit
title: "Аудит потребителей, считающих конфиг чистой функцией состояния репозитория"
status: done
epic: landscape-2026-h2
story: l26-trust-boundary
complexity: medium
role: architect
stack: python
tier: substantial
call_budget: 70
defect_of: null
scope: "scripts/service_doctor_drift.py (check_claudemd_drift→load_project_config), scripts/verify_cache.py + scripts/service_verification.py (подпись гейтов), scripts/risk_compute.py (_factor_gate_coverage), scripts/model_routing* (provenance), возможно scripts/project_config.py (provenance API resolve), tests/"
scope_exclude: "config_trust.resolve (доверенная логика тиров — не трогаем), прочие потребители load_config чей предмет НЕ репо-состояние"
relevant_files:
  - "scripts/service_doctor_drift.py"
  - "scripts/config_trust.py"
  - "scripts/model_routing_matrix.py"
  - "scripts/verify_cache.py"
  - "tests/test_model_routing.py"
  - "tests/test_claudemd_drift.py"
  - "tests/test_service_verification.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-21T11:14:15Z"
---

## Goal

Следствие l26-config-trust-tiers, поднято ревью блast-радиуса. После введения тиров load_config() возвращает СЛИЯНИЕ project + user + managed, то есть перестал быть чистой функцией состояния репозитория и стал зависеть от машины и окружения. Три потребителя трактуют его как «то, что лежит в репозитории», и от этого их поведение стало машинозависимым:

(1) verify_cache.resolve_gate_signature — подпись гейтов входит в ключ кэша Verify-First и вычисляется независимо в service_verification (на запись) и service_gates._enforce_verify_first (на чтение). Если между verify и task done изменился доверенный тир, подписи разойдутся и кэш промахнётся. Направление отказобезопасное (лишний прогон, не ложный green), поэтому не критично, но бьёт по заявленному «closes in milliseconds». Вариант: пинать подпись к load_project_config(), либо класть подпись в чек при verify и сравнивать с ней.

(2) risk_compute._factor_gate_coverage — сравнивает число гейтов из свежего load_config() на момент task done с числом сработавших из чека, записанного на момент verify. При расхождении тиров это сравнение двух разных множеств. Вариант: хранить число сконфигурированных гейтов в чеке.

(3) service_doctor_drift.check_claudemd_drift — реконструирует «ожидаемый» CLAUDE.md из load_config() (project_name, stacks, context_tier, output_mode — все НЕохраняемые ключи) и диффит с файлом в репозитории. Managed-тир с общеорганизационной политикой (например output_mode) молча меняет смысл «ожидаемого»: один и тот же коммит даёт drift на одной машине и не даёт на другой. Здесь ответ наиболее очевиден — проверка drift-а обязана читать load_project_config(), потому что её предмет это соответствие отслеживаемого файла отслеживаемому конфигу.

Плюс мелочь той же природы: model_routing_matrix формирует пояснение «Config override (.tausik/config.json model_routing.X)», хотя значение могло прийти из доверенного тира — пользователь пойдёт править не тот файл. Вариант: возвращать provenance ключа из resolve() и показывать реальный источник.

Негативный сценарий: изменение не должно ронять doctor и verify при отсутствующем или пустом доверенном тире — поведение обязано остаться идентичным текущему.

## Acceptance Criteria

1. Аудит-инвентарь: все потребители load_config(), чей предмет — состояние репозитория, идентифицированы (3 названы + provenance), каждому вынесен вердикт fix/no-change/isolate с обоснованием (Decision #160). 2. check_claudemd_drift читает load_project_config() (репо-конфиг), scoped к project_dir — drift того же коммита одинаков на любой машине. 3. Verify-First подпись гейтов: вердикт NO-CHANGE обоснован (предмет — эффективный набор гейтов, fail-safe), задокументирован в коде + тест стабильности flow. 4. _factor_gate_coverage: вердикт РЕАЛЬНЫЙ дефект, но фикс security-adjacent (подписанный рецепт/schema-миграция) → ИЗОЛИРОВАН в follow-up risk-gate-coverage-configured-count-in-check с полным описанием (дисциплина handoff: не делать schema/crypto между делом). 5. model_routing provenance: rationale показывает РЕАЛЬНЫЙ источник (project/user/managed) либо нейтральную фразу без ложного файла. 6. Негативный сценарий: при отсутствующем/пустом доверенном тире поведение doctor и verify идентично текущему (регресс-тест). 7. Тесты машинозависимости: managed-тир меняет merged load_config, но предмет-репо-потребители стабильны. Зелёный pytest.

## Plan

## Rollback

git revert затронутых файлов (verify_cache.py/service_verification.py, risk_compute.py, service_doctor_drift.py, model_routing_matrix, project_config при необходимости). Изменения read-path (load_config→load_project_config) точечные и обратимые; схема чека при добавлении поля — миграция аддитивная (nullable), откат через revert без потери данных.

## Journal

- 2026-07-21T11:13:17Z [implementation] — Аудит завершён (Decision #160). FIXED: (3) service_doctor_drift.check_claudemd_drift → load_project_config(project_dir/.tausik) вместо ambient merged load_config — зеркалит производителя bootstrap (сырой .tausik/config.json), + чинит ambient-vs-project scoping (#265). Provenance: config_trust.raw_layers() + model_routing_matrix._override_provenance() — rationale показывает реальный тир (managed/user/.tausik), нейтральная фраза при неопределимом источнике (не называет ложный файл). NO-CHANGE обоснованно: (1) resolve_gate_signature — предмет эффективный набор гейтов, merged корректен, fail-safe; задокументировано в докстринге + тест стабильности flow. ISOLATED: (2) _factor_gate_coverage → follow-up risk-gate-coverage-configured-count-in-check (security-adjacent: подписанный рецепт/schema, не «между делом»). Тесты: +4 provenance (managed/user/project/neutral), +2 drift machine-independence (managed НЕ течёт; negative: без тиров идентично), +1 signature-стабильность. config_trust.py 400/400 (raw_layers переиспользован в load_trusted_layers, DRY). Deploy all, drift чист. 429 зелёных.
- 2026-07-21T11:14:14Z [implementation] — AC verified: 1. ✓ Decision #160: 4 consumers verdicts fix/no-change/isolate with rationale 2. ✓ check_claudemd_drift→load_project_config scoped; test_managed_tier_output_mode_does_not_leak_into_drift 3. ✓ signature NO-CHANGE justified+documented; test_signature_stable_across_flow_with_trusted_tier_present 4. ✓ consumer2 verdict=isolate → follow-up risk-gate-coverage-configured-count-in-check created (defect_of), full goal recorded 5. ✓ provenance real source; test_override_provenance_names_managed/user/repo_file + neutral 6. ✓ test_no_trusted_tier_behaviour_is_unchanged; neutral provenance fallback names no false file 7. ✓ 429 green config/doctor/verify/risk/routing; verify #1157 PASS; drift clean
