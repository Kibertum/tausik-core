---
slug: a-passing-irrelevant-gate-unblocks-an-empty-verify
title: "Квитанция подписывается, когда пропущен единственный значимый гейт: холостой PASS снимает защиту от полностью пропущенного прогона"
status: done
epic: release-110-deferred-from-19
story: release110-verification-is-cheap
complexity: medium
role: backend
stack: python
tier: moderate
call_budget: 35
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/verify_zero_gate.py"
  - "scripts/gate_runner.py"
  - "scripts/verify_cached_run.py"
  - "scripts/verify_no_test_mapped.py"
  - "tests/test_unscoped_gate_is_not_evidence.py"
  - "tests/conftest.py"
  - "tausik/gates.json"
  - "stacks/go/stack.json"
  - "stacks/rust/stack.json"
  - "stacks/javascript/stack.json"
  - "stacks/typescript/stack.json"
  - "stacks/php/stack.json"
  - "stacks/swift/stack.json"
  - "stacks/flutter/stack.json"
  - "stacks/java/stack.json"
  - "stacks/terraform/stack.json"
scope_paths:
  - "scripts/verify_zero_gate.py"
  - "scripts/gate_runner.py"
  - "scripts/verify_cached_run.py"
  - "scripts/verify_no_test_mapped.py"
  - "stacks/*/stack.json"
  - "tests/*.py"
  - "CHANGELOG*.md"
  - "docs/ru/*.md"
  - "docs/en/*.md"
  - "tausik/gates.json"
scope_tools: []
depends_on: []
completed_at: "2026-09-23T22:52:27Z"
resolution: null
resolution_reason: null
tracker_refs:
  - "github#14"
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

НАБЛЮДЕНО В СЕССИИ #158, run #1643. Verify без объявленной области дал: hadolint PASS, pytest SKIP, exit=0, 'Receipt: signed'. Изменения были ЧИСТО питоновские — то есть единственный относящийся к делу гейт не выполнялся, а прошёл тот, которому нечего было проверять.

Справка verify честно предупреждает: 'Without a declared scope every scoped gate is SKIPPED and the receipt certifies nothing'. И тут же обещает защиту: 'Without --no-tests-expected an all-skipped run blocks'. Защита ключается на ПОЛНОСТЬЮ пропущенный прогон, поэтому один холостой PASS её снимает. Чем больше в наборе гейтов, не относящихся к изменению, тем надёжнее она не срабатывает.

ЧЕГО ЗАДАЧА НЕ УТВЕРЖДАЕТ: я не проверял, примет ли task done --ac-verified такую квитанцию. Первый шаг задачи — выяснить это ЭКСПЕРИМЕНТОМ, а не рассуждением. Если ниже по течению есть отсечка, дефект сводится к обещанию в справке; если нет — закрытие может опираться на квитанцию, не удостоверяющую ничего.

НАПРАВЛЕНИЕ: считать не 'сколько гейтов пропущено', а 'выполнился ли хоть один гейт, ОТНОСЯЩИЙСЯ к изменённым файлам'. Гейт, которому нечего делать, не должен считаться свидетельством.

КРИТЕРИИ: 1) прогон, где все относящиеся гейты пропущены, а нерелевантные прошли, БЛОКИРУЕТСЯ или явно помечается в квитанции как не удостоверяющий изменение; 2) НЕГАТИВНЫЙ: тест воспроизводит run #1643 (питоновская правка, pytest SKIP, hadolint PASS) и падает, если исход зелёный; 3) существующие законные прогоны с --no-tests-expected по-прежнему проходят — правка не превращает документационные задачи в неразрешимые.

## Acceptance Criteria

