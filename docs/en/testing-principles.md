**English** | [Русский](../ru/testing-principles.md)

# Testing principles

<!-- doc-map: reader=user; zone=quality -->

Guidance for contributors and agents working on TAUSIK core (`scripts/`, MCP handlers, gates, hooks). For command-level verification flow, see [Verify / QG glossary](verify-glossary.md) and [`verify`](cli.md) in the CLI reference.

## When to add or extend a test

| Situation | Action |
|-----------|--------|
| Behaviour changed | Add or update assertions for the new observable outcome (CLI text, service method, DB row shape, gate decision). |
| Bug fixed | Add a **regression** test that would fail on the old code and passes now (or document why integration/E2E cannot cover it). |
| Refactor only | Extend tests only where coverage on critical paths would otherwise drop; avoid churn for purely cosmetic edits. |

## New file vs extending an existing test module

- **Prefer basename alignment with production code.** Changing `scripts/foo_bar.py` usually belongs in `tests/test_foo_bar.py`. That keeps **scoped pytest** (basename → `tests/test_<name>.py`) predictable when you close tasks with `relevant_files`. Resolver logic lives near `gate_test_resolver.py` (see [Architecture — Testing](architecture.md#testing)).
- **Create a new `tests/test_<area>.py`** when you introduce a new surface or the existing module would mix unrelated domains (harder navigation and review).
- **Extend an existing file** when the scenario belongs to the same feature cluster and file size stays manageable.

## Scoped gates and task closure

`task done` / `tausik verify --task <slug>` use `relevant_files` to select affected
test files. The selector follows changed test files, basename matches, direct
imports, narrow `CROSSCUTTING_SCOPE` declarations, observed coverage, and the
pytest fixture subtree of a changed `conftest.py`. Every selected file and its
reason are written to `.tausik/evidence/affected-tests-<digest>.json`; verify
returns only the path, so the explanation does not inflate model-visible output.

Selection is fail-open. Invalid test-root configuration, an unreadable or
unparseable candidate, a malformed dependency declaration, an unmapped Python
source, or a security-sensitive path runs the complete applicable default lane.
An empty `relevant_files` declaration still cannot certify a task and does not
silently start a full run. The full release battery, including slow tests, remains
a release-candidate lane (`TAUSIK_VERIFY_FULL=1`). Align `relevant_files` with
what you actually changed.

**Citing a test as AC evidence.** On the `substantial`/`deep` tiers QG-2 needs
at least one criterion backed by a test that EXISTS. A citation is read in the
ecosystem's own form, not only Python's (GitLab #16): a path under `tests/`,
`test/`, `__tests__/` or `spec/` with any recognised source extension, or a
file NAMED as a test — `test_x.py`, `x_test.go`, `x_tests.rs`, `x.test.ts`,
`x.spec.js`, `x_spec.rb`, `XTest.java` — anywhere in the project, because Rust
and Go keep tests beside the code; optionally `::name` (a pytest node id, an
`fn`/`func`/`it("…")` the file declares). The file must exist inside the
project as normalised — `tests/../src/x.py` is a source file, not a test — and a
named symbol must be declared in it. The refusal says which of two things went
wrong: `CITED BUT FORM NOT RECOGNISED` or `CITED BUT NOT RESOLVED`.

## Negative: anti-patterns

- **Copy-paste tests without new behaviour.** Duplicating a case under another name, or asserting the same invariant twice, does **not** increase safety—it raises noise and CI cost. Either cover a **new** branch/invariant, consolidate duplicates, or delete redundant examples.
- **Using “no tests” as default for sensitive code.** Paths such as `scripts/hooks/`, auth, or billing are **not** exempt from verification—they require discipline and often **extra** scrutiny, not fewer tests.

## Development cost and verification scope (1.11)

Verify changed behavior and affected consumers during implementation. Reuse a
valid receipt only while its inputs/configuration remain unchanged. Broader
integration checks follow changes to shared boundaries; the complete maintained
suite, including the slow lane, is a release-candidate requirement. A default
`pytest` run excludes slow tests and must report that exclusion.

Do not add a new test solely because a file changed. Existing behavior coverage
can suffice for a refactor; documentation and cosmetic edits need their relevant
checks rather than invented unit tests. Remove editorial wording/count pins,
redundant existence assertions and smoke tests with no behavior assertion.
Keep public contracts, security negatives, evidence integrity and upgrade/restore
coverage. Record consolidation by family, naming the surviving behavior check
or why the removed constraint was not a product requirement.

Use small real fixtures with planted faults instead of repeatedly scanning the
mutable development repository/database. Expensive whole-tree integration belongs
in the release lane when it supplies distinct evidence. Narrow cross-cutting
selectors to actual dependencies; every applicable consumer remains selected.
Measure executed/deselected cases, runtime, output and model retries separately.
Fewer tests alone do not prove token or subscription savings. Temporary exceptions
name the check, scope, replacement evidence and expiry; no blanket gate bypass.

## Validation output and recovery

Agent-facing `verify` and `task done` return one bounded verdict. Successful
gate bodies and repeated progress lines are not streamed into model context;
failures retain at most the actionable excerpt and an artifact address.

Every rendered run writes complete UTF-8 gate output to
`.tausik/verification/verify-<run>.log` and machine-readable verdict, gate and
pytest counts to the adjacent `.json` file. Display-only `head`/`tail` filters
never truncate the durable log. Open the log for omitted diagnostics and the
JSON sidecar for automation. If either write fails, the verdict says that the
artifact is unavailable instead of implying that omitted detail was preserved.

## References

- [Architecture](architecture.md) — repo layout, gates, testing commands.
- [Verify / QG glossary](verify-glossary.md) — Verify-First contract, test shim, cache bypass for sensitive files.
- [CLI — Verification](cli-quality.md#verification) — `verify`, cache TTL, `task done`.
