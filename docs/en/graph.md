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

`graph show` also prints what the file DEFINES, reading the symbols already
stored:

```
scripts/source_roots.py  (indexed 2026-09-08T12:49:28Z)
  defines: _roots_from_disk:180, _tracked_files:141, declared_roots:125, resolve:205
```

The listing is bounded at twelve names and the remainder is stated as a number —
for the same reason as in `tausik symbol`: past that the answer stops being
cheaper than opening the file. For a file with no extractor the section is
SILENT rather than empty: an empty heading would read as "defines nothing",
which is a different claim from "nothing here can read its definitions".

## Navigation: what to read in order to change a file

```bash
.tausik/tausik graph read <path>            # what to read to change it
.tausik/tausik graph read <path> --affects  # what a change should turn red
```

**The answer is ranked and cut rather than complete, and that is arithmetic
rather than caution.** Measured on the live graph: an unranked neighbour list
names 42 files for `scripts/verify_scope_honesty.py` totalling 2,881 KB, 38 files
and 2,779 KB for `gate_test_resolver.py`, 29 and 2,612 KB for
`service_artifact_graph.py`. An agent handed that reads all of it and spends MORE
than the grep the graph was meant to replace. Completeness here is the failure
mode, not the goal.

The same three questions after ranking: **927, 945 and 916 bytes** — roughly one
three-thousandth of reading the neighbours.

**Rank comes from provenance.** What a RUN observed outranks what a person
declared, which outranks what git noticed changing together. Within a layer the
observation count decides. Every line carries its REASON — "a test run reached it
x36", "worked on together in one task" — because a ranked list without reasons is
indistinguishable from an arbitrary one, and the reader cannot stop early, which
is where the saving lives.

**Two questions, and they are not mirror images.** This graph has no direction of
dependency: co-change is symmetric and git cannot say which side followed which.
So `read` unions BOTH directions — storing a symmetric edge picks a side
arbitrarily, and asking one would drop most of the answer (measured on the live
tree: one direction returned 2 neighbours of 42). `--affects` uses the one
relation that IS directional, `covers`: which tests reach this file, and so what
should go red.

**Not knowing is visible.** A path the graph does not hold gets "NOT in the graph
— this is 'unknown', not 'unrelated'" and the command that fixes it. An empty
list would read as "nothing relates to this", which is a confident wrong answer.

### How this differs from RAG

The project already ships `codebase-rag` over 16,850 chunks, and a third way to
search code beside two others would make things worse without a boundary. The
boundary is:

| Question | What answers it |
|---|---|
| What relates to this file, what covers a change, what goes red | **the graph** |
| Where is this written about, what is it called, is there something similar | **RAG** |
| Where is this symbol defined and who calls it | **`tausik symbol`** |
| Where does this string appear | **grep** |

The graph answers STRUCTURAL questions — relations and consequences. RAG answers
SEMANTIC ones — content. They do not replace or compete with each other.

## The index corrects itself on every write

Every file the agent writes re-indexes exactly that file, inside the
`auto_format` hook that already runs `PostToolUse` on `Write` and `Edit`. No new
hook is added for it, and the numbers say why: re-indexing one file is 0.47 ms
of work, while starting a hook process of its own costs 54 ms — thirty times the
work in overhead.

The refresh runs AFTER formatting. A fingerprint taken before it would disagree
with disk in the same instant, and that is a lie, which is worse than being
behind.

**Quiet on write, loud on query.** The refresh never blocks and prints nothing.
When it cannot run — the database is unreachable, the file changed outside the
editor, a `git pull` landed — the artifact simply keeps its old fingerprint, and
`graph show` recomputes fingerprints from disk on EVERY query and names it as
stale. A blocking gate on a secondary index would stop primary work, and a false
block on routine teaches circumvention, which costs more than the miss.

The refresh never ADDS an artifact. A file the graph has not been told about
stays unknown until `graph build` runs: letting a write quietly widen the graph
would make the stored count stop matching what the build reported.

### What this freshness cost

