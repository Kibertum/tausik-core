---
artifact: conformance
blocked-at: scope-applicability
conformance-declaration: non-conformant
level: null
level-signals:
  adapt_per_tz: true
  adversarial_gate: false
  ai_provenance: false
  continuous_reconciliation: false
  coverage_autogen: false
  delta_tz_artifact: false
  frontmatter_structured: true
  hallucination_rate_tracked: false
  knowledge_graph_primary: false
  lifecycle_statuses_used: true
  multi_model_must: false
  pos_neg_pairing: false
  qg0_enforced: true
  qg2_enforced: true
  reference_validation_hook: true
  schema_validation_hook: true
  source_citation: false
  substrate_v1_v6: true
  tz_immutable: false
  verified_by_100pct: false
  verifies_version_pin: false
mandatory-clauses-confirmed:
  adapt-per-tz: true
  closed-lists-backward-findings: true
  quality-gates-closed-list: true
  sot-inversion: true
  spec-types-closed-list: true
  substrate-v1-v6: true
  tc-pos-neg-pairing: true
pre-adoption: false
renar-version: '1.0'
scope-exclusion:
  clause: §1.5.4
  decided-in: decisions#292
  finding: no independent client representative exists, so the two-party ACTZ signature
    (§5.5.3) is structurally impossible; §1.5.4 withholds the right to claim RENAR-N
    and requires the manifest to declare non-conformance explicitly
  scenario: Internal product без external client
  supersedes: decisions#109 core-mode — the mechanism it rested on was removed by
    ADR-005; zero occurrences remain in standard/, guide/, reference/
senar-version: '1.3'
---

# RENAR Conformance (derived view)

> Derived view — do not hand-edit. Regenerate: `tausik renar export`.

## Declaration: **NON-CONFORMANT** (§1.5.4)

TAUSIK is an internal product with no independent client representative. §1.5.4 withholds the right to claim RENAR-N from such a project and requires this manifest to declare non-conformance explicitly. The RENAR practices stay in force locally; only the claim of a level is withdrawn (decisions#292, supersedes decisions#109).

Re-entry is not a step up the ladder: it runs through §1.4.2 and requires an ACTZ signed by two independent persons (§5.5.3).

Level: **(non-conformant)**

Blocked at: scope-applicability — outside the standard's scope of application (§1.5.4) — no RENAR-N may be claimed regardless of signals

> The date-stamped manifest lives at RENAR-CONFORMANCE.yaml (write-time metadata). This view is date-free so `--check` is stable across days.
