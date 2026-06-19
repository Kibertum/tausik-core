---
artifact: adapt
created_at: '2026-06-14T11:00:33Z'
delta_n: 0
links:
- target_slug: renar-adoption
  target_type: spec
- target_slug: renar-first-tz-adapt
  target_type: task
parent_adapt: null
signatures: []
slug: adapt-renar-adoption
status: draft
title: 'ADAPT — engineering interpretation of the RENAR-adoption ТЗ (Decision #109)'
tz_ref: decisions#109
updated_at: '2026-06-14T11:00:33Z'
---

# ADAPT: ADAPT — engineering interpretation of the RENAR-adoption ТЗ (Decision #109)

> Derived view — do not hand-edit. Regenerate: `tausik renar export`.

Source ТЗ: `decisions#109` · status **draft** · delta **0**

## Forward interpretations

### decisions#109 §architecture — "sqlite = single source of truth for RENAR artifacts; ONE-WAY git-exported renar/ tree = V3 diff&review + V4 branching"

SPECs and ADAPTs are stored exclusively in sqlite (the substrate of record). The renar/ markdown+frontmatter tree is a deterministic, derived, one-way export (renar_export.build_tree → write_tree) that gives the substrate its V3 (diff & review) and V4 (branching) surfaces through git, without standing up a separate document service (unlike Kai). `tausik renar export --check` fails CI on a stale tree, the same honesty contract as `doc constants --check`.

- scope-in: Serialize specs + adapts (forward interpretations, backward findings, signatures, delta lineage) + a date-free conformance view to renar/; deterministic slug ordering + stable frontmatter keys; --check drift gate; deletion reconciliation.
- scope-out: No separate doc microservice; files are never hand-edited (regenerated from DB); write-time dated manifest (RENAR-CONFORMANCE.yaml) stays a distinct artifact, excluded from the date-free export view.
- term-mapping: ТЗ → SPEC anchor; "requirements substrate" → .tausik/tausik.db; "derived view" → renar/ tree

### decisions#109 §events-hashchain — "events hash-chain (v34) = V1 immutable history + V6 author/timestamp"

The existing v34 events hash-chain is reused as the substrate evidence for RENAR capability V1 (immutable history — any past state reconstructible) and V6 (identifiable author + timestamp). No new immutability mechanism is built; the conformance generator confirms substrate_v1_v6 from this machinery (git + sqlite WAL + v34 chain) rather than declaring it.

- scope-in: Reuse v34 hash-chain + git + sqlite WAL as the V1–V6 substrate; conformance machinery-confirms substrate_v1_v6.
- scope-out: No bespoke versioning layer; V5 cross-substrate version pin (verifies_version_pin) deferred to RENAR-3 (task_specs has no requirement-version pin yet).

### decisions#109 §honest-target — "Honest target: RENAR-3 (the audit's realistic ceiling). TAUSIK is solo so dual-signature ADAPT is core-mode — say so, don't fake a client."

The conformance generator computes level from live DB state and never declares it (renar_conformance.infer_level). The realistic ceiling is RENAR-3 (verifies_version_pin + coverage_autogen + lifecycle statuses used + QG-0 enforced). RENAR-1 is reached the moment ≥1 honest ADAPT exists (adapt-per-tz satisfied); RENAR-2 needs a signed ADAPT + a delta-ADAPT; RENAR-4/5 are explicitly out of scope as uneconomical for a solo team.

- scope-in: Target RENAR-3; reach RENAR-1 now via this honest ADAPT; honesty contract — level derived from rows, pre-adoption emitted when any mandatory clause unmet.
- scope-out: RENAR-4 (verified-by 100%, pos/neg pairing on first-class TC, ai-provenance, source citation per assertion) and RENAR-5 (multi-model for priority=must, knowledge-graph-primary, hallucination-rate tracking) — not pursued.

## Backward findings

### [gap] (decisions#109 + audit §1.4/§8.2)

The audit (§1.4, §8.2) found that 7 of RENAR's 8 drift-detector classes are unimplemented even on the reference team (kai) — only drift-8 (test-fitting) had a proof. A RENAR adoption that claims substrate-native drift enforcement would overstate reality.

Resolution: TAUSIK implements drift-1 (schema) + drift-7 (TC↔requirement provenance) as warn-only detectors (renar_drift.py), wired into gates. The other 6 classes (lifecycle/SoT/impl/terminology/order/test-fitting) are roadmap, NOT claimed in the conformance manifest — the generator leaves their signals False. Honest partial coverage, not a declared full set.

### [feasibility] (decisions#109 + audit §0/§1.4)

The audit (§0 TL;DR, §1.4) concluded the economically realistic conformance target is RENAR-3, not RENAR-4/5: 100% pos/neg TC parity, source citation per assertion, judge≠production isolation, and multi-model for priority=must describe a mature regulated-industry org, not a solo project. Aiming higher is infeasible without 1–2 quarters of substrate engineering.

Resolution: Decision #109 fixes the honest target at RENAR-3. RENAR-4/5 signals are kept False in the generator and their work items are out of scope; the roadmap (Phase 2-4) stops at RENAR-3 (verifies_version_pin, coverage_autogen).

### [contradiction] (decisions#109 + audit §4.3)

RENAR §4.5.3/§7.5 require a dual-signature ADAPT signed by an identifiable Client representative distinct from the author. The audit (§4.3) flags that full ADAPT lifecycle is enterprise-only; even the author team runs it core-mode. TAUSIK is a solo project — there is no separate client, so a literal dual-signature would force a fabricated client identity, contradicting the zero-tolerance-for-fake-data principle.

Resolution: Declare core-mode explicitly (Decision #109: "say so, don't fake a client"). The ADAPT stays draft (architect-only signing available via ed25519 in Phase 2); tz_immutable/RENAR-2 is reached by an architect signature, never by inventing a client. No fake client signature is ever recorded.

### [hidden-assumption] (decisions#109 + audit §3.3.4)

The audit (§3.3 point 4) surfaces a hidden assumption behind source-citation / Hallucination-Rate≤1% (RENAR-4/5): it presumes the ТЗ is structured with stable, reproducible anchors ([TZ-XXX §Y line Z]). Most real ТЗ are polished prose or interview transcripts where line anchors do not survive a reflow, so citation-based hallucination metrics are unreliable on typical inputs.

Resolution: Out of RENAR-3 scope. Noted as a RENAR-4 prerequisite: if pursued, ТЗ structuring (numbered, addressable sections) must precede source-citation enforcement. The generator keeps source_citation=False; no claim is made.

### [scope] (decisions#109 + audit §7.3)

The audit (§7.3) notes RENAR's §11.4 substrate mapping covers V1–V6 well for code/document substrates but only partially for analytical/streaming substrates (ClickHouse, Kafka, Delta) where V3/V4 are not first-class. This is a scope concern for RENAR generally.

Resolution: Out of scope for TAUSIK: its substrate is git + sqlite (+ v34 hash-chain), which fully satisfies V1–V6 (audit §7.2 calls §11 the strongest chapter for code/document substrates). No analytical substrate is in play, so the partial-mapping risk does not apply here — recorded for completeness, not as a TAUSIK gap.
