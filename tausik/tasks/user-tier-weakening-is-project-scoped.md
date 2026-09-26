---
slug: user-tier-weakening-is-project-scoped
title: "Ослабление в user-тире может быть ограничено проектом, а машинное ослабление называется таковым"
status: done
epic: release-19-renar-conformance
story: release19-proof-integrity
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 60
defect_of: null
scope: "config_trust (чтение тиров + resolve), config_trust_weakening (отчёт), два вызывающих места, тесты, docs, CHANGELOG."
scope_exclude: "Не менять GUARDS, не отвергать машинные ослабления (операторские файлы продолжают работать), не переписывать операторские config.json, не трогать managed-путь, не релизить."
relevant_files:
  - "scripts/config_trust.py"
  - "scripts/config_trust_projects.py"
  - "scripts/config_trust_weakening.py"
  - "scripts/tausik_utils.py"
  - "scripts/project_config.py"
  - "scripts/project_cli_doctor.py"
  - "tests/test_config_trust.py"
  - "tests/test_doctor_trust_tier_weakening.py"
  - "docs/en/config-trust-tiers.md"
  - "docs/ru/config-trust-tiers.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "scripts/config_trust.py"
  - "scripts/config_trust_projects.py"
  - "scripts/config_trust_weakening.py"
  - "scripts/tausik_utils.py"
  - "scripts/project_config.py"
  - "scripts/project_cli_doctor.py"
  - "tests/test_config_trust.py"
  - "tests/test_doctor_trust_tier_weakening.py"
  - "docs/en/config-trust-tiers.md"
  - "docs/ru/config-trust-tiers.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - "tausik/tasks/user-tier-weakening-is-project-scoped.md"
  - "tausik/stories/release19-proof-integrity.md"
scope_tools: []
depends_on: []
completed_at: "2026-09-12T13:55:16Z"
resolution: null
resolution_reason: null
---

## Goal

