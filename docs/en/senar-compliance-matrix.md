**English** | [Русский](../ru/senar-compliance-matrix.md)

# SENAR v1.3 Core — Compliance Matrix

**Date:** 2026-04-26 | **Auditors:** 6+ independent review cycles | **Framework:** TAUSIK v1.3.0

## Quality Gates

| Gate | Requirement | Status | Enforcement | Evidence |
|------|-------------|--------|-------------|----------|
| QG-0 | Goal required | ✅ Implemented | Hard block | `service_gates.py` `_check_qg0_start()` — ServiceError |
| QG-0 | AC required | ✅ Implemented | Hard block | `service_gates.py` `_check_qg0_start()` — ServiceError |
| QG-0 | Negative scenario in AC | ✅ Implemented | Hard block | `service_gates.py` `NEGATIVE_SCENARIO_KEYWORDS` (30+ en+ru) |
| QG-0 | Scope warning | ✅ Implemented | Warning | `service_gates.py` — scope + scope_exclude stderr |
| QG-0 | Security surface detection | ✅ Implemented | Warning | `service_gates.py` `SECURITY_KEYWORDS` + `SECURITY_AC_KEYWORDS` |
| QG-2 | AC verified with evidence | ✅ Implemented | Hard block | `service_gates.py` `_verify_ac()` — flag + notes + per-criterion. NO `--force` bypass. |
| QG-2 | Plan steps complete | ✅ Implemented | Hard block | `service_gates.py` `_verify_plan_complete()` — JSON plan check |
| QG-2 | Scoped pytest gate | ✅ Implemented | Hard block | `service_verification.py` — basename match `tests/test_<file>.py` per `relevant_files` (no fallback to full suite when files supplied) |
| QG-2 | Verify cache (10 min TTL) | ✅ Implemented | Skip-on-hit | `verification_runs` table — same `files_hash` + green = skip; security paths bypass cache |
| QG-2 | Quality gates (pytest/ruff) | ✅ Implemented | Hard block | `gate_runner.py` + `service_gates.py` `_run_quality_gates()` |
| QG-2 | Verification checklist (4 tiers) | ✅ Implemented | Warning | `service_gates.py` `_check_verification_checklist()` auto-tier |
| QG-2 | Root cause for defects | ✅ Implemented | Warning | `service_task.py` `task_done()` — keyword check |
| QG-2 | Knowledge capture | ✅ Implemented | Warning | `service_task.py` `task_done()` — memory/decision count |

**Result: 13/13 implemented.** Enforcement levels match SENAR spec.

## Rules

| Rule | Description | Status | Enforcement | Evidence |
|------|-------------|--------|-------------|----------|
| 1 | Task before code | ✅ Implemented | Hard (hook) | `hooks/task_gate.py` blocks Write/Edit without active task |
| 2 | Scope boundaries | ✅ Implemented | Warning | `scope` + `scope_exclude` warned on start for medium/complex |
| 3 | Verify against criteria | ✅ Implemented | Hard | QG-0 + QG-2 combined enforcement |
| 5 | Verification checklist | ✅ Implemented | Warning | 4-tier auto-detection (lightweight/standard/high/critical) |
| 7 | Root cause for defects | ✅ Implemented | Warning | Keyword detection in notes |
| 8 | Knowledge capture | ✅ Implemented | Warning | memory/decision count + `--no-knowledge` opt-out |
| 9.1 | No code without task | ✅ Implemented | Hard (hook) | Same as Rule 1 |
| 9.2 | Session time limit (180 min **active**) | ✅ Implemented | Hard block | Gap-based active time (≥10 min idle = AFK, not counted). `service_gates.py` blocks `task_start` at >180 min active; `status` shows "X min active / Y min wall"; `session extend` and `session recompute` available. Threshold configurable via `session_idle_threshold_minutes`. |
| 9.3 | Checkpoint every 30-50 calls | ✅ Implemented | Warning (auto) | MCP counter in meta table, warning at 40 calls, reset on handoff |
| 9.4 | Document dead ends | ✅ Implemented | Instruction + tooling | `dead_end()` + skill instructions + `/end` check |
| 9.5 | Periodic audit | ✅ Implemented | Warning | `audit_check/mark` + `/start` integration |

**Result: 11/11 implemented.**

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
| MCP coverage 100 tools | ✅ Implemented | `handlers.py` — 90 project + 10 brain |
| Batch execution (`/run`) | ✅ Implemented | `plan_parser.py` + `/run` skill |
| Structured logs (task_logs + FTS5) | ✅ Implemented | `backend_schema.py` + `service_task.py:task_log` |
| Fake test detection | ✅ Implemented | `/review` skill — 10 patterns |
| Skills system | ✅ Implemented | 38 skills (16 core + 22 vendor) — `service_skills.py` + `tausik-skills` repo |
| Hooks system | ✅ Implemented | 19 hooks across PreToolUse / PostToolUse / SessionStart / Stop / pre-commit |
| Roles registry | ✅ Implemented | Hybrid: SQLite metadata + `agents/roles/{role}.md` profile; CRUD CLI + 6 MCP tools |
| Doctor health check | ✅ Implemented | `tausik doctor` + `tausik_doctor` MCP — 4 groups (venv/DB/MCP/skills) + drift |
| Zero-defect skill | ✅ Implemented | `/zero-defect` (Maestro-inspired): read-before-write, verify-before-claim, never-hallucinate-APIs |

## Overall Score

| Category | Implemented | Partial | Missing | Score |
|----------|-------------|---------|---------|-------|
| Quality Gates (13) | 13 | 0 | 0 | **100%** |
| Rules (11) | 11 | 0 | 0 | **100%** |
| Metrics (6) | 6 | 0 | 0 | **100%** |
| Explorations (3) | 3 | 0 | 0 | **100%** |
| **Total (33)** | **33** | **0** | **0** | **100%** |

**SENAR v1.3 Core compliance: 100%.** All gaps closed.
