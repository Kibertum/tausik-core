---
slug: gate-false-positives-ruff-filesize
title: "Gate false positives: ruff на non-Python, filesize на legitimate large files"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/gate_runner.py, scripts/project_config.py, tests/ (test_gate_runner.py или новый модуль)"
scope_exclude: "Не добавлять language-specific autodetection (config должен быть explicit). Не менять severity/trigger семантику остальных gates. Не трогать pytest gate."
relevant_files:
  - "scripts/gate_runner.py"
  - "scripts/project_config.py"
  - "tests/test_gates.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-22T20:10:04Z"
---

## Goal

Устранить false positives в двух gates: ruff запускается на .yml/.json/.md (не py-файлы); filesize блокирует файлы, которые были over-threshold до этого коммита (legitimate large, e.g. .gitlab-ci.yml 692 lines). Ввести декларативные ключи file_extensions и exempt_files в gate config schema + runner support.

## Acceptance Criteria

1. ruff gate вызван на список из только .yml+.json файлов → возвращает passed=True с сообщением "No files matching..." (subprocess не запускается). 2. ruff gate на смешанном списке ["a.py", "b.yml"] → запускает `ruff check a.py` только (проверяется через mock subprocess.run). 3. filesize gate с exempt_files:[".gitlab-ci.yml"] пропускает нарушающий .gitlab-ci.yml в корне И в deploy/.gitlab-ci.yml (match по basename). 4. filesize gate с exempt_files:["config/huge.json"] пропускает только этот точный path, НЕ пропускает sibling other/huge.json. 5. Negative: ruff gate с реальным Python-нарушением в .py файле всё ещё блочит (no over-exemption) — нельзя обойти гейт расширением списка. 6. Существующие тесты в tests/ для runner проходят без изменений.

## Plan

## Rollback

## Journal

- 2026-04-22T20:00:08Z [implementation] — План реализации: 1. scripts/gate_runner.py::run_command_gate — перед {files} substitution фильтровать files по gate.get('file_extensions'); если список пуст И {files} в cmd → return (True, 'No files matching...') без subprocess. 2. scripts/gate_runner.py::run_filesize_gate — parse gate.get('exempt_files'): entries с '/' → exact path match; без '/' → basename match. Skip matching files до count_lines. 3. scripts/project_config.py::DEFAULT_GATES — добавить file_extensions: ['.py'] в ruff и mypy. 4. tests/test_gates.py — расширить кейсами: file_extensions filter, empty-after-filter → no subprocess (mock), exempt_files basename в root+subdir, exempt_files path exact-only, ruff real violation still blocks (integration через .py-stub).
- 2026-04-22T20:06:49Z [implementation] — AC verified: 1. ruff на только .yml+.json → passed=True "No files matching .py — gate skipped" без subprocess (TestCommandGateFileExtensions::test_empty_after_filter_skips_subprocess с mock calls==[]) ✓ 2. Mixed ["a.py","b.yml"] → ruff check a.py only (test_mixed_list_filtered_to_matching: argv содержит "a.py", не "b.yml") ✓ 3. exempt_files:[".gitlab-ci.yml"] basename скипает root и deploy/.gitlab-ci.yml (test_exempt_by_basename_matches_root_and_subdir: passed=True на обоих 700-строчных файлах) ✓ 4. exempt_files:["config/huge.json"] exact path — sibling other/huge.json всё ещё блочит (test_exempt_by_path_matches_exact_only: passed=False, output содержит other/huge.json но не config/huge.json) ✓ 5. Negative: реальное Python-нарушение всё ещё блочит (test_real_py_violation_still_blocks: FakeFail returncode=1, passed=False, "E501" в output) ✓ 6. Полная сьюта 1105 passed, 2 skipped (включая все 53 pre-existing теста test_gates.py) ✓. Bonus: pre-existing E402/F401 в test_gates.py исправлены (unused ALLOWED_GATE_EXECUTABLES удалён, добавлен noqa: E402 на sys.path-pattern imports).
