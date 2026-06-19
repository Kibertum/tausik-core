---
name: review
description: "Code review — bugs, vulnerabilities, antipatterns."
context: fork
effort: slow
---

# /review — Code Review (SENAR-aligned)

Zero-tolerance review. Find every bug, vulnerability, antipattern, and performance issue.
## Mindset

You are a hostile reviewer. Assume the code is broken until proven otherwise.
- Every line is suspect
- "It works" is not a defense

## Phase 0 — Load Context

Before reviewing, load role and project context:

1. **Check active task** (if any):
   ```bash
   .tausik/tausik task list --status active
   ```
   If active → `.tausik/tausik task show {slug}` → extract role, stack, **acceptance criteria**.

2. **Load role profile**: Read `harness/roles/{role}.md` — follow the role's /review modifiers.

3. **Load stack guide**: Read `harness/stacks/{stack}.md` — use the stack's review checklist.

4. **Load project conventions and dead ends**:
   ```bash
   .tausik/tausik memory search "convention"
   .tausik/tausik memory search "gotcha"
   .tausik/tausik memory list --type dead_end
   ```

## Algorithm

### 1. Determine Scope and Mode
- `$ARGUMENTS` = file path — review that file
- `$ARGUMENTS` = directory — review all source files in it
- `$ARGUMENTS` = "diff" or empty — `git diff HEAD~1` (last commit)
- `$ARGUMENTS` = "staged" — `git diff --cached`
- `$ARGUMENTS` contains "iterate" — enable Iterative Mode (see below). Combine with scope: `/review iterate`, `/review src/ iterate`
- `$ARGUMENTS` contains "lite" — enable Lite Mode (single `tausik-reviewer` sub-agent, structured JSON output, no 6-agent fork). See **Lite Mode** below. Combine with scope: `/review lite`, `/review src/ lite`

### 2. Read Code
Read every file in scope. Do NOT skim. Check `CLAUDE.md` for project rules.

### 3. Launch Parallel Review Agents

Launch **6 specialized review agents** in parallel via the Agent tool. Each agent receives the diff/files in scope, project context (CLAUDE.md, conventions, dead ends), and task info (goal, AC) if available.

> **Subagent model (phase=code-review):** run the 5 domain reviewers on **Sonnet 4.6**
> (`model="sonnet"` in the Agent call) — code review is a Sonnet-tier job. The
> **critic**'s adversarial synthesis benefits from a stronger reasoner — **Opus 4.8**
> (or Fable 5). Omitting `model=` is fine (the subagent inherits the session model);
> this is a cost/quality hint, not a hard requirement. Mapping:
> `docs/ru/research/model-routing-matrix.md`.

**Agent prompt template:**
> Read the agent instructions from `harness/skills/review/agents/{agent}.md`.
> Review the following files: {files_in_scope}.
> Task goal: {goal}. Acceptance criteria: {AC}.
> Stack: {stack}. Role: {role}.
> Project conventions: {conventions}. Dead ends: {dead_ends}.
> Return findings in the agent's output format.

Launch all 6 agents in a **single message** with parallel Agent tool calls:

| Agent | File | Focus |
|-------|------|-------|
| **quality** | `harness/skills/review/agents/quality.md` | Bugs, security, race conditions + SENAR 28-item checklist |
| **implementation** | `harness/skills/review/agents/implementation.md` | Goal achievement, AC coverage, wiring |
| **testing** | `harness/skills/review/agents/testing.md` | Test quality, coverage, fake test detection |
| **simplification** | `harness/skills/review/agents/simplification.md` | Over-engineering, unnecessary complexity |
| **documentation** | `harness/skills/review/agents/documentation.md` | Missing docs, changelog, CLAUDE.md |
| **critic** | `harness/skills/review/agents/critic.md` | Adversarial: find **3 weaknesses** the others miss (hidden failure modes, silent contract drift, assumption gaps) |

**Apply stack-specific review checklist** from the stack guide — include it in the quality agent prompt.

### 4. Collect, Deduplicate, and Verify

After all agents return:

1. **Collect** all findings from 5 agents into a single list
2. **Deduplicate** — if two agents flag the same file:line, merge into one issue with the higher severity
3. **Verify each finding** — read the actual code at file:line and confirm the issue exists:
   - If confirmed → mark as CONFIRMED
   - If false positive → mark as FALSE POSITIVE and discard
