---
slug: changed-path-does-not-require-its-artifact-to-move
title: "Изменение пути не требует, чтобы сдвинулся его артефакт: гейт привязан к задаче, а не к путям"
status: done
epic: release-110-deferred-from-19
story: release110-open-defects
complexity: complex
role: architect
stack: null
tier: moderate
call_budget: 60
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/gate_path_artifact.py"
  - "scripts/gate_registry_scoped.py"
  - "tausik/gates.json"
  - "tests/test_gate_path_artifact.py"
  - "tests/test_gates_catch_their_violation.py"
scope_paths:
  - "scripts/gate_path_artifact.py"
  - "scripts/gate_outcome.py"
  - "scripts/gate_registry_scoped.py"
  - "tausik/gates.json"
  - "tests/*.py"
  - "docs/ru/*.md"
  - "docs/en/*.md"
  - "CHANGELOG*.md"
scope_tools: []
depends_on: []
completed_at: "2026-09-24T07:19:43Z"
---

## Goal

Правка в охраняемом пути обязана сопровождаться сдвигом связанного с ним артефакта в ТОМ ЖЕ коммите — правило задаётся картой путей, а не памятью агента.

## Acceptance Criteria

1. Правило задаётся КАРТОЙ «глоб путей -> обязательный артефакт» в конфиге, а не зашито в код. Источник идеи — check-feature-memory.mjs из github.com/kiaquila/unicorn-hub (MIT), где правка productPaths требует spec.md, plan.md и tasks.md в том же PR.
2. Названо отличие от существующего: changelog-гейт привязан к ЗАДАЧЕ, этот — к ПУТЯМ. Пересечение разобрано, дублирование отвергнуто явно, а не оставлено читателю.
3. Правило по умолчанию ВЫКЛЮЧЕНО: включение — решение проекта, потому что чужому репозиторию наша карта путей не подходит.
4. НЕГАТИВНЫЙ сценарий: пустая карта не превращает гейт в тихо проходящий — гейт с пустой картой ПРОПУСКАЕТСЯ вслух, с причиной, а не рапортует успех.
5. НЕГАТИВНЫЙ сценарий: гейт, не сумевший прочитать список изменённых файлов (git недоступен, detached HEAD, пустое дерево), БЛОКИРУЕТ, а не пропускает — fail-closed, как остальные.
6. НЕГАТИВНЫЙ сценарий: тест на случай, когда артефакт ТРОНУТ формально, но пустой правкой (пробел, перевод строки) — такое не засчитывается за сдвиг.

## Plan

## Rollback

git revert коммита; правило по умолчанию выключено и включается конфигом

## Journal

- 2026-09-24T07:19:04Z [implementation] — AC-1: ✓ tests/test_gate_path_artifact.py::test_a_guarded_change_without_its_artifact_blocks and tests/test_gate_path_artifact.py::test_a_guarded_change_with_its_artifact_passes — scripts/gate_path_artifact.py, GateSpec path_artifact (block, commit), map in config gates.path_artifact.map; red proof in tausik/gates.json; EXCUSED entry (driven in its own module on a throwaway repo).
- 2026-09-24T07:19:04Z [implementation] — AC-2: ✓ review — module docstring and CHANGELOG name the difference: changelog gate = task at task done; path_artifact = paths at commit, whoever commits; no duplication.
- 2026-09-24T07:19:05Z [implementation] — AC-3: ✓ tests/test_gate_path_artifact.py::test_it_guards_nothing_until_a_project_declares_a_map — 'off by default' realised as an EMPTY default map (enabled so the degeneracy audit does not read it as a silent block gate); recorded here as the deviation from a literal enabled=false.
- 2026-09-24T07:19:05Z [implementation] — AC-4: ✓ tests/test_gate_path_artifact.py::test_an_empty_map_is_skipped_out_loud_not_passed — negative, NOT_APPLICABLE reason no_path_map.
- 2026-09-24T07:19:05Z [implementation] — AC-5: ✓ tests/test_gate_path_artifact.py::test_an_unreadable_staged_set_blocks — negative, no repository -> COULD_NOT_RUN (blocks).
- 2026-09-24T07:19:06Z [implementation] — AC-6: ✓ tests/test_gate_path_artifact.py::test_a_whitespace_only_touch_of_the_artifact_does_not_count — negative, git diff --cached -w --ignore-blank-lines --numstat. 211 gate/registry/degeneracy tests green.