| State of the write hook | Median |
|---|---|
| before this work | 68 ms |
| with the refresh through the full backend | 301 ms |
| with a direct `sqlite3` update | 279 ms |
| **after removing dead journaling** | **50 ms** |

The first version nearly quadrupled the cost of every write, because opening the
backend runs `init_schema` and closing it runs `wal_checkpoint(TRUNCATE)` over a
66 MB database. Both are right for a long-lived process and both are wasted on
one UPDATE from a process that exits immediately.

The rest of the difference came from elsewhere. A per-file "Modified: <path>"
journal entry turned out to have been **broken on Windows for years** — the hook
invoked the POSIX wrapper `.tausik/tausik`, which raises `OSError` there, and the
surrounding `except` swallowed it. Reviving it would have cost 190 ms on every
write, so it was removed rather than repaired: git records the changed file more
precisely, and a machine-written line dilutes the journal entries an agent makes
on purpose (decision #351).

## Cost

A full build of this repository — 4,226 artifacts, 13,312 symbols, 17,644
edges — takes **about 9 seconds**.

The first working build took **2 minutes 27 seconds**. The difference was not
the graph: the database runs WAL with `synchronous=FULL`, so every autocommitted
statement pays an fsync — roughly 6.7 ms per row across twenty-two thousand
rows. The build now runs as one transaction, and that was the whole fix. A build
nobody will run twice is a build nobody runs, and the framework then ships an
empty graph everywhere.

## Layer 2: what a test ACTUALLY touched

Before 1.9, test selection mapped `scripts/foo.py` to `tests/test_foo.py` by
NAME. That is why `CROSSCUTTING_SCOPE` exists — a hand-written patch for the
cases where the names do not line up. Names cannot see dynamic dispatch,
monkeypatching, or the local-imports-inside-function-bodies style this codebase
uses throughout. A run can.

```bash
TAUSIK_OBSERVE_COVERAGE=1 pytest tests/     # record the observation
.tausik/tausik graph build --layer observed # ingest it into the graph
```

The edge runs from the test file to the file it reached: relation `covers`,
layer `observed_coverage`, confidence 1.0 — and here that is not a shortcut, the
test DID run and it DID reach that file. `observations` counts how many tests in
that file reached it.

**Why not `coverage`.** It is not installed and cannot be: the project is
stdlib-only by a hard constraint. The observer is built on `sys.setprofile` —
function granularity rather than line granularity, which is all this needs: the
question is which FILE a test reached, never which line.

**Why a plugin and not a global hook.** Installed before `pytest.main`, the
profiler does not survive into the tests — measured, and it reported zero files.
A hook around each test also answers the question that matters: WHICH test
reached the file, not merely that somebody did.

**Off by default.** The ordinary run does not pay for a graph it is not building.

### The measured cost of observing

| State | 22 tests of one file |
|---|---|
| no observation | 5.5s |
| observation, first version | 14.5s |
| observation with the verdict cache | 7.7s |

The first version called `os.path.relpath` on EVERY call event — millions of
times in a suite — and one test hit a five-minute timeout inside
`ntpath.relpath`, taking an xdist worker down with it. Whether a file is ours
depends only on its name, and distinct names number in the hundreds against
millions of events, so the decision is made once and kept in a dict.

### What observation does NOT see, said plainly rather than papered over

The profiler runs IN-PROCESS, so a test that exercises code in a SUBPROCESS —
which is how this project checks its hooks, its CLI and its gates — leaves the
observer only its own lines, not what the process it spawned reached. Measured
on the live tree after the first full observed run: `scripts/service_doctor_hooks.py`
has four observed tests against twenty-four found by name, import and declared
scope.

That is not a reason to call observation weak: those four —
`test_doctor_commit_hooks`, `test_doctor_trust_tier_weakening` and two more —
are found by NO name-based edge at all. The layers complement each other, which
is why the selection adds them rather than choosing between them.


### The selection is a SUPERSET, and that is arithmetic rather than caution

The observed edge is ADDED to the three that already existed (name, import,
declared scope) — never substituted for them. An incomplete graph plus an exact
selection is a false-green machine: a missed test looks passed, while a
redundant one costs seconds. With nothing observed yet the selection behaves
exactly as before — absence of an observation is not a claim that nothing covers
the file.

**A full run stays mandatory** before a tag and before a batch commit. Selection
speeds the development loop; it does not replace the check before release.

## The coverage gate: what we ship is what is documented

`doc_coverage` is a blocking gate on `task done` and `commit`. It checks one
thing: every name the framework SHIPS is named in the document a reader would go
to.

Two pairs are covered today, and adding a third is one line in
`gate_doc_coverage.COVERED`, not a new test file:

| What ships | Where a reader looks | How a mention is recognised |
|---|---|---|
| CLI commands (53, from the parser) | `docs/{ru,en}/cli.md` | at a line start, or after `tausik ` |
| `doctor` checks (21, from the sources) | `docs/{ru,en}/doctor.md` | as a phrase, aliases allowed |

**Measured when it landed:** of the 53 commands, fourteen appeared in neither
`docs/ru/cli.md` nor `docs/en/cli.md`. Among them `graph` and `symbol` — both
shipped by this same release, both with documentation pages of their own, and
both missing from the command reference. A command an agent cannot discover is a
command nobody uses: the previous release measured that as 2 uses against 226
greps.

**The honesty boundary.** The gate sees whether a name is MENTIONED, not whether
what is written about it is true. A sentence correct about every name and wrong
about the behaviour passes. Claiming more would repeat the very defect it exists
against.

**What it is NOT.** It is not a check that every backticked name resolves to a
symbol. That was tried and refuted by measurement in the same session (dead
end #663): backticks here mean "a name in the system" — a config key, a status
value, a column, a subcommand, or a deliberate mention of something removed. Of
2,689 such mentions five were even candidates, and all five were intentional.

## Snapshots: what changed IN THE RELATIONS since the last release

```bash
.tausik/tausik graph snapshot v1.9.0        # remember the relations under a label
.tausik/tausik graph diff v1.8.0 v1.9.0     # what appeared and what vanished
.tausik/tausik graph diff v1.9.0 now        # against the live graph
```

This is a question nothing else asks: "requirement #12 is no longer covered by
any test" cannot be expressed by comparing TEXTS, however carefully worded — it
is a statement about EDGES.

**Stored whole and compressed; no deltas.** Measured: 23,695 edges are 2,103 KB
raw — comparable to all of `scripts/*.py` at 3,683 KB — and 150 KB compressed; a
live snapshot came out at 154 KB. A delta chain needs a base and every link
intact, and a broken link invalidates everything after it. At 154 KB per release
that fragility buys nothing (decision #354).

**A snapshot carries its own COMPLETENESS, and that decides whether the reports
survive.** Alongside the edges it stores what the graph was at the time: the
artifact count and the layers with their edge counts. Two snapshots taken at
different completeness — one before a test run was ever observed — differ by
6,051 `observed_coverage` edges that were missing from the INDEX, not from the
code. The report says so on its FIRST line, before any difference:

```
! layer 'observed_coverage' is present in the earlier snapshot (6051 edges) and
  ABSENT from the later one — its edges below are a difference in what was
  INDEXED, not in the code
```

A first report full of false "vanished coverage" destroys trust in the mechanism
permanently, and there is no second reading.

**A changed observation count is not structural drift.** The edge is the same
relation; only how often it was seen has moved, and calling that drift would
flood every report with the noise of ordinary work.

### How this sits beside the RENAR drift detectors

It complements them and replaces neither (decision #354). `drift-1` re-validates
stored rows against cross-field invariants a CHECK cannot express — a question
about DATA VALIDITY, which no snapshot comparison asks. `drift-7` catches a task
closed against a requirement edited AFTER the link was made — a relation in TIME,
and graph edges carry no time. Three mechanisms, three questions; collapsing them
into one would lose two.

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