4. **Re-prioritize** — adjust severity if context changes the assessment

### 5. Run Quality Gates
```bash
python scripts/gate_runner.py review --files {files_in_scope}
```
- Gate results are appended to the review output
- Log results if task is active: `.tausik/tausik task log {slug} "Gates: {summary}"`

### 6. Compile Final Report

Merge all confirmed findings into the standard Output Format (see below).

### 7. Record Review Run (SENAR Rule 10.15)

The `/review` skill runs **6 adversarial agents** — this is an **L3 review** (external/adversarial reviewer, separate context from the implementer). Record it so ADR (Adversarial Defect Rate) can be tracked across the project.

```bash
.tausik/tausik review record \
  --task {slug} \
  --type L3 \
  --critical {N_critical} \
  --warnings {N_high_plus_medium} \
  --notes "{1-line summary or commit/PR url}"
```

Notes:
- `--type L1` = author self-review, `L2` = peer (same context), `L3` = adversarial/external (this skill).
- ADR is shown in `tausik metrics` once any L3 reviews exist.
- Skip if no active task — store as `--task <related-slug>` if reviewing arbitrary code (still surfaces in `tausik review list`).

### Fallback: Single-Pass Review

If the Agent tool is unavailable or agents fail, fall back to a **single-pass review** covering all 5 domains yourself. Use the severity categories:

**CRITICAL** — Null access, race conditions, injection, auth bypass, data loss
**HIGH** — Missing validation, error swallowing, hardcoded secrets, N+1
**MEDIUM** — God functions, duplication, magic numbers, over-engineering
**LOW** — Misleading names, dead code, missing docs

## Output Format

```
## Review: {scope}

Role: {role} | Stack: {stack}
Verdict: {FAIL|PASS WITH ISSUES|PASS}
Issues: {N} (Critical: {C}, High: {H}, Medium: {M}, Low: {L})

### Critical

**[C1] {Title}** — `{file}:{line}`
{problematic code}
Problem: {why this breaks}
Fix: {fixed code}

### High / Medium / Low ...

### SENAR Checks
- Scope creep: {clean / flagged items}
- Dead end violations: {none / repeated dead ends}
- AC coverage: {all met / gaps found}

### Summary
{1-2 sentences: overall assessment}
{Top 3 things to fix before merge}
```

**Suggest next:** If issues found: "Fix issues and re-run `/review`." If clean: "Run `/ship` to test, close task, and commit."

## Separate Context Review

**Key principle:** The implementer and reviewer should be different instances.

The parallel review agents (step 3) inherently provide separate context — each agent runs in its own fresh context with only the diff and project context. This satisfies the "separate context" requirement by default.

### When to additionally use a standalone subagent review

- When `$ARGUMENTS` contains "separate" or "independent" — launch one extra holistic review agent in addition to the 5 specialized ones
- When the diff touches >5 files — the extra holistic view catches cross-cutting issues the specialists might miss

## Adversarial Mode (built-in)

The **critic** agent is launched as one of the 6 parallel reviewers on every `/review` run — adversarial review is default, not an opt-in mode. The critic's job is explicitly to find **3 weaknesses the other 5 agents miss** (see `harness/skills/review/agents/critic.md` for its hunting grounds).

### Deep mode (extra pass)

When `$ARGUMENTS` contains "adversarial" or "deep", run **two critic passes** sequentially, feeding the first critic's findings into the second so it hunts for what even the first critic missed. Stop if the second pass finds only LOW severity.

### When to auto-escalate to deep mode

- Reviewing security-sensitive code (auth, payments, crypto, session handling)
- Diff touches >5 files across multiple modules
- User says "deep", "thorough", "hostile"

## Lite Mode

When `$ARGUMENTS` contains "lite", **skip the 6-agent fork** and invoke the single Claude-native sub-agent `tausik-reviewer` instead. Trade adversarial breadth for token cost: one consolidated review per file, structured JSON output, main context stays clean.

### When to pick Lite over the default

- Low-stakes diff (docs, comment-only changes, trivial refactor)
- Fast preview before a full `/review`
- Token budget concern (sub-agent main-context overhead is roughly 6× lower than the parallel-6 flow)

