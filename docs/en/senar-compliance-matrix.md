**English** | [Русский](../ru/senar-compliance-matrix.md)

# SENAR v1.5 Core — Compliance Matrix

<!-- doc-map: reader=maintainer; zone=reference -->

**Claimed edition: SENAR v1.5 Core**, self-declared (owner's decision #376, 2026-09-23). SENAR v1.5 was released on 2026-09-07; until its public mirror carries it, the release procedure refuses a TAUSIK tag (task `senar-claim-names-the-published-edition`).

**Assessed:** 2026-09-23, TAUSIK 1.10 development line, against the corpus TAUSIK reads through `senar_standard_corpus` (`tausik drift --detector senar`).

> **What the rows are.** Each row names a mechanism that exists in this repository and the code that implements it. `tests/test_senar_compliance_matrix.py` counts each section against the corpus — SENAR Core has 8 rules, a Start Gate and a Done Gate, three gate properties it requires (a, c, e) and two metrics, and the tables below have exactly that many rows — and the self-check resolves every citation. There is no conformance percentage: a count of implemented mechanisms is checkable, a percentage of a standard is not.

## Core rules

| Rule | TAUSIK mechanism | Enforcement | Evidence |
|------|------------------|-------------|----------|
| 1. Task Before Code | A write with no active task is refused by the PreToolUse hook; shell writes get the same verdict | Hard (hook) | `scripts/hooks/task_gate.py` `main()` |
| 2. Scope Boundaries | Writes outside the active task's `scope_paths` are refused; a medium/complex task cannot start without a declared scope | Hard (hook + QG-0) | `scripts/hooks/scope_write_gate.py` `main()` |
| 3. Verify Against Criteria | `task done` requires per-criterion evidence in the task journal | Hard (QG-2) | `scripts/gate_ac_check.py` `verify_ac()` |
| 4. Tests Verify Requirements, Not Implementation | Substantial/deep tiers whose criteria cite no existing test are refused | Hard (substantial/deep) / Warning | `scripts/gate_ac_check.py` `checklist_hard_block()` |
| 5. Check for Latent Defects | The verification checklist by tier, reported at closure | Warning | `scripts/gate_ac_check.py` `check_verification_checklist()` |
| 6. Zero Tolerance for Incomplete Work | Every plan step done before `task done`; no `--force` on closure | Hard (QG-2) | `scripts/gate_ac_check.py` `verify_plan_complete()` |
| 7. Fix Causes, Not Symptoms | A defect task cannot close without a root cause | Hard (keyword floor) | `scripts/service_task_done_flags.py` `_root_cause_hard_enabled()` |
| 8. Capture Knowledge | Closure warns without a knowledge entry; complex/defect tasks refuse `--no-knowledge`; dead ends are recorded | Warning / Hard (complex, defect) | `scripts/service_knowledge.py` `dead_end()` |

## Core gates

| Gate | TAUSIK gate | What it prevents | Evidence |
|------|-------------|------------------|----------|
| Start Gate | QG-0: goal, criteria, a negative scenario, scope and rollback for medium/complex | Opening a task to modification | `scripts/gate_qg0_check.py` `check_qg0_start()` |
| Done Gate | QG-2: per-criterion evidence, a scoped verify bound to the files it covered, the plan complete | Closing the task and propagating its result | `scripts/gate_ac_check.py` `verify_ac()` |

## Three things that make a gate a gate

| Property | TAUSIK mechanism | Evidence |
|----------|------------------|----------|
| (a) Say what the gate stops | Every gate run records the effect it prevents | `scripts/gate_run_record.py` `record_gate_runs()` |
| (c) Judge the work as it is now | A verify handle is bound to the hash of the files it covered and refused when they changed | `scripts/verify_handle_check.py` `check_handle()` |
| (e) When you cannot tell, the answer is no | A gate that did not run is COULD NOT RUN and blocks | `scripts/gate_outcome.py` `could_not_run()` |

## Core metrics

| Metric | TAUSIK | Evidence |
|--------|--------|----------|
| FPSR — First-Pass Success Rate | Share of done tasks closed on the first attempt | `scripts/backend_queries_metrics.py` `get_metrics()` |
| Dead End Rate | Dead-end records per closed task | `scripts/backend_queries_metrics.py` `get_metrics()` |

## Beyond Core — implemented, not claimed

The claimed edition is Core. The Standard's Foundation configuration asks for more; TAUSIK implements part of it and claims none of it.

| Standard item | TAUSIK | Evidence |
|---------------|--------|----------|
| 10.2 Session duration | An advisory threshold with a documented basis — a signal, not a gate (decision #376) | `scripts/service_session_metrics.py` `session_overrun_warning()` |
| 10.3 Checkpoint cadence | A checkpoint count derived from the session's usage events | `scripts/checkpoint_signal.py` `checkpoint_advice()` |
| 10.5 Periodic audit | Cadence counted in task closures since the last audit | `scripts/service_session_metrics.py` `audit_overdue_closures()` |
| 6.4(c), 3.45 Handoff | Generated from the journal; `session end` writes one when none was | `scripts/handoff_generate.py` `generate()` |
| 8.6(b) Preventive placement | PreToolUse hooks act before the write | `scripts/hooks/task_gate.py` `main()` |
| 8.6(d) Binding to a measured digest | The handle carries the files hash of the verified set | `scripts/verify_handle.py` `mint_handle()` |
| 10.13(a) Model per session | Recorded at session open | `scripts/backend_crud.py` `session_start()` |

## Summary

Rows citing code, by Core section. The beyond-Core table is not counted: it is not claimed.

| Section | Rows citing code |
|---------|------------------|
| Core rules | 8 of 8 |
| Core gates | 2 of 2 |
| Gate properties (a, c, e) | 3 of 3 |
| Core metrics | 2 of 2 |
| **Total** | **15 of 15** |
