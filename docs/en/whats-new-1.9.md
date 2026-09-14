**English** | [Русский](../ru/whats-new-1.9.md)

# What changed in 1.9

A page for whoever is upgrading. Before reading what breaks, it is worth knowing
what it was for.

## What 1.9 is, in three points

**📏 A release that stopped taking its own word for things.** 1.8 answered the
question "does the framework enforce discipline". 1.9 asks no question — it makes
two statements about the product and requires each to be measured: a substantial
token saving, and higher development quality on any model.

**And one of the two is MEASURED ONCE — and on this pair there is no saving;
said here rather than in a footnote.** Telemetry still produces no figure: of
57,251 telemetry rows, 233 (0%) carry input tokens, and no "without TAUSIK"
baseline exists in it at all. In session #225 it was 0 rows out of 4,777 — the
instrument moved, and did not reach a number. For telemetry this is the
ABSENCE of a quantity, not a measured zero. The figure came from a different
instrument — a paired replay on a fixed corpus ([protocol §7, in
Russian](../ru/research/rag-nudge-replay-protocol.md)): ten identical questions
about the repository, one commit, one model, the harness with its rag-first
nudges against the same harness without them. With the nudges it cost more:
198,848 against 195,055 tokens of new context and output (+1.9%), 326,323
against 292,715 bytes of exploration results (+11.5%), and `search_code`, the
tool the nudges recommend, was never called with or without them (0 of 62 and
0 of 76 calls). That is one reading on one corpus, in this pair — not a
refutation of saving in general: a repeat of the same condition varied by 13%,
more than the delta itself. The promise stays what the release undertook to
measure; what is published as fact is only what was measured: no saving
on this pair, and the nudges do not change tool choice.

**🔢 Zero stopped passing itself off as a measurement.** A quantity that cannot
be obtained is now ABSENT, not nought. That sounds like a nicety until you look
at the numbers: the telemetry asserted 55,471 times that work had cost $0.00,
and model pinning had NEVER fired in 231 sessions. Both defects looked exactly
like "a feature nobody needed".

**🖧 Guarantees are stated by rule, not by host.** Five environments were handed
the same rules text promising automatic enforcement; on two of the five that was
untrue (measured in session #225; Codex became the sixth host later in the
release, on the same terms — see below). Each host now reads what is actually deployed for it — and by rule,
because "everything here is instructions" is untrue too on a host without hooks:
closing a task IS refused there.

Full list of changes: [CHANGELOG.md](../../CHANGELOG.md). This page is not a
retelling: the 1.9 section of the CHANGELOG holds more than 250 entries (the lower
bound is held by `tests/test_release_notes_1_9.py`), and what is selected here is what changes
the experience of UPGRADING.

---

## BREAKING CHANGES

This section is the **single source of the future tag's text**. That is exactly
why it exists: in 1.8 the breaking change to trust tiers stayed in the CHANGELOG
and never reached the tag's notes, and a published tag cannot be re-cut.

### 1. A write gate that cannot read the DB now refuses instead of allowing

**Before.** If `scope_write_gate` could not open `.tausik/tausik.db` — locked,
corrupt, unreachable — it let the write through. Silently.

**Now.** It refuses. A gate that could not check has no business reporting the
same outcome as a gate that checked and allowed.

**Does this affect me.** Yes, if you work with the database locked or
unreachable: a write that used to pass will now be declined, with the reason.
Unlock the DB (usually by closing a parallel process) or disable the gate
deliberately in the config. `TAUSIK_SKIP_HOOKS=1` still works and is still
telemetered.

### 2. The Notion transport is gone

**Before.** The shared knowledge base could be mirrored to a Notion workspace:
`tausik brain init/status/sync/move/draft/publish`, the `tausik-brain` MCP
server with seven tools, the `/brain` skill and two hooks that searched the
brain before a web fetch.