Skip Lite for security-sensitive code (auth, payments, crypto), >5-file diffs, or anything you would otherwise route through Adversarial deep mode — those still want the 6-agent breadth + critic.

### Algorithm

1. Resolve scope (same as step 1 of standard `/review`).
2. Read project context (CLAUDE.md, conventions, dead ends, active task) — same as Phase 0.
3. Invoke the sub-agent in a single tool call:
   ```
   Agent(
     subagent_type="tausik-reviewer",
     prompt="Review files: {scope}. Task goal: {goal}. AC: {AC}. Stack: {stack}. Role: {role}. Conventions: {conventions}. Dead ends: {dead_ends}.",
   )
   ```
4. Sub-agent reads `harness/skills/review/agents/quality.md` + `docs/en/security.md` + `docs/en/security-checklist.md` from disk at runtime, applies them, returns one JSON object: `{scope, critical[], high[], medium[], low[], meta}`.
5. Render the JSON in the **standard Output Format** (re-use the template in step 6 of standard flow).
6. Run quality gates (same as step 5).
7. Record the run as `--type L3` if the sub-agent reports its independence (it runs in a separate context — same SENAR semantics as the parallel-6 flow).

### Fallback

If `tausik-reviewer` sub-agent is missing (`.claude/agents/tausik-reviewer.md` absent — bootstrap may not have copied it on legacy installs), fall back to standard 6-agent flow and emit a one-line warning.

## Iterative Mode

When `$ARGUMENTS` contains "iterate", run a review→fix→verify loop instead of a single pass.

### Algorithm

1. **Run standard review** (all phases above, including Separate Context / Adversarial if triggered)
2. **Classify results**: count CRITICAL + HIGH issues
3. **If 0 CRITICAL+HIGH** → emit final report, stop. **REVIEW_DONE.**
4. **If issues found** → fix all CRITICAL and HIGH issues in-place
5. **Log iteration** (if active task): `.tausik/tausik task log {slug} "Review iteration {N}: {fixed_count} issues fixed"`
6. **Re-review** — go to step 1, but scope is now only the files touched by fixes
7. **Repeat** until REVIEW_DONE or iteration limit reached

### Exit conditions

| Condition | Action |
|-----------|--------|
| 0 CRITICAL+HIGH issues | Stop. Emit final report with MEDIUM/LOW as advisories |
| 5 iterations reached | Stop. Emit warning + remaining issues list |
| Same issues persist across 2 iterations | Stop. Flag as "stalemate — manual intervention needed" |

### Iteration output

Each iteration produces a compact summary (not the full report):

```
### Iteration {N}
Fixed: {list of fixed issues}
Remaining: {C} critical, {H} high, {M} medium, {L} low
Status: {continuing | done | limit reached | stalemate}
```

The **final report** after the loop uses the standard Output Format with an added iteration summary header:

```
## Review: {scope} (iterative, {N} iterations)
...standard format...
### Iteration History
- Iteration 1: found {X} issues, fixed {Y}
- Iteration 2: found {X} issues, fixed {Y}
- ...
```

### Without active task

If no active task exists, iterative mode still works but logs a warning:
"No active task — iteration progress will not be logged to task history."

### When to suggest iterative mode

- After a standard review finds ≥3 CRITICAL+HIGH issues, suggest: "Run `/review iterate` to fix and verify all issues in a loop."

## Rules

- NEVER say "looks good" or "nice work"
- NEVER skip a section because "it's probably fine"
- If 0 issues found: "No issues found — request a second review."
- Prioritize: security > correctness > performance > style
- Log review result if task is active: `.tausik/tausik task log {slug} "Review: {verdict}, {N} issues"`
- **Document dead ends**: if the review reveals a pattern that doesn't work, add it: `.tausik/tausik dead-end "approach" "reason"`
- **Defect tracking**: if bugs are found in completed tasks, create fix tasks with `--defect-of`: `.tausik/tausik task add "Fix: description" --defect-of parent-slug --role developer`

## Gotchas

- **`git diff HEAD~1` shows nothing if nothing is committed** — check `git status` first.
- **Large diffs (>500 lines)** degrade review quality. Split into focused reviews.
- **Review your own generated code** — don't skip review just because you wrote it.