1. A verify run in which every gate scoped to the declared files was skipped and only gates with no file scope executed is NOT a certifying run: without --no-tests-expected it blocks as no-test-mapped and names the unscoped gates that ran; with it, it is recorded no_tests_declared=1 and the close needs --gates-not-applicable.
2. NEGATIVE: a test reproduces the observed case (python change, pytest SKIP for no test mapping, an unscoped gate PASS) and fails if the run comes back green and certifying; the experiment on a temp project before the fix is logged.
3. NEGATIVE: legitimate runs keep passing — a run with a scoped gate that executed, a run whose gates are ALL unscoped (legacy custom config), and a --no-tests-expected run of a documentation task.
4. The project-wide test/build gates of the shipped stacks (go, rust, javascript, typescript, php, swift, flutter, java, terraform) declare file_extensions, so a polyglot change in their language still counts as executed; stack schema validation accepts them.

## Plan

## Rollback

git revert: защита добавляется в одном месте подсчёта исходов гейтов

## Journal

- 2026-09-23T22:43:26Z [implementation] — Experiment BEFORE the fix (scratch probe, temp project, managed config: ruff/ruff_format/filesize off, custom gate 'irrelevant' = python -c pass with no file scope): verify --relevant-files mod.py -> [SKIP] pytest (no test mapping), [PASS] irrelevant, passed=True, Receipt signed, handle minted; task done --ac-verified --verify-handle -> rc 0, 'Task t completed'. So there is NO downstream cutoff: the closure rests on a receipt that certified nothing about mod.py. hadolint itself no longer reproduces #1643 (docker stack.json now declares file_patterns), but every undeclared project-wide gate (go test ./..., npm test, cargo test, custom commands) does.
- 2026-09-23T22:50:26Z [implementation] — AC-1: ✓ tests/test_unscoped_gate_is_not_evidence.py::test_verify_blocks_the_observed_run_and_names_the_wide_gate and tests/test_unscoped_gate_is_not_evidence.py::test_the_declared_exemption_still_records_and_asks_for_the_ack — blocks as no-test-mapped naming the project-wide gate; under --no-tests-expected recorded no_tests_declared=1. Live re-run of the temp-project experiment after the fix: verify rc 1 'Only project-wide gate(s) ran (irrelevant)'; with the flag the handle is refused without --gates-not-applicable.
- 2026-09-23T22:50:26Z [implementation] — AC-2: ✓ tests/test_unscoped_gate_is_not_evidence.py::test_the_observed_run_is_not_an_execution — negative, reproduces the #1643 shape; mutation (entry condition disabled) turned 2 tests red, restored. Pre-fix experiment logged above.
- 2026-09-23T22:50:26Z [implementation] — Root cause: verify_zero_gate.run_state and the all-skipped entry in verify_cached_run counted ANY executed gate as evidence, so a gate with no file scope (no file_extensions/file_patterns/{files}) passing while every file-scoped gate skipped made the run EXECUTED — green, signed and closable. Fix: results carry file_scoped (gate_runner, declares_file_scope); unscoped_only() demotes such a run into the all-skipped branch.
- 2026-09-23T22:50:27Z [implementation] — AC-3: ✓ tests/test_unscoped_gate_is_not_evidence.py::test_legitimate_runs_stay_executions and tests/test_unscoped_gate_is_not_evidence.py::test_a_run_where_a_scoped_gate_ran_is_still_green — negative: scoped gate ran, all-project-wide config, legacy row without the flag stay EXECUTED; 1284 related gate/verify/stack/bootstrap tests pass.
- 2026-09-23T22:50:27Z [implementation] — AC-4: ✓ tests/test_unscoped_gate_is_not_evidence.py::test_a_gate_is_scoped_only_when_it_says_which_files — stacks go/rust/javascript/typescript/php/swift/flutter/java/terraform declare file_extensions (js-test: JS+TS union); tests/test_stacks_extensible.py and test_stack_registry.py pass (schema accepts). helm-lint left project-wide: its chart files have no stack extension to borrow.
- 2026-09-23T22:50:27Z [implementation] — Ratchets moved down in passing: test_dedupe baseline 289/684 -> 288/682, scripts/verify_handle_rules.py removed from ruff_format legacy list (formatted by the refusal-kind task). CHANGELOG ruff_format entry now names the Verify-First side effect (memory #732).
