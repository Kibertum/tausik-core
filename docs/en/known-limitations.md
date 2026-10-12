**English** | [Русский](../ru/known-limitations.md)

# Deliberate gaps, open defects, and what is out of scope

<!-- doc-map: reader=user; zone=core-surface -->

Three different things that looked identical before this page: "we decided not to do
this", "we have not finished this", and "this is broken". A guard whose blind spot is
undocumented reads as total — so the gaps are declared here rather than inferred by the
reader from silence.

**What marks a gap as deliberate is a stated reason why closing it now costs more than
living with it.** An entry without that reason is not a gap but a defect, and it belongs
in the task list. So every line below carries both the reason and a reference to whatever
holds the boundary.

## Deliberate gaps

Each entry answers one question: **what exactly is NOT guaranteed** — not "works
partially", but what gets through and in which case.

### The knowledge-routing gate cannot see a gitignored sink

**Not guaranteed:** a write of knowledge into a git-ignored file will be stopped at a
close or a commit. A path outside the repository (`~/.claude/**/memory/`) is invisible to
it as well.

**Why we live with it:** the gate's input is `git status --porcelain`, and `--ignored`
would sweep in `.tausik/`, `node_modules/` and every build artifact. An ignored file
cannot reach a commit anyway, and a leak into one is caught by another layer — the
`PreToolUse` hook. The gate's question is "does the change this project is about to record
carry knowledge off-project"; the hook's is "is this write leaking", and only the second
can see an ignored path.

**Holds the boundary:** the docstring of `scripts/gate_memory_route.py` (both limits are
stated where the code is), `tests/test_memory_sinks.py`.

### The filesize gate looks only at the task's files

**Not guaranteed:** a file already over the cap but untouched by the current task will be
named. The gate answers "did the file you are editing grow", not "is any file in the tree
over the cap".

**Why we live with it:** it is a ratchet on the change, not an audit of the tree. An audit
would require declaring an exemption for every historical file at once, or it would block
every task for someone else's debt. The whole tree is checked by a separate lane.

**Holds the boundary:** `run_filesize_gate(gate, files)` takes the task's scope;
`tests/test_gates.py`.

### The projection round-trip gate is opt-in and fail-open

**Not guaranteed:** a divergence between the `tausik/` tree and the database will be
noticed in a project that has no database (the gate skips — on a fresh clone that is the
right answer), and an internal failure of the gate itself will not fail the commit.

**Why we live with it:** a gate that blocked a project without a database would be
enforcing "have a database", not "keep the projection in sync". And a watchman's own
failure is not evidence of divergence.

**Holds the boundary:** the docstring of `scripts/gate_state_roundtrip.py`,
`tests/test_state_roundtrip_gate.py`.

### The historical-citation marker checks the SHAPE of a sha, not that the commit exists

**Not guaranteed:** `path (removed in <hex>)` stops counting as a stale reference even
when no such commit exists. Seven or more hex characters in parentheses right after the
path are sufficient grounds.

**Why we live with it:** asking git would let a broken git silently switch off the whole
stale-reference detector. That costs more than a forged marker, which has to be typed by
hand and hides nothing beyond the one reference it is attached to.

**Holds the boundary:** `_REMOVED_CITATION` in `scripts/memory_cleanup.py`,
`tests/test_repo_hygiene_ratchet.py`.

### The orphan-module scan cannot see a name built by an expression

**Not guaranteed:** a module reached only as `__import__(f"mod_{kind}")` will not be
called an orphan. A string literal (`__import__("mod")`) is visible; a computed name is
not.

**Why we live with it:** a computed name names no SINGLE module, and guessing one would
trade this false positive for a false negative — the detector would start claiming a
reference it never saw.

**Holds the boundary:** `_dynamic_import_name` in `scripts/audit_orphan_files.py`,
`tests/test_repo_hygiene_ratchet.py`.

### The stale-reference check requires the DIRECTORY to exist

**Not guaranteed:** a reference to a file inside a directory that was deleted whole will
be reported as stale.

**Why we live with it:** prose is full of slashes that are not paths
(`lru_cache/functools.cache`, `release/1.8`). Requiring an existing parent removes that
noise; without it the finding list becomes unreadable and the reader stops looking at the
real ones.

**Holds the boundary:** `_parent_dir_exists` in `scripts/memory_cleanup.py`.

