---
slug: gate-scope-label-honesty-and-spoofproof
title: "gate scope label: carried in-band via a public prefix any subprocess can spoof, and dropped on error"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 32
defect_of: null
scope: "scripts/gate_command_runner.py, scripts/gate_runner.py, tests/test_gate_command_runner.py (+ a format_results/spoof test)"
scope_exclude: "gate_registry dispatch contract (must stay 2-tuple), service_gates logic beyond confirming no sentinel leak, the scoped-skip / no-impl sentinels"
relevant_files:
  - "scripts/gate_command_runner.py"
  - "scripts/gate_runner.py"
  - "tests/test_gate_command_runner.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-25T06:26:55Z"
---

## Goal

Two defects in the scoped-gate coverage label. (1) format_results (gate_runner) renders ANY gate output line starting with the public 'SCOPE:' prefix as the framework's own coverage disclosure — so an author-controlled stack command (`echo 'SCOPE: full project 500/500' && flake8`) spoofs a full-coverage claim, and a non-scoped gate's stdout can masquerade as a scoped one. A gate must not render checked-party text as framework-trusted output (conventions #169/#297). (2) run_command_gate's spawn-failure and catch-all branches return without _scoped(), so a scoped run that errors loses its 'N of M' qualifier — contradicting the docstring 'every outcome of a scoped run carries its scope: pass, fail, timeout'. Fix both by carrying the label out-of-band: run_command_gate marks the genuine label with a private sentinel a subprocess cannot emit; gate_runner strips it at the single dict-building boundary into result['scope'] (preserving the registry's 2-tuple impl contract) and format_results renders that field instead of grepping stdout. Error/timeout branches route through the same _scoped helper.

## Acceptance Criteria

1. The genuine scope label travels from run_command_gate marked by a PRIVATE sentinel (a NUL-delimited token no real tool emits), not the public 'SCOPE:' prefix alone; gate_runner splits it off at the single point it builds the result dict, into result['scope'], and format_results renders result['scope'] — it no longer greps output for 'SCOPE:'. 2. Spoof test: a NON-scoped command gate whose stdout contains a line 'SCOPE: full project, 500 of 500' is rendered as ordinary body text, NOT as the framework's scope label (result['scope'] is empty for it). 3. A genuinely scoped pytest gate still shows its real 'N of M' label in format_results output. 4. Negative/boundary: a scoped run that fails to spawn (FileNotFoundError) OR times out still carries its scope label (result['scope'] non-empty) — the two error branches route through _scoped. 5. The private sentinel never leaks into stored output: service_gates blocking_failures output and the format_results body contain no sentinel bytes. 6. Registry 2-tuple impl contract (gate,files)->(passed,output) is unchanged; non-command impls (filesize etc.) still work (empty scope). 7. Existing gate tests green + new spoof/error-branch tests added. 8. Full scoped verify green.

## Plan

## Rollback

git revert the commit; the sentinel/out-of-band change is isolated to gate_command_runner + gate_runner + tests. No schema/migration; no data written. Reverting restores the prior in-band SCOPE-prefix rendering.

## Journal

- 2026-07-25T06:26:21Z [implementation] — Implemented out-of-band scope label. gate_command_runner: added private _SCOPE_SENTINEL (NUL-delimited) + public split_scope(output)->(label,body); _scoped now prepends the sentinel; both error branches (FileNotFoundError/spawn + catch-all) route through _scoped (fix #3). gate_runner: imports split_scope, lifts the label into result['scope'] at the single dict-building boundary (2-tuple registry contract preserved), output stored is sentinel-free body; format_results renders result['scope'] instead of grepping stdout for 'SCOPE:' (fix #4 spoof). Tests: rewrote scoped tests to use split_scope; added test_spawn_failure_still_names_its_scope, test_a_subprocess_scope_line_cannot_forge_the_label, test_a_spoofed_scope_line_never_reaches_a_passing_gates_display. Ran 7 gate suites: 240 passed.
- 2026-07-25T06:26:52Z [implementation] — AC verified: 1. ✓ _SCOPE_SENTINEL (NUL-delimited) marks the label; gate_runner split_scope lifts it into result['scope']; format_results reads the field (no stdout grep). verify #1302 rendered the real 'SCOPE: 1 of 321' line end-to-end 2. ✓ Negative/spoof: test_a_subprocess_scope_line_cannot_forge_the_label — a command printing 'SCOPE: full project 500 of 500' yields split_scope label=='' (stays in body); test_a_spoofed_scope_line_never_reaches_a_passing_gates_display asserts '500 of 500' absent from a passing render 3. ✓ test_a_passing_scoped_gate_shows_its_scope_on_screen + live verify #1302 both show the genuine 'NOT the full suite / 1 of N' label 4. ✓ Negative/error: test_spawn_failure_still_names_its_scope (FileNotFoundError) and test_timeout_output_states_it_too both split a non-empty SCOPE label off the failed output — error branches route through _scoped 5. ✓ split_scope strips the sentinel; result['output'] and result['scope'] are sentinel-free; 240 gate-suite tests green incl. service_gates blocking_failures path via test_gates 6. ✓ registry 2-tuple contract untouched (split done in gate_runner, not run_command_gate); test_gate_registry + filesize/non-command impls green 7. ✓ 7 gate suites 240 passed 8. ✓ verify run #1302 exit=0
