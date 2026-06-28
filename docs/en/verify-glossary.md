**English** | [Русский](/ru/docs/verify-glossary)

# Verify / QG terminology — glossary

Single source of truth for words that recur in CLI, MCP, hooks, and tests. Use these terms consistently in docs and agent instructions.

## Core terms

| Term | Meaning | Allowed? |
|------|---------|----------|
| **Verify-First Contract** | Heavy gates run on `verify` (CLI/MCP); `task done` closes using a fresh green entry in `verification_runs` (same `files_hash`, TTL window), not by re-running the full gate subprocess inline. | Default in v1.4+ |
| **Supported opt-out** | Documented knob that changes *where* checks run or *optional* behaviours, still within the framework contract. Not a synonym for skipping evidence or QG-2. | Yes, when intentional |
| **Bypass (policy)** | Circumventing a **mandatory** rule (especially QG-0 / QG-2). In TAUSIK docs, reserve this word for methodology gaps — not for cache behaviour. | No for QG-2 closure |
| **Verify cache bypass** | Security-sensitive paths (e.g. hooks, auth, payment) **never reuse** a cached verify result; gates still run — only the optimisation is skipped. | Yes — strengthens checks |
| **Test shim** | Pytest machinery (see `tests/conftest.py`) that **disables** `_enforce_verify_first` in most tests so the suite stays fast and stable. Not a production setting. | Tests only |

## Supported opt-outs (examples)

| Mechanism | What it does | What it does *not* do |
|-----------|----------------|------------------------|
| `{"task_done": {"auto_verify": true}}` in `.tausik/config.json` | Runs heavy verify gates **inside** `task done` (v1.3-style single step). | Does not remove AC evidence or `--ac-verified`. |
| `task start --force` | Bypasses **session capacity** gate with audit trail. | Does not bypass QG-0 content requirements or QG-2. |
| `git commit --no-verify` | Skips **git** `pre-commit` hook only. | Does not change TAUSIK DB gates or `tausik verify`. |
| `TAUSIK_SKIP_PUSH_HOOK=1` | Documented debug bypass for **push** gate (see `environment.md`). | Not a general QG-2 opt-out. |
| `task done --no-knowledge` | Confirms no knowledge capture; suppresses related warning. | Does not skip verify / AC. |

## Anti-patterns (not supported)

- Treating **verify cache hit** as “no verification” — a hit means a **recent green run** with the same scope; security paths still re-verify.
- Calling undocumented behaviour a “bypass” when it is really **breaking** QG-2 (e.g. expecting `task done` without verify cache and without `auto_verify`).
- Confusing **verify cache bypass** (always re-run for sensitive files) with **QG bypass** — the former runs gates; the latter would skip requirements (not available for `task_done`).

## Test shim (`verify_first` marker)

- Default: autouse fixture `_verify_first_autouse_compat_shim` patches `GatesMixin._enforce_verify_first` to a no-op so existing tests that call `task_done` paths do not need a full verify pipeline. Predicate helper: `tests/verify_first_compat_predicate.py`.
- Tests that assert real verify-first behaviour **must** use `@pytest.mark.verify_first` so the shim is skipped.

This is **test isolation**, not a user-facing opt-out.

## Doc review checklist

When changing verify / QG / cache text:

1. Prefer **opt-out** only for **documented** configuration or env vars.
2. Use **bypass** for **policy** (what agents must not do) or name **verify cache bypass** explicitly when talking about skipping cache reuse.
3. Mention **test shim** only in contributor/test docs, never as an operator workaround.
4. If two sections define the same term differently, treat that as a **doc defect** — align or add a TODO with owner.

## See also

- [Testing principles](testing-principles.md) — when to add tests; anti-pattern: duplicate tests without new behaviour.
- [CLI — Verification](cli.md#verification)
- [MCP — Verify-First Contract](mcp.md#verify-first-contract-v14)
- [Hooks — Disable / bypass](hooks.md#disable--bypass)
