---
slug: gate-registry-single-source
title: "Реестр гейтов: регистрация размазана по четырём механизмам, новейшие гейты не видны ни gates status, ни чеку, ни risk"
status: done
epic: landscape-2026-h2
story: l26-arch-debt
complexity: complex
role: architect
stack: python
tier: substantial
call_budget: 120
defect_of: null
scope: "scripts/gate_registry.py (new), scripts/default_gates.py, scripts/gate_runner.py, scripts/service_gates.py, scripts/project_config.py, scripts/gate_command_policy.py, scripts/project_service.py, tests/test_gate_registry.py (new), CHANGELOG.md, CHANGELOG.ru.md"
scope_exclude: "scripts/risk_compute.py (_factor_gate_coverage — отдельная задача risk-gate-coverage-configured-count-in-check), stacks/*/stack.json (стековые гейты остаются в plugin registry), .claude/** (генерится bootstrap), gate_qg0_* / gate_ac_check (QG-0 не гейты этого реестра)"
relevant_files:
  - "scripts/gate_registry.py"
  - "scripts/gate_post_scope.py"
  - "scripts/gate_tdd_order.py"
  - "scripts/default_gates.py"
  - "scripts/gate_runner.py"
  - "scripts/service_gates.py"
  - "scripts/project_config.py"
  - "scripts/gate_command_policy.py"
  - "scripts/gate_changelog.py"
  - "scripts/gate_renar_drift.py"
  - "scripts/gate_bootstrap_drift.py"
  - "scripts/project_cli_aidd_autogen.py"
  - "tests/test_gate_registry.py"
  - "tests/conftest.py"
  - "tests/test_opencode_qg0_plugin.py"
  - "docs/en/architecture.md"
  - "docs/ru/architecture.md"
  - "docs/_generated/constants.json"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - README.md
  - README.ru.md
  - CLAUDE.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-23T21:24:15Z"
---

## Goal

