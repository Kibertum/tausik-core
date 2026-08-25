---
slug: iac-bootstrap-detection
title: "Wire IaC stack detection into bootstrap STACK_SIGNATURES"
status: done
epic: v15-maturity
story: iac-stack-detection
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "bootstrap/bootstrap_config.py"
  - "agents/stacks/terraform.md"
  - "agents/stacks/ansible.md"
  - "agents/stacks/helm.md"
  - "agents/stacks/kubernetes.md"
  - "agents/stacks/docker.md"
  - "tests/test_iac_bootstrap_detection.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-25T14:59:14Z"
---

## Goal

Close the framework's biggest credibility gap: the IaC vertical (terraform/ansible/helm/kubernetes/docker) ships with default gates and stack-aware dispatch, but bootstrap's STACK_SIGNATURES has no entries for them — so a fresh Terraform repo will not auto-enable terraform-validate or hadolint, even though both are pre-defined and ready. Add detection patterns for *.tf / playbooks/ / roles/ / Chart.yaml / k8s/ / manifests/ / Dockerfile / Containerfile. Add the 5 agents/stacks/{stack}.md guide files so /task can read stack-specific guidance. Add tests covering: (a) terraform-only repo auto-enables terraform-validate; (b) docker-only repo enables hadolint; (c) mixed Python+Terraform enables both; (d) repos with bare config.yaml don't false-trigger.

## Acceptance Criteria

## Plan

## Rollback

## Journal

- 2026-04-25T14:59:13Z [planning] — AC verified: 1. STACK_SIGNATURES расширен 5 IaC: terraform/ansible/helm/kubernetes/docker ✓ (TestIacSignatures parametrized PASSED) 2. _signature_match handles 3 forms: exact filename, glob pattern (с recursive до 3 levels), directory marker ✓ (TestSignatureMatch 7 PASSED) 3. detect_stacks работает на: terraform-only, docker-only, ansible-via-roles/, helm-via-Chart.yaml, k8s-via-manifests/, mixed Python+Terraform ✓ (TestDetectStacks 7 PASSED) 4. False-positive prevention: bare config.yaml не триггерит IaC stacks ✓ (test_bare_config_yaml_no_false_iac_trigger PASSED) 5. Auto-enable: terraform→terraform-validate, docker→hadolint, ansible→ansible-lint работает через STACK_GATE_MAP ✓ (TestAutoEnable 3 PASSED) 6. agents/stacks/{terraform,ansible,helm,kubernetes,docker}.md созданы с Testing/Validation + Review Checklist + Conventions + Common Pitfalls + honest 'lint-only NOT policy-as-code' ✓ (TestStackGuides 5 PASSED) 7. Negative scenarios: empty repo нет IaC ✓ (test_empty_repo_no_iac); файл с именем 'playbooks' не директория не триггерит ✓ 8. Tests test_iac_bootstrap_detection.py 28/28 PASSED + test_bootstrap_dryrun 4/4 + test_bootstrap_real 4/4 = 36/36 PASSED, 0 регрессий