Баг 1.8 (gotcha #690, решение #363): ~/.tausik/config.json на машине владельца держит обходы двух конкретных проектов (RENAR: gates.bootstrap_drift.enabled=false; vaflower: task_done.auto_verify=true), и оба молча действуют в каждом проекте машины, потому что config_trust отвергает ослабление из тира проекта, а единственный доверенный канал — общий для всех проектов. Ввести в user- и managed-тирах секцию projects: {<абсолютный путь проекта>: {overlay}}, которая применяется ТОЛЬКО к проекту с тем же нормализованным (realpath+normcase) каталогом; ключ projects никогда не попадает в эффективный конфиг; повреждённые записи игнорируются с предупреждением; без известного каталога проекта ни одна scoped-запись не применяется (fail-closed). doctor различает machine-scoped и project-scoped ослабления: machine-scoped в силе получает подсказку перенести под projects.<путь>; scoped-записи чужих проектов не применяются и считаются в OK-строке.

## Acceptance Criteria

AC-1: resolve(project, project_dir=P) applies a user-tier projects[<P spelled with other slashes/case>] overlay to P — a guarded weakening there is in effect for P. AC-2 (negative): the same overlay is NOT applied when resolving another project Q, and not applied when project_dir is None; the projects key itself never appears in the effective config. AC-3 (negative): a non-dict projects value or a non-dict entry is ignored with a logged warning, never a crash and never elevated privilege; managed projects entry still wins over user projects entry. AC-4: the machine-wide (top-level) user-tier key keeps today's behaviour for every project. AC-5: doctor/summary names a machine-scoped weakening in effect with the hint to scope it under projects.<path>; a project-scoped weakening for THIS project is reported as project-scoped; scoped entries of other projects are not reported as in effect and are counted in the OK detail. AC-6: both live callers (tausik_utils.load_effective_config, project_config.load_config_with_rejections) pass the project directory; hooks therefore honour scoped entries. AC-7: docs/{en,ru}/config-trust-tiers.md document the projects section and the leak it closes; CHANGELOG EN/RU; focused pytest, ruff, mypy, dedupe without new groups, signed verify.

## Plan

[{"step": "config_trust: projects-\u0441\u0435\u043a\u0446\u0438\u044f, project_key, load_trusted_layers(project_dir), resolve(project_dir=)", "done": true}, {"step": "\u0414\u0432\u0430 \u0432\u044b\u0437\u044b\u0432\u0430\u044e\u0449\u0438\u0445 \u043c\u0435\u0441\u0442\u0430 \u043f\u0435\u0440\u0435\u0434\u0430\u044e\u0442 \u043a\u0430\u0442\u0430\u043b\u043e\u0433 \u043f\u0440\u043e\u0435\u043a\u0442\u0430", "done": true}, {"step": "config_trust_weakening: scope machine/project, \u043f\u043e\u0434\u0441\u043a\u0430\u0437\u043a\u0430, \u0441\u0447\u0451\u0442\u0447\u0438\u043a \u0447\u0443\u0436\u0438\u0445 \u0437\u0430\u043f\u0438\u0441\u0435\u0439", "done": true}, {"step": "\u0422\u0435\u0441\u0442\u044b AC-1..AC-6 (red first), docs EN/RU, CHANGELOG", "done": true}, {"step": "ruff, mypy, dedupe, bootstrap --check, signed verify", "done": true}]

## Rollback

git revert одного коммита: секция projects перестаёт читаться, поведение тиров возвращается к машинному; операторские файлы не меняются.

## Journal

- 2026-09-12T13:47:42Z [implementation] — Steps 1-3: config_trust_projects.py (new, 68 lines) holds PROJECTS_KEY, project_key (realpath+normcase), scoped_entry (fail-closed on None project, malformed → warning), machine_wide; config_trust composes them in effective_layer/load_trusted_layers(project_dir) and resolve(project_dir=); tausik_utils.load_effective_config, project_config.load_config_with_rejections and doctor pass the directory; weakening report gains scope machine/project, the move-it hint and the foreign-entry count. Existing 96 trust tests green; config_trust stays 471 lines (a first cut at 516 was split for the filesize gate). scope_paths widened to project_cli_doctor.py which the report needs for the directory.
- 2026-09-12T13:50:05Z [implementation] — AC verified: AC-1 ✓ TestProjectScopedEntries::test_entry_applies_to_its_project_however_the_path_is_spelled (forward slashes + upper case key → auto_verify in effect, 'projects' absent). AC-2 ✓ Negative: test_entry_does_not_leak_to_another_or_unknown_project[other-project|unknown-project]. AC-3 ✓ Negative: test_malformed_scoping_is_ignored_not_elevated[section-not-object|entry-not-object] logs a warning and keeps only the machine-wide key; test_managed_entry_outranks_user_entry_for_the_same_project. AC-4 ✓ test_machine_wide_key_keeps_governing_every_project. AC-5 ✓ doctor: test_a_machine_wide_weakening_in_effect_says_so_and_points_at_the_scoped_form, test_a_weakening_scoped_to_this_project_is_reported_as_such, test_another_projects_scoped_entry_is_counted_not_applied. AC-6 ✓ test_the_hook_reader_honours_a_scoped_entry (tausik_utils.load_effective_config) and project_config.load_config_with_rejections/doctor pass the directory (read in source; live doctor line unchanged on this repo, where both operator entries are machine-wide and tightened back). AC-7 ✓ docs/{en,ru}/config-trust-tiers.md new section, CHANGELOG EN/RU; 107/107 in the two test files, 11 of them red on the pre-change code; ruff, mypy (6 files), dedupe 322, bootstrap --check clean; signed verify below. Domain: the operator's two live workarounds on this machine can now be moved under projects[<RENAR path>] and projects[<vaflower path>] and stop governing tceh-x and this repository.
