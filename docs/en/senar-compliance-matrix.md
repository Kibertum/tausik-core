**English** | [Русский](../ru/senar-compliance-matrix.md)

# SENAR v1.3 Core — Compliance Matrix

**Claimed edition: SENAR v1.3 Core** (owner's decision #336). Later editions are in preparation and are **not** claimed by TAUSIK anywhere.

**Assessment date:** 2026-06-13 | **Auditors:** 6+ independent review cycles | **Framework at assessment:** TAUSIK v1.7.0

> **What the rows below are, and what they are not.** Each row states a mechanism that exists in this repository and names the code that implements it — those statements are checkable here and were checked. The 35 rows were assembled on 2026-06-13 against a **later, still-moving draft** of the standard, and this document previously closed by asserting conformance to that draft. It no longer does: the normative text is not vendored into this tree, so a conformance percentage against the claimed edition **cannot be computed here**, and an uncomputable figure is reported as absent rather than carried over from a different rubric (decision #334). The re-assessment against v1.3 is task `senar-14-conformance-reassessment-and-self-check`; until it closes, read this page as *what is implemented*, not as *a scored conformance claim*.

## Quality Gates

| Gate | Requirement | Status | Enforcement | Evidence |
|------|-------------|--------|-------------|----------|
| QG-0 | Goal required | ✅ Implemented | Hard block | `gate_qg0_check.py` `check_qg0_start()` — ServiceError (via `service_gates.GatesMixin._check_qg0_start` delegator) |
| QG-0 | AC required | ✅ Implemented | Hard block | `gate_qg0_check.py` `check_qg0_start()` — ServiceError (via `service_gates.GatesMixin._check_qg0_start` delegator) |
| QG-0 | Negative scenario in AC | ✅ Implemented | Hard block | `gate_negative_scenario.py` `NEGATIVE_SCENARIO_KEYWORDS` + `has_negative_scenario()` (30+ en+ru); enforced inside `gate_qg0_check.check_qg0_start()` |
| QG-0 | Scope declared | ✅ Implemented | Hard (medium/complex) | `gate_qg0_check.py` `check_qg0_start()` — a medium/complex task with no `scope`/`scope_paths` raises ServiceError (opt out `qg0.scope_hard_gate=false`); simple/unset stays a warning. `scope_exclude` remains an advisory stderr warning. |
| QG-0 | Security surface detection | ✅ Implemented | Warning | `gate_qg0_check.py` `SECURITY_KEYWORDS` + `SECURITY_AC_KEYWORDS` (re-exported by `service_gates` for backward-compat) |
| QG-2 | AC verified with evidence | ✅ Implemented | Hard block | `gate_ac_check.py` `verify_ac()` — flag + notes + per-criterion. NO `--force` bypass. (via `service_gates.GatesMixin._verify_ac` delegator) |
| QG-2 | Plan steps complete | ✅ Implemented | Hard block | `gate_ac_check.py` `verify_plan_complete()` — JSON plan check (via `service_gates.GatesMixin._verify_plan_complete` delegator) |
| QG-2 | Scoped pytest gate | ✅ Implemented | Hard block | `service_verification.py` — basename match `tests/test_<file>.py` per `relevant_files` (no fallback to full suite when files supplied) |
| QG-2 | Verify cache (10 min TTL) | ✅ Implemented | Skip-on-hit | `verification_runs` table — same `files_hash` + green = skip; security paths bypass cache |
| QG-2 | Quality gates (pytest/ruff) | ✅ Implemented | Hard block | `gate_runner.py` + `service_gates.py` `_run_quality_gates()` |
| QG-2 | Verification checklist (4 tiers) | ✅ Implemented | Warning | `gate_ac_check.py` `check_verification_checklist()` + `determine_checklist_tier()` auto-tier — v1.5 also runs `service_ac_evidence.build_report()` to surface per-AC coverage gaps and missing test refs (via `service_gates.GatesMixin._check_verification_checklist` delegator) |
| QG-2 | Root cause for defects | ✅ Implemented | Warning | `service_task.py` `task_done()` — keyword check |
| QG-2 | Knowledge capture | ✅ Implemented | Warning | `service_task.py` `task_done()` — memory/decision count |

**Result: 13/13 implemented.** Enforcement levels match SENAR spec.

## Rules

| Rule | Description | Status | Enforcement | Evidence |
|------|-------------|--------|-------------|----------|
| 1 | Task before code | ✅ Implemented | Hard (hook) | `hooks/task_gate.py` blocks Write/Edit without active task |
| 2 | Scope boundaries | ✅ Implemented | Hard (hook + QG-0) | `hooks/scope_write_gate.py` blocks a Write/Edit outside the active task's `scope_paths`; `hooks/bash_write_gate.py` extends the same verdict to shell writes; QG-0 hard-blocks a medium/complex `task_start` with no scope declared. `scope_exclude` stays advisory. |
| 3 | Verify against criteria | ✅ Implemented | Hard | QG-0 + QG-2 combined enforcement |
| 4 | External adversarial review | ✅ Implemented | Hard (under-evidenced closures) | `risk_l3_trigger.py` blocks an under-evidenced `task_done` until an L3 review is recorded (`tausik review record --type L3`); reviewer is the separate-model, read-only `tausik-external-reviewer` subagent (`external_reviewer.py`, separation of duties). Opt out `risk.l3_block_on_high=false`. The selector describes the closure's evidence; it does not predict defect escape (AUC 0.4820 — decision #212). |
| 5 | Verification checklist | ✅ Implemented | Hard (substantial/deep) / Warning | `gate_ac_check.py` `checklist_hard_block()` hard-blocks substantial/deep planning tiers whose AC cite no existing test; lower tiers get an escalating warning (4-tier auto-detection). Opt out `task_done.checklist_hard=false`. |
| 6 | Rollback plan | ✅ Implemented | Hard (medium/complex) | `gate_qg0_check.py` `check_qg0_start()` — a medium/complex task with no `rollback_plan` raises ServiceError at `task_start`; unset complexity warns. |
| 7 | Root cause for defects | ✅ Implemented | Warning | Keyword detection in notes |
| 8 | Knowledge capture | ✅ Implemented | Warning | memory/decision count + `--no-knowledge` opt-out |
| 9.1 | No code without task | ✅ Implemented | Hard (hook) | Same as Rule 1 |
| 9.2 | Session time limit (180 min **active**) | ✅ Implemented | Hard block | Bounded gap-based active time (`Σ min(Δ, threshold)`, default threshold 10 min — long AFK clipped to threshold, v14b-session-active-time). `service_gates.py` blocks `task_start` at >180 min active; `status` shows "X min active / Y min wall"; `session extend` and `session recompute` available. Threshold configurable via `session_idle_threshold_minutes`. |
| 9.3 | Checkpoint every 30-50 calls | ✅ Implemented | Warning (auto) | MCP counter in meta table, warning at 40 calls, reset on handoff |
| 9.4 | Document dead ends | ✅ Implemented | Instruction + tooling | `dead_end()` + skill instructions + `/end` check |
| 9.5 | Periodic audit | ✅ Implemented | Warning | `audit_check/mark` + `/start` integration |

**Result: 13/13 implemented.**

### Gaps and Plan to Close

| Gap | Plan | Priority |
|-----|------|----------|
| ~~Rule 2: `scope_exclude` not checked~~ | ✅ FIXED — warning added for medium/complex tasks | Done |
| ~~Rule 9.3: No automated checkpoint counter~~ | ✅ FIXED — MCP counter + warning at 40 calls + reset on handoff | Done |

## Metrics

| Metric | Status | Evidence |
|--------|--------|----------|
| Throughput (tasks/session) | ✅ Implemented | `backend_queries.py` `get_metrics()` combined query |
| Lead Time (avg hours) | ✅ Implemented | `backend_queries.py` `get_metrics()` — julianday * 24 |
| FPSR (first pass %) | ✅ Implemented | `backend_queries.py` `get_metrics()` — attempts=1 |
| DER (defect escape %) | ✅ Implemented | `backend_queries.py` `get_metrics()` — DISTINCT defect_of |
| Dead End Rate (%) | ✅ Implemented | `backend_queries.py` `get_metrics()` — memory type=dead_end |
| Cost per Task (hours by complexity) | ✅ Implemented | `backend_queries.py` `get_metrics()` — GROUP BY complexity |

**Result: 6/6 implemented.** All calculations verified correct.

## Section 5.1: Explorations

| Feature | Status | Evidence |
|---------|--------|----------|
| explore_start (time-bounded, 30 min default) | ✅ Implemented | `service_knowledge.py` `exploration_start()` — clamps 1-480 min |
| explore_current (elapsed + over_limit) | ✅ Implemented | `service_knowledge.py` `exploration_current()` — UTC elapsed calc |
| explore_end (findings capture) | ✅ Implemented | `service_knowledge.py` `exploration_end()` — summary + optional task |

**Result: 3/3 implemented.**

## Additional Features (beyond SENAR Core)

| Feature | Status | Evidence |
|---------|--------|----------|
| Multi-language gates | ✅ Implemented | `project_config.py` — 25 default stacks + custom_stacks override |
| MCP coverage 146 tools | ✅ Implemented | `tools.py` + `tools_extra.py` |
| Batch execution (`/run`) | ✅ Implemented | `plan_parser.py` + `/run` skill |
| Structured logs (task_logs + FTS5) | ✅ Implemented | `backend_schema.py` + `service_task.py:task_log` |
| Fake test detection | ✅ Implemented | `/review` skill — 10 patterns |
| Skills system | ✅ Implemented | 13 core skills + 20 official/vendor on demand (bundles via `tausik skill bundle`) — `service_skills.py` + `tausik-skills` repo |
| Hooks system | ✅ Implemented | 22 Python hooks + 1 shell pre-commit across PreToolUse / PostToolUse / SessionStart / SessionEnd / Stop / UserPromptSubmit |
| Roles registry | ✅ Implemented | Hybrid: SQLite metadata + `harness/roles/{role}.md` profile; CRUD CLI + 6 MCP tools |
| Doctor health check | ✅ Implemented | `tausik doctor` + `tausik_doctor` MCP — 4 groups (venv/DB/MCP/skills) + drift |
| Zero-defect skill | ✅ Implemented | `/zero-defect` (Maestro-inspired): read-before-write, verify-before-claim, never-hallucinate-APIs |

## Overall Score

| Category | Implemented | Partial | Missing | Rows citing code |
|----------|-------------|---------|---------|------------------|
| Quality Gates (13) | 13 | 0 | 0 | 12 of 13 |
| Rules (13) | 13 | 0 | 0 | 7 of 13 |
| Metrics (6) | 6 | 0 | 0 | 6 of 6 |
| Explorations (3) | 3 | 0 | 0 | 3 of 3 |
| **Total (35)** | **35** | **0** | **0** | **28 of 35** |

**A "Score" column stood here printing 100% five times, and it is gone.** The paragraph below the table already said the conformance percentage for v1.3 cannot be computed here and is deliberately left unstated (decision #334) — while the table directly above it printed a number. Readers take the number. Session #225 removed the percentage from the prose and did not touch the table; session #238 finished the job.

**What replaces it, and why that is measurable.** The count of implemented mechanisms stays: it is checkable row by row and was checked. A second count is added — how many rows of each section **cite code** that resolves in the tree. The gap between 13 and 7 under "Rules" is the unevenness of the evidence: the other six rows assert a mechanism in prose ("keyword detection in notes", "QG-0 + QG-2 joint enforcement"), and such a statement can be neither confirmed nor refuted by a machine. The "13/13 implemented" total counts them the same as the rest, so the share is named rather than averaged away.

**Claimed edition: SENAR v1.3 Core**, and this page carries no conformance score against it. The standard's normative text is not vendored in this tree — only our own restatement — so any rubric applied here is **ours**, and passing it off as the standard's is not allowed. The checkable property this page genuinely has is the integrity of its citations: `scripts/senar_self_check.py` resolves every function, constant and file named here against the tree and refuses when one is gone. It runs inside `tausik coherence` and in the ordinary test run (`tests/test_senar_self_check.py`). This is not attestation and not certification: §13.7 of the standard states plainly that no certification scheme is created and that the claim is made by the organisation itself.
