**English** | [Русский](../ru/dev-doc-checks.md)

# Developer doc checks (v14-doc-automation)

Tooling that keeps the documentation honest with the codebase. All
scripts are stdlib-only and produce machine-readable output for CI.

## What runs in CI (GitHub Actions)

Workflow: `.github/workflows/tests.yml`. Step: `Doc-constants drift check`.

```bash
python scripts/gen_doc_constants.py --check
```

Fails the matrix when `docs/_generated/constants.json` no longer matches
the live `pyproject.toml` `version` field or the MCP tool counts derived
from `harness/{claude,cursor}/mcp/*/tools.py`.

## Run locally before commit

Manually:

```bash
python scripts/gen_doc_constants.py --check     # exit 1 on drift
python scripts/gen_doc_constants.py --write      # fix everything --check flags, then re-check
python scripts/gen_doc_constants.py             # regenerate constants.json only
```

Or wire it into your local `pre-commit` hook (the repo ships a basic
mypy hook; add this on top):

```bash
# .git/hooks/pre-commit
python scripts/hooks/check_docs.py || exit 1
```

`scripts/hooks/check_docs.py` is a thin wrapper that:

- Walks up to find `pyproject.toml`. If nothing matches, **prints a
  friendly skip message and exits 0** — the hook never blocks commits
  in a checkout that doesn't ship TAUSIK's generators.
- Calls `gen_doc_constants.py --check` with the project's Python.
- Surfaces drift output to `stderr` with a one-line remediation hint.

## Other audit scripts (manual)

| Script | What it reports | Run |
|--------|------------------|-----|
| `scripts/audit_orphan_files.py` | Python files in `scripts/` that nothing imports / docs reference. | `python scripts/audit_orphan_files.py [--json] [--check]` |
| `scripts/audit_stale_docs.py` | Markdown files under `docs/` with no inbound link. | `python scripts/audit_stale_docs.py [--json] [--check]` |
| `scripts/audit_unused_python.py` | Top-level `def` / `class` symbols never referenced. | `python scripts/audit_unused_python.py [--json] [--check]` |
| `scripts/audit_pytest_dedupe.py` | Test functions with structurally identical bodies. | `python scripts/audit_pytest_dedupe.py [--json] [--check]` |

These are intentionally **review-only** in v1 — none of them deletes
or rewrites anything. Hook them into CI later once their false-positive
profile is well understood.

The first three scan **git-tracked files only** (`scripts/audit_tracked_files.py`
asks `git ls-files`). A gitignored file references nothing by definition, so
reporting one is noise that can never be actioned — and internal research
under `docs/research/_internal/` must not have its filenames printed into
shared reports at all. If git cannot be consulted (not a repository, git
missing, empty listing), the audits print a warning to `stderr` and fall
back to the filesystem walk rather than failing.

## Negative behaviour

- **No `pyproject.toml` ancestor** → the hook prints a SKIP message
  and exits 0. Tested in `tests/test_check_docs_hook.py`.
- **`gen_doc_constants.py` missing** (legacy checkout) → SKIP, exit 0.
- **Drift detected** → exit 1 with stderr hint:
  `[check_docs] doc-constants drift — run python scripts/gen_doc_constants.py --write and re-commit.`

## What the check actually looks at

The document above described a machine that checked two things: the version in
`pyproject.toml` and the MCP tool counts. It has grown to seven scans, and until
this section existed **only one of its seven modules was named anywhere a
reader would look**.

| Scan | What it guards | Where it lives |
|---|---|---|
| `scan_version_refs` | `vX.Y.Z` written into prose drifting from `pyproject.toml` | `doc_drift_scanners.py` |
| `scan_py_version_constants` | the same version restated as a Python constant | `doc_drift_scanners.py` |
| `scan_mcp_tool_counts` | `**N tools**`, `N project tools`, and stale `brain = N` sums (the brain server is retired, so any such sum is drift) | `doc_drift_scanners.py` |
| `scan_closed_list_enums` | a documented list of values that the code's own closed list has outgrown | `doc_drift_scanners.py` |
| `scan_test_counts` | "N tests" in prose against the number pytest actually collects | `doc_drift_scanners.py` |
| `scan_code_counts` | repo-state counters — hooks, stacks, roles, review agents, core and official skills | `doc_drift_scanners.py` |
| `scan_table_count_columns` | numeric CELLS of markdown tables, with their own subject registry | `doc_drift_tables.py` |

The modules behind them:

| Module | Purpose |
|---|---|
| `gen_doc_constants.py` | the entry point: `--check`, `--write`, and regeneration of `constants.json` |
| `doc_drift_common.py` | the shared regex tables, the scan targets, and the text helpers |
| `doc_drift_scanners.py` | the six scans above, each returning a list of findings |
| `doc_drift_tables.py` | the column scan and the registry of which column means what |
| `doc_drift_fixes.py` | the auto-fixer `--write` runs |
| `code_counts.py` | counts the repository's own state — hooks, stacks, roles, skills |
| `mcp_tool_counts.py` | counts the MCP surface each server advertises |

## Detection and repair must stay in lockstep

`--write` repairs what `--check` reports. That is a PROMISE, and it was broken:
the `N project + M brain` pair form (retired with the brain server in 1.9) was
scanned from review #208 onward and repaired by nobody. Measured in session #234: raising the
MCP tool count from 145 to 146 left **eight such references across seven files**,
`--write` finished red with "drift remains after --write", and about fifteen
edits had to be made by hand for one changed integer.

Worse than the labour: a scan that reports drift it cannot fix reads, to whoever
runs `--write`, as coverage. `tests/test_doc_drift_fixes_repair_what_they_detect.py`
now asserts that every count family the scanner knows is also known to the fixer,
so the next family cannot land half-built.

## Where the repair does NOT go

The fixer never edits inside a fenced code block, and never inside CLAUDE.md's
`DYNAMIC` section — the same places the scanner does not look. Documentation
teaches by example, and an "example" silently rewritten to match today's numbers
stops being the thing it was illustrating.
