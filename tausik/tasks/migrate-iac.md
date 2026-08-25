---
slug: migrate-iac
title: "Migrate ansible/terraform/helm/kubernetes/docker"
status: done
epic: v16-plugin-arch-and-docs
story: migrate-builtins
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "stacks/{ansible,terraform,helm,kubernetes,docker}/* (NEW), agents/stacks/{ansible,terraform,helm,kubernetes,docker}.md (move)"
scope_exclude: "scripts/*, bootstrap/*"
relevant_files:
  - "stacks/ansible/stack.json"
  - "stacks/terraform/stack.json"
  - "stacks/helm/stack.json"
  - "stacks/kubernetes/stack.json"
  - "stacks/docker/stack.json"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-25T16:48:08Z"
---

## Goal

Create stacks/{ansible,terraform,helm,kubernetes,docker}/stack.json + guide.md (move from agents/stacks/). Migrate ansible-lint/terraform-validate/helm-lint/kubeval/hadolint. IaC signatures (glob *.tf, dir markers playbooks/, k8s/, manifests/) preserved with new format.

## Acceptance Criteria

1. stacks/{ansible,terraform,helm,kubernetes,docker}/{stack.json,guide.md}.
2. ansible owns ansible-lint; terraform owns terraform-validate; helm owns helm-lint; kubernetes owns kubeval; docker owns hadolint.
3. detect использует все три формы: exact (Chart.yaml, Dockerfile), glob (*.tf), dir-marker (playbooks/, roles/, k8s/, manifests/, .kube/).
4. filenames для docker (dockerfile, containerfile), helm (chart.yaml, chart.yml, values.yaml, values.yml), ansible (ansible.cfg).
5. path_hints для ansible (/playbooks/, /roles/), helm (/templates/), kubernetes (/k8s/, /manifests/, /.kube/).
6. agents/stacks/{ansible,terraform,helm,kubernetes,docker}.md → stacks/<name>/guide.md.
7. Registry загружает все 25 стэков errors=[].

## Plan

## Rollback

## Journal

- 2026-04-25T16:48:08Z [implementation] — AC verified: 1. ✓ stacks/{ansible,terraform,helm,kubernetes,docker}/{stack.json,guide.md}. 2. ✓ Каждый owns свой gate. 3. ✓ Все 3 формы detect используются: exact (Dockerfile, Chart.yaml), glob (*.tf), dir-marker (playbooks, roles, k8s). 4. ✓ filenames для docker/helm/ansible. 5. ✓ path_hints для ansible/helm/k8s. 6. ✓ Guides перемещены. 7. ✓ Registry: 25 стэков errors=[]. ALL stacks migrated.
