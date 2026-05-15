**English** | [Русский](/ru/docs/testing-principles)

# Testing principles

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

`task done` / `tausik verify --task <slug>` use `relevant_files` to map edited paths to test files. Empty `relevant_files` intentionally falls back to the **full** suite (safe default). Security-sensitive paths bypass verify-cache reuse but **still run gates** ([Verify / QG glossary](verify-glossary.md)). Align `relevant_files` with what you actually changed.

## Negative: anti-patterns

- **Copy-paste tests without new behaviour.** Duplicating a case under another name, or asserting the same invariant twice, does **not** increase safety—it raises noise and CI cost. Either cover a **new** branch/invariant, consolidate duplicates, or delete redundant examples.
- **Using “no tests” as default for sensitive code.** Paths such as `scripts/hooks/`, auth, or billing are **not** exempt from verification—they require discipline and often **extra** scrutiny, not fewer tests.

## See also

- [Architecture](architecture.md) — repo layout, gates, testing commands.
- [Verify / QG glossary](verify-glossary.md) — Verify-First contract, test shim, cache bypass for sensitive files.
- [CLI — Verification](cli.md#verification) — `verify`, cache TTL, `task done`.