### Archiving a task is irreversible and does not shrink the tree

**Not guaranteed:** `archived_at` can be cleared by a command — no such command exists;
and the task's projection file stays in `tausik/tasks/` after archiving, because the
exporter selects tasks with no filter on that column (memory has one).

**Why we live with it:** archiving was designed as "hide from `task list`", and in that
role it works. Both halves are filed as tasks, and reversibility is declared a
precondition of shrinking the projection.

**Holds the boundary:** `docs/en/task-archive-spec.md`, the caveats in `docs/en/cli.md`,
`tests/test_hygiene_cli.py`.

### The MCP server holds old code until the IDE restarts

**Not guaranteed:** an edit in `scripts/` reaches the MCP tools immediately. Until the
host restarts, the server may execute the previous modules.

**Why we live with it:** reloading modules in a live server breaks connection state for
more than immediacy is worth. The divergence is DECLARED instead:
`self_check.drift_detected` raises the flag, and from then on MCP answers in that session
cannot be trusted — the CLI, which re-reads disk on every call, can.

**Holds the boundary:** `tausik_self_check`, the "MCP Health" section of the `/start`
skill.

### `/rewind` does not undo what the agent did through the shell

**Not guaranteed:** Claude Code's `/rewind` restores the files an agent changed. Its
checkpoints track only edits made by its own file tools; anything written through Bash,
a script or another process is not in the snapshot and is not rolled back.

**Why we live with it:** it is the host's mechanism, not ours, and TAUSIK agents do much
of their work through the shell. Pretending otherwise would hand the next agent a safety
net that is not there.

**Holds the boundary:** git. Commit or stash before a risky step; `git diff` shows what a
rewind would miss.

### The rules file keeps its changing part last

**Not guaranteed:** that everything the agent is given stays in the prompt cache. The
host caches the longest unchanged prefix, so whatever changes invalidates what follows it.

**Why we live with it:** some context has to change — the session state and the memory
tail. It is kept in one block at the very end of the rules file (`<!-- DYNAMIC:START -->`),
after every stable rule, so a change there costs only itself. Per-prompt hook text arrives
after the conversation prefix for the same reason.

**Holds the boundary:** `tests/test_context_order.py` fails if anything static follows
the dynamic block in the generated rules file or in this repository's `CLAUDE.md`.

### Time windows have SECOND granularity

**Not guaranteed:** an event written in the same second in which a window bounded by `now`
is read will fall inside the selection.

**Why we live with it:** `utcnow_iso()` writes seconds across the whole project, and
moving to milliseconds would touch every timestamp in the schema and in the projection.
For an open interval the upper bound is simply not set — it is meaningless there.

**Holds the boundary:** the memory record about the event window,
`tests/test_med_findings_fix.py`.

### Doctor checks are best-effort

**Not guaranteed:** a failure of one check will be distinguished from its negative result:
an exception inside a check becomes a WARN carrying the error text, not a FAIL.

**Why we live with it:** `doctor` is an overview, not a gate. One broken check must not
hide the other nine.

**Holds the boundary:** `scripts/project_cli_doctor.py` (every check in its own `try`),
`tests/test_doctor_*.py`.

## Open defects

**They are not listed here by hand, and that is a decision rather than an omission.** A
hand-maintained defect list falls behind silently; that is exactly how a document that
called itself the map of the project's direction ended up asserting a state two releases
old. Open defects live in the task database, and that is where to read them:

```bash
tausik task list --status planning      # what is filed and waiting
tausik roadmap                          # the release composition with counters
```

A defect found inside a task is filed as its own task rather than fixed in passing — so
"none currently open" here would mean only that nobody looked.

## Out of scope

What TAUSIK does not do by design, rather than by omission:

* **It does not fix a failing gate for you.** A gate names the check, the cause and the
  remediation command; a human or an agent applies it. A gate that repaired itself would
  teach everyone to stop reading the cause.
* **It gives an agent no direct database access.** MCP and the CLI only. Raw SQL would
  bypass the projection, the triggers and the receipts — everything reproducibility rests
  on.
* **It does not replace code review.** Gates check discipline and boundaries, not intent.
  An L3 separation of duties requires a different model from the author's.
* **It does not serve several projects from one daemon.** The MCP server is bound to a
  project at spawn; a systemwide mode is a separate body of work, not a gap.
