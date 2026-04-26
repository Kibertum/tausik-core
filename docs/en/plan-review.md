# Engineering Review Protocol

Used by /plan skill for pre-planning engineering review.

## Size Detection

Auto-determine from complexity score (step 1):
- **6+ points → BIG** (full 4-section review with pauses)
- **3-5 points → MEDIUM** — use SMALL review but mention if any section warrants deeper look
- **1-2 points → SMALL** (quick review, 1 question per section)

If the auto-detected size feels wrong, tell the user and ask to override.

## BIG Change — Full Review

Work through all 4 sections. After each section — **stop and ask for feedback** before proceeding.

For each issue found, provide:
1. Clear description of the problem
2. Why it matters (concrete consequence)
3. 2–3 options (including "do nothing" if reasonable), for each:
   - **Effort**: low / medium / high
   - **Risk**: low / medium / high
   - **Impact**: low / medium / high
   - **Maintenance cost**: low / medium / high
4. Your recommended option and why

Be opinionated. Don't give neutral summaries — give verdicts.

### Section A — Architecture Review

Evaluate:
- Overall system design and component boundaries
- Dependency graph and coupling risks
- Data flow and potential bottlenecks
- Scaling characteristics and single points of failure
- Security boundaries (auth, data access, API limits)

Highlight top 3–4 issues. Then:
> "Architecture review done. Approve to continue to Code Quality review?"

### Section B — Code Quality Review

Evaluate:
- Project structure and module organization
- DRY violations — flag duplication aggressively
- Error handling patterns and missing edge cases
- Technical debt risks
- Areas that are over-engineered or under-engineered

Highlight top 3–4 issues. Then:
> "Code quality review done. Approve to continue to Test review?"

### Section C — Test Review

Evaluate:
- Test coverage (unit, integration, e2e)
- Quality of assertions
- Missing edge cases
- Failure scenarios that are not tested

Highlight top 3–4 issues. Then:
> "Test review done. Approve to continue to Performance review?"

### Section D — Performance Review

Evaluate:
- N+1 queries or inefficient I/O
- Memory usage risks
- CPU hotspots or heavy code paths
- Caching opportunities
- Latency and scalability concerns

Highlight top 3–4 issues. Then:
> "Performance review done. Ready to create the task plan. Approve?"

## SMALL Change — Concise Review

One focused question per section, no deep dives:

- **Architecture**: Does this fit existing patterns or introduce a new one?
- **Code quality**: Any obvious DRY violations or edge cases to handle?
- **Tests**: What's the minimum test coverage needed here?
- **Performance**: Any obvious bottlenecks for this change?

Output as a brief summary, then:
> "Quick review done. Ready to create the task plan. Approve?"

## Rules

- Do NOT create any tasks in DB until the user approves after the final review section
- Do NOT assume priorities — ask if unclear
- Prefer explicit recommendations over neutral options
- "Engineered enough" = not fragile, not over-engineered
