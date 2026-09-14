---
artifact: conformance
blocked-at: scope-applicability
conformance-declaration: non-conformant
level: null
level-signals:
  adapt_per_tz: false
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
mandatory-clauses-basis:
  adapt-per-tz:
    basis: measured
  closed-lists-backward-findings:
    basis: measured
  disclaimer: 'What each confirmation above RESTS ON. `measured`: derived from this
    database, with a violating state turning it false. `declared`: judged over a declaration
    this manifest publishes. `machinery`: true because the running framework enforces
    it, the premise watched by the named repository test. `vacuous`: the obligation
    has no subject here, the arrival of one watched by the named ratchet. A constant
    is not a measurement, and this block is what keeps the two from reading alike.'
  implements-edge-subsystem:
    basis: vacuous
    premise-watched-by: renar_br_premise.premise_broken via tests/test_renar_br_premise.py,
      on the canonical schema (conftest.canonical_schema_db — what `tausik init` creates,
      from git, so it RUNS IN CI); it reads the schema for a `level` column admitting
      `subsystem`, a BR-named table or an `implements` column, not a list of names
  quality-gates-closed-list:
    basis: declared
  sot-inversion:
    basis: machinery
    premise-watched-by: tests/test_renar_mandatory_clauses.py::test_the_machinery_sot_inversion_rests_on_is_switched_on
      (verify_first blocking and enabled in the live gate registry; task_gate.py wired
      on Write|Edit in bootstrap_hooks)
  spec-types-closed-list:
    basis: measured
  substrate-v1-v6:
    basis: machinery
    premise-watched-by: tests/test_events_chain.py (V1 hash-chain of the event journal)
      and tests/test_renar_manifest_chain.py (the manifest's git audit journal)
  tc-pos-neg-pairing:
    basis: vacuous
    premise-watched-by: renar_tc_premise.classes_appeared via tests/test_renar_tc_premise.py,
      on the live project database — the only database the declaration describes;
      and the ADR-013 guard test (tests/test_spec_types_closed_list.py), which watches
      the same premise more broadly but SKIPS IN CI, because .tausik/ is gitignored
      and no workflow creates the database (task db-gated-ratchets-never-run-in-ci)
mandatory-clauses-confirmed:
  adapt-per-tz: false
  closed-lists-backward-findings: true
  implements-edge-subsystem: true
  quality-gates-closed-list: true
  sot-inversion: true
  spec-types-closed-list: true
  substrate-v1-v6: true
  tc-pos-neg-pairing: true
pre-adoption: false
renar-version: '1.1'
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
