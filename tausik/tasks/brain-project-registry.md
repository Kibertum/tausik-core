---
slug: brain-project-registry
title: "Глобальный реестр ~/.tausik-brain/projects.json + инкремент имён"
status: done
epic: shared-brain
story: brain-onboarding-docs
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/brain_project_registry.py (новый), scripts/brain_init.py (интеграция register_project), scripts/brain_scrubbing.py (union_with_registry option), tests/test_brain_project_registry.py (новый), небольшая правка tests/test_brain_init.py для проверки registry-call"
scope_exclude: "CLI subparser для brain registry (оставляем на отдельную задачу), cross-machine sync, migration старых .tausik/config.json без registry — OOS"
relevant_files:
  - "scripts/brain_project_registry.py"
  - "scripts/brain_init.py"
  - "scripts/brain_scrubbing.py"
  - "scripts/brain_mcp_write.py"
  - "tests/test_brain_project_registry.py"
  - "tests/test_brain_init.py"
  - "tests/conftest.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-23T14:47:45Z"
---

## Goal

Реестр всех TAUSIK-проектов на машине: {project_name, path, registered_at}. При `brain init` проект регистрируется; если имя занято — авто-инкремент ([вычеркнуто: third-party-project] → [вычеркнуто: third-party-project]-2). Scrubbing blocklist строится как union project_names из всех registered проектов.

## Acceptance Criteria

1) scripts/brain_project_registry.py создан с API: get_registry_path(), load_registry(), save_registry(entries), register_project(name, project_path), all_project_names(), canonical_name(name). Нулевые внешние зависимости (stdlib only).
2) Registry path: `~/.tausik-brain/projects.json` по умолчанию, override через env var TAUSIK_BRAIN_REGISTRY (для тестов и кастомных layout-ов). Parent dirs создаются при first save.
3) save_registry атомарно (temp file + os.replace).
4) canonical_name(name): strip() → lower() → re.sub("\\s+", "-") — совпадает с brain_config.compute_project_hash convention.
5) register_project(name, path) — идемпотентно: если entry с таким же (canonical_name, normalized_path) уже есть — возвращает существующий, НЕ дублирует.
6) Auto-increment при коллизии: если canonical_name совпадает но path другой → добавляем -2, -3, ... до свободного слота. Возвращаем итоговое имя и entry.
7) all_project_names() возвращает плоский union всех "name" из registry — для union-блоклиста scrubbing.
8) brain_init.run_wizard вызывает register_project(project_name, cwd) и использует ВОЗВРАЩЁННОЕ (возможно инкрементированное) имя для brain.project_names и SHA256-хэша. Если реестр вернул другое имя (collision) — wizard логирует это в io.print.
9) brain_scrubbing.scrub_with_config опционально принимает union_with_registry=True (default False) — тогда делает union(cfg.project_names, all_project_names()) перед detection. По умолчанию поведение не меняется — backward compat. MCP write-tools включают union для максимальной защиты.
10) >=12 тестов в tests/test_brain_project_registry.py: round-trip save/load, пустой реестр, atomic write resilience, register new, register idempotent same path, collision auto-increment (2 collisions → name-3), canonical normalization ("Hello World" → "hello-world"), path-normalization (backslash vs forward-slash на Win), all_project_names union semantics, env var override через TAUSIK_BRAIN_REGISTRY, wizard integration (с monkeypatched registry path).
11) mypy scripts/ clean; ruff clean; существующий pytest 1434 проходит.
12) OOS: CLI `tausik brain registry list/remove`, cross-machine sync registry, auto-migration старых конфигов — следующие задачи.

## Plan

[{"step": "\u041d\u0430\u043f\u0438\u0441\u0430\u0442\u044c scripts/brain_project_registry.py: API + atomic save + canonical_name + collision-increment", "done": true}, {"step": "\u041d\u0430\u043f\u0438\u0441\u0430\u0442\u044c tests/test_brain_project_registry.py (>=12 \u0442\u0435\u0441\u0442\u043e\u0432 \u0441 tmp_path + monkeypatch TAUSIK_BRAIN_REGISTRY)", "done": true}, {"step": "\u0418\u043d\u0442\u0435\u0433\u0440\u0438\u0440\u043e\u0432\u0430\u0442\u044c register_project \u0432 brain_init.run_wizard (\u0443\u043f\u0440\u043e\u0441\u0442\u0438\u0442\u044c project_names \u043b\u043e\u0433\u0438\u043a\u0443)", "done": true}, {"step": "\u0420\u0430\u0441\u0448\u0438\u0440\u0438\u0442\u044c brain_scrubbing.scrub_with_config union_with_registry=True (optional)", "done": true}, {"step": "\u041f\u0440\u043e\u0433\u043d\u0430\u0442\u044c mypy + ruff + \u043f\u043e\u043b\u043d\u044b\u0439 pytest", "done": true}, {"step": "/review, \u0443\u0447\u0435\u0441\u0442\u044c \u043f\u0440\u0430\u0432\u043a\u0438, task done + \u043a\u043e\u043c\u043c\u0438\u0442", "done": true}]

## Rollback

## Journal

- 2026-04-23T14:38:05Z [implementation] — Review: PASS WITH ISSUES, 6 findings (0 critical, 2 high, 3 medium, 1 low). Gates: pytest 1453 pass, ruff clean, mypy clean.
- 2026-04-23T14:40:53Z [implementation] — AC verified: 1. brain_project_registry.py с API get_registry_path/load/save/register/all_project_names/canonical_name ✓ 2. env TAUSIK_BRAIN_REGISTRY override + default ~/.tausik-brain/projects.json ✓ 3. Atomic save: tmp+fsync+os.replace + unlink на ошибке (test_save_unlinks_tmp_on_failure) ✓ 4. canonical_name: strip+lower+\\s+→'-' матчит brain_config.compute_project_hash ✓ 5. Идемпотентно для same path (test_register_project_idempotent_same_path) ✓ 6. Auto-increment: [вычеркнуто: third-party-project] → [вычеркнуто: third-party-project]-2 → [вычеркнуто: third-party-project]-3 (test_register_project_collision_auto_increments) ✓ 7. all_project_names возвращает union (test_all_project_names_union) ✓ 8. brain_init.run_wizard: register_project + resolved_name в io.print при collision ✓ 9. scrub_with_config(union_with_registry=True), включено в brain_mcp_write.scrub_inputs ✓ 10. 22 теста (was ≥12): load/save round-trip + atomic + register new/idempotent/collision/canonical/path-norm/env override + wizard integration via fixture + lock + explicit-canonical-collides pinning ✓ 11. /review iterate: H1 (atomic unlink + fsync), H2 (RegistryLockError advisory lock), M2 (drop dead union append), L1 (log OSError вместо swallow) — fixed. 12. OOS соблюдено: нет CLI registry list/remove, нет cross-machine sync
