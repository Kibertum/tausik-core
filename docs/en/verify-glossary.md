**English** | [Русский](../ru/verify-glossary.md)

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

### What the framework wrote itself is not the agent's scope

`verify` compares the declared scope against what git reports, and before 1.9 it
counted against the agent the files the framework rewrites ITSELF during a
close: `CLAUDE.md` and `AGENTS.md` (via `update-claudemd`), `ROADMAP.md` (via
`doc roadmap`), `docs/_generated/*`. They cannot be declared in advance, because
at declaration time they have not changed yet.

Measured in session #235: of 135 under-declared runs in the last 300, **26 (19%)
consisted of nothing but framework output**, and another 39 (29%) were mixed.

They are now subtracted, on the same principle that already subtracts a task's
own export (convention #409, decision #283): a check whose subject is "what did
the AGENT change" does not count what it wrote itself.

**The decision is taken by the DIFF, never by the name.** `CLAUDE.md` and
`AGENTS.md` are only PARTLY generated: the framework owns the region between the
`DYNAMIC` markers and a human or an agent owns the rest. Subtracting by name
would hide real work, so the subtraction fires only when the change lies
entirely inside the generated region. An unreadable diff, missing markers or no
git at all leave the file IN the agent's scope: being unable to check is not
permission.

`CHANGELOG.md` is written by the agent and is NOT subtracted — its absence from
a declaration is a real under-declaration, and that is what the check exists to
show.

### A deleted file can be declared in the scope

A task that DELETES a file must name it in `--relevant-files`: the deletion is
part of the change. Before 1.9 that was impossible. The list went to the gate's
command verbatim, `ruff` was handed a path that no longer existed and answered
`E902 no such file`, and the whole run came back `exit=1` with no handle. The
only way past it was to leave the deletion out — to under-declare on purpose. A
mechanism that pushes toward under-declaration has no standing to measure it.

A path that is not on disk is no longer substituted into a gate's command. Three
boundaries:

- the filter sits where the command's ARGUMENTS are built, not where
  applicability is decided: `file_extensions` and `file_patterns` judge by NAME
  and must keep working for a file that is already gone;
- it applies only to a command that interpolates `{files}`. A gate that never
  receives the list cannot be broken by a deleted file, and substituting its
  verdict would be a lie — a missing tool must stay `COULD_NOT_RUN`;
- if NOTHING survives the filter, the gate returns `NOT_APPLICABLE` with the
  code `all_files_deleted` rather than "passed". A file gate with nothing to
  read has checked nothing. Without that branch an empty list becomes `.`, and
  `ruff check .` would lint the entire repository.

The declaration and the signed receipt keep the FULL list, deletions included:
the receipt describes the CHANGE, and the change included removing a file.