**Now.** None of that ships (decision #358). The shared store is local and
file-based — `~/.tausik-knowledge` — and `--global` on `decide` and
`memory add` is the only way a record leaves this project. `tausik knowledge
import-brain` still reads the local mirror file `~/.tausik-brain/brain.db`, so
nothing already mirrored is lost.

**Does this affect me.** Only if you ran the brain. Bootstrap over a 1.8
checkout removes the stale `tausik-brain` entry from every host config it
manages, so your IDE stops logging an MCP error for a server that no longer
exists. Run `tausik knowledge import-brain` once if the mirror holds records
you want in the shared store.

---

## What else changes on upgrade

### Database schema: 44 → 62

Eighteen migrations apply automatically on first access (the figures here are
read from `SCHEMA_VERSION` by `tests/test_release_notes_1_9.py`, so the page
cannot fall behind the tree again). Each is preceded by a backup at
`.tausik/tausik.db.bak.v<old>`; spares are cleared with `tausik db prune --keep N`.

The most visible is v58: the token and cost columns in `usage_events` became
nullable. **NULL means "not measured", and that is not the same as 0.** The
migration turned 55,307 rows — provably never measured — into NULL and touched
no row carrying a real number.

The last ones are small and worth knowing: v59 lets a graph edge say it was
OBSERVED rather than inferred; v60 records a test that was never seen red; v62
puts an index on `tasks.defect_of` — without it `tausik status` on a database
with a history (1,504 done tasks) spent 5.3 s in one `EXISTS`, and the
SessionStart hook hit its 6 s timeout and silently delivered no context; with
the index the query takes 5 ms, `status` 0.3 s, the hook 0.9 s; v61
adds `tasks.tracker_refs` — the first column added to `tasks` after v43, which
is how the post-migration that rebuilt `tasks` from a frozen v43 column list
was caught erasing any later column. That rebuild is fixed in the same release —
it re-applies every later column after itself — so a database upgrading from
before v43 keeps the column (`tests/test_migration_v43_model_mismatch.py`).

### Cost and model: what used to stay silent

* **Zero no longer passes as a measurement.** `calculate_cost_usd` returns
  absence for an unpriced model and 0.0 for one priced at zero; both used to
  return 0.0, and nothing could tell them apart.
* **Per-session spend was inflated twofold** on 156 of 160 sessions; the total
  now says which part of it was computed on the superseded arithmetic.
* **Prices live in the project's config**, and its word beats the shipped table.
  A rate is a PAIR of numbers (input and output), not one.
* **The session's model is recorded.** `sessions.model_id` was empty in all 231
  sessions, so model pinning (RENAR 10.13) never fired. The source is a chain:
  `TAUSIK_AGENT_MODEL` → host variables → the host's provider. The model is NOT
  inferred from the host's name: Claude Code pointed at another endpoint runs
  that endpoint's model.

### Gates: silence stopped being an option

* A gate with neither an implementation nor a command **blocks** instead of
  staying quiet.
* A rejected command override **blocks**; substituting the built-in default made
  the refusal invisible.
* `ruff` runs on the `verify` trigger too, not only on `commit`.
* New gate `cross_model_parity`: a difference between hosts that share an
  extension point must be NAMED. It does not demand sameness — Cursor has no
  extension point — but an undeclared difference blocks. It fires only on
  host-layer edits.

### Running the tests

* **The lane is parallel by default** (`-n auto` in `addopts`). `pytest-xdist` is
  required; without it pytest exits on "unrecognized arguments: -n".
* **Selection follows IMPORTS, not names** — the cheap run reaches wider, and
  half the corpus stopped being unreachable.
* `pyproject.toml` no longer promises `tausik verify --full`, which never
  existed.

### New commands

| Command | What it does |
|---|---|
| `tausik coherence` | The repository-level question no gate was asking: what in the tree stopped adding up |
| `tausik audit evidence` | Closure-receipt citations no longer rot in silence |

### Codex is a sixth host — and the claim stops where the measurement stopped

`bootstrap.py --ide codex` (and `--ide all`) scaffolds Codex CLI: the
`tausik-project` MCP server registered in the PROJECT's `.codex/config.toml`,
the same skill set as Claude under `.codex/skills/`, sub-agents generated from
the canonical Markdown into `.codex/agents/*.toml`, and `.codex/hooks.json`
built from the SAME hook declaration Claude's profile uses (absolute paths,
because Codex has no workspace variable). Support is a release promise only
because a real Codex host proved it, not because the files exist: in the live
acceptance run Codex called `tausik_status` and got the structured reply, its
catalog listed `i-have-adhd` and the `tausik-reviewer` agent, and the forbidden
`Path('outside.txt').write_text(...)` was refused before the file existed.

**The boundary, stated once here.** That refusal happened under a hook profile
the user had TRUSTED in Codex. The same operation with the generated profile
present but untrusted ran to completion — no hook fired. Nothing on disk tells
the two states apart, so Rule 1 and the write ACL on Codex are hard *once you
trust the project hooks*, and an untrusted profile enforces nothing. The
[enforcement matrix](model-providers.md#codex-enforcement-matrix) carries that
condition on both rows and a test keeps it there.

### The agent's own quickstart

[agent-quickstart.md](agent-quickstart.md) (EN/RU) is written for the agent
reading it first: connect on its host — every host bootstrap scaffolds, Codex
with its trust condition — check, then the cycle as exact calls with the
replies and the refusals it will actually see, each quoted from a live run and
held to the code by `tests/test_agent_quickstart.py`.

### Context: across projects, across sessions, through compaction

**The global config no longer carries another project.** In 1.8 the user-tier
`~/.tausik/config.json` could bring a weakening enabled for one project into
yours (`auto_verify: true` from a neighbour). User-tier weakening now lives in a
`projects` section keyed by the project's absolute path; `tausik doctor` labels
every effective weakening MACHINE-WIDE or project-scoped and lists foreign
entries separately.

**`task start` brings memory by relevance.** On top of the recency tail in
CLAUDE.md, start, resume and `task show` print a `Relevant memory (N)` block
built from the task's own declaration; an empty answer is named with the terms
tried.

**The rules file gained a compaction section.** It says what to carry verbatim
through context compaction. The rules file is preserve-if-exists: on an
already-bootstrapped project the section appears only after the generated file
is deleted and bootstrap re-run.

**`knowledge export --redacted`** masks paths, addresses, URLs and project names
with typed placeholders before shared memory is published.

**Caveman mode is a response contract**, not only a length: the shape
`done → verified by → left → your call`, five named exceptions and a pre-send
check — inside the same directive, no second mode.

### Output economy: two levers, both off on purpose

`read_ledger` (do not pay twice for an unchanged file) and a byte cap on command
output both ship, both are **off by default**, and each has a decision with a
number behind it. Turning them on is your choice, not our default.

---

## See also

- [publishing.md](publishing.md) — the two repository lines, and why a published tag never moves
- [enforcement-coverage.md](enforcement-coverage.md) — what is enforced on your host, and by what
- [cost-telemetry.md](cost-telemetry.md) — how to read cost after v58
