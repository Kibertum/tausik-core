---
name: debug
description: "Debug a bug — reproduce, isolate root cause, fix."
context: fork
effort: medium
---

# /debug — Debug

Systematically reproduce, isolate, and fix bugs.
## Phase 0 — Load Context

1. **Check active task** (if any):
   ```bash
   .tausik/tausik task list --status active
   ```
   If active → `.tausik/tausik task show {slug}` → extract role, stack.

2. **Load stack guide**: Read `harness/stacks/{stack}.md` — use stack-specific pitfalls and conventions.

3. **Search for known gotchas**:
   ```bash
   .tausik/tausik memory search "gotcha"
   .tausik/tausik memory search "{error keyword}"
   ```

## Algorithm

### 1. Gather Information
- `$ARGUMENTS` = error message → start from that error
- `$ARGUMENTS` = file → investigate that file
- `$ARGUMENTS` = description → parse the symptom
- Ask user for: error messages, stack traces, steps to reproduce, expected vs actual behavior

### 2. Reproduce the Issue
Before fixing anything, confirm the bug exists:
- Read the relevant code path end-to-end
- Trace the execution flow from input to error
- If tests exist, run them to see failures:
```bash
pytest {test_file} -v --tb=long 2>/dev/null
npx jest {test_file} --verbose 2>/dev/null
```

### 3. Isolate Root Cause
Work backwards from the symptom:
1. Find the exact line where behavior diverges from expectation
2. Check inputs at that point — are they what you expect?
3. Check assumptions — null checks, type expectations, state prerequisites
4. Check stack-specific pitfalls from the stack guide
5. Search for related code that might affect the issue:
   - Recent changes: `git log --oneline -10 -- {file}`
   - Similar patterns: `mcp__codebase-rag__search_code` for the function/variable name; `Grep` only as fallback when RAG is empty or stale

### 4. Identify the Bug Category
- **Logic error**: wrong condition, off-by-one, incorrect operator
- **State error**: unexpected mutation, race condition, stale data
- **Type error**: null/undefined, wrong type, implicit conversion
- **Integration error**: API contract mismatch, schema change, version conflict
- **Environment error**: missing config, wrong env variable, path issue

### 5. Fix
1. Make the minimal change that fixes the root cause
2. Do NOT fix symptoms — fix the cause
3. Consider: does this fix introduce new issues?
4. Add a guard or validation to prevent recurrence

### 6. Verify
- Run the reproduction steps again
- Run related tests
- Check for regressions in adjacent code

### 7. (Optional) Auto-helper for failed verify gates

If your fix triggers a `tausik verify` failure (filesize / ruff / mypy / pytest), invoke the **`tausik-gate-fixer`** sub-agent instead of decoding stderr by hand:

```
Agent(
  subagent_type="tausik-gate-fixer",
  prompt="gate_name=<name>; stderr=<copied verify output>; relevant_files=<list>; task_slug=<slug>; goal=<task goal>",
  model="sonnet",
)
```

> **Subagent model (phase=code-review):** gate-fix diagnosis is a Sonnet-tier job
> (`model="sonnet"`). Omitting `model=` is fine (inherits the session model) — a hint,
> not a requirement. Mapping: `docs/ru/research/model-routing-matrix.md`.

It returns a JSON `{gate, family, plan: [{step, action, target, change, why}], meta}` with a 1-3 step fix plan. Apply the plan, re-run `tausik verify`. The sub-agent is read-only — never applies edits itself. Fall back to the standard manual flow if `.claude/agents/tausik-gate-fixer.md` is missing on legacy installs.

## Output Format

```
## Debug: {issue summary}

### Root Cause
{1-2 sentences explaining what went wrong and why}

### Fix
File: `{file}:{line}`
Before: {buggy code}
After: {fixed code}

### Verification
{test results or manual verification steps}

### Prevention
{how to prevent this class of bug in the future}
```

**Suggest next:** "Run `/ship` to review, test, and commit the fix."

## Rules
- NEVER guess — trace the actual execution path
- NEVER fix symptoms without understanding the root cause
- ALWAYS verify the fix works before reporting it
- If you can't reproduce: say so, and explain what you tried
- Minimal fixes only — don't refactor while debugging
- Save gotchas: `.tausik/tausik memory add gotcha "{title}" "{description}"` for non-obvious bugs
- Log if task active: `.tausik/tausik task log {slug} "Debug: root cause — {description}, fix applied"`

## Code search hierarchy

When tracking the bug across files, prefer the cheapest tool that fits:

1. **`mcp__codebase-rag__search_code`** — first choice for symbols, error messages, patterns, "where is X used". Returns ranked chunks, not full files. Cheapest token-wise.
2. **`Grep`** — only when you already know which file(s) to search in, or when RAG is empty/stale.
3. **`Read`** — only when you have an exact path. Don't `Read` unfamiliar code — use `search_code` first to locate the relevant chunks.

## Gotchas

- **Don't assume the bug is where the error appears** — trace the full call chain. The real cause is often 2-3 frames up the stack.
- **Windows-specific bugs** are common in path handling (`\` vs `/`), encoding (`cp1252` vs `utf-8`), and subprocess (`shell=True` behaves differently).
- **Async bugs** rarely reproduce deterministically — add logging at await points to capture timing.
