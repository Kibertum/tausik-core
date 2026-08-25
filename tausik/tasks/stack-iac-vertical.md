---
slug: stack-iac-vertical
title: "IaC vertical — Ansible/Terraform/Helm/K8s/Docker (lint-only honest scope)"
status: done
epic: enterprise-stack-agnostic
story: stack-verticals
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/project_types.py (VALID_STACKS extension)\nscripts/gate_stack_dispatch.py (filename heuristics + .tf ext)\nscripts/default_gates.py (5 new IaC gates)\ntests/test_stack_iac.py (новый)"
scope_exclude: "scripts/project_config.py (импорт уже работает)\nscripts/gate_runner.py (уже re-exports)\nagents/skills/* (отдельно)\nagents/stacks/*.md (можно отложить — descriptions гарантируют honest scope)\nbootstrap detect_stacks (для будущего task — не в scope)"
relevant_files:
  - "scripts/project_types.py"
  - "scripts/gate_stack_dispatch.py"
  - "scripts/default_gates.py"
  - "tests/test_stack_iac.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-25T14:05:30Z"
---

## Goal

Расширить VALID_STACKS: ansible, terraform, helm, kubernetes, docker. Lint-only gates: ansible-lint, terraform validate + tflint, helm lint, kubeval (или kube-score), hadolint (Dockerfile). Каждый с stacks ограничением. Honest documentation: agents/stacks/*.md для каждого нового stack — раздел 'Limitations' прямо говорит "lint/syntax only, NOT policy-as-code (OPA/Sentinel/checkov не included)". Detection: ansible.cfg / *.tf / Chart.yaml / *.yaml(K8s) / Dockerfile presence. Tests: каждый IaC stack triggers свой lint gate, не пытается pytest.

## Acceptance Criteria

- [ ] VALID_STACKS расширен 5 новыми: ansible, terraform, helm, kubernetes, docker
- [ ] gate_stack_dispatch._EXT_TO_STACKS расширен: .tf→terraform, .tfvars→terraform; YAML с особенными именами обрабатывается через filename heuristics (см. ниже)
- [ ] gate_stack_dispatch добавляет filename-based detection (не только по extension): Dockerfile/Containerfile→docker, ansible.cfg→ansible, Chart.yaml/Chart.yml→helm, *.tf→terraform; уже purpose-built helper detect_stacks_from_files расширен или новая функция infer_stacks_from_files учитывает filenames
- [ ] DEFAULT_GATES добавляет 5 lint-only gates: ansible-lint (stacks=['ansible']), terraform-validate (stacks=['terraform']), helm-lint (stacks=['helm']), kubeval (stacks=['kubernetes']), hadolint (stacks=['docker']). Все enabled=False (auto-enable через bootstrap detection)
- [ ] Каждый gate description явно содержит "lint/syntax only — policy-as-code (OPA/Sentinel/Checkov) NOT included" — honest scope
- [ ] STACK_GATE_MAP автоматически содержит ansible→[ansible-lint] и т.д. (через _build_stack_gate_map)
- [ ] tausik stack info terraform/ansible/helm/kubernetes/docker показывает соответствующий lint gate + filesize universal
- [ ] Negative scenarios: pytest skipped на main.tf (test); ansible-lint skipped на main.py (test); IaC gates не активируются на Python project
- [ ] Tests test_stack_iac.py: (a) VALID_STACKS contains all 5; (b) gates registered + STACK_GATE_MAP integration; (c) filename detection (Dockerfile, Chart.yaml, *.tf); (d) extension detection (.tf); (e) honest limitation docs in descriptions; (f) cross-stack filtering — error case Python pytest на Dockerfile

## Plan

## Rollback

## Journal

- 2026-04-25T14:05:29Z [implementation] — AC verified: 1. VALID_STACKS расширен 5 IaC: ansible/terraform/helm/kubernetes/docker ✓ (TestValidStacks 5 PASSED) 2. gate_stack_dispatch._EXT_TO_STACKS: .tf/.tfvars→terraform ✓ (test_filename_extension_detection terraform PASSED) 3. Filename heuristics: Dockerfile/Containerfile/Chart.yaml/ansible.cfg + variants (Dockerfile.prod) ✓ (test_filename_extension_detection 8 PASSED) 4. Path hints для YAML/JSON: playbooks/, roles/, k8s/, manifests/, .kube/ ✓ (test_path_hint_detection 5 PASSED) 5. 5 lint-only gates registered: ansible-lint, terraform-validate, helm-lint, kubeval, hadolint ✓ (TestRegistration parametrized PASSED) 6. STACK_GATE_MAP integration ✓ (test_in_stack_gate_map PASSED) 7. Honest 'NOT policy-as-code'/'NOT vulnerability scanning' в descriptions ✓ (test_descriptions_state_lint_only PASSED) 8. tausik stack info terraform/ansible/helm/kubernetes/docker ✓ (test_stack_info_lists_lint_gate parametrized PASSED) 9. Negative scenarios: pytest skipped на Dockerfile/main.tf, ansible-lint skipped на main.py, hadolint runs on Dockerfile, terraform-validate runs on main.tf, kubeval runs on k8s/deployment.yaml ✓ (TestCrossStackFiltering 6 PASSED) 10. test_unrelated_yaml_not_tagged — bare config.yaml не активирует IaC stacks ✓ 11. Tests test_stack_iac.py 37/37 PASSED + регрессии 148 (gate_stack_aware + go_rust + php_js + stack_info_cli + gates + qg2_gates) PASSED
