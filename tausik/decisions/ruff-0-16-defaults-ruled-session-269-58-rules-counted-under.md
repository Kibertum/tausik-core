---
slug: ruff-0-16-defaults-ruled-session-269-58-rules-counted-under
task: rule-on-ruff-016-new-defaults
date: "2026-09-23"
edges: []
---

## Decision

RUFF 0.16 DEFAULTS RULED (session #269; 58 rules counted under the project config). ADOPTED, findings fixed: PLE2515, PLE2502 (invisible/bidi chars now escapes), PLR0124 (x!=x -> math.isnan), B017 (8 blind raises(Exception) narrowed), PYI036. REJECTED as deliberate: DTZ001/005/011 (local times intended; naive datetime is test input), PLR0133 (tests pin facts), PLW1510 (196 subprocess.run read returncode by design), TRY004. REJECTED as cosmetic churn over legacy-unformatted files (reasoning of #386): I001, ISC004, UP*, FURB*, SIM* except SIM115, PIE*, RET501, C4xx, PERF102, RUF012/015/022/023/046/059/007, FLY002, PYI034/041. SPLIT OUT, each finding needs judgment: S110/S112 (79, silent-errors principle), SIM115 (125 open() without context manager), RUF100 (546 stale noqa) — tasks in deferred-110-audit-hygiene.

## Rationale
