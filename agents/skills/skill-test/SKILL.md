---
name: skill-test
description: "Auto-test a skill by generating scenarios and running them. Args: [skill-name]. Use when user says 'skill-test', 'test skill', 'validate skill'."
effort: slow
context: fork
---

# /skill-test — Skill Auto-Testing

Generates test scenarios for a skill and validates them through subagents.
## Algorithm

### 1. Validate skill exists

Read the skill name from args. Search for `SKILL.md` in:
- `agents/skills/{name}/SKILL.md` (core skills)
- `.claude/skills/{name}/SKILL.md` (installed skills)

If not found — list available skills and stop with error.

### 2. Analyze skill

Read the `SKILL.md` file. Extract:
- **Triggers**: what phrases invoke it
- **Algorithm**: what steps it performs
- **Edge cases**: documented gotchas
- **Inputs/outputs**: what it expects and produces

### 3. Generate test scenarios

Create 3-5 test scenarios covering:
1. **Happy path**: standard invocation with typical input
2. **Edge case**: boundary condition or unusual input
3. **Error handling**: missing required data, invalid state
4. **Integration**: interaction with TAUSIK DB (tasks, sessions)
5. **Idempotency**: running twice should not break state (if applicable)

Each scenario must have:
- **Name**: short descriptive label
- **Setup**: preconditions (e.g., "active task exists")
- **Input**: what the user says or passes
- **Expected behavior**: what should happen (not exact output — behavioral check)

### 4. Run scenarios

For each scenario, launch a subagent:

```
Agent(prompt: "You are testing the /{name} skill.
Scenario: {scenario.name}
Setup: {scenario.setup}
Input: {scenario.input}
Expected: {scenario.expected}

Read the skill at agents/skills/{name}/SKILL.md.
Simulate running this skill mentally (do NOT actually execute MCP tools or CLI).
Analyze: would the skill's algorithm produce the expected behavior given this input?
Check for: missing error handling, unclear instructions, logic gaps.

Report:
- PASS: skill handles this correctly
- FAIL: describe what would go wrong and why
- WARN: handles it but with potential issues",
subagent_type: "general-purpose")
```

### 5. Report results

Show a summary table:

| # | Scenario | Result | Details |
|---|----------|--------|---------|
| 1 | Happy path | PASS | ... |
| 2 | Error handling | FAIL | Missing check for... |

**Overall verdict:**
- ALL PASS: "Skill is solid."
- Any FAIL: "Skill needs fixes. Suggest creating a task with `/plan fix-{name}-skill`."
- WARN only: "Skill works but has minor gaps."

## Gotchas

- This is a **dry-run analysis**, not live execution. Subagents analyze the SKILL.md logic, they don't run actual commands.
- Core skills (in `agents/skills/`) should be edited at root, not in `.claude/skills/` (generated copy).
- For live testing of skills, use `/dispatch` with real task scenarios instead.
