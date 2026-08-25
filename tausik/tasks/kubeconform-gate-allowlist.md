---
slug: kubeconform-gate-allowlist
title: "kubeconform missing from gate executable allowlist (breaks the k8s gate that replaced kubeval)"
status: done
epic: null
story: null
complexity: simple
role: devops
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/gate_command_policy.py"
  - "tests/test_stack_iac.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-26T12:02:07Z"
---

## Goal

The kubernetes stack.json now issues a kubeconform gate command (replacing archived kubeval), but ALLOWED_GATE_EXECUTABLES in gate_command_policy.py whitelists kubeval/kube-score and NOT kubeconform — so the new default/override gate fails _validate_custom_gate (HIGH-1 class). Add kubeconform to the allowlist, keep kubeval, regression-pin.

## Acceptance Criteria

1. "kubeconform" is in ALLOWED_GATE_EXECUTABLES (gate_command_policy.py), placed with the IaC tooling next to kubeval. 2. A test asserts a gate command 'kubeconform -summary -ignore-missing-schemas {files}' passes _validate_custom_gate / validate_default_gate_command. 3. Existing gate-policy tests stay green. 4. tausik verify --task green.

## Plan

## Rollback

## Journal

- 2026-07-26T12:02:05Z [implementation] — AC verified: 1. ✓ 'kubeconform' added to ALLOWED_GATE_EXECUTABLES next to kubeval; bootstrap --ide all redeployed 2. ✓ test_stack_iac.py::test_kubeconform_executable_is_allowlisted asserts membership + _validate_custom_gate(override) is None 3. ✓ test_stack_iac+test_gate_registry+test_gate_command_neutering: 106 passed 4. ✓ verify --task: pytest PASS scoped over test_stack_iac.py 5. ✓ Domain: kubeconform is the maintained k8s validator (kubeval archived); _validate_custom_gate guards config overrides not trusted stack defaults, so the default '| head' pipe is unaffected — a real user enabling the gate now clears validation
