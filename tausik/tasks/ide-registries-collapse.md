---
slug: ide-registries-collapse
title: "Свёртка четырёх реестров хостов в один"
status: done
epic: kilo-zai-host-parity
story: kilo-zai-foundation
complexity: medium
role: developer
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: "providers/ package (an opencode Provider is new model-observation code, not registry collapse — the gap stays pinned in tests); docs/ (no doc enumerates the accepted ide_profile set); scripts/eval_memory_retrieval.py (eval fixture asserts retrieval, not code truth); harness/ templates"
relevant_files:
  - "bootstrap/bootstrap_config.py"
  - "scripts/skill_profile_detect.py"
  - "scripts/service_doctor_drift.py"
  - "scripts/host_mechanisms.py"
  - "scripts/gate_cross_model_parity.py"
  - "tests/test_cross_model_parity_gate.py"
  - "tests/test_ide_single_source.py"
  - "tests/test_enforcement_coverage.py"
  - "tests/test_skill_profile_detect.py"
  - "tests/test_skill_profile.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "bootstrap/bootstrap_config.py"
  - "scripts/skill_profile_detect.py"
  - "scripts/service_doctor_drift.py"
  - "scripts/host_mechanisms.py"
  - "scripts/gate_cross_model_parity.py"
  - "tests/test_cross_model_parity_gate.py"
  - "tests/test_ide_single_source.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
assurance_profiles: []
assurance_impact: null
depends_on: []
completed_at: "2026-10-06T19:25:39Z"
resolution: null
resolution_reason: null
tracker_refs: []
started_model_id: null
started_model_version: null
done_model_id: null
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

IDE_DIRS, ide_utils.IDE_REGISTRY, skill_profile_detect.VALID_IDES и providers знают разные множества хостов: tausik config set ide_profile kilo отказывает как unknown для полностью scaffolded хоста (deferred как four-ide-registries-collapse-into-one). Свести в один источник истины, расхождения удержать тестом на переходный период.

## Acceptance Criteria

1) tausik config set ide_profile kilo и opencode проходят. 2) Все четыре реестра читают один источник; тест ловит любое расхождение. 3) Негативный: действительно неизвестный ide отвергается одинаково на всех поверхностях. 4) Doctor/coverage отчёты не меняют смысловых выводов по покрытию.

## Plan

## Rollback

git revert of the collapse commit. Each derivation is one guarded import (try/except with an annotated mirror literal), so reverting restores the literal lists in bootstrap_config.IDE_DIRS and skill_profile_detect.VALID_IDES; the pin tests restore from git history of tests/test_cross_model_parity_gate.py. No DB, no config migration involved.

## Journal

- 2026-10-06T19:11:47Z [implementation] — Baseline measured (temp project, rc): config set ide_profile opencode REFUSED rc=2 (Valid: claude,codex,cursor,kilo,qwen); kilo passes rc=0; vscode refused rc=2. Four registries today: IDE_DIRS(bootstrap_config:89, 7 hosts, literal), IDE_REGISTRY(ide_utils:13, 7 hosts, canonical facts incl rules_file), SCAFFOLD_IDES(bootstrap_config:119, 6 = IDE_REGISTRY minus windsurf, promise backed by generators), VALID_IDES(skill_profile_detect:24, 5, hardcoded, missing opencode), providers registry = 5 runtime slugs (code, pinned subset). Plan: IDE_DIRS derives from IDE_REGISTRY; VALID_IDES derives from SCAFFOLD_IDES (try-import + annotated mirror, __file__-relative path, idiom per service_doctor_drift._scaffold_ides); fix stale mirror there (missing codex); flip parity-gate pins (unselectable -> empty); extend test_ide_single_source; update host_mechanisms docstring + gate message. Providers gap (no opencode provider) stays pinned, not implemented — scope_exclude.
- 2026-10-06T19:21:25Z [implementation] — Implemented: IDE_DIRS derives from IDE_REGISTRY, VALID_IDES derives from SCAFFOLD_IDES (guarded import + annotated mirrors); stale drift-scanner mirror gained codex; parity-gate message and host_mechanisms header say the collapse is done; pins flipped (unselectable==[]), ide_single_source gained derivation+negative tests. Local: 117+154+65 targeted green; mypy configured run 562 files clean; ruff clean. AC probe on working-tree scripts: opencode rc=0, kilo rc=0, vscode rc=2 with 6-host Valid list.
- 2026-10-06T19:25:30Z [implementation] — AC-1: check config set ide_profile opencode rc=0 and kilo rc=0 measured on working-tree scripts (temp project probe); before: opencode rc=2. AC-2: check IDE_DIRS derives from IDE_REGISTRY, VALID_IDES derives from SCAFFOLD_IDES (guarded imports + annotated mirrors); divergence held by test_ide_dirs_is_derived_from_the_registry + test_ide_profile_alphabet_is_exactly_the_scaffold_list + TestHostRegistryCollapseHolds; verify #3536: 973 passed, gates 8 pass/1 skip(hadolint). AC-3: check negative unknown ide rejected on every surface — test_unknown_ide_is_unknown_on_every_surface (absent in all four registries, providers.get KeyError); live vscode probe rc=2 with 6-host Valid list. AC-4: check doctor/coverage unchanged — enforcement_coverage + doctor drift gates green in verify #3536; IDE_REGISTRY facts untouched, coverage reports keep reading it. Domain: a consumer project can now select opencode as its profile because bootstrap scaffolds it — verified against a real temp project, not only in-process tests.
- 2026-10-06T19:25:57Z [done] — AC-1: ✓ tausik config set ide_profile opencode rc=0, kilo rc=0 (live probe, working-tree scripts, temp project). AC-2: ✓ tests/test_ide_single_source.py::test_ide_dirs_is_derived_from_the_registry + ::test_ide_profile_alphabet_is_exactly_the_scaffold_list + tests/test_cross_model_parity_gate.py::TestHostRegistryCollapseHolds; verification_run #3536 (973 passed). AC-3: ✓ tests/test_ide_single_source.py::test_unknown_ide_is_unknown_on_every_surface + live vscode probe rc=2 (6-host Valid list). AC-4: ✓ verification_run #3536 gates: enforcement_coverage + doctor drift suites green (IDE_REGISTRY facts untouched; coverage reports keep reading it).
