---
slug: renar-first-tz-adapt
title: "Phase 1: author first real ТЗ + ADAPT → flip adapt-per-tz, reach RENAR-1"
status: done
epic: renar-adoption
story: renar-substrate-and-reach-1
complexity: medium
role: architect
stack: python
tier: null
call_budget: null
defect_of: null
scope: "Data authoring only via CLI/MCP: tausik spec add, tausik adapt create/interpret/finding/link, tausik renar conformance/export. Source grounding: docs/audit/_findings/02-renar-analysis.md, Decision #109, prompt.md. Regenerate renar/ tree."
scope_exclude: "Do NOT sign the ADAPT (dual-signature is Phase 2 / RENAR-2 — leaving it draft is the honest RENAR-1 state). Do NOT fabricate findings — each must trace to the audit. Do NOT edit scripts/ (no code change this task). Do NOT create delta-ADAPTs."
relevant_files:
  - "renar/specs/renar-adoption.md"
  - "renar/adapts/adapt-renar-adoption.md"
  - "renar/conformance.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-14T11:03:31Z"
---

## Goal

Dogfood the RENAR artifact flow on a real TAUSIK feature (candidate: the 2.0 global-MCP ТЗ, or the renar-adoption feature itself): create a SPEC acting as the ТЗ anchor, then `tausik adapt create/interpret/finding` capturing the forward engineering interpretation AND backward findings (real gaps/contradictions/hidden-assumptions). Verify `tausik renar conformance` flips from pre-adoption to level RENAR-1 (adapt-per-tz=true) on honest data — no fabricated artifacts.

## Acceptance Criteria

AC-1: a real SPEC-ARCH 'renar-adoption' exists as the ТЗ anchor (Decision #109 architecture: sqlite single source of truth + one-way git-exported renar/ tree + honest conformance, target RENAR-3) — verified via `tausik spec show`. AC-2: an ADAPT 'adapt-renar-adoption' (tz_ref → Decision #109) carries ≥2 forward interpretations (§7.4.3) and ≥4 genuine backward findings grounded in the independent audit (docs/audit/_findings/02-renar-analysis.md) spanning ≥3 distinct closed-7 categories — verified via `tausik adapt show`. AC-3: the ADAPT is linked to the SPEC and to this task. AC-4: `tausik renar conformance` flips from pre-adoption (level:null) to level RENAR-1 (adapt-per-tz=true) on honest data. AC-5: `tausik renar export` regenerates the tree incl. the new spec+adapt and `--check` is clean. AC-6 (negative/boundary): findings with an invalid (non-closed-7) category are rejected by `tausik adapt finding` (ServiceError, no row written), and a finding with an empty description is refused — proving closed-list enforcement holds for the authored data. No fabricated artifacts: every finding traceable to the audit.

## Plan

[{"step": "Create SPEC-ARCH renar-adoption (\u0422\u0417 anchor, Decision #109 architecture)", "done": true}, {"step": "Create ADAPT adapt-renar-adoption (tz_ref \u2192 Decision #109)", "done": true}, {"step": "Add \u22652 forward interpretations (\u00a77.4.3) grounded in Decision #109", "done": true}, {"step": "Add \u22654 backward findings from audit across \u22653 closed-7 categories", "done": true}, {"step": "Link ADAPT \u2192 spec + task; verify negative (invalid category/empty desc rejected)", "done": true}, {"step": "Run renar conformance (expect flip to RENAR-1), renar export, --check clean", "done": true}, {"step": "verify --task + task done --ac-verified", "done": true}]

## Rollback

Artifacts are DB rows: `tausik adapt delete adapt-renar-adoption` + `tausik spec` delete removes them; re-run `tausik renar export` to drop their files from renar/. No schema change, no code change. git revert the renar/ tree commit if needed.

## Journal

- 2026-06-14T11:02:46Z [implementation] — Authored SPEC-ARCH renar-adoption (ТЗ anchor) + ADAPT adapt-renar-adoption: 3 forward interpretations (§7.4.3, grounded in Decision #109 architecture/events-hashchain/honest-target), 5 backward findings across 5 closed-7 categories (gap/feasibility/contradiction/hidden-assumption/scope) all traceable to docs/audit/_findings/02-renar-analysis.md. Linked ADAPT→spec+task. Conformance FLIPPED pre-adoption→RENAR-1 (adapt-per-tz=true, blocked at RENAR-2 honestly). renar export now 4 files, --check clean. AC-6 negative verified: invalid category rejected (argparse choices) + empty description refused (ServiceError), no row written. ADAPT left draft (no fake client signature — core-mode per finding #3).
- 2026-06-14T11:03:31Z [implementation] — AC verified: 1. ✓ SPEC-ARCH renar-adoption (1.0-draft, active) created as ТЗ anchor — verified via adapt_show link + spec exists; content_ref=decisions#109 + audit 2. ✓ ADAPT adapt-renar-adoption has 3 forward interpretations (§7.4.3) + 5 backward findings across 5 closed-7 categories (gap/feasibility/contradiction/hidden-assumption/scope), all traceable to docs/audit/_findings/02-renar-analysis.md — verified via tausik_adapt_show 3. ✓ ADAPT linked to spec renar-adoption + task renar-first-tz-adapt — verified via adapt_show links[] 4. ✓ tausik renar conformance flipped pre-adoption(level:null)→RENAR-1 (pre-adoption:false, adapt-per-tz:true, blocked at RENAR-2) on honest data — CLI output 5. ✓ tausik renar export → 4 files incl specs/renar-adoption.md + adapts/adapt-renar-adoption.md; --check real exit 0 (clean) 6. ✓ Negative: invalid category 'bogus-cat' rejected (argparse closed-list choices); empty description refused with 'Finding description is required.' (ServiceError) — no row written, finding count stayed 5. Domain: ADAPT left draft (no fabricated client signature — core-mode), every finding cites a real audit section.