Чтобы объявить гейт, сейчас надо попасть в четыре несвязанных места: (1) метаданные — default_gates.UNIVERSAL_GATES ∪ stacks/*/stack.json; (2) диспетч встроенных реализаций — цепочка if/elif в gate_runner.py:182-191; (3) политика безопасности команд — gate_command_policy.py, где «встроенность» выводится из command is None; (4) хардкод в пути task-done — service_gates.py:263-297. Гейты gate_changelog и gate_verify_first живут ТОЛЬКО в (4), и последствия конкретны: `tausik gates status` их не перечисляет; `gates enable/disable changelog` до них не дотягивается (у changelog свой ключ task_done.changelog_gate.enabled); они не попадают в gate_runs и, значит, ЧЕК НЕ МОЖЕТ ДОКАЗАТЬ, что QG-2-гейт отработал — прямая дыра в главном артефакте продукта; они не участвуют в risk._factor_gate_coverage, что усугубляет уже заведённую risk-gate-coverage-configured-count-in-check. Цель: один GATE_REGISTRY {name: GateSpec{default_config, impl, phase}}, где phase ∈ {scoped, post-scope}; gate_runner диспетчит через spec.impl (цепочка if/elif умирает), default_gates выводится из того же реестра, service_gates гоняет post-scope в цикле вместо двух хардкоженных вызовов. Прецедент того, что это работает — консолидация gate_verdict (gate_runner.py:265-268: «жило в пяти местах, и они уже разъехались в обе стороны»).

## Acceptance Criteria

1. `scripts/gate_registry.py` — единственное место объявления встроенных гейтов: `GATE_REGISTRY: dict[str, GateSpec]`, где GateSpec = (name, phase ∈ {scoped, post_scope}, default_config, impl). Тест: `default_gates.UNIVERSAL_GATES` выводится из реестра и байт-в-байт равен прежнему снимку из 8 имён (ruff, mypy, filesize, bandit, tdd_order, bootstrap_drift, renar_drift_schema, renar_drift_provenance).
2. `gate_runner.run_gates` не содержит цепочки `if name == ...`: диспетч через `GATE_REGISTRY[name].impl`, гейт вне реестра → `run_command_gate`. Тест: гейт, добавленный в реестр в рантайме, исполняется своей impl без правки gate_runner.
3. post-scope гейты (`verify_first`, `changelog`) объявлены в реестре; `service_gates._run_quality_gates_report` гоняет их циклом по реестру вместо двух хардкоженных вызовов; порядок verify_first → changelog сохранён (тест на порядок).
4. `gates_status()` перечисляет verify_first и changelog с честным `enabled` (для changelog резолвится из legacy `task_done.changelog_gate.enabled` — статус не должен врать) и с пометкой phase. Тест: оба имени присутствуют.
5. `get_gates_for_trigger` НЕ отдаёт post-scope гейты (у них другая сигнатура) — `run_gates` их не исполняет. Тест: 'verify_first' отсутствует в get_gates_for_trigger('task-done').
6. Каждый исполненный post-scope гейт пишет строку в `gate_runs` (verification_run_id NULL, trigger='task-done', passed=факт добавления blocking_failure) — чек может доказать, что QG-2-гейт отработал. Тест: строки gate_name='verify_first' и 'changelog' появляются после прохода task-done.
7. «Встроенность» гейта определяется реестром, а не `command is None`: `gate_command_policy` спрашивает реестр. Тест: override команды для filesize отклоняется прежним сообщением; поведение стековых/кастомных гейтов не изменилось.
8. Регресс: полный pytest зелёный; `gates status` и `verify --task` работают на живом проекте; CHANGELOG.md + CHANGELOG.ru.md обновлены.

## Plan

## Rollback

git revert коммита задачи. Реестр изолирован в новом модуле gate_registry.py; все старые точки объявления превращаются в тонкие делегаты, поэтому откат восстанавливает прежние литералы целиком. Промежуточной миграции данных нет (gate_runs пишет новые строки, схема не меняется).

## Journal

- 2026-07-23T20:34:57Z [implementation] — Прочитаны все 4 точки регистрации (default_gates, gate_runner if/elif 182-191, gate_command_policy, service_gates 263-297). Создан scripts/gate_registry.py: GateSpec(name, phase, default_config, impl, skip_on_fileless_close, enabled_resolver), 8 scoped + 2 post_scope. Impl резолвится ЛЕНИВО по строке — иначе default_gates -> gate_bootstrap_drift -> project_config -> default_gates цикл. Форма 'svc:method' для post-scope: позднее связывание обязательно, иначе ломается pytest-шим conftest, отключающий Verify-First для легаси-сьюта.
- 2026-07-23T20:59:59Z [implementation] — Реализация готова: default_gates выводится из реестра; gate_runner диспетчит через impl_for (if/elif удалён); gate_post_scope.py гоняет verify_first→changelog циклом, пишет gate_runs (verification_run_id NULL, commit сразу) и шлёт bypass-событие ТОЛЬКО при выключении гейта, который шипится ON; gate_command_policy спрашивает реестр (ruff остаётся override-able, filesize нет); get_gates_for_trigger режет post_scope. Побочно закрыта тихая дыра: гейт без impl и без command раньше отвечал PASS ("No command configured"), теперь SKIP + warning. Полный pytest: 5478 passed, 2 failed — обе разобраны: (1) test_changelog_gate TestWiring поймал РЕАЛЬНЫЙ дефект моего кода — включённость changelog решалась в двух местах (_enabled_map через changelog_gate_enabled и impl через _read_changelog_gate_config), они могли разойтись; сведено к одному читателю (_read_changelog_gate_config(cfg=...)); (2) doc-constants drift от +1 тестового файла — регенерить gen_doc_constants.
- 2026-07-23T21:06:08Z [implementation] — Adversarial-ревью собственных фиксов (конвенция #276): найдено и исправлено нарушение memory #265 — _enabled_map при сервисе без tausik_dir падал в ambient-конфиг, то есть политику ЭТОГО закрытия мог решать другой репозиторий. Теперь root=None -> {} (все гейты ON) + warning + тест. Дополнительно: project_config.py вышел за 400 строк (410) -> вынес apply_post_scope_enabled в реестр и ужал докстринги до 400 ровно (гейт бьёт по >400). Ruff: убраны 2 предсуществующие ошибки в чужих файлах (project_cli_aidd_autogen E402, test_opencode_qg0_plugin F401) — 'All checks passed'. Доки EN/RU архитектуры и оба CHANGELOG обновлены, doc-constants регенерированы, bootstrap --ide all развёрнут (drift check чистый).
- 2026-07-23T21:12:11Z [implementation] — Второй проход ревью: resolve_enabled теперь управляет не только строкой статуса, но и ЗАПУСКОМ гейта — значит проглатывание исключения резолвера означало бы, что один нечитаемый ключ тихо отправляет QG-2-гейт на пенсию. Исправлено на fail-closed (исключение -> ON) + тест. Живая проверка AC4: `.tausik/tausik gates status` показывает [ON] verify_first и [ON] changelog. doctor: 'Quality gates 12 registered, 12 resolved, 2 on verify' (было 10) — все чисто. bootstrap --check чистый после трёх раскаток.
- 2026-07-23T21:24:12Z [implementation] — AC1 PASS - UNIVERSAL_GATES derived from GATE_REGISTRY, byte-identical to the hand-frozen pre-refactor snapshot: tests/test_gate_registry.py::TestDerivedMetadata (3 tests, incl. copy-isolation and every impl path resolving). AC2 PASS - dispatch is a registry lookup: TestDispatch::test_runtime_registry_entry_runs_its_own_impl (gate added to the registry at runtime executes with no gate_runner edit) + TestNoDispatchChainLeftBehind::test_gate_runner_holds_no_gate_name_branches. AC3 PASS - post-scope gates run from the registry in declaration order: TestPostScopeLoop::test_runs_in_declaration_order (verify_first then changelog) + test_service_gates_holds_no_hardcoded_post_scope_calls. AC4 PASS - TestVisibilityAndPhaseFilter::test_post_scope_gates_are_listed + test_changelog_enabled_reflects_the_legacy_switch; live: .tausik/tausik gates status shows [ON] verify_first and [ON] changelog, doctor reports 12 registered (was 10). AC5 PASS - test_scoped_runner_never_sees_a_post_scope_gate. AC6 PASS - TestPostScopeLoop::test_each_gate_leaves_a_gate_runs_row (verify_first=1, changelog=0), test_verdict_is_read_from_the_report_not_claimed, test_unwritable_evidence_blocks_the_close. AC7 PASS - TestBuiltinIsDeclared (4 tests): ruff override still legal, filesize and verify_first refused, unknown gates keep the legacy inference. AC8 PASS - full pytest 5481 passed / 0 failed (the single red was doc-constants drift from the added test file, regenerated); ruff All checks passed; doctor All clean; bootstrap --check no drift; CHANGELOG.md + CHANGELOG.ru.md updated. Self-review found and fixed three real defects rather than testing around them: the changelog gate's on/off briefly had two readers that could disagree (the same defect class one layer down), _enabled_map fell back to the ambient config for a service with no project handle (memory #265), and resolve_enabled swallowed resolver errors although it now gates execution - all three now fail closed.
