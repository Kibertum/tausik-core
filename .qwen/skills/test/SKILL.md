---
name: test
description: "Run or write tests. Use when user says 'run tests', 'write tests', 'test coverage', 'add tests', 'test this'. Args: [file|directory|function]"
effort: medium
context: inline
---

# /test — Tests

Auto-detect test framework, run existing tests, generate missing ones.
## Phase 0 — Load Context

1. **Check active task** (if any):
   ```bash
   .tausik/tausik task list --status active
   ```
   If active → `.tausik/tausik task show {slug}` → extract role, stack.

2. **Load role profile**: Read `agents/roles/{role}.md` — follow the role's /test modifiers.
   - developer: unit tests first, mock sparingly, test contracts
   - qa: test pyramid, negative testing, coverage gaps, flaky = bug
   - architect: integration tests, contract tests, failure modes

3. **Load stack guide**: Read `agents/stacks/{stack}.md` — use the stack's testing section for framework, fixtures, patterns.

## Algorithm

### 1. Detect Test Framework
Use stack guide if loaded. Otherwise scan project root for signals:
- `pytest.ini`, `conftest.py`, `pyproject.toml [tool.pytest]` → **pytest**
- `jest.config.*`, `package.json[jest]` → **jest**
- `vitest.config.*` → **vitest**
- `*.test.go` → **go test**
- Fall back to file extension heuristics if needed

### 2. Determine Mode
- `$ARGUMENTS` = "run" or empty → run all tests
- `$ARGUMENTS` = file/directory → run tests for that scope
- `$ARGUMENTS` = "gen" or "generate" → generate tests for changed files
- `$ARGUMENTS` = "coverage" → run with coverage report
- `$ARGUMENTS` = "e2e" → run E2E tests (see E2E section below)

### 3. Run Tests
Execute with verbose output using stack-appropriate commands:
```bash
# pytest
pytest {scope} -v --tb=short

# jest / vitest
npx jest {scope} --verbose
npx vitest run {scope}

# go
go test {scope} -v -race

# coverage
pytest --cov={module} --cov-report=term-missing
npx jest --coverage
```

### 4. Generate Tests (if mode = gen)
Follow stack guide conventions for test file naming and patterns.
For each target file:
1. Read the source file completely
2. Identify all public functions/methods/classes
3. Generate tests covering:
   - Happy path (normal inputs)
   - Edge cases (empty, null, boundary values)
   - Error cases (invalid inputs, exceptions)
4. Place test file in the project's test directory convention
5. Run generated tests to verify they pass

### 5. Report Results
```
## Test Results: {scope}

Stack: {stack} | Framework: {framework}
Status: {PASS|FAIL} ({passed}/{total})
Duration: {time}

### Failures
{test_name}: {error message + relevant stack trace}

### Coverage (if requested)
{module}: {percentage}%
Uncovered lines: {list}
```

**Suggest next:** If called standalone (not from /ship): "Run `/review` if not yet reviewed, then `/ship` to close and commit." If called from /ship: return results silently, no suggest.

## E2E Testing (Playwright)

When `$ARGUMENTS` = "e2e" or project has `playwright.config.*`:

### 1. Detect Playwright Setup
```bash
# Check for existing Playwright config
ls playwright.config.* 2>/dev/null
npx playwright --version 2>/dev/null
```

If not installed, guide user: `npm init playwright@latest`

### 2. Run E2E Tests
```bash
# Run all E2E tests (headless)
npx playwright test --reporter=list

# Run specific test file
npx playwright test {file}

# Run with UI for debugging
npx playwright test --ui
```

### 3. Generate E2E Tests
When asked to generate E2E tests for a user flow:
1. Identify the flow (login, checkout, signup, etc.)
2. Read relevant page components to understand selectors
3. Generate test using Playwright's Page Object pattern:
   - Navigate to URL
   - Fill forms, click buttons using accessible selectors (`getByRole`, `getByLabel`, `getByText`)
   - Assert visible outcomes (text, URLs, element states)
4. Prefer `getByRole`/`getByLabel` over CSS selectors — more resilient to UI changes

### 4. Report E2E Results
Include: browser(s) tested, screenshot paths on failure, trace file links.

## SENAR Integration

After running tests:
1. **Log results** to active task: `.tausik/tausik task log {slug} "Tests: {passed}/{total}"`
2. **If tests fail on code that was working before** — this may be a defect in a completed task. Create a defect task: `.tausik/tausik task add "Fix: description" --defect-of {parent-slug} --role developer`
3. **Map test results to acceptance criteria** — if the task has AC, note which criteria are now verified by passing tests and which still need manual verification.
4. **Document test-related dead ends**: if a testing approach didn't work (e.g., mocking strategy failed), record it: `.tausik/tausik dead-end "approach" "reason"`

## Fake Test Detection

After generating tests (mode = gen) or when reviewing existing tests, scan for fake test patterns:

| Pattern | Example | Action |
|---------|---------|--------|
| **No assertions** | `def test_foo(): result = foo()` (no assert) | Add meaningful assertions |
| **Tautological** | `assert x == x`, `assert True` | Replace with behavior check |
| **Hardcoded expected = actual** | `assert foo() == foo()` (re-calling) | Use independent expected value |
| **Conditional assertion** | `if condition: assert ...` (condition always False) | Make assertion unconditional |
| **Skip without reason** | `@pytest.mark.skip` (no message) | Add reason or remove skip |
| **Empty test body** | `def test_something(): pass` | Implement or delete |
| **Assert in bare except** | `try: assert ... except: pass` | Remove bare except |

**Note:** `@pytest.mark.skip(reason="...")` with a reason is NOT a fake test.

If any generated test matches a fake pattern — fix it immediately before reporting success. If reviewing existing tests and fake patterns are found — report as HIGH severity.

## Rules

- NEVER modify source code to make tests pass — report the bug instead
- NEVER write tests that test implementation details — test behavior through public API
- Generated tests MUST be runnable immediately — verify by running them
- Generated tests MUST pass fake test detection — no tautological or empty assertions
- Use project conventions for test file naming and location (check stack guide)
- If no test framework detected, ask user which to use
- Log test results if task is active: `.tausik/tausik task log {slug} "Tests: {passed}/{total}, coverage {pct}%"`

## Gotchas

- **pytest on Windows** may have path issues with `conftest.py` — always run from project root.
- **Generated tests that import from `src/`** need correct `sys.path` setup or `pyproject.toml [tool.pytest] pythonpath`.
- **Flaky tests are bugs** — don't retry and hope. Investigate timing, shared state, or network dependencies.
