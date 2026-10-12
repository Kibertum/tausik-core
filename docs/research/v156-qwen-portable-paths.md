# v1.5.6 design — rename-proof paths for Qwen Code

Status: **design / open question** (implementation deferred — needs live Qwen verification)
Task: `v156-portable-paths-all-ides` · follow-up from v1.5.5 rename-proof work.

## Problem

v1.5.5 made generated configs rename-proof for Claude, Cursor and Kilo via
`bootstrap/bootstrap_paths.py::portable_path`, which rewrites an in-project
absolute path to a workspace-variable-relative one the host expands at launch:

| Host | Variable |
|---|---|
| Claude Code `.mcp.json` | `${CLAUDE_PROJECT_DIR:-.}` |
| Claude Code hooks | `${CLAUDE_PROJECT_DIR}` |
| Cursor / Kilo (VS Code family) | `${workspaceFolder}` |

**Qwen Code has no equivalent workspace variable** in its `settings.json`
format, so `bootstrap/bootstrap_qwen.py` still embeds **absolute** paths for:

- MCP server scripts + their `--project <abs>` arg (`mcpServers[*].args`),
- hook commands (`python <abs>/scripts/hooks/<hook>.py`).

`_stdio_mcp_server` emits only `{type, command, args}` — **no `cwd` field** — so
there is no per-server working-directory hint to lean on either. Renaming the
project folder therefore breaks every embedded path in `.qwen/settings.json`.

## Pivotal open question

**What is Qwen Code's working directory when it spawns an MCP stdio server and
a hook command?**

- If **CWD = project root** (the folder containing `.qwen/`) → Solution A is
  enough and minimal.
- If CWD is unspecified / Qwen's own install dir → only Solution B is safe.

The repo docs (`docs/en/environment.md`) confirm Qwen sets `QWEN_CODE` /
`QWEN_HOME` envs but document **no** workspace variable and **no** launch-CWD
guarantee. This must be confirmed against a live Qwen Code build before
implementing — hence implementation is deferred (see negative AC).

## Solution A — relative paths + `--project .`  (CWD-dependent)

Write paths relative to the project root and pass `--project .`:

```json
{ "command": "python", "args": [".qwen/mcp/project/server.py", "--project", "."] }
```

- **Pros:** zero new files; trivial diff in `bootstrap_qwen.py` (swap `_p(abs)`
  for the project-relative form, mirroring `portable_path` but with a literal
  relative base instead of a variable).
- **Cons:** correct **only if** Qwen launches with CWD = project root. If not,
  `.` and the relative script path resolve against the wrong directory and the
  server never starts. Fragile and host-version-dependent.

## Solution B — self-locating launcher  (CWD-independent) — **recommended**

Generate one tiny launcher per project, e.g. `.qwen/scripts/tausik_launch.py`,
referenced by a **relative** command. The launcher derives the project dir from
its **own** `__file__` and re-execs the real target:

```python
# .qwen/scripts/tausik_launch.py  (generated)
import os, sys, runpy
PROJECT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # .qwen/scripts -> project
target = os.path.join(PROJECT, ".qwen", *sys.argv[1].split("/"))
sys.argv = [target, "--project", PROJECT] + sys.argv[2:]
runpy.run_path(target, run_name="__main__")
```

```json
{ "command": "python", "args": [".qwen/scripts/tausik_launch.py", "mcp/project/server.py"] }
```

- **Pros:** **rename-proof regardless of CWD** — `__file__` is always absolute
  and tracks the folder when it moves. Same mechanism works for hook commands.
  One generated helper, fully under our control; mirrors the "paths outside the
  project stay absolute" rule (external lib/venv passed through untouched).
- **Cons:** one extra generated file; still depends on the launcher path itself
  being resolvable. If Qwen *also* needs an absolute `command` path, fall back
  to an absolute launcher path while keeping the self-location logic — that
  alone fixes `--project` and all in-project script paths, which is the bulk of
  the breakage.

## Recommendation

Adopt **Solution B** (self-locating launcher). It is the only option that is
correct independent of Qwen's launch CWD, and the launcher pattern generalises
to any future host that lacks a workspace variable (Codex, Windsurf-as-CLI).
Keep Solution A as a simplification *iff* a live test proves CWD = project root.

## Implementation checklist (deferred to a follow-up)

1. Confirm Qwen launch CWD + whether `command` may be relative (live test).
2. Add `portable_launcher_args(...)` helper next to `portable_path` (shared).
3. Generate `.qwen/scripts/tausik_launch.py`; rewrite `mcpServers` args + hook
   commands through it; keep out-of-project paths absolute.
4. Tests: `tests/test_bootstrap_qwen.py` — rename simulation (generate, move the
   parent dir, assert paths still resolve); parity with `test_bootstrap_paths`.
5. Update `docs/en|ru` (Qwen no longer the rename-proof exception) + CHANGELOG.
