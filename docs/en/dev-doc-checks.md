**English** | [Русский](/ru/docs/dev-doc-checks)

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
python scripts/gen_doc_constants.py             # regenerate the JSON
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

## Negative behaviour

- **No `pyproject.toml` ancestor** → the hook prints a SKIP message
  and exits 0. Tested in `tests/test_check_docs_hook.py`.
- **`gen_doc_constants.py` missing** (legacy checkout) → SKIP, exit 0.
- **Drift detected** → exit 1 with stderr hint:
  `[check_docs] doc-constants drift — run python scripts/gen_doc_constants.py and re-commit.`
