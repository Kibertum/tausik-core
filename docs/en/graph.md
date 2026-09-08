# `tausik graph` — what changes with what, and on what evidence

The artifact graph answers the question an agent asks itself before every edit:
**what else will I have to touch**. It answers with two kinds of evidence, never
with a guess, and it always says which kind it is standing on.

RU mirror: [`../ru/graph.md`](../ru/graph.md).

## Three commands

```bash
.tausik/tausik graph build            # fill it: index + both edge layers
.tausik/tausik graph show <path>      # what relates to this file, and why
.tausik/tausik graph status           # how much is stored, what is stale, which roots
```

The MCP twin is `tausik_graph` with a `command` argument (`build`, `show`,
`status`). One tool for three subcommands rather than three: the MCP surface is
paid for on every turn, and three names would have cost triple for the same
reach (decision #350).

## Two layers, kept apart

| Layer | Where it comes from | Confidence |
|---|---|---|
| `git_cochange` | the files kept landing in one commit | rises with observations, never reaches 1.0 |
| `declared_relevant_files` | a task's `relevant_files` | 1.0 — somebody STATED this |
| `declared_scope_paths` | a task's scope ACL | 1.0 |
| `declared_crosscutting` | `CROSSCUTTING_SCOPE` in a test | 1.0 |

The separation is the whole point. "Observed together twelve times" and "a
person declared these one task" are different claims, and averaging them into
one number turns a guess into a fact. An edge that cannot say where it came from
is refused by the schema itself — a database constraint, not a check written
twice.

The co-change layer knows no languages: it reads git history, so it works
identically for code, documentation, configuration and images. Verified by
running it over python, terraform and markdown — one edge per stack, identical
relation, layer and confidence (decision #349).

## Roots are asked of the PROJECT

Three sources, in descending order of authority, and the answer always names
which one spoke:

1. **`source_roots` in `.tausik/config.json`** — the project's own word outranks
   anything we infer.
2. **Git-tracked files** — the top-level directories where source actually
   lives. Tracked, not merely present: `node_modules/` and `build/` are on disk
   and are not the project's source, and git already knows the difference
   because somebody wrote it into `.gitignore`.
3. **A disk scan** — for a tree that is not a repository yet. Named separately
   because its answer is weaker and the reader is entitled to know that.

There is no fourth source. A tree whose source cannot be located yields an EMPTY
list and says so, rather than a confident answer about the wrong directories.

> **Why this matters more than it looks.** Before 1.9 the roots were the
> constant `("scripts", "bootstrap", "tests", "harness")` — the directory names
> of THIS repository, shipped into everybody else's. Measured on a consumer
> project: the symbol index found ZERO declarations while `backend/` sat there
> full of them. That is worse than an empty answer, because a consumer usually
> DOES have a `scripts/` directory — holding its own deploy scripts — so the
> index returned a slice of the wrong thing and looked like it worked.

## What the graph says about your stack

Artifact kinds cover all 25 declared stacks: imperative source is `code`,
declarative source (terraform, helm, kubernetes, ansible) is `config`, prose is
`doc`, data is `data`. A test is recognised in ANY of their conventions:
`_test.go`, `spec/`, `__tests__/`, `*.spec.ts`, `test_*.py`.

`other` remains the honest answer for a suffix the framework does not know. It
means "something else", not "we did not look".

## Symbols: Python only, and said out loud

`graph build` fills `artifact_symbols` from the definitions the `ast` parse
finds. There is no extractor for other languages in 1.9, and the output NAMES
how many files it could not read:

```
symbols: 13312 from files this framework can parse
  37 source file(s) have NO symbol extractor here — Python only in 1.9.
  Their co-change and declared edges are built as usual.
```

Silence here would be the defect: a Go project would read "0 symbols" as "my
code has no definitions" rather than "this framework cannot read them yet".
Absence is not zero (decision #334).

## Freshness is recomputed on EVERY query

`graph show` recomputes each involved file's fingerprint from disk and names the
ones that have moved on:

```
scripts/symbol_index.py  (indexed 2026-09-08T12:47:57Z)
  STALE — these have changed since indexing: scripts/symbol_answer.py
```

Trusting the stored hashes would be cheaper. It would also make a stale answer
indistinguishable from a fresh one, which is the single outcome this graph must
never produce.

## Cost

A full build of this repository — 4,226 artifacts, 13,312 symbols, 17,644
edges — takes **about 9 seconds**.

The first working build took **2 minutes 27 seconds**. The difference was not
the graph: the database runs WAL with `synchronous=FULL`, so every autocommitted
statement pays an fsync — roughly 6.7 ms per row across twenty-two thousand
rows. The build now runs as one transaction, and that was the whole fix. A build
nobody will run twice is a build nobody runs, and the framework then ships an
empty graph everywhere.

## What the graph does not express

Listed deliberately, so the absence of these relations is not later mistaken for
a data defect (decision #349):

- **direction of dependency** in the co-change layer: the relation is
  symmetric — "A changes with B" follows from history, "A depends on B" does
  not;
- **symbol-to-symbol edges**: symbols are stored, edges run between files only;
- **history of confidence**: an edge carries one current number, so "they were
  related and stopped being" is unrepresentable;
- **test coverage**: no such edge yet — it is filed as its own task;
- **cross-stack relations** by anything other than co-change.
