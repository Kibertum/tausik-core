---
slug: k8s-stack-kubeconform
title: "Modernize kubernetes stack gate: kubeval → kubeconform"
status: done
epic: null
story: null
complexity: simple
role: devops
stack: null
tier: light
call_budget: 20
defect_of: null
scope: "stacks/kubernetes/stack.json, stacks/kubernetes/guide.md"
scope_exclude: "other stacks/* dirs; scripts/*; .claude/* deployed copies; the stack registry/loader code."
relevant_files:
  - "stacks/kubernetes/stack.json"
  - "stacks/kubernetes/guide.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-26T10:23:42Z"
---

## Goal

Replace the kubernetes stack's deprecated `kubeval` validator (archived by its maintainer, superseded by kubeconform) with `kubeconform`, so the shipped default IaC gate points at a supported tool — bringing kubernetes to the same current-tool quality bar as terraform/helm/ansible.

## Acceptance Criteria

1. `stacks/kubernetes/stack.json` replaces the `kubeval` gate with a `kubeconform` gate: correct command (e.g. `kubeconform -summary -output text {files}`), `enabled:false` (opt-in preserved), `severity:warn`, `stacks:["kubernetes"]`, sane timeout. 2. `stacks/kubernetes/guide.md` updated — kubeconform is the primary schema validator; kubeval noted as deprecated/legacy. 3. `tausik stack lint` reports the kubernetes decl as schema-valid. 4. Detection signatures unchanged (k8s/, manifests/, .kube/). 5. NEGATIVE/EDGE: gate stays disabled-by-default so projects without the binary aren't blocked; an absent `kubeconform` binary fails-open (warn), never a hard block; and NO other stack's stack.json is modified (git diff limited to stacks/kubernetes/).

## Plan

## Rollback

`git checkout -- stacks/kubernetes/` reverts both files to the kubeval baseline; no DB or deployed-state change to undo.

## Journal

- 2026-07-26T10:23:24Z [implementation] — AC1 gate=kubeconform (-summary -ignore-missing-schemas), enabled=false, severity=warn, stacks=[kubernetes]. AC2 guide.md updated, kubeval marked deprecated. AC3 schema-valid via registry validate_decl (NONE errors) + registry loads clean; note: stack lint only covers user overrides so built-in validated via validator directly. AC4 detection unchanged (k8s/manifests/.kube). AC5 opt-in preserved (disabled default, warn=fails-open), git diff limited to stacks/kubernetes/ only. Domain: kubeconform is the maintained successor; no other IaC stack ships a deprecated tool now.
- 2026-07-26T10:23:35Z [implementation] — AC verified: 1. ✓ gate=kubeconform (command `kubeconform -summary -ignore-missing-schemas {files}`), enabled=false, severity=warn, stacks=[kubernetes], timeout=60. 2. ✓ guide.md schema-validation line now kubeconform, kubeval noted as archived predecessor. 3. ✓ decl schema-valid: registry validate_decl returned NONE errors, default_registry loads with no errors (stack lint only covers .tausik/stacks user overrides, so built-in validated via the schema validator directly). 4. ✓ detection unchanged (k8s, manifests, .kube dir-markers + path_hints). 5. ✓ opt-in preserved: enabled=false so a project without the binary is never blocked; severity=warn fails-open not hard-block; git diff limited to stacks/kubernetes/{stack.json,guide.md} only, no other stack touched.
