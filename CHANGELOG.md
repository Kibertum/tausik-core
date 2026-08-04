# Changelog

All notable changes to this project will be documented in this file.

This project adheres to [Semantic Versioning](https://semver.org/).

> Russian mirror: [`CHANGELOG.ru.md`](CHANGELOG.ru.md). Both files cover
> the same releases — keep them in sync when adding a new entry.

## [Unreleased]

Nothing yet.

## [1.8.0] — 2026-08-03

### Fixed — Python 3.13 changed `ntpath.isabs`, and the path redactor stopped redacting on Windows

Found by the release matrix: eight cells green, the ninth — windows + 3.13 — red
on two `test_knowledge_origin` tests.

`relative_source_file` takes the machine's directory layout out of the
`source_file` column. It asked `os.path.isabs` whether a value was absolute, and
that answer MOVES: Python 3.13 stopped `ntpath.isabs` from calling a path with
one leading separator and no drive letter absolute. The function then returned
such a path UNCHANGED — leaving the directory layout in the very column this
redaction exists to clear. On one platform, from one minor release onward,
silently.

The uncomfortable part is not the Python change. This same module defines
`_ABSOLUTE_RE` a hundred lines above and states outright why `os.path.isabs`
cannot be used. One function in the module did not use it. It does now.

Absoluteness is a property of the SPELLING. Asking the interpreter what it
thinks today makes the answer a moving target.

### Fixed — CI provisioning was fixed in one of the two places

The same defect closed in `.gitlab-ci.yml` was left untouched in
`.github/workflows/tests.yml`, and the release's nine-cell matrix failed on it in
all nine. Fixing the FOUND CASE instead of the FORM is exactly what convention
#361 forbids, and it was violated within an hour of the case being found.

Three failures, one root: the runner did not install `requirements.txt`.

- `test_mcp_no_deprecated_primitives` — `ModuleNotFoundError: No module named
  'mcp'`. Not a skip but an error: a red that says "your code is broken" about an
  unprovisioned runner.
- `test_mypy_clean` — three `import-not-found` errors on `mcp.server`,
  `mcp.server.stdio` and `mcp.types`, under a message asserting that "the
  declared tree is no longer clean" — a missing PACKAGE presented as a TYPE
  regression.
- `test_both_host_profiles_are_actually_scanned` — the runner deployed only the
  claude profile. The guard against forgetting the second profile was defeated by
  an environment that had one.

Both CI configurations now ask for the same thing: `requirements.txt` and
`bootstrap --ide all`.

### Fixed — the security gate had never run on a release, and fired twice on the first one

GitHub's `security-review` workflow is wired to `pull_request` into main.
Releases were published by pushing straight to main, so the event it subscribes
to never happened. The first release to travel through a pull request switched
it on, and it immediately reported two HIGH-severity findings.

- **B324, `audit_pytest_dedupe`** — `hashlib.sha1` with no stated purpose. The
  hash is a bucket key for grouping identical test bodies in a report, not a
  signature anyone trusts. That is now SAID in the code via
  `usedforsecurity=False` rather than suppressed with `# nosec`: a suppression
  hides the intent instead of naming it.
- **B613, `brain_scrubbing`** — the file carried invisible bidi controls. The
  module that exists precisely to FIND them held them as literals: the
  `_ZERO_WIDTH_RE` class was spelled with the characters themselves. A scanner
  cannot tell a detector from a payload — and it is right not to, because no
  reader could see what the class contained either. The class is now written as
  escapes, and the set of matched code points was checked by walking EVERY point
  in the ranges: 16 characters, none lost, none gained.

Two tests come with it: one pins the whole set, the other asserts the file
carries no invisible characters of its own — a file-level property that costs
nothing to check and should not be learned from a release pull request.

### Fixed — the shape of a path was decided by asking which OS was reading it

Found while publishing: the first full run on Linux produced 7 failures where
Windows produced 6949 greens. None of them is flaky — all seven are one thing.

- **`path_glob.normalize`** collapsed `..` through `os.path.normpath`, which
  treats a backslash as a separator ONLY on Windows. `A\B\..\C` became `a/c` on
  the maintainer's machine and stayed `a/b/../c` on Linux — so a rule written as
  `a/c` simply stopped matching there. The docstring had promised all along that
  "a Windows backslash, a trailing separator and a `../` are not three different
  ways to spell the same path"; one line of code delivered that on one platform.
  The separator is now replaced BEFORE the collapse, and the collapse is
  `posixpath`'s rather than the platform's.
- **`memory_sinks._tree_relative`** asked `os.path.isabs`, which calls
  `d:/proj/core` relative anywhere but Windows. The path fell through as
  "already project-relative" and the one line the reader must act on printed the
  whole absolute path — precisely the defect convention #282 forbids, back again
  on the other platform. `path_glob.is_absolute` now answers by SPELLING: a POSIX
  root, a UNC root and a drive letter are absolute everywhere; `C:x`
  (drive-relative) is not.
- **`knowledge_home_guard`** checked UNC syntax only AFTER `abspath`. On Linux
  `abspath` glues `\\server\share\kn` onto the working directory, the check never
  fires, and the guard goes on to create a directory with that literal name. The
  single refusal the entire "written without redaction because it never leaves
  this machine" argument rests on was Windows-only, and its test said otherwise
  only because it had never run anywhere else. The check moved to the RAW value:
  a spelling belongs to the string, not to the operating system.

Plus three tests that measured something other than what they named: one checked
an incidental property of `abspath` instead of "a drive letter is not read as a
URL scheme"; one required two host profiles and relied on the author's machine
having them; one read `.tausik/config.json`, which is gitignored by design, and
died with `KeyError` on any clean clone. The first now asserts the property, CI
provisions both profiles for the second, and the third SKIPS with its reason
stated when the setting is absent rather than failing or quietly passing.

**Why this survived to the tag.** The pipeline is configured for `main`, tags and
merge requests. All of 1.8 — 74 commits — was developed on a branch where it
never ran once, and Linux saw the release for the first time on publication day.
The header of `.gitlab-ci.yml` says it exists so the gate would stop standing
behind the door after the CRLF episode. It was behind the door again, for a
different reason, with the same result.

### Fixed — the count of breaking changes lived in prose, where nobody counted it

Three divergences found by review before the tag. The first is about the
checking mechanism itself.

- **The `whats-new-1.8` intro (EN + RU)** promised FIVE breaking changes above
  six sections. `test_breaking_change_count_converges` was green throughout: it
  compares `### N.` headings across four documents, and there really are six
  headings everywhere. The number spelled out in the opening sentence it never
  saw — precisely the failure its own docstring names as the reason it exists,
  and it survived the arrival of the sixth change. A reader does not count
  sections; a reader reads the first sentence. The test now reads it too: it
  extracts the number stated in words or digits from four documents (both
  whats-new pages and both READMEs) and compares it with the section count.
  Russian numerals inflect, so the table holds stems rather than dictionary
  forms; the detector is checked against live data and against negatives —
  "v1/v2 → v3" is not read as a count of breaking changes.
- **Breaking change 2** told you to move the shared knowledge store by hand
  (`mkdir` + `mv`), while the 1.8 code adopts it on its own:
  `adopt_legacy_store_if_present` COPIES the file from the old address on first
  use and only runs when the new location is absent. The document sent you to do
  work already done, and to do it with the wrong verb. Both pages now state the
  code's behaviour and its single exception: when `TAUSIK_HOME` is set, adoption
  does not run at all, and there the move really is yours. The check changed from
  "the directory should not exist" to "the file is there" — the old directory
  survives the copy.
- **`README` (EN + RU)** called the headline of 1.8 "the project's state travels
  in git", while the tag notes and whats-new called it the shared knowledge base
  and the end of the server-side session. No single statement was false, which is
  why no gate caught the divergence: the release simply presented as three
  different releases depending on where you looked. The section is rewritten —
  three pillars, and six breaking changes with a link to the walkthrough.

Along with it, the "6630 tests" badge against a live 7115 — an understatement
rather than a falsehood (the number is documented as a lower bound, decision
#182), but a tag is the cheapest moment to remove it.

### Fixed — the ruff gate rested on the linter's DEFAULT, not the project's choice

Found while publishing: the release pipeline failed with 1572 findings over a
tree in which not one line of code had changed. CI installs ruff unpinned, 0.16.1
shipped, and its default rule set moved — EXE001, I001, SIM115, PLW1510, RUF100
and more turned themselves on.

The gate had been enforcing `E4, E7, E9, F` plus `BLE001` all along, but the
config said only `extend-select = ["BLE001"]`: everything else came from the
vendor's default. A verdict that depends on the version of the tool that ran it
is not measuring the code. The rule set is now stated in the config IN FULL, and
the result no longer depends on what happened to install: `ruff check scripts/
tests/ bootstrap/` returns zero on both 0.15.12 and 0.16.1 — measured by running
both.

Pinning the version in CI was rejected as treating the symptom: it would have
left the verdict hostage to the install and broken the same way at the next
default change. Adopting ruff's newer defaults is a decision about 1539 findings,
and it belongs in a task, not in a release-day pipeline.

The one genuine finding is fixed with it: an unused `import hmac` in
`scripts/verify_handle.py`. The nonce is compared in SQL, there is no Python
comparison, and nothing read that import from there.

### Fixed — four documents outran their code, with every doc gate green

Found by review, and the gates are the point: `docs_lint`, `audit_stale_docs`
and `gen_doc_constants --check` all pass on every one of these. They check
links, mirrors and generated constants — not whether a sentence is true.

- **`quickstart` (EN + RU)** said the git projection runs "on task close". The
  contract has been "any durable write to one of the five projected kinds" since
  the trigger moved; `team-state-in-git.md` and `cli.md` were updated, quickstart
  was not. It is the first document a new user reads, and it was teaching them to
  re-run `state export` by hand after every `decide`, `memory add` and `task log`.
- **`docs/ru/research/risk-model.md`** — the design document for the risk
  composite — did not know about the backtest that refuted it. Its "known
  limitations" listed five ways the model is imprecise and none saying it does
  not discriminate at all (AUC 0.4820, decision #212). A reader who opened the
  DESIGN rather than the changelog came away believing the composite works. The
  status now sits ABOVE the limitations, because that ordering is the message.
- **`i18n-strategy.md`** contradicted itself: the tree diagram called
  `en/research/` "localized — paired with ru/research/" while the "What's NOT
  localized" list, in the same file, said research keeps its original language.
  Actual counts: 1 EN against 10 RU. Resolved toward the practice rather than the
  aspiration — research notes record what someone measured on a date, and a
  translated measurement is an invitation for two copies to drift. The
  `audit_stale_docs` exclusion for research now matches a stated rule instead of
  quietly covering a gap, and it stays.
- **`tausik metrics`** printed its closure-risk block with no caveat while
  `tausik status`, from the SAME module, printed "descriptive, not predictive".
  Presenting one number with two degrees of confidence in two places is how it
  came to be read as a quality verdict. The block header now carries it too.

One reported item did NOT survive checking and is recorded as such rather than
"fixed": the claim that `mcp.md` documents only one reason a `decide` stays
local. Since 1.8 `decide` does not publish anywhere at all, so there is no
silent-local path left to document, and `mcp.md` already says exactly that.

### Fixed — the Rule 5 checklist gate denied evidence it had been handed

Matching required `AC-N` on the SAME line as the citation, so the fuller form —
a heading, then one line per test beneath it — parsed as a heading with no
evidence plus citations belonging to nothing. The gate then reported "no
acceptance criterion names a test" over a checklist that named several, and it
did so on four consecutive closes; its own escalating nudge reached "reminder
#4". Measured on the notes of four real closed tasks: 101 evidence lines matched
to no criterion.

The form is not a matter of taste. One criterion covered by four tests does not
fit on one line, and the gate's message showed a single-line example without
saying it was the only shape recognised. Both messages now name both forms.

Worth stating why this counted as a defect rather than an inconvenience: the
gate exists so a check mark cannot stand in for evidence. A gate that denies
evidence it was given teaches its reader to skip its output — and it is then
skipped equally on the closes where the checklist really is absent. What was
lost is the signal, not the convenience.

Recognition is widened WITHOUT becoming acceptance of anything, which is the
half that keeps it a gate. A section is opened only by a line carrying an
EXPLICIT `AC` token, and ends at the next such heading, a blank line, or the
start of the next log entry; a line inherits it only if it carries BOTH a check
mark and a real citation.

The `AC` token is required for a reason found by reviewing this change before
release rather than after. The first version opened a section from any line an
index could be read out of — using a pattern whose `AC` prefix is optional,
correctly, because it was written for the `acceptance_criteria` FIELD where
every line is numbered by construction. Pointed at free-form notes it read
`3 retries were added to the flaky client` as a heading for criterion 3 and
credited the next citation to it. Since evidence is counted per TASK and the
hard block clears at one real citation, a single sentence beginning with a digit
could have cleared the gate for a task with no coverage at all. Recognising a
heading and reading an index are different questions and now use different
patterns. Each
half rules out a different mistake — without the tick, a planning note that
merely mentions a test path would be counted as evidence for whatever criterion
it followed; without the citation, a bare tick would acquire a criterion by
proximity, which is exactly the substitution being guarded against. A task with
no checklist is still warned, and the tests assert that in both directions.

### Fixed — the shared store spelled tag lists differently from the project store

`knowledge_write` wrote `",".join(tags)`; the project store writes and reads a
JSON array. Nothing broke, because neither the CLI search nor the MCP formatter
printed tags at all — the divergence was unobservable rather than harmless. It
was armed: the obvious next improvement is one tag renderer over a result set
holding rows from both stores, and that renderer either swallows the
`JSONDecodeError` the project code already catches — showing "no tags" for rows
that have them — or it raises. A defect with a delayed action built into the
DATA, growing more expensive with every row written.

Converged on the project store's form rather than declaring two formats legal.
The alternative was to pin the divergence with a test and require every future
reader to handle both, which is a tax on code that has not been written yet,
levied to avoid one migration today while the store holds a few dozen rows.
Existing rows are normalised on the next open, idempotently, leaving NULL and
empty values alone — `[]` and "no tags" are different claims, and turning one
into the other would give the read side something new to tell apart for no gain.
The Notion-mirror import goes through the same canonical writer, so the codebase
stops being a second producer of the old shape.

The renderer that would have broken is now written, which is what demonstrates
the fix: `memory list`, `memory show` and the mixed `memory search` output all
read tags through one function. One loss is recorded rather than guessed at — a
tag CONTAINING a comma was already destroyed by the CSV write, since `["a,b"]`
and `["a", "b"]` both became `a,b` and nothing in the stored value tells them
apart. It is read as two tags, and the ambiguity is documented instead of being
resolved by a heuristic that would be wrong half the time.

### Fixed — `TAUSIK_HOME` was unvalidated, and the no-scrubber argument rested on it (BREAKING)

The shared store is written WITHOUT redaction, and the reason on record is that
it is a file in the user's own home that never leaves the machine. That is not a
property of the code — it is a property of a DIRECTORY, and `TAUSIK_HOME` let
anything name that directory. `knowledge_home()` did `abspath(expanduser(...))`
and nothing else. Point it inside a work tree and the accumulated knowledge of
every project this person works on leaves with the first `git add -A`. Point it
at OneDrive or Dropbox — which live inside the home directory, so "it is in my
home" stays true while the conclusion drawn from it stops being — and it leaves
over the network. None of this needs malice: a wrong variable in a CI config, an
MCP wrapper started with someone else's environment, a copied `.env`.

The response is split by whether the danger can be removed rather than only
reported, because a guard that refuses an ordinary setup gets switched off and
then guards nothing:

- **Network paths and cloud-sync directories: refused.** Nothing written locally
  changes what a sync client does. Matching is on whole path COMPONENTS, never
  substrings — `~/notes/my-dropbox-notes` is a directory someone named after a
  tool, not one a tool syncs.
- **A git work tree: neutralised, not refused.** The store's own directory gets
  a `.gitignore` of `*`, the same trick `.tausik/` already uses, so `git add -A`
  skips it. Refusing here would have rejected the DEFAULT location for everyone
  who keeps their home directory in a dotfiles repository — a common practice,
  and a false alarm is how a guard loses its authority.
- **A store git is ALREADY tracking: refused.** `.gitignore` does not untrack
  what is indexed, so there the disclosure has happened and continuing quietly
  would add to it.

Symlinks and junctions are resolved BEFORE anything is judged: a link named
`~/.tausik-knowledge` pointing into `~/Dropbox` passes every name-based check
while being precisely the case being guarded against. UNC paths are rejected
before resolution as well as after, because resolving one reaches for the
network and an unreachable share blocks for as long as the OS will wait. A
network path wearing a drive letter — the shape of a corporate roaming home —
is caught by the volume type rather than the spelling.

The two halves are split on purpose, and it is not tidiness. What a PATH says
cannot change while a process runs, so it is validated once and cached. What GIT
says can: a directory becomes a repository, a file gets added. A long-lived MCP
server is exactly the process that validates a location early and keeps running
while the filesystem moves under it, and a remembered "that was not a
repository" would be the guard switching itself off. So the git half is
re-decided on every open, and it is reached only from the code about to open the
store — never from a read that merely asks where the store would be, which keeps
the store's laziness contract intact. It stays cheap because finding the work
tree is a walk up for `.git`; `git` itself runs only once one has been found,
which for most people is never.

An existing `.gitignore` is not taken as proof of anything, and that was the
sharpest edge here. A store directory can easily pick one up from scaffolding or
an editor, and `*.log` in it protects nothing — treating its mere presence as
"already handled" is how a guard silently does nothing in the one case it exists
for. So the question asked is whether git IGNORES the store, and when the answer
is no the rule is appended rather than the file replaced, because the other
rules in it are somebody's and not ours to drop.

Two honest degradations rather than pretend answers. With git absent, the work
tree is still found by walking up for `.git` — worse than asking git, and far
better than reporting "no repository" and switching the protection off on the
machine least likely to notice. Whether a file is already TRACKED cannot be
answered without git, so with none available the store is protected going
forward instead of refused: a refusal resting on an unanswerable question is a
guess wearing a refusal's clothes.

Two limits are stated rather than implied: on macOS a network MOUNT is not
detected (`/Volumes` is where its local external drives appear too, so refusing
the unclassifiable would refuse ordinary disks), and `box` and `mega` are absent
from the sync-directory list despite being real products — they are ordinary
English words, and `~/archive/mega/` is likelier than a sync root spelled that
way. Their actual sync roots carry suffixed names, which are matched.

### Fixed — the shared store no longer records which client each row came from

`origin_project` held the ABSOLUTE root of the originating project on every row
of every table. On a machine where one person works for several clients out of
one home directory — the path of this repository names a client — that made
every client's directory name readable from every other project: same file, same
OS account, no export and no privilege required. `SELECT origin_project` was the
whole attack. The trust boundary in consulting work is the CLIENT, and an
earlier version of the argument for storing an unredacted path treated "same OS
account" as "same trust domain"; those are not the same thing.

The read path already displayed the last component only, and that was never a
fix — it changed what a command PRINTS while the value at rest still named the
client to `sqlite3`, to the logical export, and to any backup of it.

`origin_project` now holds `basename@fingerprint` (eight hex digits of SHA-256
over the canonicalised root). This keeps the property the absolute path was
stored for — two projects called `core` stay distinguishable, which basenames
alone could not do — and drops the directory names. The obvious alternative, a
pseudonym plus a mapping table, was rejected for a stated reason: the table has
to live somewhere, and wherever it lives it holds exactly the string that was
supposed to stop existing. This fingerprint is COMPUTED, so a project answers
"is this row mine?" by deriving its own label, and nothing anywhere needs the
inverse. Snippet `source_file` is normalised to a project-relative path for the
same reason — a path outside the project collapses to its basename rather than a
`../../` chain, which would spell the same directory names relatively.

Rows written before this are rewritten on the next open of the store, in all
three tables, idempotently, leaving NULL and non-path values alone. That runs on
open rather than as a command because a migration nobody runs is a migration
that did not happen — the same reasoning the legacy-store adoption uses.
`PRAGMA user_version` is deliberately NOT bumped to gate it: the version guard
is fatal by design, so a bump would make every older TAUSIK on the machine
refuse to open the shared store, which is a breaking change bought to avoid a
scan of a personal knowledge base on a path that already rebuilds the schema and
the FTS triggers on every open.

Two things the migration deliberately does NOT do, both found by reviewing it
adversarially rather than by running it. It does not rewrite a free-text value
that merely CONTAINS a separator — `origin_project` is free text by design, so
`team/backend` is a tag, not a path, and fingerprinting it would destroy a
legitimate value irreversibly to remove a disclosure that was never there; the
predicate requires an ABSOLUTE path, spelled so that a row written on Windows is
still redacted when read on Linux. And it no longer leaves a live handle behind
when it fails: `connect_knowledge_db` closed the connection when the version
check raised but not when the schema setup did, which was safe only while that
setup was pure `CREATE IF NOT EXISTS`. Per-row work can hit a contended lock, and
a leaked handle holds the WAL open for every other project pointing at the file.

Not marked BREAKING, and the judgement is stated rather than left implicit: no
user action is required, the data migrates itself, and the only behaviour a
person could have depended on is a `--global` write from OUTSIDE any project —
which used to succeed by attributing the row to whatever directory the shell
stood in. That now raises. A fabricated origin is worse than no write, because
nothing downstream can tell it from a real one.

### Added — "What changed in 1.8" upgrade page (EN + RU)

`docs/en/whats-new-1.8.md` and `docs/ru/whats-new-1.8.md`. Releases here are git
tags with hand-assembled notes, so the four breaking changes lived only in the
changelog — a file nobody reads while upgrading. Each now carries its migration,
a "does this affect you?" check, and the reason it is breaking rather than
hygiene.

It also records an INTERACTION between two of them that neither describes on its
own: the trust-tier migration tells you to write `~/.tausik/config.json`, which
creates the very directory the shared-store move exists to remove (project
discovery walks up looking for exactly `.tausik`). The page names
`TAUSIK_USER_CONFIG` and the managed tier as the ways out. Found by reading the
two migrations against each other rather than in sequence.

### Changed — "session" was two things; the seam is now visible (decision #223)

`sessions` glued together WORK CONTINUITY (the handoff: what was done, what is
in flight, what to do next) and AGENT CONTEXT HYGIENE (the 180 active-minute
limit, the 200-call capacity budget, the checkpoint counter). They are
properties of different subjects, and three couplings between them are gone:

- `session_handoff` no longer requires an open session. The coupling had it
  backwards: an agent that has just hit the 180-minute limit is the one that
  most needs to write down where it stopped, and refusing there lost the
  document the limit exists to force. With no open session the handoff attaches
  to the most recent one; only a project that has never had a session is
  refused.
- Saving a handoff no longer resets the checkpoint counter as a side effect.
  The reset is now `reset_checkpoint_counter`, a named operation. `/checkpoint`
  still does both — explicitly, and in that order.
- **An absent session is no longer treated as unlimited capacity.** The
  200-call gate used to return early when no session was open, so it stopped
  gating and said nothing. That also inverted the incentive: the cheapest way
  past a capacity refusal was to end the session and never start another. It
  now refuses, and the refusal names the other things a missing session
  silently switches off — usage telemetry, token metrics, model pinning, and
  the "this session" brain slice (which reports lifetime numbers as session
  ones: wrong, not empty).

NOT dropped: work continuity stays. The proposal to drop it rested on the
git-native projection having taken over, and that premise was measured and
refuted — `sessions` is not a projected kind, the projection is off by default,
`next_steps`/`warnings` have no column outside `sessions.handoff`, and the
projection documents its own gaps. The condition under which the drop becomes
possible is now an executable gate
(`tests/test_session_two_halves.py::TestTheDropConditionIsNotMet`) rather than a
paragraph. See `docs/ru/sessions.md`.

Nothing was deleted: the table, the lifecycle calls and every session-keyed
metric keep working. Calibration turned out never to have depended on sessions
at all — it reads `tasks` only.

### Added — a verify run can now be PRESENTED instead of searched for (schema v44, receipt v3) (BREAKING)

`task done` used to prove verify-first by SEARCHING `verification_runs` for a
row that was green, matched the files_hash and the gate signature, and was
younger than 600 seconds. The link between "I verified" and "I am closing" was a
time-window query, and three of its properties were defects: a substantive
refusal ("you declared a subset of what git says changed") reached the agent as
a CACHE MISS, because miss was the only word the lookup had; the freshness
window belonged to the server and was invisible to the model; and two processes
holding different modules in memory computed "fresh" differently.

`tausik verify --task <slug>` now mints and PRINTS an explicit state handle
(`<run_id>.<nonce>`, 128 bits of entropy), and `task done --verify-handle` looks
up exactly that run. This is SEP-2567's "explicit state handles" applied as
decision #218 specified. Redemption re-derives everything from live state — the
declared files are re-hashed off disk, the gate signature is recomputed from the
live config — so a tree that moved is caught by the thing that actually changed
rather than by a clock, and the resulting refusal says which. Every refusal is
fail-closed, spending is atomic and single-use (SEP-2322 replay), and the
security-sensitivity predicate now reads the files the RECEIPT names rather than
the argument the caller passed.

Receipts are `tausik-receipt/v3`: they carry `files`, `gate_signature` and a
signed `expires_at`. A v2 receipt stays cryptographically valid and still works
on the old path, but cannot be PRESENTED — it names neither what it covered nor
which gates ran, and the refusal lists exactly which fields are missing.

The handle's lifetime is one hour (`verify_handle_ttl_seconds`), longer than the
600-second cache TTL it does not replace, and it is published in the
`tausik_verify` tool description, in the CLI output and inside the signed
receipt — SEP-2567: "A policy only in server documentation is not visible to the
model."

The handle is validated by the gate but SPENT inside the transaction that
writes `status='done'`. Redeem-once exists so one green cannot close two tasks;
that is a property of closing, not of passing a check. Spending it at the gate
meant a close blocked by a later check burnt a verify run for a task that never
closed — and certified nothing in exchange.

NOT a change in what counts as green: `task done` WITHOUT `--verify-handle`
behaves exactly as before. The handle changes how a green is presented, not
which greens count.

### Fixed — a migration test named its subject "the latest migration"

`test_migration_v43_model_mismatch` derived the version under test from
`SCHEMA_VERSION`, so v44 broke every arithmetic in it at once: the fixture
popped v44 instead of v43 and then asserted the database had stopped at 43. It
also applied the live index script to a v42 database, which now names a column
v44 adds. Both are pinned to literals; a test that names its subject by "latest"
stops testing its subject the moment something else becomes latest.

### Fixed — `brain move` left ghost files behind

All three of its writes went around the git projection. Two raw
`DELETE ... WHERE id = ?` statements removed rows and left their files in
`tausik/` as ghosts — describing entries the database no longer had — and one
raw `decision_add` created a row with no file at all. The command works in
batches, so one run left as many ghosts as it moved rows, and a later full
`state export` hid every one of them by rebuilding the tree from scratch:
`status` stayed clean while the incremental tree rotted.

Deletes now go through `decision_delete` / `memory_delete` on the write layer,
which resolve the row's slug BEFORE removing it and let the projection shrink
with the database — including re-rendering rows whose edges pointed at the
departed one. The insert goes through the same `write_local` funnel as every
other decision. Projection failures stay fail-open: a broken export does not
roll back or abort the migration.

### Fixed — CLI help sent people to the shared store's old address

The store moved out of `~/.tausik/` (see below). The code moved; the words did
not. Four help strings and four docstrings kept naming `~/.tausik/knowledge.db`,
and help text is read as an instruction: someone told that path goes there,
finds nothing, and concludes their entries were never saved.

Help now reads the location from `knowledge_db.default_store_display_path()`,
built from the same constants the code opens, so the next move carries the words
with it. The comment explaining WHY the store moved deliberately keeps the old
path — there it is a fact about the past, and a sweep that "fixed" it would turn
a correct explanation into a false one. A test asserts both directions.

### Fixed — the shared store no longer masquerades as a project (BREAKING)

The shared knowledge base was placed at `~/.tausik/knowledge.db`, and
`find_tausik_dir` locates a project by walking UP looking for a directory named
exactly `.tausik`. So the moment that directory existed, every path beneath the
user's home resolved to the HOME as its project.

This was observed, not theorised. Commands run from temporary directories wrote
a stray project database and config into the home; six tests turned red by
silently sharing that one "project"; and any of the user's own repositories
living under their home without a `.tausik` of its own would have resolved the
same way. Moving the directory aside turned all six green, and putting it back
turned them red again.

The store now lives in `~/.tausik-knowledge/`, following the precedent `brain`
already set with `~/.tausik-brain` for exactly this reason. An existing store at
the old address is adopted on first read — not by a migration command, because a
migration nobody runs is a knowledge base nobody has — and the old copy is left
in place, since deleting inside someone's home is theirs to decide.

The guard is a PROPERTY comparing the two constants, not a literal: the shared
home's name must differ from the project marker and neither may prefix the
other. A literal would have pinned the spelling of the bug. The behavioural half
walks up from a directory beneath a shared store and asserts discovery does not
adopt it, and a companion asserts a real project below one still wins.

A test written with the store already guarded ONE direction — that `TAUSIK_DIR`
must not move the shared store — and that one-way guarantee read like a two-way
one. The damage was entirely in the direction nobody asked about.

### Changed — recording a decision no longer publishes it anywhere (BREAKING)

`tausik decide` used to run the text through a classifier that looked for
project-specific markers and mirrored anything general-looking to Notion. That
is gone. Visibility is a judgement about INTENT, and the words cannot carry it —
the same sentence is a private note in one project and a lesson worth sharing in
another, and only the author knows which.

The rule failed in the direction that costs something. Six of this project's own
internal decisions reached the owner's wiki, among them the one cancelling the
2.0 plan and the one about the release date, each labelled "no project-specific
markers detected" — because a well-written decision usually reads generally.

Three destinations now, all chosen rather than inferred: this project by
default, the shared local store with `--global`, and the outside world only via
`tausik brain move --to-brain`, by name. The blocker for this was the absence of
an explicit flag; `--global` arrived earlier in this release, so the classifier
had nothing left to stand in for.

PUBLISHING NOW KEEPS THE LOCAL COPY. `brain move --to-brain` deleted the local
row by default, which only became untenable once it was the path people are
pointed at: a publish that removes the project's copy is a handover, and it
contradicted this module's first guarantee. `--drop-local` still moves, for
whoever means it; `--keep-source` is accepted and now names the default.

`tausik knowledge import-brain` brings the accumulated mirror into the shared
store — no network, since the mirror is already a local file. It is idempotent
by construction: each record's identity is derived from its Notion page id, so a
rerun imports nothing rather than tripling the base. Cached web pages are left
behind, because fetched material has no author and importing it would pass
someone else's article off as a note. Origins are written as `brain:<hash>`,
which is what the wiki actually recorded — dressing a hash up as a directory
would invent a path that never existed.

Sixty lines of now-dead mirror machinery were removed rather than left for
someone to wire back, and the module docstring rewritten: it still described the
publish path it no longer has.

### Fixed — Notion is optional, and now it is proven rather than promised

Recon for this task found that most of it was already true: nothing in the agent
loop fails when Notion does. Recording a decision writes locally whatever the
mirror did, `memory add` calls a purely local heuristic, hooks skip silently, and
closing a task or starting a session never touch the brain at all. The scrubber
already sits on the publication boundary, and that is its only call site.

What was missing was not a mechanism but EVIDENCE. An unenforced property drifts,
and this one drifts quietly: breaking it produces no error, just decisions that
stop being recorded. So the guarantees are now tests written against the ways
they could be lost — the universality hint imports nothing that could reach a
network, and no module outside the single publication funnel
writes CONTENT to Notion. That last one was stated too broadly at first and
review corrected it: two callers do reach Notion outside the funnel — one
archives a page by id, the other creates the empty databases during setup — and
neither carries user text, so they are allowlisted with their reason rather than
waved away. A third caller fails the test.

One place did make Notion genuinely mandatory. When `.tausik/config.json` could
not be read, `doctor` added the brain skill to its critical set — "default-on
when config unreadable" — turning an OPT-IN subsystem into a required one in
exactly the case where we know least, and contradicting the rule stated nine
lines above it — far enough that nobody read them together. The commonest way to reach that branch is a fresh project with no
config: precisely the project that has never touched Notion, failing its health
check over a wiki it does not use.

Uncertainty now relaxes the requirement, since `enabled` defaults to false and
that is the only reading consistent with the rest of the config layer — and the
doctor SAYS it could not tell, because an undetermined check that reports nothing
is indistinguishable from one that passed. The rule moved out of a long function
into `brain_skill_requirement`, which is how the contradiction had gone unnoticed:
a branch buried mid-function is not read, and was not testable.

### Added — the shared store finally has a backup, and it stays on this machine

Every project's database is backed up as a matter of course. The shared
knowledge file — the one accumulating what was learned across all of them — had
nothing. `tausik knowledge export --to <dir>` and `tausik knowledge restore
--from <dir>` close that.

The backup is LOGICAL, one readable file per record, never a copy of the `.db`.
Three separate reasons and any one settles it: a database file is not
inspectable, so a backup nobody can read is a backup nobody can trust; it is not
byte-stable either, since freelist movement and WAL checkpoints vary while the
content does not, which would make "unchanged means no diff" false; and a byte
copy carries the FTS5 shadow tables holding tokenised copies of every title,
body and snippet, plus pages of deleted rows never overwritten.

Destinations are local only (decision #219). Nothing on the write path redacts
anything and every row carries the absolute path of the project it came from, so
a backup leaving the machine would withdraw the premise that made un-redacted
storage acceptable rather than the conclusion. `s3://`, `https://` and UNC paths
are refused with the reason, not just a refusal. The check is by SHAPE rather
than reachability — a remote that happens to be down today is still a remote —
and it stays permissive about mounted volumes, because at this level a mounted
share is indistinguishable from a local disk and refusing every mount would
refuse the external drive that is the likeliest backup target there is.

Round-tripping is asserted on CONTENT, field by field, and that caught a real
defect before it shipped. The frontmatter writer escapes the backslash FIRST, so
a reader unescaping with a chain of replacements would turn a literal backslash
followed by `n` into a line break — corrupting `origin_project` on every Windows
row while reporting success. The reader scans instead, consuming each escape
with its target. Swapping it back for the naive chain reddens the round trip.

The destination must be empty or already be one of our backups. Review
reproduced the alternative live: a hand-written ADR file disappeared after a
single export, because reconciliation deletes what it does not recognise. Worse,
`state_export` writes `decisions/` and `memory/` under a project's own tree —
the same names — so pointing --to at that tree would have removed the project's
records on the first run. Reconciliation now also spares any file not named for
a record, and a record whose identity is not a safe filename is refused rather
than joined into a path.

Restores match records by uuid ONLY, with the conflict target named rather than
left to `OR IGNORE`. The difference is data: `OR IGNORE` suppresses every
constraint, and snippets carry a unique hash while memory carries a check on its
type, so a record with a fresh identity whose code already existed would have
been dropped in silence and counted as restored. Anything that is not an
identity collision now raises and names the file. Counts are actual inserts, and
rows already present are reported separately — "left alone" and "restored" are
different outcomes, and only one of them means the backup was applied. The
restore commits once at the end: a failure part-way leaves the store untouched,
because a half-restored store looks like a working one.

Restoring twice, or restoring over a store that partly survived, converges
instead of doubling. A record deleted from the store disappears from the backup
too, or it would be resurrected by the next restore. Repeating a backup of an
unchanged store rewrites nothing — the file content is a pure function of the
row, and unchanged files are not touched at all.

Failures are loud on both sides: no store to back up, no directory to restore
from, a directory that is not a backup, and a backup taken at a newer schema all
raise and say what was not done.

### Added — an older TAUSIK refuses a newer shared store instead of guessing

One machine, several projects, several TAUSIK versions, one shared knowledge
file. When a project meets a store written by a NEWER framework it now stops and
says so, naming both versions and what to do about it.

The tempting alternative was a quiet fall back to project-only knowledge. That
is the worst of the three options available: the person keeps working, notices
nothing, and discovers a week later that shared hints stopped arriving — with no
event to trace it back to. Refusing is louder and kinder.

Ordering carries the guarantee. `init_knowledge_schema` stamps `user_version`
unconditionally, so the check has to run BEFORE it — otherwise an older
framework would rewrite the marker DOWNWARD on every open and destroy the
evidence of skew for every other project on the machine, not just its own. A
test pins the stamp is untouched after a refusal, and reversing the two lines
reddens eight tests.

Fatal is scoped, not universal, and the line is drawn by who asked. Writing a
shared entry or searching shared knowledge refuses outright: the person asked
for the shared store and deserves a straight answer. The knowledge block does
not — it is display-only, its callers are the session-start hook and the
CLAUDE.md refresh, and letting the guard through there would mean one project's
newer store stops every OTHER project from starting a session at all. It renders
the refusal instead, every session, until someone fixes it.

The reverse skew is not an error. A store older than this code migrates on open
and keeps its rows.

### Added — search and the knowledge block read the shared store too

With this the shared knowledge base is a working feature rather than a place to
put things: `memory search` and the block injected into CLAUDE.md now draw from
`~/.tausik/knowledge.db` alongside the project, and each shared row says so.

Provenance follows the precedent `cq` rows already set rather than inventing a
second scheme: `source` states where the row came from, the title carries a
visible `[shared]` prefix, and the id is None. The id matters most. A shared row
does have one — in another database — and printing it would invite `memory show
<id>` to return a DIFFERENT, real, local record. Two renderers already branch on
an absent id, so they needed no teaching.

Shared entries get their OWN section and their own budget in the knowledge
block, which is arithmetic rather than taste. The block runs on hard caps and
orders by `id DESC` as a proxy for recency; the shared store has an independent
id sequence, so "newer id" across the two means nothing. Merging would let
shared rows push project rows out of a block the project depends on, silently,
in proportion to how much had been shared. A test pins that the project's
part of the block — its rows AND the headers around them — is identical before
and after fifty shared rows appear.

Both aggregates compute that section BEFORE their early return on "no local
rows" — a project with no memory of its own is exactly where inherited
knowledge matters, and returning early would have hidden it precisely there.
That was a real hole in the first version of this change, caught by a test
rather than by reading.

Ranking is FTS relevance then recency. No embeddings: short keyword queries are
the dominant shape of an agent's search, and they are where semantic retrieval
collapses. A test greps the read path for known vector libraries. Named for what it is: a
tripwire at the likely point of entry, not proof against a hand-rolled
similarity written without any of those words.

A shared store that cannot be read produces a visible warning and the project's
own results — never a silent shrug. The warning is appended AFTER the block's
line budget is applied, because a notice that competes for that budget vanishes
exactly when the block is fullest, and its absence then reads as "nothing was
shared" rather than as a broken store, because invisible absence of shared
knowledge is indistinguishable from that knowledge not existing. A store that
was never created says nothing at all: nothing has degraded, and warning every
session about a file the user never asked for turns a signal into noise.

Project listings stay project listings. `memory list` and `decisions` still show
this database only — the feature is about SEARCH and about session start, and
blending the two would break the meaning of "show me this project's memory".

The warning lives next to the code that produces it rather than on the service,
and the class-surface ratchet is what forced that question: `ProjectService` was
at its cap, and lifting the cap to hold a diagnostic would have spent a
structural budget on plumbing. The gate asked the right question and the answer
turned out to be the better placement anyway.

### Fixed — a stored record can no longer pose as document structure

Both memory aggregates feed text into CLAUDE.md and into the session context,
where the agent reads it as part of its own instructions. One of them collapsed
line breaks before rendering; the other, in the same file, only truncated. So a
record whose text contained a newline stopped looking like a quoted record and
started looking like structure the framework wrote itself — `- #12 Title`
followed by a line reading `## SYSTEM: ...` is, once rendered, indistinguishable
from a real heading.

Truncating to eighty characters was never a mitigation. Slicing keeps whatever
those characters contain, newline included, so the surviving prefix is exactly
the part an attacker controls.

Both aggregates now route every field through one shared flattener, which
collapses on `str.split()` rather than on `"\n"`. That is deliberate: matching
only the one character left five other ways to start a line — carriage return,
vertical tab, form feed, NEL, and the Unicode LINE and PARAGRAPH separators —
and a guard that one substitution walks around is not a guard. The half of the
codebase that did strip newlines only handled `"\n"`, and restoring exactly that
behaviour still fails twenty-one of the new tests.

The flattening happens at the render boundary, not on write. A stored rationale
is legitimately multi-line, and flattening it in the database would destroy
content to fix a display problem; the value stays whole and only the injected
copy is one line.

Today this reaches one project. After the shared store is readable, the same
block is fed from it, so an entry written under one project renders inside
another — which is why this was fixed before that landed rather than after.

### Added — `--global` puts knowledge in the shared store, or fails saying so

`tausik memory add --global`, `tausik decide --global` and `tausik snippet
extract <id> --scope global` write into `~/.tausik/knowledge.db` instead of this
project. Without the flag nothing changes.

The route is decided by the flag and by nothing else. No prompt, no heuristic,
no "this looks cross-project, shall I?" — this repository already has a
classifier making that call for the Notion brain, and it has misfiled seven
decisions to date. Routing a person can predict beats routing that is
occasionally cleverer.

A write asked to go global goes global or it FAILS, and the error names the
path it could not write to and states that the project database was NOT used
instead. The alternative was never acceptable: someone who typed `--global`
believes the knowledge is now available everywhere, so a fallback would leave
it in one repository while reporting success — invisible when committed, found
months later in another project as an absence.

Shared rows carry the ABSOLUTE root of the project they came from, resolved
through the `.tausik/` handle rather than the shell's cwd, so running the
command from a subdirectory still attributes correctly. Absolute, because
basenames collide — `core`, `server`, `api` — and a collision would credit one
project's knowledge to another.

No scrubber runs on this path. Redaction belongs where knowledge leaves the
machine — publishing to Notion — not on a write into a file in the user's own
home. Scrubbing here would corrupt entries (a redacted path is a wrong path) to
buy privacy against oneself.

That argument covers less than it first appeared to, and the shortfall is
recorded rather than smoothed over. It shows that nothing leaves the MACHINE; it
does not show that nothing crosses a CONFIDENTIALITY boundary. One person works
for several clients out of one home directory, so an entry written under one
client is readable from every other project — no export needed. Two follow-ups
carry that: one on the client name sitting in `origin_project`, one on the
planned backup target for this unredacted file, which currently includes
S3-compatible remotes and would carry it off the machine the argument rests on.
The permissions on the store are narrowed to owner-only at creation, matching
how the signing key is already treated — that bounds who else on the machine can
read it, and nothing more.

The universality hint does not fire either: it asks whether an entry belongs in
a shared store, and the flag has already answered that. A control test asserts
the hint still fires on the local path, so its absence here means something.

### Added — a shared knowledge database, one file per person rather than per project

Knowledge learned in one repository was trapped there. A pattern paid for once,
a gotcha found the hard way, a decision worth carrying — each lived in exactly
one project's `.tausik/tausik.db`, and the next project started from nothing.
There is now `~/.tausik/knowledge.db` (overridable with `TAUSIK_HOME`), holding
memory, decisions and snippets with FTS over all three.

What it deliberately does NOT hold is the project schema. Tasks, sessions,
events and verification runs stay where they belong; nothing here reads or
writes a project database. A shared store that also tracked work would be a
second source of truth for the thing that already has one.

It is multi-writer by construction, not by accident: a person has several
editors open on several projects and all of them point at this one file. So WAL
and a non-zero busy timeout are requirements rather than tuning, and long
transactions are out — a writer holding the file makes every other project's
search hang, which reads as "the tool is slow" instead of as a lock.

Creation is lazy, and that took a deliberate guard. `sqlite3.connect()` creates
whatever file it is handed, so a read path that simply opened the store would
bring an empty one into existence on every status call in every project,
including for people who never opted in — a defect invisible by construction,
since the result looks exactly like an empty store. Existence is therefore
settled on the filesystem before connecting, and only a write may create.

Every row is born with a UUID, which no acceptance criterion asked for. A
project row is identified by its rowid, and a rowid is a fact about one
machine's database; the moment two machines exchange knowledge — the entire
point of the file — rowids collide and "the same entry" becomes
indistinguishable from "a different entry in the same slot". Adding identity
afterwards means reconciling records that already exist. It costs one column
today, and today is the cheapest it will ever be.

`origin_project` and `origin_slug` are free text rather than foreign keys: a
shared record must outlive the project it came from, so it may name its origin
but must never depend on it.

### Fixed — three claims from session #154 that outran their code (session #155)

Same theme as the two entries below, one size down: prose asserting more than the
code delivers. Found by reviewing the batch that had just been written.

**"Never raises" now covers the import.** `_project_write` and
`_flush_pending_projection` both promised never to raise, and both did their
deferred `from state_triggers import ...` outside any try. The imported function
guards its own body completely; the import did not. These two run from `_update`
and from `commit_tx`, so an ImportError would have broken the database write
itself — a best-effort projection taking down the thing it is best-effort about.

**The orphaned-edge sweep is no longer called self-healing, because it does not
converge.** Re-serializing the entity that HOLDS a stranded edge does not touch
`memory_edges`, so the predicate the scan runs on never clears: the same orphans
are found and the same files re-rendered on every later departure. Measured on
2000 memory rows with 40 orphans, three consecutive sweeps: 40 renders, then 40
that changed nothing, then 40 more. The bill is bounded by orphan count rather
than tree size, but archived memory only grows. The docstring now states this
with the numbers; converging means invalidating the edge where the departure
happens, at the service layer, and that is tracked as its own task rather than
smuggled into a fail-open projection trigger.

**The database-identity guard asks the filesystem before it compares strings.**
It claimed "two genuinely distinct files cannot share a realpath", which folding
case afterwards makes false exactly where it costs most: NTFS supports
per-directory case sensitivity — the documented path for WSL2 — so `Data.db` and
`data.db` can exist separately, and `normcase` would have declared them one file.
A fail-closed guard becomes fail-OPEN for the class it was written to catch. When
both paths exist, `(st_dev, st_ino)` now answers, which is what "the same file"
means; the string comparison remains as a fallback for a path that does not exist
yet or a volume with no usable inode, and the residual risk there is named rather
than denied.

### Fixed — the projection hook says what it covers, and it is less than it claimed (session #155)

The write-layer hook was introduced with the line "a mutator nobody remembers to
wire is covered on the commit that introduces it". It is not, and this repeats
that sentence only to retract it: it stood in the trigger's docstring, in a test
docstring, and in both changelogs, so a reader had four independent-looking
confirmations of something no code did.

What the hook actually reaches is an UPDATE by slug and three deletes on
epics/stories/tasks. Around it go every INSERT (`_ins` takes raw SQL and knows
neither table nor slug), both knowledge kinds — memory and decisions are keyed by
row id, not by a slug column — the budget setters that write the projected
`call_budget` and `tier` columns, `task_append_notes`, `task_claim`, and the bulk
`UPDATE memory SET archived_at`. Those are carried by the eighteen hand-written
`auto_export_*` calls in the service layer, which the retracted sentence invited
the next author to delete as redundant.

Measured rather than argued: with only the manual calls silenced and the hook
fully alive, the projection property goes red on all six seeds. That measurement
is now a test, and it is written to fail the day the hook becomes complete — so
whoever completes it has to correct the prose instead of inheriting it.

The gaps are listed by name in the docstring, and the question "is my new mutator
covered?" now has one true answer instead of two contradictory ones: neither
mechanism guarantees it — the property test does, and it sees what its generated
operation set exercises. Finishing the hook is tracked separately for 2.0; the
duplicate render it would remove costs a second serialization and a file read,
not a second write, because the export is idempotent.

### Fixed — the projection writes into the project that owns the database, or nowhere (session #155)

Hanging the git projection off the write layer made it cover mutators nobody
remembers — and moved it below `ProjectService`, down to a bare `SQLiteBackend`
that has a database path and nothing else. Two things the service used to supply
travelled along as assumptions instead of values, and both were wrong.

The address was `dirname(dirname(db_path))/tausik`, which names a project root
only when the database sits inside that project's `.tausik/`. A backend opened at
`<tmp>/case0/tausik.db` wrote into `<tmp>/tausik` — a sibling of the directory the
caller named, outside anything it owns; at `:memory:` it wrote beside the
repository. The directory must now name itself `.tausik`, and when nothing proves
it does, there is no projection at all rather than one somewhere else. The costs
are asymmetric: failing closed loses one unprojected row, failing open writes
files into a directory nobody asked about.

The switch was worse, because it was the reason the address defect fired. Reading
`state.auto_export` from the ambient working directory meant one project's config
answered for another project's database — the same defect the address had already
been fixed for, one policy layer up. No test in this repository ever enabled the
projection; this repository's own config enabled it for every temporary database
the suite built. Measured: 311 tests left 31 stray `.md` files in the shared pytest
temp root, under colliding universal slugs (`e`, `s`, `mvp`, `setup`), never
cleaned up. After the fix the same run leaves none.

The switch is now read from the project the address points at, derived from that
address rather than resolved a second time, so "where we write" and "may we write"
cannot name two different projects.

### Fixed — a rejected `task update` really writes nothing now (session #154)

The entry below from session #153 described a narrower repair than it claimed.
Validating the three budget fields against each other stopped one interleaving —
and the very next block in the same method still raised after those budgets had
been written. `task update --call-budget 40 --scope-paths '{not-json'` stored the
call budget AND a tier derived from it, reported failure, and left by exception
past the projection, so the row and `tausik/tasks/<slug>.md` disagreed silently.
Same shape, one validator further down; the earlier fix removed the failure
someone had hit rather than the shape that produced it.

All validation and normalization now completes before any write, and the writes
themselves run in a transaction. The transaction is not belt-and-braces: it
covers the refusals no amount of up-front validation can pre-empt — the backend
rejecting an unknown column, SQLite rejecting a bad `story_id`, a full disk —
each of which lands between the budget setters (raw auto-committing writes) and
the field write. The deferred-projection queue was already rollback-aware, so a
discarded write discards its queued file with it.

The tests now pair a valid budget with a refusal from each distinct point in the
method rather than budget-with-budget, which is the combination that had just
been fixed and therefore could not detect this.

### Fixed — a drive-letter difference no longer disables brain publishing and blames your project (session #154)

The guard that decides whether this service speaks for the project compared two
path strings. On Windows and macOS `d:\...` and `D:\...` are one file and two
strings, so a project reached through the other spelling failed the check. The
guard is fail-closed, which made the consequence worse than a missed publish:
`decide` then reported "this service is not bound to the project DB, so an
external publish would escape from a throwaway context" — telling a user working
inside their own project that their context was disposable. That message had been
rewritten one release earlier precisely so it would stop naming a reason that was
not the reason.

The comparison now asks whether the two paths name the same FILE: `realpath`
first, then `normcase`. `state_serialize.assert_export_target` already folded case
before comparing and its comment names this exact hazard; this guard was written
later and did not follow the pattern. Both normalizations can only merge two
spellings of one file — two genuinely distinct files cannot share a realpath — so
the guard is not loosened in the direction that matters: a different directory
stays foreign, and unresolvable provenance still fails closed.

The symlink case is decided rather than left implicit: a link to the project's
database IS the project's database, and refusing it would be the same
over-refusal one indirection further out.

### Changed — the L3 escalation says what actually justifies it (session #154)

Decision #206 demoted the closure-risk composite to descriptive, and the line
`task done` prints was changed to match. The trigger underneath was not: it still
fed the same composite — AUC 0.4820 over 374 closures, no power to separate
closures a defect escaped from those it did not — into a check that appends a
blocking failure and returns. The comment defending that arrangement said the
trigger "only ever ADDS review". It does not. It refuses the close.

The block is kept, and the three candidate outcomes were weighed on the record
(decision #212). What changed is the justification, because the old one was not
available: above the threshold, most of the evidence that could be measured sits
at its worst value, and that is a description true by construction whatever the
AUC says — "there is almost no evidence this close was verified" is a reason to
ask for a second reader on its own terms. So the message no longer calls the
closure "high-risk"; it calls it under-evidenced, states outright that this is
not a prediction, and cites the measurement. The remaining gap is named in the
module rather than papered over: the SELECTOR is still the a-priori weighting
nobody validated, and fixing that needs a held-out sample this project does not
have yet.

Switching the threshold to complexity was rejected, not overlooked. Complexity
alone backtests at AUC 0.6327, p = 0.0016 — better than the whole five-factor
formula — but the backtest refused to re-weight on the same 374 rows for a
reason that applies with more force to a blocking threshold: it would buy a
validated-looking coefficient and the same blindness.

Two claims that contradicted the measurement were removed from the source. The
`gate_coverage` weight no longer calls itself "the strongest closure-risk signal
we have" next to a backtest measuring it at AUC 0.409, p = 0.0098 — significantly
inverted. And `tausik status` now carries the same "descriptive, not predictive"
caveat `task done` does; one composite presented with two different degrees of
confidence in two places is how it came to be read as a quality verdict.

### Changed — the projection property is checked over generated sequences (session #154)

The test that carried the guarantee "after any sequence of mutations the tree
equals `build_tree(db)`" checked one hand-written sequence, five functions long,
in registry order. Three live defects walked past it green, and none of that was
luck: the script closed a story before any task in it started, so the
`status == "open"` cascade branch was dead code; every delete in it was a leaf, so
`ON DELETE CASCADE` never fired; and the invariant was sampled once per group, so
"the projection fell behind and caught up" was indistinguishable from "it never
fell behind".

The sequence is now generated — 80 steps per seed over six fixed seeds, drawn from
27 operations by precondition, so order, nesting and which entity an operation
lands on all vary — and the invariant is taken after every single mutation. The
coverage ratchet counts write paths instead of the five entity kinds: the tables
`build_tree` actually reads (traced, which is how `task_logs` and `memory_edges`
got included) crossed with the three DML verbs, compared for equality. The
observation point is the SQLite trace callback rather than a scan of function
bodies for literal DML — that approach was dead-ended because nearly every write
here goes through a shared helper, and a trace callback sits below the helper.

### Fixed — a memory leaving the projection no longer strands the files that linked to it (session #154)

`memory_edges` is polymorphic — `source_type`/`target_type` columns rather than a
foreign key — so the cascade machinery, which reads `PRAGMA foreign_key_list`, is
structurally unable to see it. Deleting or archiving an entry left every file whose
`edges:` block named it describing an edge to nothing, while a full `state export`
dropped that edge; the two disagreed about a file neither had any reason to
re-render.

The departure itself — `export_one` answering `None`, the one signal delete and
archive share — now re-serializes whoever is left holding a dangling edge. The
sweep asks a question of the data ("which live edges point outside the projection
now") rather than of the departed row, because after a `DELETE` the id can no
longer be recovered from the slug; the same phrasing picks up an edge orphaned by
any earlier means.

### Fixed — `export_one` and `build_tree` rendered the same entity differently (session #154)

`export_one` promises bytes identical to `build_tree`'s, and the incremental
projection is built on that promise. `build_tree` resolves edge targets against
the live projection only (`memory ... WHERE archived_at IS NULL`), so an edge to an
archived entry is dropped there; the single-entity renderer looked the target up
without that filter and kept the edge. Same entity, two renderers, different
bytes — which `state export --check` would report as drift with nothing to point
at. The filter is now applied in both.

### Fixed — a rejected `task update` no longer half-applies (session #153)

`task update` validated its three budget fields one after another and wrote each
as soon as it passed: `--call-budget 5 --cost-budget-usd not-a-number` stored the
call budget, then raised on the cost budget. The call reported failure, the row
had changed, and the function left by exception without reaching the projection —
so the DB and `tausik/tasks/<slug>.md` disagreed, silently, until the next
`state export --check` called it "drift".

All three are now validated before any is written. That is the shape `task_add`
already used (`validate_task_add_inputs`); the fix is to apply it here rather than
to compensate afterwards in a `finally`, which would record the half-write instead
of preventing it. The cost-only and token-only paths had no test at all and now do.

### Fixed — deleting a parent no longer leaves its children on disk (session #153)

`stories.epic_id` and `tasks.story_id` are `ON DELETE CASCADE` and every connection
runs with `PRAGMA foreign_keys=ON`, so SQLite deleted the children itself and
Python never learned which rows went. Deleting an epic removed the epic's file and
left every story and task beneath it behind — files describing rows the DB has
never heard of, committed into a tree teammates clone. A full `state export` hid
this (it rebuilds from scratch); only the incremental path accumulated them.

The descendants are now collected before the delete and re-asked afterwards, which
also fixes the quieter half: `decisions.task_slug` is `ON DELETE SET NULL`, so
deleting a task left the decision's file still naming it. One mechanism covers
both, because `export_one` answers `None` for a row that is gone and fresh bytes
for a row that merely changed.

Which children exist is read out of the schema (`PRAGMA foreign_key_list`), not
listed in the code. Both previous fixes in this area shipped a list, and each list
was missing whatever broke next; a projected kind with a cascading foreign key is
now covered by the migration that adds it.

### Fixed — the projection follows the write, not the caller's memory (session #153)

Starting a task auto-activates its parent story; closing the last task auto-closes
the story and the epic. All four of those writes went straight through the backend
in `service_cascade`, and none of them projected: the DB said `active`, the tree
said `open`, and an epic could finish in SQLite while `tausik/epics/*.md` still
showed it running — on the tree a teammate clones. Only `state export --check`
ever noticed, and it reported "drift", not "the cascade never exported".

This is the third time this leak has been patched. The export was wired into two
service methods, then eight, then fourteen; the cascade was never on any of those
lists. So the hook moved to where the writes already meet — `SQLiteBackend._update`,
the single choke point for `epic_update`/`story_update`/`task_update` — and asks
the export registry (`ENTITY_DIRS`) whether the written table is projected, rather
than consulting a table list kept alongside it that would drift the same way.

This paragraph originally ended "a mutator nobody remembers to wire is now covered
on the commit that introduces it". That was false, and session #155 corrected it —
see the [Unreleased] entry on what the hook covers. The hook closes updates by slug
and three deletes; the hand-written service-layer calls still carry everything else.

Projection is deferred while a transaction is open and flushed on commit, because
`task done` runs its status change and the cascade inside one: an eager write
would leave a file describing state a rollback discards — the same divergence with
the sign flipped. A rollback drops the queue; the flush de-duplicates, so
`state import` updating thousands of rows re-renders each entity once.

Also corrected: `test_stale_tree_is_not_reported_as_carrying_new_state` produced
its stale tree by relying on `be.task_update` not projecting — the defect itself
standing in for a scenario. It now turns `state.auto_export` off, which is how the
drift actually arises (the flag is opt-in and off by default).

### Fixed — the state tree survives a Windows checkout (session #153)

`.gitattributes` now pins `tausik/**` to `text eol=lf`, the same rule the `renar/`
tree has carried since June. The projection is written LF-only and `state export
--check` reads it back with universal-newline translation deliberately off, so a
CRLF re-save cannot pass as clean — which means a CRLF *checkout* reads as
corruption too. With `core.autocrlf=true`, git's default on Windows, every fresh
clone converted all ~2100 files and started life with a red `state export --check`
and a red `gate_state_roundtrip` on a tree nobody had touched — on the headline
feature of this release, at the first thing a new user does.

The pin is asserted from the exporter's own registry rather than from a list
retyped in a test: `tests/test_state_tree_eol_pin.py` derives the covered
directories from `state_serialize.ENTITY_DIRS` and the tree root from the
resolver the CLI uses, so a sixth projected entity kind fails loudly instead of
landing quietly outside the rule. It is proven against real git, not against the
attribute string — a temporary repo is cloned with `autocrlf=true` and a control
file outside the tree must come back CRLF, so a green result cannot come from a
sandbox where the conversion never fired. The rule is also asserted NOT to reach
outside the tree: a blanket `* eol=lf` would reformat tracked files it does not
own, which is why the `renar/` fix refused one.

This was the second derived tree to ship without the pin that the first one
already had. Both registries — this and the complexity proxy's generated-dirs
list — are hand-kept, which is why the miss was silent.

### Changed — the closure risk score stops presenting itself as evidence (session #152)

Backtested against this project's own 374 scored closures, 56 of which a defect
later escaped from. The inversion that opened the investigation — escaped
closures averaging *lower* risk — turns out not to be significant (permutation
p = 0.3848). The measured answer is duller and worse: **AUC 0.4820**. The
composite does not separate closures a defect escaped from those it did not, and
it was printed as a quality verdict at every single close.

Per factor, with the weights that were assigned a priori and never checked:

| factor | weight | AUC | p | |
|---|---|---|---|---|
| `gate_coverage` | **0.25** | 0.409 | 0.0098 | significantly INVERTED |
| `test_delta` | 0.20 | 0.495 | 0.7666 | no signal |
| `ac_evidence` | 0.20 | 0.499 | 0.5287 | no signal |
| `security_hits` | 0.20 | 0.467 | 0.2515 | no signal |
| `code_churn` | 0.15 | **0.617** | 0.0098 | the only correctly-signed one |

Sixty percent of the weight rests on factors with no measurable signal, the
heaviest one points the wrong way, and the only working predictor is the
lightest. A composite averaging that into a coin flip is the expected result, not
bad luck.

The `gate_coverage` inversion is not complexity in disguise — the obvious
confound, since complex tasks both run more gates and escape more. Stratifying
kills that explanation: the effect grows inside strata rather than vanishing
(complex: AUC 0.293, p = 0.0170; all 11 escaped complex closures had every gate
run). No mechanism is claimed for it — n is 11, and asserting the plausible story
is the exact error this change exists to correct.

Two more things the numbers say. Risk is **blind to complexity**: nearly flat
across simple/medium/complex (0.3330 / 0.2905 / 0.3147) while the escape rate
varies fourfold (6.8% / 18.1% / 27.5%) — so complexity alone scores **AUC 0.6327**
(p = 0.0016), beating the whole five-factor model. And `complexity_understated`,
the most common escape precursor, moves the score **down**: flagged closures
escape at 25.8% against 14.0%, with a *lower* average risk (0.2464 vs 0.3198).

What changes: the closure line now reads `Risk profile: … — descriptive, not
predictive`. `tausik metrics` prints AUC beside the two averages, plus
complexity's AUC on the same population, so the number's standing is visible
where it is read rather than only in a research note. The mandatory L3 review on
`high` stays — it is noisy, but the asymmetry favours keeping it: a noisy prompt
to look harder costs time, a noisy reassurance costs defects.

No re-weighting, deliberately. With 56 escapes and two significant factors,
fitting weights on the same data would buy a flattering coefficient and the same
blindness; there is no held-out sample at this size to falsify it on. Introducing
complexity as a factor waits for the same reason. Full measurement:
`docs/ru/research/risk-model-backtest-2026-07.md`.

### Fixed — `decide` judged a decision by its headline and shipped its rationale (session #152)

The router classified `text` alone. The publish payload also carried `rationale`
— which, being a good rationale, is where the project detail lives. So the
question "is this internal?" was answered on strictly less material than what
left the machine.

The marker rule was not at fault. `memory_markers` drops two-segment slugs
(`shared-knowledge`, `doc-swarm`) as indistinguishable from English kebab
compounds unless a three-segment slug corroborates them in the same text. In the
decision that escaped, the headline held only two-segment slugs while the
corroborating ones (`redoc-1-8-final`, `l26-memory-decay`) sat in the rationale:
`classify(text)` returns brain, `classify(text + rationale)` returns local with
four markers. Right rule, half the evidence.

Both the publish payload and the classifier blob now derive from one function, so
a fourth field reaches the classifier on the same commit that adds it. Two more
holes closed alongside:

- **Decisions were outside the publish risk gate.** `maybe_block_high_risk_publish`
  began with `if category not in _CLASSIFIER_CATEGORY: return False`, and
  `decisions` was not in it — between a rationale and Notion stood only the
  scrubber. Routing does not cover this: `brain move --to-brain` and the brain MCP
  handler publish decisions without passing through it. Now gated (decision #205).
  Fixing that surfaced a latent bug in the same file — the blob picked keys as
  `PATTERNS if category == "patterns" else GOTCHAS`, so any third category was
  silently read with gotcha keys, yielding empty strings that classify as "empty
  content" and would have blocked every publish of that category for a reason no
  message explains. It is a keyed lookup now, and an unregistered category raises.

- **An external publish could fire from a throwaway context.** The brain write did
  not care which DB the service held: calling `decide` on a temp DB created a live
  page in the user's Notion — a side effect escaping into production from a
  context whose whole premise is that nothing outside it changes. `decide` now
  publishes only when bound to the project's own DB, and fails closed when it
  cannot tell. The message says which of the reasons applied instead of reporting
  "brain not enabled" for all of them.

### Fixed — a decision published to the brain was never recorded in the project (session #152)

`decide` routed: content with no project-specific marker went to the shared brain,
and the function returned before writing the row. Notion was then the only carrier
— no DB row, no `tausik/` file, absent from `tausik decisions` and from the memory
block injected at session start. The mechanism that exists to stop an agent losing
project context could lose it.

This was not an oversight but a specified contract: the test suite asserted
`len(svc.decisions()) == 0` after a brain-routed decision, justified by "otherwise
the decision is double-written". That premise was wrong. `brain_sync.open_brain_db`
opens a SEPARATE cross-project mirror file and never touches the project DB, so a
row in each is the project's record plus the shared one, not a duplicate. The two
stores were conflated, and exclusive routing grew out of it.

The brain is now a **mirror, never a destination** (decision #203): routing decides
where a decision is ALSO published, never whether the project records it. Every
`decide` path funnels through one local write that also projects to `tausik/`. The
success message changes from `saved to brain` to `saved to local and mirrored to
brain` — anything parsing that string needs updating.

Found by using it: the decision recording this release's own scope went to Notion
and left no trace in the project.

### Fixed — `metrics tokens` presented per-tool cost it had never measured (session #150)

The table said "per-tool aggregates" and sorted tools by total input tokens. It
could not have measured that: API usage is reported per MESSAGE, not per tool
call — a limitation the capture hook states about itself ("PostToolUse payload
carried per-tool API usage. It does not"). What the file holds is a
message-level figure stamped onto whichever tool happened to run. In practice
`in_p50` and `in_p90` came out as **2 for every tool**, `in_total` was that
number times the call count — a call counter wearing a cost label, and the
column the table was ranked by — and summing `cache_read` re-counted one cached
conversation on every call, which is how a single tool appeared to have read
568 million tokens across 26 sessions.

The numbers stay, because call volume is genuinely useful. What changes is that
the output now says what they are before showing them, instead of letting a
reader take a ranking of call counts for a ranking of spend.

This closes Gate B without a quantitative verdict, and the reason is worth
recording: the decision about sub-agents was never measurable. There is no
pre-sub-agent baseline (agents landed 2026-04-10..17; telemetry starts
2026-06-15), and the instrument does not attribute cost per tool in either
direction — `Agent` invocations are recorded as 2 input tokens, so a sub-agent's
own consumption is invisible.

### Added — `doctor` reports acceptance criteria parked at closure (session #150)

A criterion marked DEFERRED when a task closes is a promise with no owner and
no due date, and an epic can close over it. That is not hypothetical: two
criteria deferred on 2026-05-06 went unexamined for two and a half months, and
by the time the follow-up needed them the data they were meant to produce had
never been captured.

The check is deliberately narrow in two ways, both learned by getting them
wrong first. It only reads a criterion as parked when the marker follows the
criterion directly — a looser first cut matched four tasks of which three were
false, because "deferred loading" is a feature name here and "deferred … then
closed" is already resolved. And it only looks inside epics that are still
open, because six of this project's ten parked criteria belong to work that
shipped long ago.

It is also clearable, which matters more than it sounds. The deferral text
lives in a closed task and can never stop matching, so the warning would have
stood forever no matter what anyone did — the same unclearable-warning defect
fixed in `doctor` earlier this release. Recording who now owns the criterion
(`AC-N CARRIED BY <slug>`) clears it.

### Added — contextual headers make mid-file passages findable (session #150)

A chunk cut out of a file stops carrying what the file was about, so a query
phrased in the document's terms cannot reach a passage phrased in its own. Each
indexed chunk now carries a short header — path words, the symbol it defines
(or the one it sits inside, for a continuation chunk), and the file's own
summary line. This is the contextual-retrieval technique from onyx / Anthropic
with the model taken out of it: the header is built from metadata the indexer
already has, so the same input yields the same bytes and indexing stays
reproducible and offline.

The header lives in its own indexed column, never in the chunk's content.
Search returns the source exactly as written; a word that exists only in the
header still matches, and still does not appear in what comes back.

Measured, not asserted — `scripts/rag_retrieval_bench.py` derives its queries
mechanically from the corpus and samples deterministically, so the set cannot
be tuned toward a flattering answer. Over 353 files, 115 queries per set,
recall of the specific target chunk:

| K | context set | control set |
|---|---|---|
| 3 | 0.4870 → 0.8348 (+0.348) | 0.5739 → 0.6435 (+0.070) |
| 5 | 0.7043 → 0.9739 (+0.270) | 0.6870 → 0.7391 (+0.052) |
| 10 | 0.8783 → 1.0000 (+0.122) | 0.8087 → 0.8348 (+0.026) |

The control set asks only for words already inside the target chunk, where the
header should not help and above all must not hurt — adding text to an index
dilutes term frequency. It does not: the gain is positive on both sets at every
K, and largest at K=3, which is what an agent actually reads.

An existing index grows into the new layout on first open: the column is added
and the FTS table rebuilt from the chunks, which are the source of truth.
Chunks keep an empty header until the next reindex, degrading to the previous
behaviour rather than to a broken one.

### Fixed — skill bundles were unreachable for every user (session #150)

`tausik skill bundle` resolved its manifest from a `skills-official/` directory
beside the core checkout. That directory exists while developing the framework
itself and never in a bootstrapped project, so the command failed with "no
bundles manifest" for everyone actually using TAUSIK.

Bundle composition now belongs to the store that ships the skills:
`bundles.json` travels inside a tausik-skills-format repo, next to its
`tausik-skills.json`, and resolution scans the cloned repos. The core-adjacent
directory remains only as a development fallback.

The alternative — keeping the bundle list in the core with `repo:skill`
references — was rejected on a boundary, not a preference. The core is
publicly mirrored, so a core-side list of every bundle's members would require
naming private skills in a published file. Bundles that share a name across
stores therefore union their skill lists: a public store can declare a bundle
and leave it empty while a private store fills it, and neither manifest ever
names the other's contents. A bundle stops being a placeholder the moment any
store fills it.

Two failure modes are now told apart, because they need different advice: no
store provides a `bundles.json` at all (add a repo) versus one store's manifest
being unreadable (the offending repo is named).

### Changed — two CLI commands moved back into the module named for their domain (session #150)

An audit of every module in the 360–400 line band asked one question of each:
can its boundary be named in one word? Thirty-one of thirty-three could —
`trust`, `vendor`, `parser`, `migrations`, `conformance`, `export`, and six
that are a single mixin class. Two could not, and both were in the CLI family:
`project_cli_ops.py` ("ops" names nothing) and `project_cli_extra.py` ("extra"
means whatever did not fit). Their docstrings enumerated ten and four unrelated
commands instead of naming a domain.

That family already has a convention — 24 of its 26 modules are named after the
command they implement. The measurable defect was not the naming but a tear:
`project_cli_metrics.py` held the metrics *dispatcher* while `cmd_metrics`
itself sat in `_ops`, and `project_cli_audit_extra.py` held the audit
*subcommands* while `cmd_audit` sat in `_ops` too. A module named for a domain
did not contain that domain's command.

`cmd_metrics` and its cost-rollup helper moved into `project_cli_metrics.py`;
`cmd_audit` moved into `project_cli_audit.py`, which is `_audit_extra` renamed
— nothing in it is extra. The remaining twelve commands were deliberately left
alone: shattering the CLI dispatch surface days before the 1.8 documentation
capstone buys tidiness at the price of regression risk. `project_cli_ops.py`
now says plainly that it is residue rather than a domain, and the split is
tracked separately.

That the band is a fossil rather than live pressure is visible in the
distribution: modules pile up at 350–399 (35 of them) while the cap has been
500 since decision #190, and only eleven sit anywhere between 400 and 499. The
boundaries were placed under the old 400 cap and have not moved since — three
modules say so in their own docstrings ("extracted from project_cli_ops for
filesize gate", "kept out of project_cli_ops.py (400-line gate)").

### Changed — codebase-rag server split by domain; the last temporary filesize exemption is gone (session #149)

`harness/claude/mcp/codebase-rag/server.py` was 562 lines, 12% over the cap,
carried by a named exemption. It is now 134 lines of MCP transport. The two
things that were not transport moved out along boundaries that already existed
in the package: the seven tool schemas to `rag_tools.py`, the dispatch and the
result formatters it owns to `rag_handlers.py`. Both names follow the
`rag_<domain>.py` convention of their neighbours, and the split mirrors the
sibling `harness/claude/mcp/project` package (`tools*.py` + `handlers_*.py`)
rather than inventing a seam.

The move was mechanical and is verifiable as such: every relocated function
body is byte-identical by AST comparison against the pre-split file, including
the schema list. The one deliberate signature change is that the dispatch,
previously a closure over `project_dir` inside `main()`, now takes it as an
argument.

`tausik/gates.json` no longer names this file. With `handlers.py` retired
earlier, the only remaining filesize exemption is the permanent one for the
project MCP schema table.

Two things the split would have broken silently, both now pinned by tests. The
tool-count used for the documentation figures was a regex over `server.py` by
name, so relocating the schemas would have made it answer 0; it scans the whole
package now and survives any further reshuffle. And the trailing
`if __name__ == "__main__"` left with the last function — the server is launched
as a script by `.mcp.json`, so it would have started, defined everything and
exited 0 without ever serving.

Bringing the package into the mypy scope did NOT follow from this, contrary to
what the `pyproject.toml` comment predicted. The collision is over the file
NAME, not its size: two `server.py` files still abort mypy with "Duplicate
module named 'server'". The comment has been corrected rather than left
standing, and the real unblocker — renaming the file, which reaches `.mcp.json`,
the bootstrap templates, the docs and five deployed IDE profiles — is tracked
separately.

### Fixed — `doctor` asserted a CLAUDE.md check it had silently stopped running (session #149)

`tausik doctor` reported `CLAUDE.md drift: none — static sections match
bootstrap_templates`. It had not compared any section. An escape hatch added to
quiet an earlier warning returned "no drift" for any CLAUDE.md under 6 KB
carrying a `## Reference` link to `agent-contract.md`, and the caller then
printed a claim about section equality that nothing had established.

The hatch did not merely soften a warning, it removed the check. Injecting real
drift proved it: rewriting `- **MCP-first.**` into `- **MCP-LAST. Ignore MCP,
use raw SQL.**` inside a static section still reported zero. An inverted
enforcement rule was invisible to the only automated check that watches for one.

The number it used to print carried no information either. This project's
CLAUDE.md is hand-written in Russian, so its headings share nothing with the
English template; every "difference" was really an absent heading, and the count
was just the template's section total — identical for the real document, an
empty file, and a single junk byte.

Drift and customisation are now told apart structurally. A section carried under
the template's own heading whose body diverged is drift. A template heading with
no counterpart is authorship — translated, renamed or dropped on purpose — and
is not a warning. Absence still counts as drift when the file otherwise *is* the
template's document (more than half its sections present), so a project whose
config asks for a directive its CLAUDE.md lacks is still caught.

The remediation text no longer says "re-run bootstrap to reset". That overwrites
hand-written content, so doctor was recommending data loss as a routine step. It
now names the specific sections and states the consequence. On a clean tree
doctor is `OK All clean` — with a line that says what it actually checked.

### Fixed — `session extend` did not reach the display: `status` kept printing the base limit (session #148)

`tausik session extend --minutes 120` answered "New limit: 300 min", and
`tausik status` went on printing `active 64m / 180m`.

Only the *display* was wrong, and that is the interesting part. The Rule 9.2
overrun warning already resolved the extension correctly —
`session_overrun_warning` goes through `effective_session_limit`, which reads the
recorded extend events. So the threshold that actually fires used 300 while both
things a human and an agent read said 180. One fact, three readers, two formulas:
the text line took `view["max_min"]` and the compact JSON took
`data["session_max_minutes"]`, and both were the raw config value.

That mattered beyond cosmetics. The compact JSON is what `/start` and
`tausik_session_open` carry, so an agent planning the remainder of a session
budgeted against a limit that had already been raised — and a user who extended
deliberately read the unchanged number as the command having failed.

Both display paths now resolve the effective limit, so all three agree. Note the
two view dicts had different indentation and a single-shot edit reached only one
of them; the accompanying tests are what caught the half-fix, which is why they
assert the two channels equal *each other* rather than each equal 300.

`tausik doctor` deliberately keeps reporting the configured base — it describes
configuration, not the state of whichever session is open — and that intent is
now written at the line and pinned by a test, so it does not read as the same
bug and get "fixed" into one.

### Fixed — the repo-wide mypy zero was red, and its scope excluded the code the agent actually uses (session #148)

Two findings, one root: nobody had re-measured what `mypy` covered.

**The zero was already red.** `tests/test_mypy_clean.py` exists specifically to
turn "no new errors" into an enforced zero. It was failing — `mypy scripts/`
reported two `import-untyped` errors for PyYAML. Verified against a clean
`git worktree` of the previous commit with the same venv, so it predates this
session's work and is unrelated to any uncommitted change. A prior session had
reported the full suite green; it was not.

PyYAML is an *optional* RENAR dependency, lazily imported inside
`except ModuleNotFoundError` so the CLI works without it. It ships no stubs, and
the obvious fix — `pip install types-PyYAML` — is unavailable here: the venv is
deliberately lean and `tausik doctor` asserts nothing third-party leaked into
it, so installing a stub package to satisfy one check would break another. It is
now an `ignore_missing_imports` override on the `yaml` module, with the
distinction written down: nothing in this repo's own code is being excused, only
the absence of type information in a dependency we deliberately do not require.

**The scope excluded `harness/`.** `[tool.mypy] files` was `["scripts"]`, so the
entire MCP package — the surface `CLAUDE.md` tells the agent to prefer over the
CLI — had never been type-checked. Not a decision; nobody had looked. It is now
in scope, and the 21 errors that surfaced were all `no-any-return`. Twenty of
them were one shape: handlers that take `svc: Any` and return
`svc.some_method(...)`. That one is structural rather than debt — the handler
package must not import `ProjectService`, which is the dependency the
standalone-package split exists to prevent — so it carries a per-module override
with that reasoning, and the contract the `Any` hides (every entry returns `str`
for a `(svc, args)` call) is pinned by `tests/test_mcp_dispatch_surface.py`
instead. Everything else in the package is now checked. The twenty-first error
was not that shape and was not suppressed: `mcp_reaper.cached_enumerate` declared
`-> Any`, flattening its caller's type at the cache boundary, and it is now
generic over what it memoizes — a real bug the widened scope surfaced.

`harness/claude/mcp/codebase-rag/` stays out for a concrete reason, not a
preference: it holds a second `server.py`, and two files mapping to one
top-level module name make mypy abort before checking anything. That
restructuring is `mcp-rag-server-module-split`, and the config names it.

The test itself no longer passes a path. It invokes `mypy` with no argument, so
the enforced scope *is* the declared scope — previously the two were separate
lists, which is why widening the config would have left the new code unenforced
without a word.

### Changed — the MCP handlers god-module was cut along the boundaries it already documented (session #148)

`harness/claude/mcp/project/handlers.py` was 1345 lines and 77 handler
functions covering every domain the framework has, with no literal data to
excuse the length. It was the reason the file-size gate carried a **temporary
named exemption**: removing the blanket `harness/claude/mcp/` directory
exemption had made it visible, and the refactor was too large to bundle into
that task.

The cut needed no new taxonomy. The module already carried section comments —
`--- Tasks ---`, `--- Sessions ---`, `--- Knowledge (Memory) ---`,
`--- Hierarchy (Epics & Stories) ---`, `--- Roles (CRUD) ---` — and the
package already had the pattern for acting on them: `handlers_spec.py` and
`handlers_adapt.py` each export a `<DOMAIN>_HANDLERS` dict that `handlers.py`
merges. The split extended that convention rather than inventing a second one.
Nine new domain modules — `task`, `session`, `status`, `knowledge`,
`hierarchy`, `stack`, `role`, `verification`, `cq` — plus `handlers_render.py`
for the one shared primitive (list rendering, where the point is that an empty
result must read as "No tasks found." rather than as an empty string).

`handlers.py` is now **174 lines** and holds only what is genuinely dispatch:
the tool-call counter, `handle_tool`, the merged table, and the three
single-handler surfaces (exploration, audit, FTS maintenance) that have no
domain to be the second member of. Largest resulting module: 250 lines. The
temporary exemption is **removed** — the gate passes on merit, not by name.

Two things the diff cannot show are now pinned by
`tests/test_mcp_dispatch_surface.py`, asserted against the tool **schema**
rather than a hardcoded count:

- every declared tool still resolves to a handler and no handler routes a tool
  the schema never declares — a tool lost in the move would have surfaced as
  `Unknown tool: ...` at call time, not at import;
- no two domain modules claim the same name. `dict.update` resolves a collision
  silently in favour of whichever merged last, so a duplicate would have routed
  to an arbitrary one of two handlers with no error anywhere.

Behaviour is unchanged: handler bodies moved verbatim. Tests that reached into
`handlers` for a moved private now import from the domain module that owns it,
which also documents where each one lives.

### Added — `doctor` names open tasks that no epic can reach (session #148)

The release boundary of this project is mechanical: "everything in epic X".
Both `tausik roadmap` and `task list --epic` reach a task only through
story → epic, so a task attached to neither is invisible to both — and a
release-scope question answers "that task does not exist" instead of "that
task is unaccounted for". The error runs in the direction of *under*-reporting,
which is the direction nobody re-checks.

It had already happened once: four orphans were reattached by hand and the fix
recorded as a decision, with no signal added. Roughly twenty sessions later
exactly four more had accumulated — including the release capstone
(`redoc-1-8-final`) and a task the gate config names by slug
(`mcp-handlers-god-module-split`, whose temporary `exempt_files` entries are
supposed to be removed when it closes). Both had silently dropped out of the
1.8 count.

`tausik doctor` now carries a ninth check, **Backlog hygiene**. It warns when
an open task (`planning`/`active`/`blocked`/`review`) cannot be reached from
any epic, names up to three slugs inline, and prints the exact repair —
`tausik task move <slug> <story>`. The invariant checked is epic
*reachability*, not story attachment, so a task hanging off a story whose epic
is gone counts too. Closed tasks are ignored: an orphan that moves no scope
number is history, not a finding. WARN and never FAIL — `task_add` documents a
standalone task as legitimate, so the check has authority to surface, not to
block.

### Fixed — `tausik_session_open` shipped 90% noise and outgrew the tool-result ceiling (session #147)

`/start` Phase 1 makes exactly one call, so every byte `tausik_session_open`
returns is paid at the start of every session. Measured on a real session, the
envelope was **49 165 chars** — past the host's tool-result cap, so the compound
RPC built to collapse five calls into one degraded into a file dump that cost
**more** than the five it replaced.

Only ~5 KB of it was signal. The rest was two independent leaks, both from
composing full-fidelity producers verbatim:

- **26 022 chars of module telemetry.** `self_check.collect()` returns
  `watched_modules` (12 385) and `current_mtimes` (13 637) — 108 absolute paths
  and their mtimes. The dashboard reads `drift_detected` and `stale_modules`
  and nothing else.
- **15 480 chars of duplicated handoff.** `session_current()` returns the whole
  row, `handoff` column included — the same handoff this envelope already
  returns *parsed* under its own key (4 720 chars). The nested copy is a JSON
  string inside JSON, so `\u`-escaping inflated the Cyrillic **3.3×**.

`_handle_session_open` now projects both sections down to what Phase 3 renders.
Same payload: **36 989 → 3 017 chars (−91.8%)**.

- **Allowlists, not denylists.** The bug was a producer changing under a
  consumer that forwarded everything. A denylist would let the next heavy field
  added upstream re-inflate the payload silently.
- **Error sections pass through unprojected.** A section that failed carries
  only `{"error": ...}`; narrowing that to an allowlist would erase the one
  diagnostic the degraded-dashboard design exists to show.
- **`tausik_self_check` keeps full fidelity.** Full telemetry is the explicit
  diagnostic's whole purpose; the narrowing applies to the automatic call only.
- **Also a data-minimisation boundary.** `/start` runs unattended every session,
  so the dropped fields were a standing export of the developer's directory
  layout (client names included in the paths) and machine mtime fingerprints to
  the model transcript. `stale_modules` now names the culprit by basename —
  enough for "restart your IDE" — and the envelope carries no absolute host
  path at all.
- **The ceiling has teeth.** `tests/test_session_open_handler.py` asserts a
  realistic envelope (120 watched modules, 4 KB Cyrillic handoff) stays under
  8 000 chars, *and* separately proves each dropped blob alone exceeds that
  budget — so the guard cannot pass vacuously if a blob returns.

### Added — `class_surface` gate: the line cap was measuring the wrong unit (session #147)

The filesize gate counts raw lines per **file**, which makes one whole class of
defect structurally invisible: a god-object assembled from mixins keeps every
file comfortably under the cap while the class they compose does not. Measured
here, `SQLiteBackend` exposes **129** public members inherited from 8 bases and
`ProjectService` **118** from 9 — the next-largest class in the repo has 28.
Neither has ever tripped a gate.

The line cap also **caused** the split it was hiding. Module sizes across
`scripts/` decay monotonically from 60 modules at 100–149 lines down to 22 at
300–349, then **rise** to 26 at 350–399 and collapse to 6 above 400: a pile-up
against the old 400 boundary and a cliff past it. Files were cut to fit, so each
one looked healthier while the composed surface grew. Several modules say so
outright — `service_verification.py` carries the comment *"lives in its own
module for filesize compliance."*

New `class_surface` gate (`scripts/gate_class_surface.py`) caps a class's
composed public surface after inheritance. It **complements** the line cap rather
than replacing it: "this class does too much" and "this file is too long to read"
are different defects and neither implies the other.

- **AST, never import.** A gate must be able to measure a branch nobody has read
  yet, so it never executes repo code. The cost is that dynamically attached
  members are invisible, so counts are reported as a **lower bound** — a derived
  measurement must not be dressed up as a declared one (convention #325).
- **Whole-repo, not per-file** (0.65s). A scoped gate only sees what someone
  edited, so a class that drifts past the cap *through its bases* stays green
  forever — the same blindness that let `service_knowledge` reach 406 lines
  without blocking anyone.
- **Ratchet baseline.** The two known oversized classes are recorded at their
  current size and fail only if they **grow**; a gate that reddens everything on
  day one gets switched off. A test pins that the baseline matches reality
  exactly, so it can never become a licence to grow back up to it.
- Parse failures **fail** the gate rather than being footnoted onto a pass:
  coverage cannot be claimed over a file that was never read (convention #305).

**The blanket `harness/claude/mcp/` exemption is gone.** A whole *tree* is never
the right exemption unit — it also covers every file added there later, and it
had been hiding the two largest modules in the repo. Exemptions are now
file-precise, each with a written reason:

| File | Verdict |
|---|---|
| `mcp/project/tools.py` (988) | **permanent** — 97% is one literal schema table, 0 functions; a declarative table is not logic |
| `mcp/project/handlers.py` (1281, 77 handlers) | **temporary**, named owner `mcp-handlers-god-module-split` |
| `mcp/codebase-rag/server.py` (562) | **temporary**, same owner |

Note the direction of the config merge: committed config *unions over* the
hardcoded defaults, so an exemption can be added from config but never removed
there. Retiring the blanket entry required a deliberate source edit — which is
the safer default, but worth knowing before assuming a config change took effect.

**Measured, not assumed:** the follow-up premise that ~30 modules were mechanical
wrappers to be stitched back did **not** survive measurement. Of the 25 modules in
the 360–400 band, one has zero own definitions (and it is DDL data, not a shim),
eight are single-class mixin modules, and the rest carry 2–20 definitions each.
The one genuine re-export facade cannot be merged at all: its nine constituents
total ~1763 lines, 3.5× the cap. So zero modules were stitched, and the follow-up
task was re-specified to the question that survives — whether specific split
boundaries are defensible — rather than left pointing at a disproved premise.

### Fixed — `tausik sync` would have corrupted the journal and nulled fields (session #147)

The DB↔tree round-trip regressed after `state-git-import` pinned it, and nothing
caught it: that pin was a one-time live measurement, not a standing gate. On this
repo a dry-run import of the tree reported **336 rows to update and 437 journal
lines to add** — meaning `tausik sync`, the command an engineer runs after
`git pull`, was not idempotent but *destructive*.

Root cause, shared by three of the four defects: the projection is a **lossy,
canonicalizing** view — the emitter sorts memory tags, dedups task path lists,
reformats timestamps to the `Z` form and flattens multi-line journal messages onto
one line. The divergence detector compared *raw DB values* against *already-
canonical file values*, so the canonicalization itself read as a change.
Comparison now runs in the canonical space, through the emitter's own helpers
(imported, not re-implemented, so the two cannot drift apart). The emitter is
untouched — the 2024 committed files keep their bytes.

- **Journal duplication.** `_journal_section` flattens a multi-line message by
  design (an entry must stay one line so two branches merge as added lines), so
  the raw multiset key never matched a multi-line DB row: every sync would append
  a flattened duplicate of all 437. Keyed canonically now.
  *Known limitation, unchanged:* importing into an **empty** DB still stores the
  flattened message. What is fixed is duplication on re-import, not the design's
  lossiness.
- **Tag order** (239 rows) and **timestamp form** (`+00:00` vs `Z`, 94 rows) no
  longer read as changes.
- **An absent key is no longer a request to clear the column** *(policy change)*.
  `fm.get()` collapsed "the file never mentioned this key" into `None`, so a
  projection written before a field was set would silently `UPDATE … SET col=NULL`
  on the next sync. Absent keys are now dropped from the delta entirely. An
  **explicit** empty value (`key: []`, `key: null`) still clears — git-wins holds
  for divergence, but the tree, which arrives from `git pull` as untrusted input,
  can no longer null a column by mere omission.
- **`sync_suggested` no longer claims a direction it has not established.** It
  documented a non-empty plan as "the files carry state the DB does not, so
  suggest `tausik sync`" — but divergence proves only that the sides *differ*. On
  this repo the direction is the opposite (the DB is newer), and following that
  advice would have reverted a recorded decision and reopened a closed task. It
  now separates what the counts do prove (`added`/`journal`/`edges` — rows the DB
  has no entry for) from an ambiguous field-level difference, and offers both
  `tausik sync` and `tausik state export` rather than naming one as *the* fix.
- **The signal was invisible, which is why this survived five sessions.** The
  `sync_suggested` section is watchdog-bounded at 6s, and its cold first call —
  the only call `/start` ever makes — overran that budget on a 2024-file tree.
  The projection is now warmed in a daemon thread at MCP startup (I/O only; no
  memoized verdict, which would go stale on the next DB write), and the section
  gets a 20s bound as it is inherently O(tree). The bound stays hard and the
  section is computed last, so the hang the watchdog exists to prevent does not
  return.

Live tree after the fix: `{added: 0, updated: 2, journal: 0, edges: 0}` — and both
remaining entries are *genuine* staleness (a task respecced by decision #191 and
one closed via the CLI while the MCP held stale modules), not phantoms.

Guarding it now: a standing test exports a live DB and dry-run imports it back
into *that same DB*, asserting all four counters are empty, over a tree covering
every entity type, Cyrillic, multi-line journals, unsorted tags, both timestamp
forms and omitted keys. Every prior test imported into a *fresh* DB, where both
sides already speak the file's dialect and agree trivially — which is exactly why
none of them caught this.

### Review fixes (session #146) — skill-activate scan bypass + fail-open decode + gate matching

An adversarial review of this batch's code caught five real defects — three
critical — in the skill supply-chain and filesize work just shipped:

- **`skill activate` bypassed the invisible-Unicode scan (critical).** The scan
  added this batch lived only in the install path (`copy_skill`); `skill_activate`
  copied vendor skills into the activated tree with a signature check but *no
  content scan* — a signed-but-compromised or unsigned-warn skill went in
  unscanned. The exact install/activate drift the `skill_tree_ignore` docstring
  warns about, recurring (the signature check had the same bug earlier). Fixed by
  a shared guard `skill_content_scan.assert_skill_tree_clean` that *both* paths
  call; regression-tested on the activate path.
- **Fail-open on invalid UTF-8 (critical).** `scan_skill_tree` decoded `strict`
  and silently skipped any file that wasn't valid UTF-8 — yet `copytree` lands it
  byte-for-byte, so one stray invalid byte beside a U+E0000 payload defeated the
  scan. Now decodes `errors="replace"`; only a real IO error skips a file.
- **Scan was markdown-only (critical).** Only `.md/.markdown/.txt` were scanned;
  a payload in `references/notes.py` or `data/config.json` (files a SKILL.md can
  tell the agent to open or run) sailed through. Coverage broadened to the prose,
  config and script extensions skills ship.
- **Filesize gate hardening (medium×2).** The committed-config lookup now stops
  at the repo's `.git` root instead of climbing unboundedly from cwd (no adopting
  a foreign `tausik/gates.json` from a monorepo/CI ancestor); and exempt dirs
  match on path-segment boundaries instead of raw substring, so `tests/` no longer
  exempts `unittests/` — a pre-existing flaw whose blast radius grew once the
  exempt list became externally editable.

### Embeddings revisit — `brainh-semantic-search` respecced to FTS5-first hybrid

Sobering industry data was weighed against the planned local-embeddings feature
(task `l26-embeddings-revisit`, decision #191). Cursor's online A/B (2025-11-06)
is the most trustworthy measure because it includes production retention, not
just offline accuracy: +12.5 % offline but only +0.3 % code-retention overall
and +2.6 % on repos over 1 000 files — a sub-3 % effect concentrated in large
bases. Sourcegraph *removed* embeddings for BM25F over a code graph; short
keyword queries (the dominant agent query form) collapse semantic models to
~0 nDCG@10, which is why grep survived; CORE-Bench (Jun 2026) concludes no method
dominates — hybrids win.

`brainh-semantic-search` is **respecced, not closed**: pure local embeddings →
an FTS5-first **hybrid** where semantic is an *optional re-rank on top of*
keyword search, gated on (a) a provider being present, (b) the query being
natural-language rather than a short keyword, and (c) the base being large enough
to clear the sub-3 % bar — always degrading gracefully to plain FTS5. Effect must
be measured on *our own traffic* (LoCoMo is discredited: a no-memory baseline beat
Mem0 73:68), not vendor benchmarks. Per-alternative verdict recorded: **BM25F** —
already have FTS5, strengthen field-weighting (cheapest, keep); **ast-grep /
tree-sitter** — for *code*, not brain prose (belongs to the codebase-RAG, not
here); **LSP symbol-path addressing** — for code-citation stability (the `km-*`
chain), out of scope for brain semantic search.

### Skill supply-chain threat model + invisible-Unicode install guard

The dominant 2026 attack vector is the markdown skill, not the MCP server: the
payload is *prose the agent reads verbatim*, so a signature over the bytes proves
*who* published but not *what* is hidden in the text (Snyk ToxicSkills 2026-02-05:
36.8 % of 3 984 skills problematic, 91 % of malicious ones used prompt injection).
Task `l26-skill-supply-chain-threat` models TAUSIK's own store against the known
primitives and adds the one missing mitigation.

- **Threat model documented** (`docs/en/skill-supply-chain-threat-model.md` + RU
  mirror, cross-referenced from `security.md`). Each 2026 vector gets an explicit
  status: post-verification swap (Orca) — *mitigated at install, accepted for
  already-installed*; silent same-name overwrite — *mitigated* (gated by
  signature + content scan); scanner-bloat (Unit 42, 22 MB README) — *accepted*
  (our scan has no skip-large-file escape hatch, so the evasion doesn't apply);
  install-count gaming — *not applicable* (no popularity surface exists to game).
  OMS/Sigstore stays rejected by the owner — TAUSIK holds its ed25519 line.
- **CVE-2025-59536 analysed** (repo-supplied `.claude/settings.json` hooks
  executing before consent). Verdict: **does not apply to a cloned TAUSIK
  project** — `.claude/` is gitignored and hooks are generated locally by
  bootstrap (the user-initiated bootstrap *is* the consent boundary), and the
  project config tier is untrusted so a committed config can only tighten, never
  redirect a hook. Two residual paths (tampered vendored framework, config
  redirection) are named and dispositioned rather than left implied.
- **Invisible-Unicode detector implemented** (`scripts/skill_content_scan.py`,
  wired into `copy_skill` before any file lands). It refuses a skill hiding
  agent-directed instructions in the U+E0000 tag block, zero-width formatting, or
  bidi overrides (Trojan Source). It complements `brain_scrubbing`'s zero-width
  *stripping* — here we *detect and block*, and additionally cover the U+E0000
  tag block the brain regex predates. Ten tests, including a poisoned SKILL.md
  that fails to install.

### Filesize gate: cap 400→500 (interim) + exemptions move to a committed config

The 400-line filesize cap was deforming architecture more than it protected. A
direct re-measure confirmed the #129 audit: **six** core files sit at *exactly*
400 lines (`service_task`, `service_task_done`, `project_parser`,
`project_cli_doctor`, `gate_registry`, `config_trust`) and ~10 more crowd the
390–399 band — writing to the limit, not to the concept. Roughly 30 modules in
`scripts/` document themselves as split *only* to pass the gate. Two changes
(decision #190, task `l26-filesize-gate-revisit`):

- **Interim cap 400 → 500.** Chosen (of the three offered variants) as an
  interim measure, with the number calibrated from evidence: 500 absorbs every
  documented wrapper-merge with margin (`gate_runner` 393 + `gate_filesize` 97 =
  485; `service_knowledge` 394 + `service_cq_row` 48 = 437) while a genuinely 2×
  file still blocks — a fails-then-passes boundary test covers the protection
  regression. The real fix — measuring a class's **public surface after MRO
  assembly** instead of raw file lines (the gate is blind to god-objects
  assembled from ≤400-line mixins: `ProjectService` = 117 methods across 9,
  `SQLiteBackend` = 129 across 12, and it exempts `handlers.py` at 1289) — is
  deferred to a dedicated follow-up, since it needs class-graph analysis and
  touches core objects.
- **Exemptions are now config-driven from a committed file.** Exempt dirs and
  basenames are read from the branch-coupled `tausik/gates.json` — the
  non-dotted projection a fresh clone actually carries, since `.tausik/` is
  gitignored and never arrives on a clone — and merged over the hardcoded
  fallbacks in `gate_filesize.py` as a union that can never silently drop a
  baseline exemption. Adding an exemption no longer means editing gate source. A
  malformed config degrades to the fallbacks rather than crashing the gate
  (convention #226). `TAUSIK_GATES_CONFIG` overrides the path for CI/tests.

Downstream factual drift from the cap change was fixed in the same commit
(`CLAUDE.md`, the bootstrap CLAUDE.md template); the full `docs/` sweep is left
to `redoc-1-8-final`. Nine tests added; two stale `400` golden assertions in
`test_gate_registry.py` moved to 500.

### Review fixes (session #146 batch) — two correctness bugs the tests missed

An adversarial review of the three telemetry/process modules added this batch
caught two real bugs that shipped green because the suites never exercised the
offending inputs, plus a few hardening items:

- **Tokenizer era read a date as the minor version.** `tokenizer_era`'s regex
  accepted any digit run after the major version as the minor, so a real
  bare-major dated id like `claude-opus-4-20250514` parsed as `(4, 20250514)`
  and was labelled NEW — flipping a genuine Opus-4 (old-tokenizer) id to the
  wrong era and applying the ~30% correction backwards on real cost telemetry.
  The minor is now capped at 1–2 digits with a digit-boundary guard; such an id
  parses as major-only → OLD.
- **`sum_usage_tokens` could crash the metrics hook.** Its docstring promised
  "zero-safe", but bare `int()` on a non-numeric token field (a stray `"N/A"`
  in a transcript) raised `ValueError` — and `parse_transcript` calls it per
  line unguarded, so one bad value lost the whole session's metrics. Conversions
  are now wrapped; a malformed field yields 0.
- **OTLP spans can no longer run backwards.** A negative `duration_sec`
  (out-of-order/clock-skewed transcript timestamps) could put a span's start
  after its end; the session wrapper now clamps the duration and the builder
  rejects any `end < start` document, symmetric with its id validation.
- Hardening: the `gen_ai.*` lint now also catches the split-string evasion
  (`"gen_ai" + ".x"`); `TAUSIK_OTEL_EXPORT` honours an explicit falsy value as
  an ops kill switch over config; and the sibling-enumeration call site in
  `self_check` degrades to "unknown" on any exception instead of crashing.

### Optional OTLP/JSON trace export — additive, opt-in, and honest about churn

TAUSIK has its own event and metric format; the industry converges on
OpenTelemetry as the transport (any vendor ingests OTLP). Session metrics can
now ALSO be emitted as an OTLP/JSON trace span — an additional output; the
internal events remain the source of truth. It is off by default and enabled
per project via `otel_export.enabled` or the `TAUSIK_OTEL_EXPORT` env var; when
off, the SessionEnd metrics path is byte-for-byte unchanged. The exporter is
stdlib-only — it writes OTLP/JSON (the JSON encoding of the OTLP trace protobuf)
that any OTLP receiver accepts, rather than depend on the OpenTelemetry SDK — so
the practical payoff (compatibility with EU AI Act audit stacks and existing
observability platforms) costs no new dependency.

An important honesty note, verified against the source on 2026-07-18: the GenAI
semantic conventions are NOT stable — they live in
`open-telemetry/semantic-conventions-genai` with ZERO published releases, status
Development. Blog claims of "stable OTel GenAI" conflate the semconv release
train with GenAI maturity. So every `gen_ai.*` attribute name lives in one
mapper module (`scripts/otel_semconv.py`), which self-declares the instability,
and a lint test fails if any `gen_ai.*` literal appears elsewhere in `scripts/`.
When these names churn, the change touches one file — and it is expected, not a
regression.

### Sibling-MCP: report and warn, never kill — and stop the per-call PowerShell probe

The recurring "MCP feels hung or drifting" class (#77/#79/#80) traces to sibling
tausik-project MCP servers accumulating — each Claude Code session in a window
spawns its own `server.py`, and old ones live as long as their owning
`claude.exe`. The 2026-07-18 forensics (Win11 build 26200) settled the design
question: there were no ORPHANS to reap — every sibling sat under a LIVE
`claude.exe` in the same window, and a stale-but-alive session cannot be told
apart from an active one by the process tree. An automatic reaper would
therefore risk tearing down a live session (its WAL connection and in-flight
work). The chosen contract (decision #189) is **report and warn, never kill**:
`self_check` now surfaces a `sibling_warning` — a hard, threshold-crossing
"close old sessions" message that explicitly states the framework will not kill
a process — which makes "live siblings are never killed" true by construction,
with no killer code to misfire.

The actual latency pain was not the missing reaper: `_enumerate_sibling_mcps`
spawned a fresh PowerShell `Get-CimInstance` on EVERY self_check call (wmic was
removed from the Win11 26200 base image, so the wmic path always fell through),
~0.6-1s over 100+ processes — which is what made `/start` look like a hang. New
module `scripts/mcp_reaper.py` memoizes the enumeration behind a 30s
process-scoped TTL, so repeated checks in a session reuse it instead of
re-probing.

### Tokenizer-era correction, and the calibration hypothesis it disproved

The 2026 model generation (Opus 4.7+, Fable 5, Mythos 5, Sonnet 5) ships a new
tokenizer that emits roughly 30% more tokens for the same text than the prior
one (Sonnet 4.6 / Opus 4.6 / Haiku 4.5 and older). Token and dollar comparisons
that straddle that boundary are invalid without a correction. New module
`scripts/token_accounting.py` places any model id on one side of the boundary
(`tokenizer_era`, returning an honest "unknown" for a bare rank alias or a
foreign family rather than a guessed factor), expresses counts on a common
era's scale (`normalized_token_count`), and sums usage rows with the ~30%
correction applied only to off-era rows (`era_normalized_total`) — a single-era
total is byte-identical to the naive sum, so within-era comparisons are never
distorted.

The task's own hypothesis — that part of the framework's observed budget
underestimation is a tokenizer artifact — was tested against the actual
calibration signal and **rejected**. `calibration_drift` is computed over
`call_actual / call_budget`, which are TOOL-CALL COUNTS: integers that carry no
tokens and are unaffected by any tokenizer. The recorded number is 0% — none of
that drift is attributable to the tokenizer change; the correction belongs only
where tokens or dollars cross the boundary (usage rollups, token budgets), and
`calibration_drift`'s docstring now says so.

Separately, server-side compaction is billed under `usage.iterations[*]`, which
the top-level `input_tokens` / `output_tokens` do not include. `parse_transcript`
(session metrics) summed only the top level and so understated the real billed
count; `sum_usage_tokens` now folds the iterations back in.

### A committed baseline for memory retrieval, before the knowledge-layer rework

The knowledge-layer rework (decision #143) consolidates flat memory entries into
topics, and no public evidence says that helps answer quality — so before any
change we now have a number to regress against. `scripts/eval_memory_retrieval.py`
runs a committed, content-keyed set of 49 questions through the same FTS5 search
an agent uses and prints ONE accuracy figure: the current flat store scores 100%
at top-5 (98% at top-1) over 325 entries. The questions key on distinctive
content phrases, never on record ids, so the number survives a reindex or id
shift — a test proves the score is identical after the same content is inserted
at different ids.

The honest reading, recorded with the number: this is a ceiling for
keyword-anchored facts — TAUSIK's memory titles are keyword-rich, so a
distinctive-term search retrieves them near-perfectly. That supports, rather than
undercuts, decision #143: the rework cannot claim accuracy gains here (there is
no headroom), so its justification stays command-merge and smaller injected
context. The harness is fail-safe — an empty or unreadable store yields 0.0 with
a note, and a query that matches nothing is a miss, never a crash.

### A gate holds every SKILL.md to the cross-vendor agentskills.io canon

The SKILL.md format left Anthropic and became the cross-vendor agentskills.io
spec (OpenAI, Google, Microsoft, Cursor, JetBrains, Mistral, AWS and others
implement it). A reference validator exists but is not vendored here; instead a
built-in gate (`skill_spec_conformance`) enforces the same machine-checkable
rules in-process: a skill `name` is 1–64 chars of `a-z0-9` with single hyphens —
no leading, trailing, or doubled hyphen — and must equal its directory name; a
`description` is 1–1024 chars. Under progressive disclosure the name is the
~100-token metadata loaded for every skill at startup, so a malformed one breaks
dispatch across every vendor. The gate is inert unless a `SKILL.md` is among the
changed files, and local scaffolds whose directory starts with `_` or `.` (the
non-deployed `_profile-demo` reference) are skipped. All 15 shipped skills pass.

The spec is deliberately treated as hygiene, not trust: it is not versioned and
carries no security provisions whatsoever, and both the gate and the docs say so
plainly — conformance keeps progressive disclosure working, it is never a trust
signal.

### The MCP tool surface has a measured cost and a ratchet that keeps it cheap

TAUSIK ships 124 tools over MCP — about 51 KB of tool definitions, ~12.8k
estimated tokens loaded before the user says a word. That number now has a test
behind it (`tests/test_mcp_tool_token_cost.py`): it measures the surface, caps it
so a careless doubling reddens CI, and enforces the two properties Claude Code's
deferred loading (`ENABLE_TOOL_SEARCH`) depends on — no single description exceeds
the 2 KB the host keeps (a longer one is silently truncated, hiding its tail), and
every tool name is unique and carries a searchable domain token so name-based
dispatch still resolves at this scale. Measurement only; no tool or schema
changed, and every current description already fits under 2 KB (largest 483 B).

### Verbose command output rolls up instead of dumping every line

`events` and `task list` printed one or two lines per row. On a mature project
that is hundreds of lines the agent re-reads constantly — pure token cost that
grows with the project. Borrowing cubest's aggregate view, both commands now
collapse a large result into a compact, deterministic rollup: `events` groups by
entity-type and action, `task list` by status and role, each line a count, the
groups ordered most-frequent-first with ties broken by key so the same input
always prints the same lines. Budget knobs `--top-n` and `--max-lines` cap how
many group lines print, and whenever anything is dropped a footer names the
denominator — how many groups and rows are not shown — so the shorter view can
never hide the tail silently.

It only collapses when it actually saves: below a 25-row threshold the output is
printed in full, byte-for-byte as before, so small lists and every existing
fixture are untouched. `--full` always bypasses the rollup to the exact prior
output on any size. The change is presentation only — no data, schema, or
semantics move, and a test proves `--full` is byte-identical to the pre-rollup
render on a large sample.

### The MCP tool-list narrows to what the active task is allowed to use

A task already carries a `scope_tools` ACL (SENAR Rule 2), but it was enforced
only on writes — the MCP server advertised all 117 tools to the agent no matter
what the active task declared. Borrowing onyx's curated-surface idea, the server
now exposes to the agent only the union of the active task's declared
`scope_tools` and an always-safe core (the whole `tausik_task_*` and
`tausik_session_*` families plus status / search / verify / doctor / self-check /
update-claudemd); every other tool is hidden from the tool-list. For a typical
single-extra-tool scope that is a 56% cut in the tool-definitions the host loads
into the system prompt (117 tools/43.7 KB → 40/19.3 KB, measured), and a
correspondingly smaller attack surface.

It is fail-open by construction, symmetric to the write-gate's legacy freedom:
the feature is off by default (opt in with `mcp.scope_tools_exposure: true`), and
even when on, all tools are exposed whenever no task is active, no active task
declared a non-empty `scope_tools`, or anything goes wrong resolving the scope —
the saving never silently strands a project that never opted in. When two tasks
are active it restricts to the union of the declared ones; an undeclared
co-active task contributes nothing and does not, by itself, restore full freedom
once a sibling has declared a scope.

Hiding is a UX and token optimization, not the security barrier. `call_tool` and
the write-gate are untouched, so a hidden tool invoked directly still passes the
existing scope enforcement — the gate remains the barrier, the shorter list is
only what the agent sees first. The scoped list is computed at `list_tools` time,
so the agent gets it whenever the host (re)fetches the tool-list — on every
server connect with a task already active; re-scoping the instant a task starts
mid-session (via a `tools/list_changed` notification) is left to the
deferred-loading track and does not conflict with this shaping.

### Scoped pytest can see the tests that guard a whole tree, not just one basename

The pytest gate scopes a run to the tests that map to the changed files, via a
`tests/test_<basename>.py` heuristic. A whole class of tests is built the other
way round: they iterate a TREE — every hook, every skill, every generated
profile — and are therefore relevant to any change inside that tree without being
tied to a single basename. A task that changed one hook, scoped its pytest, and
went green could still have broken three such tests the scope could not, even in
principle, find. The heuristic's boundary was real but nowhere declared. Now a
cross-cutting test opts in by declaring a module-level `CROSSCUTTING_SCOPE` — the
path prefixes it guards, e.g. `["scripts/hooks/", "bootstrap/"]` — and the
resolver adds it to a scoped run whenever a changed file falls under one of those
prefixes, matched by path, not basename. It stays additive: a change matching no
prefix still pulls nothing, so the "no full-suite fallback" promise holds. The
mechanism refuses to become a registry people forget to maintain: a ratchet gate
detects any test that iterates a source tree and requires it to either declare a
scope, opt out visibly with `CROSSCUTTING_SCOPE = []`, or sit in a frozen,
shrink-only baseline — so a NEW tree-iterating test that would silently escape the
scope reddens CI instead. The six trees the original incident touched
(hook-encoding, bootstrap-hook parity, block-message quality, the single-canonical
MCP tree, the doc-check hook, and bypass telemetry) now declare their scopes, and
declared prefixes are checked to still exist so a binding cannot rot.

### `tasks.model_mismatch` is NOT NULL on every DB now, not just fresh ones

The fresh schema declares `model_mismatch INTEGER NOT NULL DEFAULT 0`, but the
migration that introduced it (v33) added it with `ALTER TABLE ... ADD COLUMN ...
DEFAULT 0` and no NOT NULL — SQLite rejects NOT NULL on `ADD COLUMN`. So a
freshly-initialised DB had `notnull=1` while every DB carried forward by
migrations had `notnull=0`: the column could hold NULL, and a NULL is matched by
neither `WHERE model_mismatch = 0` nor `WHERE model_mismatch = 1`. A query for
"tasks without a model mismatch" would silently drop such a row — green on CI
(fresh schema), wrong in the field (migrated schema), the exact class the schema
fixture-parity gate exists to catch. It has not fired yet only because every write
path fills the column explicitly; that is luck, not a guarantee. SQLite cannot
tighten a column in place, so migration v43 rebuilds the central `tasks` table:
it backfills any NULL to 0, recreates the table with the column NOT NULL and in
the canonical column order, copies every row by explicit column name (never
positionally — the migrated column order differs), and recreates all six indexes,
all seven triggers, and the external-content `fts_tasks` index. Row ids are
preserved, so the defect_of self-reference, the incoming foreign keys from
decisions/memory, and the full-text index all stay intact; `PRAGMA
foreign_key_check` runs clean afterward. The rebuild is a guarded, idempotent
step: it no-ops unless it finds a real, fully-migrated `tasks` whose
`model_mismatch` is still nullable, so a fresh DB, a re-run, or a partial test
fixture is left untouched. The upgrade also retires the column from both the
constraint-drift and the column-order ratchets in the fixture-parity gate.

### The closure-risk gate_coverage factor no longer changes if the trust tier flips

`risk_compute._factor_gate_coverage` measured how much of the configured gate set
a task actually verified — but it took its numerator (gates that ran) from the
signed verify receipt and its denominator (gates configured) from
`get_gates_for_trigger(load_config())` recomputed at *task-done*. Those are two
different moments, and if the trusted config tier changed between verify and done
the denominator moved, so the same verify run scored a different risk on a
different machine or a different day — a comparison of two different gate sets
dressed up as a coverage ratio. The configured-gate count is now captured *in the
receipt at verify time* (`configured_gates_count`), right beside the ran-gate
list it is divided against, so both come from one signed verify-time source and
the factor is reproducible. The count is `len(gate_results)` — the runner emits
one result per gate scheduled for the trigger, ran or skipped, so it is exactly
the configured total. Receipts written before this field existed carry no count,
so the reader falls back to the old recompute for them: legacy closes reproduce
exactly, a missing field is never a crash or a divide-by-zero. The field is
additive telemetry, not a new attestation about coverage completeness, so it does
*not* bump the receipt schema — verification re-canonicalizes the stored bytes and
never branches on the schema string, so old and new v2 receipts verify identically.

### A broken CLI no longer costs the OpenCode gate two slow subprocesses per write

The OpenCode QG-0 plugin caches its active-task verdict precisely because the CLI
probe costs 300 ms warm / 1.1 s cold on Windows and is paid on every write. But
when the CLI was *unreachable*, `_verdict` let the probe's exception escape before
`_cache` was assigned — so the degraded state was never cached. Every subsequent
write re-spawned the probe, and the fail-open branch then awaited a supervision
emit that shells the *same* broken CLI: two slow subprocesses on every keystroke
for as long as the CLI stayed broken, exactly the sluggishness the cache exists to
prevent. The unreachable verdict is now cached under the same DB-signature + TTL
guard as an active one — one probe per window, re-probed the moment the signature
moves (a recovered CLI or a started task) or when no signature is available (no
Bun → the lenient direction is never reused). The degradation stays countable but
is recorded only on a *fresh* probe, so one outage leaves one row per window
instead of one per write; the user-facing DEGRADED warning stays loud on every
ungated write (it is a cheap `console.warn`, not a spawn). Fail-open and
fail-secure policy are unchanged — only the number of slow spawns is.

### "Routing Adherence" was measuring an unenforceable rule — it's a recommendation fit now

`tausik metrics` reported *Routing Adherence 1.6%* over n=10909, with
`deviation sonnet->opus: 10739`. A metric that reports a rule broken 98.4% of the
time is not measuring a violation — it is measuring that the rule cannot be
followed: the harness does not switch models programmatically (the bootstrap
WORKFLOW says so), the session model is the user's manual choice, and every task
that runs on Opus while the matrix suggested Sonnet was logged as a deviation. The
metric is reframed from compliance to calibration: it is now *Model Recommendation
Fit*, the presentation names the manual per-session choice, and a low match rate
reads as "the matrix recommends models people don't run", not as indiscipline. The
recorded data is unchanged — the same rows still feed the routing matrix — only the
framing that made a non-violation look like a release-metric failure is gone.
(decision #183)

### `memory lint` stops crying wolf — stale_file is a path anchor now, not a slash

The stale-file detector flagged any `segment/segment.ext` token whose file did
not resolve, but memory is prose where a slash is more often an alternation
separator than a path: `lru_cache/functools.cache`, `release/1.8`, `HEAD/v1.6.1`,
`ru/senar.md` (a fragment of `docs/{ru,en}/senar.md`), plus placeholder examples
like `tests/test_x.py`. On the live memory set the report was 90% noise — 53
findings, and a report that is mostly noise is one people stop reading, so a real
stale path drowns. A token is now flagged only when its PARENT DIRECTORY actually
exists (a real deletion inside a live directory) and its basename is not a
conventional placeholder (`x.py`, `test_file.py`). Same run: 53 → 6 findings, all
six paths inside directories that exist; every listed false positive is gone, and
a genuine deletion in a live dir is still reported.

### QG-0 and the evidence detector now agree on the word "negative"

The framework carries two negativity detectors — `NEGATIVE_RE` reads task-done
evidence, `has_negative_scenario` gates task start — and they had drifted apart:
the evidence side matched the whole family `negative | негативн | отрицательн`,
but QG-0 knew only the first two. A criterion that named its negative case as
"отрицательный результат" therefore counted as evidence at close yet was HARD
blocked at start, and the fix was to reword to the detector's vocabulary — the
keyword theatre the project punishes elsewhere. QG-0 now knows `отрицательн` too,
and a producer-derived parity test reads the negative-word forms from
`NEGATIVE_RE` itself and fails if either detector learns a form the other does
not — so the split cannot silently reopen. A differential run over all 963 closed
ACs changed zero verdicts: this widens what QG-0 accepts, it does not re-judge
past work.

### The AC-evidence parser can finally read a measurement — the strongest evidence there is

A criterion proven the strongest way the project has — a full gate run
(`5778 passed … in 564s`, `verification_run #1285`) — scored as "no evidence",
because the parser only knew four evidence types (test ref, manual, review,
check mark). Measurement was not among them, so the cheapest way to clear the
Rule 5 checklist was to add a check mark: the gate rewarded decoration over
proof. There is now a fifth type, `measurement`, and it is the one detector in
the set that checks a FACT rather than a word: a `verification_run #NNNN` line is
counted as real verification activity only when that run exists, belongs to the
task being closed, and is green (`exit_code == 0`) — the id is fact-checked
against the `verification_runs` table. A decorative `verification_run #1` (a
nonexistent, foreign, or red run) clears nothing. A pytest summary is recognised
as a measurement by its passed-count shape (a number, not a keyword) and counts
toward per-criterion coverage, but — carrying no run id — cannot by itself clear
the fact-based activity gate. The upshot: the strongest evidence is now also the
cheapest to write honestly, and the check mark stops being the shortest path.

### `test_count` is a lower bound now, so adding a test no longer reds the whole suite

The doc-constants check pinned `test_count` to an exact match, but that number is
a *measurement* that moves with almost every task — add a test, close green, and
the full suite turns red on `test_check_docs_hook` until someone regenerates
`constants.json` (often unseen until the next nine-minute full run). test_count is
now treated as a **lower bound**: the recorded value is a floor, a suite that GREW
(`recorded ≤ live`) is never drift, and the cross-file doc numbers ("6227 tests")
are read as honest "N+" claims. The only failures left are the ones that mean
something — a suite that SHRANK below the recorded floor, and a doc that OVERCLAIMS
more tests than the code actually has. Version, MCP-tool, and code counts stay
exact-pinned: those are *declared* intent, not measurements. `--skip-test-count`
still exists for the orthogonal CI case where optional-dependency modules
`importorskip` themselves out of collection. (decision #182)

### The AC-evidence parser stops penalising the log format its own tooling writes

SENAR Rule 5 credits a criterion only when an evidence line binds a resolvable
test to a numbered AC. The binder was start-anchored, so the `[timestamp]` prefix
that `task_log` prepends to *every* note — and an `AC verified:` / `AC:` header the
agents and fixtures write in front of the number — hid the number from it. A line
like `[2026-…] AC verified: 1. ✓ tests/test_x.py::test_a` bound to nothing and the
test ref fell into "unmatched". Measured across the closed backlog, 41 tasks cited
a *resolvable* test the gate refused to credit purely on form. The parser now
strips exactly those two project-authored prefixes **before index detection only**
(the stored evidence keeps its timestamp), then runs the *same* strict regex — so a
numberless `- pytest tests/x.py: 15/15` or a stray `see section 3.` still earns no
credit. Re-measured on the live DB: mis-scored closures fell 41 → 21 (the residual
21 genuinely lack a criterion number on the test line), while the "no resolvable
ref at all" population did not grow — the fix binds, it does not loosen.

### `tausik_self_check` now asks the producer which modules to watch, not a hand list

The MCP stale-module detector snapshotted mtimes for a hard-coded tuple of
eleven service modules. The server imports dozens more (`complexity_understatement`,
`service_task_done`, `ac_evidence_detectors`, …), and any of them going stale was
invisible by construction — the check answered "in sync" while the server ran old
bytecode, once even writing a false `complexity_understated` calibration event
against a module outside the list. The watch set is now derived from the **producer**:
every module in `sys.modules` whose file lives under the deployed server tree
(`<profile>/scripts` and `<profile>/mcp`). Stdlib and site-packages fall outside
those roots by construction, so a `pip install` can never masquerade as drift.
Modules imported *lazily* after startup — the permanent blind spot, since they
never appeared in the boot snapshot — are now flagged when their file mtime
postdates the server boot. The eleven-name tuple survives only as an eager-import
list (force-load critical modules so their file is resolvable at snapshot time),
a responsibility now named as such in the code. The `sys.modules` walk costs
~6 ms per call over ~900 modules.

### A decision headline is measured in characters, and now gets 1024 of them

`tausik decide` capped the `decision` field at the shared 512-character `MAX_TITLE`
— the same budget as a task title, though a decision headline legitimately states
both a choice and its shape. The limit was always in **characters**, not bytes
(`len(str)` counts code points), so the folk belief that Cyrillic was penalised
2× was never true; the real friction was simply that 512 symbols runs out on a
verbose Russian headline. Decisions now have their own `MAX_DECISION = 1024`
symbol budget, and `rationale` is validated against the same limit (previously
unbounded), so the wider headline does not just move the pain into the rationale.
Task titles are untouched — they keep the 512-character `MAX_TITLE`.

### Git-native state is now guarded by a round-trip gate — the `tausik/` tree must equal the DB

`state-git-export` made the DB serializable to a deterministic `tausik/` markdown
tree; this closes the loop and makes that projection trustworthy. A new
`state_roundtrip` gate re-serializes the live DB and byte-compares it to the tree
on disk, so a commit can no longer carry state that disagrees with its source of
truth — it catches the three drift modes head-on: forgot to `tausik state export`
before committing, hand-edited a file past the DB, or a non-deterministic
serializer. It runs on the **commit** trigger, not task-done: closing a task
mutates the DB (and can auto-close its parent story/epic), so a task-done-time
check would flag its own in-flight write as drift — the commit boundary is where
"the files that enter git must equal the DB" actually matters. It is opt-in and
fail-open: a project that never ran `tausik state export` has no tree and the
gate skips rather than inventing a red, and any internal fault passes rather than
crashing the commit. The durable tree lives in the NON-dotted `tausik/` (the
runtime `.tausik/` — DB cache, venv, keys, receipts — stays ignored), and
`state.auto_export` keeps the tree in step with the DB as work lands.

> **Upgrade note.** The gate is a hard block on the commit trigger. A project
> that has already adopted git-native state (has a `tausik/` tree) should run
> `tausik state export` and `git add tausik/` once before its next commit — a
> tree that drifted or was left unstaged will otherwise block that commit with
> the exact fix in the message. Projects with no `tausik/` tree are unaffected
> (the gate skips).

### The seven deferred mypy `disable_error_code` overrides are gone — the types are fixed, not silenced

`mypy-baseline-debt` reached zero by deferring seven modules' real
`arg-type`/`assignment` errors behind per-module `disable_error_code`. Each is
now fixed at the type level and the override removed: `record_gate_runs` takes
`verification_run_id: int | None` (the FK column is nullable — post-scope gates
have no verification run); `check_qg0_start`'s bypass-telemetry callback is typed
`Callable[[], object] | None` (its return was already discarded — not a defect,
a too-narrow annotation); `state_import` guards `target_type`/`relation` to `str`
before building an edge (a malformed edge is now skipped, not force-fed); the
reused variable names in `state_export` and `graph_mermaid` are disambiguated;
and the `auto_export_*` calls in `service_task`/`service_knowledge` go through
`cast("ProjectService", self)` at the mixin-facade boundary rather than widening
the helpers' honest `ProjectService` signature. `mypy` is `Success` over all 279
files with no `arg-type`/`assignment` suppression left — only the two structural
`attr-defined` mixin-facade overrides remain, tracked separately.

### `tausik status` showed a different project on the CLI than over MCP

Two presenters formatted the same `svc.get_status()` and surfaced
non-overlapping signal sets: the CLI gave closure risk, RENAR conformance, epics,
calibration drift, session capacity and a skill-set warning but hid open
explorations and audit-overdue; the MCP handler showed exactly the reverse. A
human reading the CLI and an agent reading MCP saw two different dashboards —
which defeats the point of a shared status. Both channels now render from one
`status_view.build_status_view`, so any signal present on one is present on the
other; the two `render_status_*` functions differ only in output shape. The
compact-JSON hot path stays cheap via `include_rich=False` (it enriches the data
the compact formatter reads but skips the rich-only DB queries and skills scan).
On the way through, `cmd_status` stopped resolving `load_config()` three times
off the process cwd and now threads `svc.tausik_dir()` once — the CLI's own copy
of the `mcp-config-read-paths-ignore-project-handle` defect the MCP side already
fixed — and `handlers.py` shed ~60 lines of inline formatting.

### The SENAR docs described protection weaker than the code enforces — and the drift scanner was blind to it

A fresh agent reading the contract would have concluded there was no gate where
one exists. The compliance matrix called Rule 2 (scope) and Rule 5 (verification
checklist) "Warning" — both are hard blocks (`scope_write_gate`/`bash_write_gate`
on writes; `checklist_hard_block` for substantial/deep tiers) — and omitted
Rules 4 and 6 entirely though both ship enforced (`risk_l3_trigger` gates
high-risk closures behind an L3 review; QG-0 blocks a medium/complex start with
no `rollback_plan`). Its header said "v1.5" while the footer said "v1.3".
`docs/ru/senar.md` flatly contradicted `docs/en/senar.md` — the RU note claimed
Rules 4–5 "are not yet enforced as hard blocks" while EN (correctly) said they
are as of v1.5; the code is on the EN side. `hooks.md` still advertised
"20 Python hooks + 1 shell = 21" (actual: 22 + 1) and never listed
`scope_write_gate` at all.

All fixed, and the reason it drifted uncaught is fixed with it: `hooks.md` was
outside every scan list, so `scan_code_counts` never read the header — it is now
a `CODE_COUNT_EXTRA_TARGET` (counts only, never versions, so its historical
"v1.4" refs survive). The hooks-count patterns tolerated only a `real-time`
qualifier, so "22 Python hooks" / "22 Python-хука" / "21 активный хук" slipped
through — the qualifier is now an explicit allow-list (real-time / Python /
active / активн…), still not `\w+`, so it never swallows an unrelated noun. The
auto-fixer repairs `hooks.md` too. A regression test drops a stale "20 Python
hooks" into a `hooks.md` fixture and asserts the scanner now reports it.

### mypy is clean again — the documented pre-commit hook no longer lies

`python -m mypy` reported 28 errors on a clean tree, while the pre-commit hook
the docs tell you to install (`git config core.hooksPath scripts/hooks`) blocks
any commit on a non-zero mypy — so the documented install path would have
refused every commit to this repository, a recommendation the project did not
itself keep. mypy is now at zero. The import-not-found errors (hooks/ and
bootstrap/ modules imported from `scripts/` via runtime `sys.path` injection,
which mypy cannot follow statically) are silenced with `ignore_missing_imports`
overrides, the same mechanism already used for `memory_markers`. The ten
mechanical `no-any-return`s are fixed at the value, not suppressed (a `cast`, or
a `bool()`/`str()`/`int()` at the boundary). The genuine `arg-type` / `assignment`
mismatches in seven modules (`state_import`, `state_export`, `service_knowledge`,
`service_task`, `gate_post_scope`, `service_gates`, `graph_mermaid`) are deferred
under a per-module `disable_error_code` that names the SPECIFIC code — so mypy
still catches every other error class in those files — and tracked as a follow-up
(`mypy-residual-argtype-untangle`) to un-pick one code at a time back to zero.

### Verify output no longer scolds a full-suite run or claims a pass after a skip

Four residuals left by the MCP-verify skip-visibility fix. (1) The
"no relevant_files declared for this task … `tausik task update <slug>`" NOTE
fired on EVERY full-suite (task-less) verify — the widest verification the tool
offers — with a literal `<slug>` that named no task; it is now gated on a real
`task_slug` and names the actual slug, and the task-less path gets its own
accurate line (full-suite run, not cached). (2) `python scripts/gate_runner.py`
still printed `All gates passed.` right after `[SKIP] pytest` — the exact
verify-summary-reports-skipped-as-pass lie `gate_verdict` was extracted to end,
in the neighbour file the extraction never reached; it now names the skipped
gates, and an all-skipped run says no gate executed. (3) The `no-tests-declared`
NOTE branch in `_handle_verify` was dead (the handler never passes
`no_tests_expected`, its only trigger) and is removed. (4) `service_task_done`
unpacked a `_cl_block` flag it never used and keyed the branch on the message
string instead; it now uses the block flag directly.

### A missed supervision-audit write no longer vanishes silently

`emit_supervision_bypass` / `emit_supervision_degradation` return a bool so a
caller can tell a landed row from a swallowed miss, but the four PreToolUse hooks
that call them (`task_gate`, `scope_write_gate`, `bash_write_gate`,
`memory_pretool_block`) ignore it — so when the DB write missed (no DB yet in the
bootstrap→init window, or a locked/corrupt DB under concurrent WAL access), a
`TAUSIK_SKIP_HOOKS` weakening was applied and left no countable trace, which makes
the release-1.8 enforcement claim unfalsifiable. The fix is central, in the
EMITTER rather than in each hook: on a miss `_emit_supervision` now appends the
event to a file fallback-sink, `.tausik/supervision_pending.jsonl` — a sink that
does not share the DB's failure mode, so it survives exactly the moments the DB
does not — and reconciles the backlog into `events` (with each event's ORIGINAL
timestamp) on the next successful write, where the metric then counts it. Because
the guarantee lives in the emitter, every present and future caller is covered
without having to remember the bool. Concurrency-safe: each pending file is
claimed atomically with `os.replace`, and a crashed drain's leftover is recovered
on the next pass. The one accepted edge is a possible OVERcount if a crash lands
between commit and unlink — the safe direction, since the whole point is to never
HIDE a weakening, and inflating a count never does that. If even the file sink is
unwritable, a last-resort stderr line keeps the weakening visible in the moment.

### Command firewall descends nested PowerShell / cmd wrappers, not just POSIX shells

The POSIX command scanner raw-joined 34 interpreters but descended into the
`-c` payload of only 7 POSIX shells, so a command hidden behind an INNER quote
in a non-shell wrapper — `powershell -c "powershell -c 'git push --force'"`,
`cmd /c "sh -c 'rm -rf /'"` — survived: after the outer quote layer is stripped
the inner command is anchored by an apostrophe, which the WARN patterns' command
-start anchor rejects, and no descent re-scanned it cleanly. All such forms were
confirmed rc=0 (allowed) before this fix. The PowerShell scanner's `payloads`
already descended its whole interpreter set; this brings the POSIX side to the
same parity via `_interpreter_payloads`, which now also reads PowerShell's
`-c`/`-Command` and `cmd`'s `/c`/`/k`. Scope is deliberate: only the DANGER
scanner descends further — `bash_write_parse`, which feeds the BLOCKING scope
gate, is untouched, so no new false blocks there. Named residuals, symmetric on
both channels: `ssh host '<cmd>'` runs on a remote host this firewall cannot
reason about, `wsl` has no `-c` form, a language interpreter's `-c` is code not a
shell line, and `-EncodedCommand` is not decoded — for those the outermost layer
is still judged but an inner layer behind a surviving quote is not descended
into. The overclaiming docstring ("a shell payload is now RE-SCANNED") is
narrowed to say which wrappers descend and which do not.

### secret-scan now covers the shell channels

`secret_scan` (SENAR Rule 10.12) was registered only on `Write|Edit|MultiEdit`,
so a secret written by a shell — an AWS key in a `cat > .env <<EOF` heredoc body,
or `Set-Content -Path .env -Value 'AKIA...'` — reached the exact content the Write
path would have warned on, and the hook never ran. It is now on `SHELL_MATCHER` in
both bootstraps and admits the shell tools via `shell_channel.is_shell_tool` (not a
literal `("Bash","PowerShell")` list — a second copy of that set is how the
PowerShell tool went ungated in the first place), so the gap closes on both channels
at once rather than re-splitting them. The whole command string is scanned, a strict
superset of extracting the written value: it catches the heredoc body and `-Value`,
plus `export KEY=AKIA...` — the secret literal in context, which Rule 10.12 also
covers — with zero new shell parsing (the one thing that has produced every
regression in this directory). Default stays WARN; `TAUSIK_SECRET_SCAN_STRICT=1`
blocks on the shell channel too. A secret passed by variable or env
(`--token "$TOKEN"`) is not a literal anywhere and is not flagged — the stated
residual, and the correct way to pass it. The hook now also forces UTF-8 stderr
itself instead of relying on the launcher's `-X utf8`, so a non-ASCII warning
survives a test or manual invocation.

### `rm -rf ~` now blocked — the home directory is a wipe root

The command firewall's wipe-root set (`rm_wipe_detect._WIPE_ROOTS`) recognised
`/`, `.`, `..` and a Windows drive root, but not `~`. So `rm -rf ~` — which deletes
the entire home directory, every project, every SSH/GPG key, every stored credential
— passed untouched, though its consequence is not milder than `rm -rf /` (and in
practice worse: `/` is usually root-owned and write-protected, `~` is all user-owned
and deletes cleanly). `~` is a literal tilde in the command line BEFORE the shell
expands it, so it is catchable here without resolving anything; it is now in the set,
covering `~`, `~/` and `~/*` (all normalise to `~`) across both the POSIX `rm` and
PowerShell `Remove-Item` channels, which share the one judge. A subdirectory of home
(`rm -rf ~/proj`) stays allowed, mirroring the leniency a named subdirectory already
gets. Decision #177 also settled the two operands the parent regression fix left
open: `..` stays blocked (unchanged), and a bare `*` needs no new entry —
`normalise_operand` already reduces `*`, `./*` and `.*` to `.`, so they were blocked
all along, and the previous docstring claim that `rm -rf *` was allowed was simply
wrong about the code (now corrected and pinned by test). `$HOME` and `${X:-/}` remain
a stated residue: resolving them would mean running a shell, so they are judged as
themselves (not a wipe) and pinned so the boundary is a decision, not a silent gap.

### Two hooks stopped reading config behind the trust tiers' back

`session_cleanup_check` (session-warn threshold) and `tool_output_truncation_nudge`
(output-line threshold) each did a raw `json.load` of the project's
`.tausik/config.json` — so the two settings an operator is most likely to set
machine-wide, via the user (`~/.tausik`) or managed (`$TAUSIK_MANAGED_CONFIG`)
tier, silently did nothing in these hooks. A tier exists only insofar as every
consumer reads it; these two didn't, which undercuts the trust model in principle,
not just in detail. Both now go through a new `tausik_utils.load_effective_config`,
which reads the project file and merges the user + managed tiers via
`config_trust.resolve`. It lives in `tausik_utils` (not `config_trust`, which is at
its size cap) with a lazy `config_trust` import, so a bare `import tausik_utils`
stays cheap and there is no cycle — important because the truncation hook is a
PostToolUse hook that spawns fresh on every Read/Grep/Bash. Any read problem
degrades the project tier to `{}` and never crashes. Regression tests pin all three
cases per hook — user-tier value now takes effect, project-only unchanged, malformed
config falls back safely — with an autouse fixture isolating the trusted tiers so the
suite never reads the developer's real `~/.tausik/config.json`. The adjacent items
the finding lumped in (unifying the config-path helpers, the three `.tausik` dir
resolvers, the `TAUSIK_DIR` push-ticket divergence) are deferred to their own steps.

### Command firewall now catches find-driven filesystem wipes

`find / -delete`, `find . -delete`, `find / -exec rm -rf {} \;`, and
`find / -type f -exec rm -f {} +` all passed the firewall (rc=0). The wipe
detector judged the operands of `rm` itself, but in the `-exec` form `rm`'s
operand is the placeholder `{}` and the root is an argument to `find` — and
`-delete` invokes no `rm` at all. This was a documented, unclosed gap:
`rm_wipe_detect.py`'s own header filed `find` as "a different detector … its own
task". That task is now done. A `find` deleting-detector in `danger_patterns.py`
routes through the **same** `is_wipe_root` / `normalise_operand` the `rm` detector
uses — no second definition of "what is root", so the two can't drift (the failure
mode this directory's history keeps reproducing). A hard root (`/`, a drive, `..`)
blocks whenever the find deletes, even name-filtered (a filtered slice of the whole
filesystem is never a legitimate wipe); the cwd `.` blocks only when the delete is
NOT name/path-scoped, so the routine `find . -name '*.pyc' -delete` stays allowed
while `find . -delete` does not. Pinned by a `TestFindBasedWipes` class covering
both the block side (11 idioms) and the allow side (8, incl. named subdirs and
non-deleting finds). Stated residual (not silent): deletes driven through a wrapper
— `find … | xargs rm`, `find … -exec sh -c 'rm …'` — and exec verbs beyond
rm/rmdir/unlink/shred are not covered.

### Closure-risk churn factor no longer fails open on a git error

Adversarial review of the git-wrapper consolidation caught a fail-open regression it
had introduced. `risk_compute._git_numstat_lines` used to call `subprocess.check_output`,
which *raised* on a non-zero git exit; that exception propagated to `_factor_code_churn`,
which dropped the `code_churn` factor so the risk model defaulted it to the conservative
**1.0** ("fail-visible"). The migration to `git_exec.run` (which returns rather than
raises on non-zero) silently removed that: on any git failure — unborn HEAD,
`fatal: bad revision 'HEAD'`, a corrupt repo — stdout came back empty, the line count
was `0`, and the factor read as **0.0**, the *lowest* possible risk. A closure that
should have scored conservatively would have scored as trivially safe. The function now
inspects `returncode` and re-raises on non-zero, restoring the fail-visible path, and a
new test stubs a non-zero-`returncode` result (not a raised exception — the gap the
original test missed) and asserts the factor is dropped, not computed as zero.

### Config loader no longer drags the database layer at import

`project_config` — the most-imported module in the tree — pulled `project_backend`
and `project_service` (the whole SQLite + service layer) at *import time*, purely to
offer a `get_service()` factory. That import-time edge meant nothing could read
`.tausik/config.json` without loading the database code, which is the concrete
blocker for shipping a standalone config loader (the v2 engine-standalone-package
goal): a package that only parses config must not require the ORM. `get_service()`
and its two DB imports now live in a new leaf `service_factory.py`; the one importer
(`project.py`) was repointed. Separately, the session-duration constants, the
context-tier enum + resolver, and the LLM-pricing normaliser/lookup moved to a new
dependency-light `tausik_constants.py` — `project_config` re-exports every one of
them, so all existing `from project_config import X` call sites (MCP handlers,
`service_session`, `project_cli`, `cost_pricing`, `bootstrap`, tests) are untouched.
A `test_config_module_boundary` suite pins it: an AST guard plus a subprocess import
with the DB modules blocked prove `project_config` now stands alone, while
`service_factory` correctly still fails without them. The remaining concern-splits
(gate merge/validation out of `project_config`; the `project_cli_ops` /
`project_cli_extra` multi-concern files) are deliberately deferred to their own steps
— this change is the architectural edge-break, not the full 9-way carve.

### Version metadata reconciled — the framework stopped misreporting its own version

A discipline framework that misstates its own version undercuts its whole premise.
`TODO.md` said "Released v1.5.0", the SENAR compliance matrix headers (EN + RU) said
"TAUSIK v1.5.1", while `pyproject`, `constants.json` and `tausik_version.__version__`
all said v1.7.0 — three different answers to one question. All now state the coherent
truth: **v1.7.0 released, v1.8 in flight on `release/1.8`**. The matrix's audit *date*
(2026-06-13) is deliberately kept, not bumped — refreshing it would fabricate a
compliance audit that never ran. And `scripts/README.md` no longer hardcodes
`tausik_version.py`'s version ("1.1.0", itself stale) — it now describes the module as
the single-source `__version__`, so that line can never drift on a release again. The
final 1.7→1.8 bump/tag stays a separate release step; this is only the reconciliation.

### One guarded git primitive — the stdin-hang guard can't be copy-pasted away

Seven ad-hoc git wrappers had accreted across the framework, each re-deciding
whether to close stdin. That mattered because of a real, twice-seen defect: inside
the MCP server `sys.stdin` is the JSON-RPC pipe to the IDE, and on Windows git
probes stdin (paginator / credential prompt) and blocks, hanging the worker
(`v14b-defect-mcp-task-done-stdin-hang`). The guard had been lost once by
copy-paste (`risk_compute`, then restored) and one gate-reachable site
(`hooks/git_push_gate._git_head_sha`) shipped **without** it — safe only by luck,
because its stdin happened to be consumed earlier. New `scripts/git_exec.py` is the
single chokepoint: `run_git(cmd, **kwargs)` (a `subprocess.run` drop-in that forces
`stdin=DEVNULL`) and the ergonomic `run(args, *, timeout, …)` on top of it. The five
importable `scripts/` git call sites route through it, and `verify_git_diff`'s
injectable-runner seam now defaults to `run_git`, so even future code that forgets
stdin is guarded. The `git_push_gate` hook stays independent — invoked as an
isolated subprocess with only `hooks/` on `sys.path` (shared utils are duplicated
into `hooks/`, not imported from `scripts/`), so it keeps its own call and gains the
missing `stdin=DEVNULL` in place: the one genuinely-unguarded *reachable* site. The
`bootstrap/get_lib_commit` installer is deliberately left as-is — it runs only as a
standalone CLI, never inside the MCP worker, so the JSON-RPC-stdin hang cannot reach
it, and the file already sits at its 400-line budget; a defence-only line there
would buy no safety. `timeout` is a required keyword on `run` — no silently-unbounded
git call can exist. Pinned by `tests/test_git_exec.py` and the
existing AST anti-regression scan, which now recognises `git_exec` as the one
sanctioned `subprocess.run` of a git command.

Deliberately **not** done in the same pass: the four "is this a test file?"
predicates (`gate_test_resolver`, `risk_compute`, `gate_filesize`,
`gate_tdd_order`) look like duplicates but answer four different questions with
load-bearing differences — `src/foo.spec.ts` is a test for TDD-order but
intentionally not filesize-exempt nor risk-test-churn; a root-level `test_x.py`
isn't filesize-exempt (that gate matches the `tests/` **directory** only); and only
the risk predicate lowercases. Unifying them would change at least one gate's
behaviour, so they stay distinct — a difference that is a feature, not drift.

### Model rank↔id reverse map is derived from profiles, not hand-copied

The mapping "which model id fills which capability rank" lived authoritatively in
`model_profiles.DEFAULT_FAMILIES["claude"]`, yet `model_routing_matrix` carried a
hand-written `_PROFILE_SLUG_BY_MODEL_ID` literal restating its reverse — with no
guard forcing the two to agree. A rank's canonical id could bump in one place and
the reverse map silently keep the old answer. That literal is now *derived* from
`DEFAULT_FAMILIES` via `reverse_index`, so a point-release bump (opus 4-8 → 4-9)
propagates for free and the two can never drift; a `TestProfileSlugSingleSource`
class pins the derivation, the historical/future family-fallback cases
(`claude-opus-4-7`, `claude-opus-4-9` resolve via the token path with no explicit
entry), and the negative case (an id with no family token, absent from profiles →
`None`, never a wrong-slug guess). `cost_pricing._MODEL_PRICING` is deliberately
left untouched: it is a distinct *pricing* table that must enumerate historical
ids for old sessions, and it is already mechanically drift-guarded by
`test_every_routed_claude_model_has_a_price` — folding it into the rank map would
add coupling, not remove it.

### Role-count drift now fails the doc-drift check

Adding the sixth built-in role (`devops`) exposed a blind spot: the doc-drift
scanner counted stacks, hooks and review-agents but never *roles*, so a stale
"N roles"/"N ролей" reference could drift uncaught — and had. `constants.json`
now carries `roles_count` (derived by `code_counts.count_roles` from
`harness/roles/*.md`), and `_CODE_COUNT_PATTERNS` gained EN + RU role patterns
(fence-blind like the others). The stale literals were reconciled: both
`architecture.md` trees said "5 roles" (missing devops) — now "6 roles"; the EN
tree also said "12 core" skills against a live 13 and is reconciled to
`skills_core_count`. Regression-pinned by five new `TestRolesCount` cases
(flags stale EN/RU, clean on 6, ignores a fenced tree comment, no false-positive
on "role-scoped").

### doc-drift scanner split under the filesize cap + hooks regex hardened

`doc_drift_scanners.py` had grown to 524 lines — the one file in `scripts/` over
the 400-line cap, and (irony) the module that powers the doc-drift gate. Split
three ways with no duplication and no circular import: `doc_drift_common.py`
(regex table + line-preserving helpers), `doc_drift_scanners.py` (the `scan_*`
walkers, 239 lines), `doc_drift_fixes.py` (the auto-fixer). `write_cross_file_fixes`
is re-exported from the scanners module, so `gen_doc_constants` and existing tests
are untouched. Separately, the hooks-count pattern was adjacency-anchored
(`\b(\d+)\s+hooks\b`) and so missed `21 real-time hooks` — an adjective between the
number and the noun — which had drifted uncaught (README said 21, constants 22).
It now tolerates an optional real-time qualifier and the RU singular `хук`, still
ignoring fenced illustrative numbers. README hooks 21→22 and architecture's test
example reconciled to the live count. (A `4101` inside a ```bash fence stayed
scanner-invisible by design — the illustrative-number guard — and was fixed as a
plain literal, not by teaching the scanner to read fences.)

### Kubernetes stack validates with kubeconform, not the archived kubeval

The built-in `kubernetes` stack shipped a `kubeval` gate — a tool its own
maintainer archived and explicitly superseded with `kubeconform`. It was the only
deprecated binary among the IaC stacks (docker/helm/terraform/ansible all point at
maintained linters). The gate is now `kubeconform -summary -ignore-missing-schemas`
(supports current K8s versions + CRDs; the flag lets CRDs without a published
schema pass rather than fail a lint). Unchanged by design: still `enabled:false`
(opt-in, so a project without the binary is never blocked), still `severity:warn`
(schema typos, not policy — kube-score / OPA / Kyverno remain custom gates), same
`k8s/` `manifests/` `.kube/` detection. `guide.md` notes kubeval as the deprecated
predecessor.

### Fixed: `spec` / `adapt` CLI swallowed errors and exited 0 (silent failure)

Sibling of the `role` fix below: the `tausik spec` and `tausik adapt` dispatchers
caught `ServiceError`, printed it to stdout and returned — so a failing command
(e.g. `spec show <missing>`) exited 0. Both now route the error to stderr and
exit non-zero, matching the top-level `project.py` contract and every other
command. Regression-pinned by new handler tests (`SystemExit(1)` on stderr; happy
path still exits 0). This closes the class the role fix's note deferred.

### Fixed: `role` CLI swallowed errors and exited 0 (silent failure)

`tausik role show <missing>` (and `role create/update/delete` on their error
paths) caught the `ServiceError`, printed it to **stdout**, and returned — so the
process exited **0** on a real failure. A script or CI step checking `$?` saw
success; the sibling `task show <missing>` correctly exits 1. The handlers now let
the error reach the top-level dispatcher's contract — message to **stderr**, exit
**non-zero** — matching every other command. Regression-pinned by three subprocess-
free handler tests (error → `SystemExit(1)` on stderr; happy path still exits 0).
The identical swallow in the `spec`/`adapt` handlers is tracked separately.

### DevOps role ships as a sixth default profile

`harness/roles/devops.md` joins architect/developer/qa/tech-writer/ui-ux as a
built-in role, so delivery work — infrastructure-as-code, CI/CD, containers,
orchestration, observability — routes and prompt-injects like any other role
(`task add --role devops`, profile injected on claim). The profile is
skill-modified the same way the others are (`/review`, `/plan`, `/task`, `/test`,
`/commit`) with a deployment-safety-first lens: plan the rollback first, prefer
additive gated changes over big-bang cutovers, treat a green schema-lint as
"catches typos, not policy". It was not invented on a hunch — seeding surfaced
that seven pre-existing tasks already carried `devops` as a free-text role, so
this promotes an organic convention to a first-class registered role. Deployed to
every IDE tree by bootstrap (`Roles: 6 copied`); `docs/{ru,en}/roles.md` updated.

### Memory graph renders as Mermaid diagram-as-code (borrowed from cubest)

`tausik memory graph --format mermaid` renders the live memory/decision knowledge
graph (`memory_edges`) as a Mermaid flowchart — native in artifacts, GitHub and
Obsidian, for both the agent and a human. Borrowed from cubest's "one cube, many
projections" idea. Deterministic like the state export (nodes in sorted id order,
edges by `(source, relation, target)`), so a re-render never churns; labels are
sanitised to a Mermaid-safe subset so no title or decision first-line can break
the diagram, and only live state travels (non-archived memory, valid edges,
slug-bearing nodes that participate in an edge). An empty graph yields a valid,
empty `graph LR`.

### State export/import wired into the lifecycle (no manual sync)

The git-native projection now tracks the DB without manual commands. On a durable
write — **every** mutation of the five projected kinds, from `epic add` through
`task log` to `decide` — the changed entity is incrementally re-serialized to just
its own file (byte-identical to a full export of that entity, proven by a pin
test), not the whole tree. An entity that leaves the projection (deleted, or
memory archived) has its file removed, so the tree can shrink as well as grow.

The coverage is checked as a property, not as a list of call sites: after any
sequence of mutations with no manual command in between, the files on disk equal
`build_tree(db)` byte for byte. That test is why this reads "every" — the first
cut wired three call sites by hand and the prose said "task done, decide, memory
add", while 18 of ~20 mutating methods silently skipped the export. A decision
recorded WITH a task_slug, the common case, reached the DB and never the tree; a
periodic full `tausik state export` rebuilt it, which is why `status` reported no
divergence. Counting call sites could not have caught that, and neither could a
test that asserts the call sites someone remembered to list.

Worst-case cost, measured rather than assumed: `task log` on the project's
longest journal (21 entries, a 40 KB document) goes from 5.3 ms to 26.6 ms per
call — the whole task doc is re-rendered to compare it against the file on disk.

On session start,
`tausik_session_open` carries a best-effort `sync_suggested` signal: a content-based
dry-run import that reports what the `tausik/` tree holds but the DB does not (e.g.
after a `git pull`), so `/start` can offer `tausik sync`. Every trigger is
fail-open by construction (gotcha #271): a serialization or IO fault is logged and
swallowed, never breaking or rolling back the underlying operation — the DB write
is the source of truth, the file projection is best-effort. The whole mechanism is
gated behind `state.auto_export` (default off) so a project that has not yet
un-gitignored `tausik/` never gets surprise files; state-git-roundtrip-gate will
flip the default. (Refactor note: `service_knowledge`'s cq-row helper moved to
`service_cq_row` to stay under the filesize cap once the hook landed.)

### The git-native tree can be imported back into the DB cache

`tausik state import` (alias `tausik sync`) is the inverse of `state export`: it
reads the `tausik/` tree — the canonical source of truth — and rebuilds the SQLite
working cache, the command an engineer runs after `git pull` / `git checkout` so
the DB reflects the branch. It is idempotent and delta-based: a file whose parsed
projection matches its DB row is left untouched, and re-running with no file change
writes nothing. Git wins on conflict, but never silently — every overwrite of a
locally-diverged row is reported, `--dry-run` shows the add/update/journal/edge
plan without touching the DB, and nothing is deleted (an incremental import never
removes an entity absent from the tree, so a `checkout` of one branch cannot erase
work not yet merged from another). A malformed file aborts the whole batch inside a
transaction — never a partially-written DB — and FTS is rebuilt so search sees the
imported state. The parser is the exact stdlib inverse of the emitter, and the
round-trip is pinned on real data: re-exporting an imported DB yields a byte-
identical tree across all ~1950 entities, including two subtleties found by that
pin — self-referential `defect_of` FKs are deferred to commit so slug-order
insertion never trips them, and identical journal lines are reconciled as a
multiset so a genuinely-duplicated log row survives the round-trip instead of
collapsing to one. Together with the exporter this closes the `team-state-in-git`
round-trip: state now travels branch-native with the code.

### Project state can be exported to a git-native tree

`tausik state export` serializes durable project state — tasks (with their
`task_logs` as an append-only Journal), epics, stories, decisions, memory and the
memory graph — from the SQLite DB to a `tausik/` markdown+frontmatter tree, one
file per entity keyed by the stable slug from the v42 migration. The whole point
is byte-determinism: the same DB state yields an identical file on every machine
and every re-run, so a teammate's `git clone` sees the tasks and decisions a
binary `tausik.db` hides, and state merges branch-native with the code. The
serializer hand-rolls a stdlib YAML emitter with a fixed frontmatter key order,
alphabetical tags, edges sorted by `(relation, target_type, target)`, ordered-list
dedup, ISO-8601 `Z` dates, explicit `null`, and conservative quoting of any scalar
a YAML parser could misread as a number/bool/date (`2026-01`, `on`, a bare `n`);
newlines are LF-only including on Windows. Only live state travels — archived
memory and invalidated edges are excluded — and an entity without a stable slug
refuses the export loudly (run the migration first) rather than fabricating an
ephemeral slug that would diverge between machines. `tausik state export --check`
fails CI on a stale tree, reading files with universal-newline translation off so
a CRLF re-save cannot pass as clean; deletion reconciliation is scoped to the five
entity subdirectories so a hand-written `tausik/README.md` is never swept, and any
removal is announced. Adversarial review hardened the `--check` CRLF blindness, the
over-broad deletion, the missing `memory.title`, and the YAML-1.1 `y`/`n`/`inf`/`nan`
quoting before merge. Import (`state-git-import`) is a separate task.

### Slug allocation is race-safe, and a failed backfill is no longer silent

Reviewing the v42 migration surfaced three follow-ups. New rows computed their
slug by reading the taken set and then INSERTing in a separate statement — a
TOCTOU race on a connection opened `check_same_thread=False`, where two
concurrent writers could compute the same base slug. The UNIQUE index is now the
source of truth: `insert_with_slug` retries on a collision with the next suffix,
so a raced write is corrected, never crashed and never silently duplicated. The
v42 backfill caught its errors and only `warning`-logged them while the caller
discarded the result, so a genuinely failed identity migration re-ran unseen on
every DB open — it now logs at ERROR and records a queryable `v42_slugs_backfill_error`
marker that a successful run clears. And the slug helper's table name, previously
f-string-interpolated, is now checked against a `{decisions, memory}` allowlist.
The decisions+memory CRUD moved to its own `KnowledgeCrudMixin` to stay under the
filesize cap.

### QG-0 now recognises a negative scenario written in Russian

The Start Gate requires an AC to name at least one negative scenario, but its
keyword list knew English `negative` (and `timeout`, `exception`, `crash`,
`exceed`, `overflow`) with no Russian counterpart — so in a Russian-language
project a criterion that spelled its negative case as `НЕГАТИВ: …` failed a gate
it plainly satisfied. Caught by dogfooding: the framework blocked its own author.
Each missing marker gains its Russian mirror (`негатив`, `таймаут`, `исключени`,
`паден`, `крах`, `превыш`, `переполн`) — additive, so no positive criterion newly
passes; the `без`/`without` redaction that keeps "Без ошибок" a non-scenario is
untouched, and `сбор`/`сборка` deliberately do not match.

### Decisions and memory get an identity that survives a branch merge

Tasks are addressed by slugs, so two engineers on two branches never collide on
a task id. Decisions and memory were not: they used local autoincrement ids
(`#171`, `#307`), so both branches mint `#308` and a `git merge` of the exported
state would duplicate or clobber. This is the load-bearing precondition for the
whole state-in-git epic — without stable identity the projection cannot merge.

The v42 migration adds a `slug` to both tables and backfills every existing row
deterministically: a memory's slug from its title, a decision's from its first
line, in id order so two machines resolve the same collisions to the same
`-2`/`-3` suffixes. The project's working language is Russian, and a bare
ASCII-fold would empty every Cyrillic title into a bare `memory-<id>` — so the
slug is *transliterated* to Latin (`доменная проверка` → `domennaya-proverka`),
giving a portable, readable `tausik/memory/<slug>.md` that is byte-identical on
NTFS, ext4 and APFS. The transliteration table and the dedup order are frozen:
changing either re-slugs history.

Additive and reversible: two nullable columns plus a unique index built *after*
the backfill, run by the migration runner behind an auto-backup. The 171
decisions and 300+ memories of this very repo migrated with every row uniquely
slugged and every memory-graph edge still resolving — validated on a copy of the
live database before the live one was touched. The integer id stays the primary
key, so `#171`/`#307` keep displaying exactly as before. See decision `#173`.

### Reviewing the groundwork found four more holes in the machinery that guards it

An adversarial pass over the state-in-git groundwork surfaced four defects, each
a case of a check being weaker, or more forgeable, than it read.

`task done <already-done-slug> --relevant-files X` wrote the new scope to the
task row *before* the "already done" guard fired — so a call that then failed
with an error had already overwritten the scope of a closed, certified task: the
very list that fed its risk score, its verify-cache hash and its signed receipt,
rewritten invisibly. The guard now refuses the closed task before any write.

The "COMPLEXITY UNDERSTATED" proxy subtracts the files every task touches by
ceremony, but its hand-written list of them omitted `AGENTS.md` — which
`update-claudemd` writes on every close as a synced sibling of `CLAUDE.md`. Any
task that touched it was quietly counted one file more complex than it was, the
exact overcount the proxy exists to remove. The sibling name now comes from the
one place that owns it, so the two lists cannot drift.

The scoped-pytest coverage label (`SCOPE: 2 of 318 — NOT the full suite`) was
recognised by its public `SCOPE:` prefix, grepped straight out of gate stdout —
so an author-controlled stack command could print the same line and forge a
full-coverage claim, and a scoped run that *failed to spawn* dropped the label
entirely. The genuine label now rides a private sentinel a subprocess cannot
emit, lifted into a trusted field at one boundary; a `SCOPE:` line in tool
output is just text. Spawn and timeout failures carry the label like any pass.

The AC-evidence detectors claim each marker is equally loose in Russian and
English, but two had drifted in opposite directions: `review` demanded a phrase
in English while a bare `ревью` passed in Russian (so an English "code review"
was hard-blocked where the Russian was not), and `доменн` matched inside
`поддоменное` (subdomain) where the bounded English `domain` never credited
`subdomain`. Both are realigned so the two working languages earn the same
credit for the same evidence.

### Groundwork: project state that travels with the branch, not a server

A teammate who clones the repo sees no TAUSIK state at all — `.tausik/` is
gitignored and `tausik.db` is a binary SQLite file two people cannot merge. The
1.8 answer is not a shared server or Notion (both branch-agnostic, both
decouple state from the code it describes) but a **git-native projection**:
durable project state — tasks, plan, journal, decisions, project memory —
serialised one file per entity into `tausik/`, so a decision made on a feature
branch merges into `main` exactly when that branch's code does.

This first task lays the contract only, no runtime yet: `docs/{ru,en}/team-state-in-git.md`
and spec `team-state-in-git-format` fix the directory layout, the
markdown+frontmatter format, the byte-identical round-trip rules (LF, fixed key
order, deterministic list sorting), the per-table scope (what travels, what
stays local), and the git merge semantics. The load-bearing follow-up is stable
identity for decisions and memory, which today use local auto-increment ids that
would collide across branches. See decision `#172`.

### The one instruction on offer could not be carried out

`tausik verify --task X` over an empty scope skipped every gate, signed a
receipt anyway, and printed: *"Pass --relevant-files for verification."*
`verify` had no such flag. The command that did (`task update
--relevant-files`) was named in no message at all. And `task done
--ac-verified --relevant-files ...` wrote the scope inside the `status=done`
transaction, so a close blocked by Verify-First threw the declaration away —
leaving the task as unscoped as before, to be verified again over nothing.

Three commands pointing at each other with no way through. Ignoring the
warning was the *rational* response, not a careless one, and a year of
closures resting on "no relevant_files passed — scoped gates SKIPPED" is what
that rationality bought.

`verify` now takes `--relevant-files`. It declares the scope *and* verifies it,
persisting the paths to the task so `task done` reads the same list and hits the
cache — one source of truth, the task row. Without `--task` it is an explicit
error rather than a silent no-op, and an empty list (a glob that matched
nothing) keeps the existing scope instead of quietly wiping it back into the
state this whole fix removes.

A declaration is not a result, so `task done` now records `--relevant-files`
the moment it is given, before any gate can block the close. The blocked close
still blocks; the task keeps the scope it was told about.

Both messages were rewritten to name whole, runnable commands. The tests do not
compare them against expected strings — they extract the command from the
message and hand it to the real argparse parser, which is the only check that
would have caught the original defect.

The ten added lines pushed `service_task_done.py` past the filesize gate, and
the seam it exposed was real: deciding whether a task may CLOSE is a different
question from where its declared scope came from and when that gets written
down. The second now lives in `task_done_scope.py`.

### Seven sessions of "COMPLEXITY UNDERSTATED" were counting the paperwork

The advisory compares declared complexity against the number of files a task
touched. Six of those files are touched by *every* task regardless of size:
both CHANGELOGs (mandatory by convention #275), the framework-maintained
CLAUDE.md, the generated `docs/_generated/constants.json`, and each document
that exists twice because the project ships a Russian mirror. A one-line fix
arrived at close carrying +6 files and was told it looked `complex`.

It fired in seven consecutive sessions, and every one of those advisories was
also written to the supervision log — so the calibration data had been
accumulating a systematic understatement that never happened. The measurement
was noisy, not the estimates.

What changed is the measured quantity, not the scale: `_SIMPLE_MAX_FILES` and
`_MEDIUM_MAX_FILES` are untouched. A file counts when it can carry a behaviour
change — ceremony files and generated artefacts drop out, and a document
counts once rather than once per language. A *lone* mirror still counts: the
canonical key is derived from the path rather than looked up against the set,
so editing only `README.ru.md` remains one file of work. Dropping it would make
translation invisible, which is the more insulting error of the two.

Backtested on all seven closures that were flagged: five advisories disappear,
two survive — including one that declared `simple` while changing four hook
modules, which is the case the advisory exists for. The warning now names both
numbers ("9 behaviour-bearing files of 13 declared"), because a warning that
says nine about a thirteen-file `git status` reads like a broken tool.

### The suite never hung — it was longer than every timeout aimed at it

Three sessions killed the full `pytest` run at 200 s, 420 s and 600 s, saw it
stop at 38%, 77% and 64%, and concluded it hangs. It does not. Run without a
timeout it finishes: **5759 passed, 23 skipped, 140 deselected in 554 s**. Two
measurements say the same thing from the other side — `faulthandler_timeout` of
60 s and then 120 s produced no dump at all (no single test ran a minute), and
`--durations=30` puts the slowest test at 5.28 s with the whole top thirty
adding up to 10% of the total. There is no hot spot to fix: ~0.09 s across 5759
tests is what nine minutes is made of.

So the change is not a speed-up, it is a way to tell *stuck* from *long*
without a human guessing. `faulthandler_timeout = 60` plus
`faulthandler_exit_on_timeout = true` (both stock pytest, no plugin) mean any
single test over a minute dumps every thread's traceback and exits non-zero.
Silence from the guard now *means* "not stuck, just long" — budget the ten
minutes instead of shortening the timeout and re-deriving a hang.

Measuring it also found what three sessions of guessing had not: **the suite
was red.** `test_check_docs_hook::TestRealRepoSync` failed on doc-constants
drift — a test file added at the end of session #134 moved `test_count`
5913 → 5923 and `docs/_generated/constants.json` was never regenerated. The
closure that introduced it was verified by the scoped pytest gate, which maps
`relevant_files` to test files by basename; nothing mapped to
`test_check_docs_hook.py`, so the gate never ran the test that was failing and
the receipt was green.

That receipt is now harder to over-read. A scoped run prefixes its output with
one line naming what it covered — `SCOPE: scoped run over 2 of 318 test file(s)
mapped from relevant_files -- NOT the full suite: …` — on pass, on failure and
on timeout alike. The verdict and the size of the thing it was earned on travel
together into the signed receipt, so "PASS pytest" can no longer be read as a
statement about the project. `gate_command_runner.py` and
`gate_test_resolver.py` also got test files named after them: neither had one,
which meant the scoped gate could not verify its own scoping code.

Checked, and cleared: the "full pytest 5744/5750 passed" lines in session
#134's evidence are honest. A scoped run cannot print four-digit pass counts,
and the `23 skipped` matches today's full run exactly. Those runs were real and
green — the suite went red afterwards, in the last closure of the session.

### Of two closure checks printed side by side, only one spoke Russian

QG-2 printed two NOTEs together: "no `Negative:` evidence found" and "domain
challenge unanswered". The second was satisfiable in the language this
project's evidence is actually written in; the first was not — `DOMAIN_RE` has
been bilingual since birth, `NEGATIVE_RE` was `\bnegative\b`. On three real
closures of session #134 the negative scenarios WERE exercised and pinned by
tests, and were flagged anyway, because they were described in Russian.

The filed hypothesis — evidence written to notes AFTER the check that reads it
— is **refuted by the code**: `service_task_done` logs the evidence and
re-reads the task before every closure check. The verdict depends on the TEXT,
not on the path it arrived by, so writing the same lines earlier via `task log`
changes nothing. That is pinned by a test rather than argued.

`MANUAL_RE` and `REVIEW_RE` had the same monolingual gap, and it cost more:
they feed `checklist_missing`, a HARD block for substantial/deep tiers. A
manual run described in Russian could block the closure.

The Russian alternatives are deliberately **as loose as** their English
counterparts (bare stem, not a required phrase). Convention #301: when you port
a detector to a new dialect, port the false-positive list it already paid for —
inventing a stricter dialect is how two judges start disagreeing. The known
weakness "the detector matches a WORD, not a fact" remains, is now symmetric
across languages, and is not fixed here.

Detectors moved to `scripts/ac_evidence_detectors.py` — the file hit the
filesize gate and the seam is real: WHAT counts as a marker is not HOW lines
are segmented and matched to AC items. The producer-side registry
`PROSE_DETECTORS`/`STRUCTURAL_DETECTORS` moved with them: the parity test reads
the detector names FROM THE PARSER'S BYTECODE instead of listing them itself,
so a new English-only detector fails the test instead of quietly reopening the
gap.

### The primary platform's main shell reached no hook at all

`.claude/settings.json` registered the firewall, the shell-write gate and the
push gate with `"matcher": "Bash"`. On win32 — the platform CLAUDE.md, the docs
and the `.cmd` wrapper all call primary — the agent is handed a SECOND shell
tool, `PowerShell`, and it matched none of them.

Nothing was broken and nothing failed. The rules were correct, the tests were
green, and the gates simply were never invoked for a large share of the commands
actually being run. That is the shape worth naming: supervision can be whole by
RULE and holed by CHANNEL, and the second kind is invisible to a test suite in
which every test also says "Bash".

What went ungated, measured before anything was changed:

* `Remove-Item -Recurse -Force C:\` — unexamined. `_WIPE_ROOTS` held POSIX roots
  only, so the root of the disk was the one root the firewall could not name, on
  the only OS where it exists.
* Rule 1 (task before code) and Rule 2 (scope ACL) — `Set-Content`, `Out-File`,
  `New-Item` and `>` bypassed both.
* `git push --force` — reached NO gate. The push-ticket registration also
  carried `"if": "Bash(git push *)"`, a second, dialect-specific copy of a
  decision the hook already makes for itself.
* Session accounting — `activity_event` and `task_call_counter` did not count
  the channel, so a session worked through PowerShell reads as idle and the
  180-minute Rule 9.2 limit quietly stops applying.

Reusing the POSIX tokenizer was not an option: `shlex(posix=True)` treats `\` as
an escape, so `Remove-Item C:\` either loses its operand or raises. PowerShell's
escape is a backtick and `\` is an ordinary path character — a dialect needs its
own reader or it mis-parses exactly the operands that make a command dangerous.

The fix is a split rather than a second copy of the rules, because a second copy
is how every regression in this directory started:

* `pwsh_cmd_parse` / `pwsh_cmd_norm` — tokenizer, statement model, alias table
  (`rm`/`del`/`rd`/`ri` → Remove-Item, `sc`/`ac`, `iex`, …), PowerShell's
  unambiguous-prefix parameter binding (`-Rec`, `-Fo`), cmd's `/s` `/q`
  spellings, and descent into `powershell -Command` / `cmd /c` / `iex` payloads.
* `danger_patterns` — WHAT is dangerous, once, for every dialect. Adding a third
  shell now means writing a scanner, not re-deciding what `git push --force`
  means. Windows entries (`Format-Volume`, `Clear-Disk`, `Remove-Partition`,
  `vssadmin delete shadows`) close a channel gap, not a policy change: the POSIX
  side has blocked `mkfs.` since the first version.
* `rm_wipe_detect.is_wipe_root` — ONE judge of which places mean "everything",
  asked by both dialects, with two dialect-specific flag parsers above it.
* `shell_channel` — the single place that knows which tool speaks which shell.
  The literal `!= "Bash"` it replaces was written out in every gate, and
  `bootstrap_hooks.SHELL_MATCHER` is now pinned against it by a test, so a
  dialect gaining a parser without a matcher fails instead of going ungated.

Differential run over a shared operand corpus (convention #298), old judge
against new: 0 operands stopped being judged a root, 11 started — exactly the
volume-root spellings (`C:\`, `C:/`, `D:\`, `C:\*`, …) and nothing else. The
sentence "POSIX behaviour is unchanged" is written from that output, not from
belief. `~`, `..` and a bare `*` remain out of the set; that is a policy
question and it belongs to its own task.

**Follow-up, found by dogfooding within the hour.** The new gate blocked this
project's own `git commit -m @'…'@` — the commit closing the task above. A
PowerShell here-string carries DATA, but the tokenizer did not know the
construct: an apostrophe anywhere in the body ("the hook doesn't know") ended
the ordinary quote scan, the command failed to tokenize, and the regex fallback
— which over-detects by design — read a bare `>` in the message's prose as a
redirection and reported `bypassed` as a write target.

The POSIX twin had carried `_strip_heredocs` against precisely this symptom
since it was written, with the failure spelled out in its docstring. The new
dialect inherited the detectors and not the false-positive defences, which is
channel parity by RULE and a gap by PROTECTION — and the more expensive
direction: a false BLOCK on the most routine multi-line operation there is,
whose only exits train the bypass (#291).

`@'…'@` and `@"…"@` are now one token, with PowerShell's own two conditions
enforced — the opener must end its line, the terminator is recognised only at
the START of a line. Relaxing either re-exposes the body as live shell, which
is the same trap the POSIX side hit on an indented pseudo-terminator. A real
target after a here-string (`@'…'@ | Out-File notes.md`) is still seen, and
`iex @'…'@` still descends: the body is data until something executes it.

Every other data-carrying construct was then audited rather than assumed —
quotes (closed), script blocks (deliberately NOT data: they execute), `$(…)`
and `@(…)` (named residual) — in the coverage doc below.

**And the commit after THAT was blocked too**, by the push gate, for the
opposite reason. Closing the channel had made it try both tokenizers and block
if either saw a `git push` — sound against evasion, wrong in practice. The
POSIX lexer does not know a here-string either, broke out at the apostrophe in
"PowerShell's", and read the `git push --force` in the message's prose as a
command. Of two judges, the one that cannot read the language wins every
disagreement. The dialect now follows the TOOL, through the same
`shell_channel` table that already routed write targets and scanning; a
tokenizer chosen by hand at a call site is a dialect chosen by hand.

Deliberately NOT routed through `scan_target`, which joins an interpreter's
payload back raw and would have blocked an honest `python -c "print('git
push')"` — trading one false block for another. That case is pinned. The
resulting residual (an ordinary push inside a wrapper payload is not ticketed;
`bash_firewall` still catches a force-push there) is named in the coverage doc
rather than left to be discovered.

`docs/{ru,en}/enforcement-coverage.md` is new — the enforcement-boundary section
split out of the RU agent contract (it no longer fit under the filesize cap once
the matrix landed, and the topic stands on its own; the EN mirror did not exist
at all before). It carries the channel-coverage matrix, including the gap this
task does NOT close: `secret_scan` covers neither shell channel. That is equal on
both sides rather than a skew, and closing it on one would put the channels back
out of step.

### The Rule 5 checklist gate was cleared by the word "scope"

`checklist_missing` counted vocabulary. The tier tables held words —
`scope`, `secret`, `phantom`, `edge case` — and one occurrence anywhere in a
task's notes silenced the gate. For substantial and deep planning tiers it was
not a nudge but a HARD block on closing, so the condition for finishing the most
expensive tasks in the system was that a word appeared in a text field the agent
writes itself.

The v1.4 note for `check_verification_checklist` already called the v1.3 keyword
count "trivial to fool ('scope clean, no secrets' produced 2 hits)" and
announced the structured AC-evidence parser as its replacement. The parser was
added on top. The keyword count stayed, and stayed the sole source of the
verdict.

Measured across the 851 closed tasks that carry acceptance criteria, the two
disagree on 380 — 44.7%. 320 tasks cleared the keyword scan with no real
evidence behind any criterion; 60 were warned at while their evidence was real.
This is also the honest answer to a note carried forward from the previous
session, that the warning was ignored at every close: there was no action that
cleared it except guessing the password.

The verdict now comes from the evidence parser that was supposed to own it:

* Warning when no criterion names a test, a manual run or a review. A bare check
  mark is a claim that verification happened, which is the thing being checked.
* Hard block (substantial/deep only) when no criterion cites a test file that
  EXISTS. A path that does not resolve is treated as no evidence — an
  unresolvable citation and an invented one are the same string, and the
  adversary for this predicate is an agent writing its own notes.

Two tests in the suite had been pinning the old behaviour in place — one passed
`notes="scope clean, no secret leak"` and asserted the gate stayed open. They
now assert the opposite, and that same string is pinned as a case that must NOT
close a task. On the historical rows the change is stricter almost everywhere:
27 closed tasks would newly be blocked, and exactly one stops being blocked —
`release-1-3-docs-sweep`, which cites three test files that all exist and was
blocked only for lacking a magic word.

Known and filed rather than papered over: the parser credits an evidence line
only in the `AC-N: …` shape, so 61 of the tasks now called "no evidence" do cite
a real test, just differently. The gate's message names the working form.

**Correction.** This entry, and the code it describes, overstated how strong the
new gate was. Adversarial review of the fix demonstrated three ways to clear it
for free: the `::test_name` was split off and never looked at, so an invented
function on a real file passed; `tests/../scripts/gate_ac_check.py` escaped the
test tree and let the gate's own implementation count as a test; and a bare
basename resolved against any of the ~300 files under `tests/`. The docstring
had called a resolving citation "the only claim it cannot make cheaply" — it was
among the cheapest. Separately, the resolution used the process's current
directory, so the same task with the same genuine evidence was hard-blocked when
`task done` ran from a subdirectory, with a message that no `task log` line
could satisfy — precisely the false-positive-trains-the-bypass loop this release
condemns elsewhere, and the opt-out it points at is quieter than
`TAUSIK_SKIP_HOOKS` because it records no supervision event.

All three citation holes are now closed (the path must normalise to inside
`tests/`, and a named function must be defined in the file), and the root is
resolved from the project, not the cwd. The claim in the code has been narrowed
to what is actually true, with the things it still does not establish — that the
test ran, that it passed, that it relates to the task — written down rather than
implied. One more count moved with the fix: 33 historical closes would now be
blocked rather than 27, and the single case that stops being blocked is
unchanged. A related comment claiming "nothing reads a keyword list any more"
was false and has been corrected in place: the advisory level still accepts
`manual` / `/review` / `adversarial`, deliberately, which is exactly why the
hard gate does not.

### `tausik_verify` over MCP said which gates existed, not which ones ran

`verify passed=True … gates=['hadolint', 'pytest']` is what the agent saw. It
reads as "both gates passed". What it actually meant, on a task with no declared
`relevant_files`, was: pytest was SKIPPED for lack of scope, and the only thing
that executed was a Dockerfile linter — on a Python change. The run was still
recorded in `verification_runs` with exit 0 and signed with a receipt, and
`task done --ac-verified` accepts exactly such a cached green. The CLI printed
`[SKIP] pytest` the whole time; the two surfaces disagreed, and CLAUDE.md
directs the agent to the one that was lying.

This is the same defect `gate_verdict` was extracted to end — the release note
for that one says it "lived in five places". This handler was the sixth, and it
was missed because it renders gate NAMES rather than verdicts, so it never
contained the tell-tale `"PASS" if passed else "FAIL"` the sweep looked for.

The handler now shares the CLI's formatter, so both surfaces answer the same
thing, and adds what a bare verdict list still would not say: which gates did
not execute, and — when the scope is empty — the command that fixes it. Pinned
by tests that were confirmed failing against the old format, including one that
holds the line in the other direction: a run where everything really did pass
must NOT carry a skip note.

### The `rm` guard blocked nine safe cleanups and allowed five machine-wipes

`rm -rf /`, `rm -rf /*` and `rm -rf .` were literal substrings, and a substring
is wrong in both directions at once. Measured against the real hook:

* Blocked, and shouldn't have been: `rm -rf .venv`, `rm -rf .pytest_cache`,
  `rm -rf .mypy_cache`, `rm -rf .tausik/tmp`, `rm -rf ./build`,
  `rm -rf /tmp/scratch`, `rm -rf /var/tmp/x`, `rm -rf .git/hooks/tmp`,
  `rm -rf /home/u/proj/build` — every one of them merely *starts* like the root.
  The firewall blocked the investigation of this bug twice while it was being
  written, which is the same incident the file already records from 2026-07-18.
  There is no approval path on a block, so the only way past a false positive is
  `TAUSIK_SKIP_HOOKS` — each one trains the agent to switch supervision off.
* Allowed, and shouldn't have been: `rm -fr /`, `rm -r -f /`, `rm -f -r /`,
  `rm -rvf /`, `rm --recursive --force /`, and the same behind a prefix or a
  wrapper (`sudo rm -fr /`, `bash -c 'rm -fr /'`). One spelling was listed;
  every other spelling of the identical command went through.

Flags are now read as flags — any order, clustered or separate, short or long —
and operands as operands. What cannot be resolved — an operand that only becomes
root after expansion, like `$HOME` — is stated in the code as a residual instead
of left for the next person to discover.

**Correction.** This entry first claimed "the operand set is unchanged from what
the three substrings covered, so this is a repair and not a policy change". That
was false, and adversarial review of the fix measured it: the substrings matched
by PREFIX, so `rm -rf .*`, `rm -rf ./*`, `rm -rf ../*`, `rm -rf /.`, `rm -rf //`,
`rm -rf /./` and `rm -rf ./* ./.??*` had all been blocked by accident — and the
exact-match set stopped blocking every one of them. Closing five flag spellings
opened seven operand spellings, which is the trade this entry was written to end.
The operand is now normalised before it is judged (a trailing glob resolves to
the directory it empties, `//` and `/./` resolve to the root), so a spelling that
names the same tree gets the same verdict; all seven are blocked again and
pinned by tests. Two further corrections came out of the same review: `-f` is no
longer required, because every command this hook sees runs non-interactively and
`rm -r /` has no tty to prompt at, and `git rm -rf .` is no longer treated as a
filesystem wipe — it stages a deletion in the index and `git checkout` undoes it.
Whether `~` and a bare `*` belong in the set remains open and filed.

The other blocked phrases (`DROP TABLE`, `mkfs.`, `dd if=/dev/zero`) stay
substrings, because for those the substring genuinely is the meaning.

### `cat notes-df.txt` is no longer a destructive git command

One missing pair of parentheses. The firewall's git-clean pattern was built from
`-[a-zA-Z]*f[a-zA-Z]*d\b|-fd\b|-df\b`, and that top-level `|` split the entire
assembled regex — the last two branches ran with no command-start anchor, no
path prefix, and no `git` in front of them. Anything containing `-fd` or `-df`
was blocked: `ls -df`, `curl -fd 'a=b' url`, `mycmd --output-fd 3`, and a file
named `notes-df.txt`.

The release that introduced this constructor did it to stop
`mygit-helper push --force` from false-positiving, and reintroduced the same
illness one line below — which nothing caught, because the only git-clean test
was `git clean -fd`, a string that matches through either branch and so cannot
tell a working pattern from a broken one.

Grouping now happens inside the constructor rather than at each call site, so
the next pattern with an alternation in it cannot repeat this. Four negatives
and four positives are pinned, including the nested-wrapper form.

### A nested shell wrapper no longer hides a destructive git command

The three sessions above chased this one-liner through the WRITE gate. The
firewall — the hook that blocks `git push --force`, `git reset --hard` and
`rm -rf /` — was never checked against it. It turns out its own answer to "what
is this command really" held for one layer and broke at two:
`bash -c "sh -c 'git push --force origin main'"` was allowed, and so were the
`git reset --hard` and `git checkout -- .` forms.

Unquoting the payload was done by joining tokens back together, which strips
exactly one level of quotes. At two levels the inner apostrophe survived into
the scanned text, and the character in front of `git` was then `'` — not a line
start and not a shell separator, so the command-start anchor that makes
`mygit-helper push --force` safe made the real thing safe too. The `rm -rf /`
twin kept being blocked throughout, because those patterns are anchor-less
substrings; that asymmetry is why the hole survived a hook the project has
audited three times.

A shell `-c` payload is now re-scanned as the command line it is, reusing the
same bounded descent the write gate got. Widening the anchor to accept a quote
was the one-character fix and is deliberately not taken: it also blocks
`bash -c 'echo "git push --force"'`, where the quoted text really is data.
Descending keeps the token-vs-prose rule working one level down instead of
trading a missed command for a blocked echo — both directions are pinned by
tests.

### A command prefix no longer hides the shell wrapper behind it

Found by adversarially reviewing the FIX above rather than the code it replaced
(convention #276), minutes after that task closed. `env bash -c 'echo x > e.py'`
still yielded nothing: the shell test read the sub-command's first token, and
that token was `env`. The same one-line bypass of Rule 1, one level further out
— and `env bash -c` is no more obfuscation than `bash -c` was.

`env`, `sudo`, `doas`, `nohup`, `nice`, `ionice`, `stdbuf`, `timeout`, `command`
and `exec` are now stripped before the command is identified, along with their
flags, their `VAR=value` assignments, and the one numeric argument `timeout` and
`nice` take. A token that merely STARTS like a prefix (`environment.py`,
`timeout_test.sh`) is not one.

This also closes `sudo tee f`, which the residual boundary listed as an uncaught
"writer behind a wrapper" — the writer was never hidden by `tee`, only by the
word in front of it. The filesize gate then refused this task's own close, and
the seam was already obvious: `bash_cmd_norm.py` now holds "what command is this
really" (prefix stripping, shell-payload extraction, the nesting bound) and
`bash_write_parse.py` keeps "what does it write". Both bypasses this session
were a wrong answer to the FIRST question while every write detector was
correct. What remains genuinely out of reach is pinned by a test
instead of asserted in prose: a command assembled from STDIN (`xargs -I{} bash
-c`) and one executed on another host (`ssh host 'cmd'`), where this project's
paths mean nothing.

### The `bash -c` wrapper no longer hides a write from Rule 1

Filed one commit ago as its own hole, closed here. `bash -c 'echo x >
scripts/foo.py'` yielded no write target at all: the redirection sits inside a
single quoted argument, and nothing parsed into the payload. "No code without a
task" (Rule 1) and the scope ACL (Rule 2) were therefore bypassable by a
one-liner of the same class Decision #162 closed for heredocs — while the
documented residual claimed the gate had raised the cost of evasion to "must
actively obfuscate". `bash -c` is an everyday form.

`write_targets` now descends into the `-c` payload of `bash`, `sh`, `zsh`,
`dash`, `ksh`, `ash` and `busybox`, combined short flags (`-lc`, `-ec`)
included, bounded by a named `_MAX_WRAPPER_DEPTH` so a nested chain terminates
by decision rather than by RecursionError. A payload that fails to tokenize
degrades the WHOLE answer to `regex_fallback`: handing back the more confident
of two readings is the wrong one for a caller that fails closed on uncertainty.

Negatives are pinned too, because a stricter parser earns its strictness only if
it stays quiet on the ordinary: `bash script.sh` (no `-c` — the argument is a
file to run), `bash --color=auto -c 'pytest -q'` (a long option is not a
short-flag cluster), `echo 'bash -c "x > y"'` (a quoted mention is not a write).

The test that pinned the OLD behaviour was written deliberately one task earlier,
so that teaching the parser to recurse would announce itself rather than pass
silently. It did, and is inverted here.

### Fixed: the memory-route hook blocked a mere mention of a sink path

Same-session defect of the change above, found by dogfooding: the hook refused a
diagnostic `python -c` that only QUOTED `.cursor/rules/a.mdc`, naming the garbage
"path" `.cursor/rules/a.mdc/"',`. The cause is a shared parser with two
consumers that have opposite costs of error. When a command does not tokenize,
`bash_write_parse` falls back to a regex that deliberately over-detects. For
QG-0 that is cheap — the worst case asks for a task the write needed anyway. For
a guard whose block accuses the agent of leaking project knowledge, and whose
only exits are a `confirm: cross-project` marker that would be a lie or a
permanent config exemption for a one-off command, a false positive costs more
than the writes it catches: it teaches the escape hatch.

The parser now STATES which reading produced its answer
(`write_targets_with_confidence` → `parsed` / `regex_fallback`); `write_targets`
is unchanged, so QG-0's over-detecting contract holds bit-for-bit. The
memory-route hook declines to judge a fallback answer and records
`fail_open_unparseable_bash` — the gap is countable, not silent, and the in-tree
half of the deny-list is judged again by the gate and pre-commit before anything
can be committed.

### The `bash -c` wrapper defeats the Bash write gate — the boundary was overstated

Found while probing the above. `bash -c 'echo x > scripts/foo.py'` yields NO
write target: the redirection lives inside a single quoted argument and nothing
parses into an interpreter payload. So "no code without a task" (Rule 1) and the
scope ACL (Rule 2) are bypassed by a one-liner of the very class Decision #162
closed for heredocs. The documented residual claimed the gate raised the cost of
evasion to "must actively obfuscate"; `bash -c` is an everyday form, not
obfuscation. `docs/ru/agent-contract.md` now says so, and the hole is filed as
its own task rather than left under a reassuring description. A test pins the
current behaviour so the day someone teaches the parser to recurse, it says what
changed.

### Fixed: the drift gate could not see the hooks it exists to protect

`bootstrap_drift` blocks a close when a source edit did not reach the deployed
copy that actually runs. Its comparator listed `scripts/` with a non-recursive
`os.listdir` filtered to `*.py`, while `bootstrap_copy.copy_dir` deploys the
whole tree — so `scripts/hooks/**` and `scripts/providers/**` were shipped and
never compared. Session #128 had already made that load-bearing: `_common.py`
imports `hook_supervision.py`, so a half-landed deploy takes down EVERY hook
with a module-level `ImportError` on every single tool call — and the one gate
whose entire job is "the edit did not reach the copy that runs" would have
reported clean through it.

The comparator now walks `scripts/` recursively and judges every file `copy_dir`
would deploy, minus exactly what `copy_dir` skips (`__pycache__/`, `.git/`,
`*.pyc`). Not `*.py`: a comparator applying a narrower rule than the copier it
checks is the same second-copy-of-the-rule defect one layer down, and
`scripts/hooks/pre-commit` — a shell file — is a deploy target too. Files that
exist only in the profile (`vendor_seo/`, leftover `.pyc`) are still not drift;
the question is whether a source edit failed to land, and an extra file in the
destination is not an answer to it.

The existing test asserting that a stale non-`.py` file must NOT be reported was
inverted rather than deleted — it had locked the narrower rule in. A new test
ties the comparator's ignore rules to `copy_dir` behaviourally: it runs the real
copier into a temp target and asserts the comparator's file set is exactly what
landed, so a future change to the copier fails the build instead of silently
shrinking the check. Five of the new tests fail against the previous
implementation.

### Project knowledge stops leaking into other agents' memory

TAUSIK's whole claim is that what an agent learns about a project lands in
`.tausik/tausik.db`, so the *next* agent inherits it. Every host ships its own
memory instead — Claude `~/.claude/**/memory/`, Cursor `.cursor/rules/`, Copilot
`.github/copilot-instructions.md`, aider a chat-history file — and an agent
writing there is not misbehaving, it is doing what its host taught it. The
knowledge is simply gone the moment the project is opened in a different tool.
One narrow guard existed (Claude's home memory, Write/Edit only), which meant
the rule was enforced for exactly one host and one vector.

- **`scripts/memory_sinks.py`** — one deny-list, consumed by all three layers,
  because a rule spelled twice is a rule that drifts (convention #266). Nine
  in-tree sinks plus the home one; a `**`-aware segment glob; `sinks_from_config`
  so a project can *extend* the list (`gates.memory_route.extra_sinks`) or exempt
  a path (`allow`) — mechanism generic, policy configured (convention #277).
  Extra sinks append, never replace: naming your in-house agent's memory file
  must not switch off the ones the framework ships.
- **`memory_route` gate (blocking, `task-done` + `commit`)** — IDE-agnostic, so
  it catches a hand edit, a script, and a host TAUSIK has never heard of. Reads
  `git status --porcelain --untracked-files=all`: with git's *default* mode a
  brand-new `.cursor/rules/` collapses to a single `.cursor/` entry that matches
  no pattern, so the first write into a fresh sink directory — the likeliest
  shape of the defect — would have passed. Not a git repo, or no git: inert, and
  says so. Inside a repo where git failed: fail-closed, because the answer was
  computable and we did not get it.
- **`scripts/hooks/pre-commit`** calls the gate before mypy, honouring the same
  `gates.memory_route.enabled` switch — a project that turned the gate off must
  not be blocked by a second, independent reader.
- **PreToolUse hook now covers `Bash`.** `cat >> ~/.claude/.../memory/x.md <<EOF`
  wrote exactly what the Write path refused; the parse reuses
  `bash_write_parse.write_targets`, the same parser QG-0 uses for the identical
  hole (Decision #162).
- **Litmus block in the generated rule files** (CLAUDE.md / AGENTS.md /
  `.cursorrules` / QWEN.md, every tier). This is the only layer that reaches a
  host whose memory is cloud-side and writes no file for any gate to see — the
  honest limit, stated rather than implied.

What is deliberately **not** on the deny-list: `.cursorrules`, `.windsurfrules`,
`CLAUDE.md`, `AGENTS.md`, `QWEN.md` and the `.cursor/` `.qwen/` `.kilo/`
`.opencode/` trees. `bootstrap --ide all` writes every one of them, so listing
them would make the framework block its own deployment — and the failure would
be *invisible here* (this repo gitignores them) while firing in every project
that tracks them. The carve-out is derived from `ide_utils.IDE_REGISTRY` rather
than restated, and a test asserts no sink pattern can ever swallow one.
`.cursor/rules/**` remains foreign despite its TAUSIK-owned parent: an explicit
sink pattern wins over the carve-out, stated as precedence instead of left to
the order of two `if`s.

Also: `uncommitted_changes` gained an `untracked=` parameter defaulting to git's
`normal` — widening a shared query rewrites the question for every existing
caller (memory #286), so the new mode is opt-in and the changelog / fileless-close
callers are untouched. And the filesize gate refused this task's own close, so
`path_glob.py` (the `**` matcher and normalisation — no knowledge of memory,
agents or policy) and `bootstrap_templates_tiers.py` (the `minimal` / `full`
bodies, selected by `context_tier`) were extracted along their existing seams,
relocation only.

### Fixed: gate metrics were blind to a post-scope gate that had never fired

Follow-on defect of the gate registry, found while verifying it end-to-end.
`gate_activity_summary` built its known-gate set from `get_gates_for_trigger`,
which the registry work deliberately made exclude post-scope gates. Rows those
gates had already written still appeared — they come from the table — but a
post-scope gate with *no* rows vanished from the report entirely. That is the
one reading convention #226 exists to forbid: "this gate guarding every close
has never once fired" is the most useful thing the table can say, and it was
being rendered as silence. The known set now spans both phases, and the
registry half is gathered outside the config `try` — it is static in memory, so
an unreadable config must not be able to blank the part that never needed it.

### One gate registry — the QG-2 gates the check could not prove had run

Declaring a gate meant landing in four unconnected places: metadata in
`default_gates.UNIVERSAL_GATES`, dispatch in a chain of `if name == ...` in
`gate_runner`, "is it built-in?" *inferred* from `command is None` in
`gate_command_policy`, and — for the two gates that run after the scoped
pipeline — a hardcoded call in `service_gates`. `verify_first` and `changelog`
lived in the fourth place only, and the consequences were not cosmetic: `gates
status` did not list them, `gates enable/disable` could not reach them, and they
wrote no `gate_runs` row — so nothing downstream could prove that the QG-2 gate
guarding every close had actually run. A framework that asks every task for
evidence kept none about its own most load-bearing check.

- **`scripts/gate_registry.py`** — one `GateSpec(name, phase, default_config,
  impl)` per built-in gate; `phase` is `scoped` (judges the task's files,
  `(gate, files) -> (passed, output)`) or `post_scope` (takes the close context
  and edits the QG-2 report). Implementations are addressed by dotted string and
  resolved lazily — an eager import would close a `default_gates` →
  `gate_bootstrap_drift` → `project_config` cycle. Post-scope gates use a
  `svc:method` form so the binding stays late, which is what keeps
  `GatesMixin` overrides and the pytest Verify-First shim working.
- **`default_gates`** now projects the registry instead of holding a literal;
  `UNIVERSAL_GATES` is byte-identical to what it replaced, asserted against a
  hand-frozen snapshot rather than against the registry itself.
- **`gate_runner`** dispatches through `GATE_REGISTRY[name].impl`; the `if/elif`
  chain is gone and a gate outside the registry is a command gate by
  construction. `run_tdd_order_gate` moved to `gate_tdd_order.py` (re-exported).
- **`gate_post_scope.py`** runs the post-scope phase in registry order
  (Verify-First, then changelog, so both blocking reasons reach the agent at
  once), honours `enabled`, applies the fileless-close exemption declared on the
  spec, and writes **one `gate_runs` row per gate** with a NULL
  `verification_run_id` — these belong to a close, not to a verify run. The rows
  commit immediately: a gate that ran and blocked is precisely the event worth
  recording, and losing it because the close then failed would erase the
  evidence in the cases that matter most. If the rows cannot be written the
  close is blocked, not crashed (convention #221).
- **`gates status` no longer lies.** Post-scope gates are listed with their real
  on/off state, including the changelog gate, whose switch is the legacy
  `task_done.changelog_gate.enabled`. `config_trust` already guards
  `gates.*.enabled`, so a repository-travelling `.tausik/config.json` can tighten
  these gates but not turn one off; when a user/managed tier does turn off a gate
  that ships ON, the skip is a countable supervision-bypass event. Turning off a
  gate that ships OFF (the opt-in changelog gate) is not a bypass and is not
  reported as one.
- **"Built-in" is declared, not inferred.** `ruff` is in the registry *and* is a
  command gate, so vendored-path and wrapper-dropping overrides stay legal;
  `filesize` and the post-scope gates take no command override. Previously both
  answers came from `command is None`, true of the current built-ins only by
  coincidence of their configs.
- **A silent PASS removed on the way past.** A gate with no implementation and no
  command reached `run_command_gate`, which answered `"No command configured."`
  as a *pass* — a gate that never executed reporting success, the exact reading
  `gate_verdict` exists to forbid. It is a SKIP with a warning naming the fix.

One defect was found by the suite during the work and fixed rather than tested
around: routing the changelog gate's on/off through the registry briefly gave
that question two answers (`gate_post_scope` asking one reader, the gate itself
asking another) which could disagree in both directions — the same defect class
this task removes, one layer down. `_read_changelog_gate_config` now takes an
optional preloaded config and is the single reader. A malformed policy block
deliberately resolves to ON, so the gate still runs and fails closed on it.

### AGENTS.md dynamic sync finished — no more "marker not found" on every update-claudemd

The AGENTS.md always-on layer (Linux-Foundation-governed, read by 30+ tools) was
wired but abandoned: `resolve_sibling_targets` mirrors the regenerated DYNAMIC
section into an AGENTS.md sibling, and the bootstrap template already ships the
`DYNAMIC:START/END` markers — but this repo's own AGENTS.md predated them and is
preserved-if-exists, so every `update-claudemd` printed `marker not found in
AGENTS.md — skipped` and left the file stale. The markers are now present in the
live file, so the sibling write lands and the warning is gone.

The source-of-truth question is settled and recorded (decision): the static body
of both files comes from one place — `bootstrap_templates.build_full_body` — with
CLAUDE.md and AGENTS.md as peer renderings for different audiences (Claude vs the
30+ other tools), and the dynamic section is generated from the TAUSIK DB and
mirrored to both. The industry "AGENTS.md is truth, thin CLAUDE.md points at it"
pattern was deliberately not adopted: each host reads its own file and the sync
is already solved by the shared template, so a pointer would add indirection for
no gain. A regression test now asserts both the live files and every context-tier
of the template carry the markers. CLAUDE.md stays compact (95 lines, well under
the ~200-line every-session-load guideline).

### Cost telemetry now works on any model, not only Claude — a project can price its own

The Opus-4.8 fix closed the silent $0.00 for one family and left it open for
every other: a project running GLM or a custom model still recorded `cost_usd =
0.00` for every event, because the built-in table prices only Claude tiers and
nothing else was consulted. That is the same defect the batch fixes for Claude,
surviving one family over — the "works on any model" line was true for IDE and
shell but only Claude for the meter.

The config key `llm_pricing_usd_per_million` — normalized on every config load
and then read by nothing, an abstraction with no consumer — is now that
consumer. `get_pricing` consults it whenever the built-in table misses, applying
the flat per-1M rate to input and output alike, so a project states its own
tariff in `.tausik/config.json` and its telemetry stops reading zero. The same
override would have priced `claude-opus-4-8` before the table caught up, so it
also feeds `models_missing_pricing`: a Claude id a project prices through the
override counts as covered. Anthropic rates are never invented for a non-Claude
family — the project declares the number or the meter stays honestly unknown.

And unknown is now audible. The DB column is `cost_usd REAL NOT NULL`, so the
stored cost stays 0.0; what changed is that an unpriced, non-empty model warns
once per id on stderr (`unknown is not free`, ASCII so it survives a non-UTF-8
hook pipe) instead of recording a confident zero in silence. The per-event
"unknown model" line the usage hook printed — which fired on every call and did
not consult the override — is gone; the once-per-id, override-aware warning in
`calculate_cost_usd` owns it now. An explicit `0.0` override is honoured (a
genuinely free local model) and distinct from unpriced. Documented in
`docs/en/model-providers.md`.

### The `.claude` literal tail in the engine: a metrics hook that worked by accident, an orphan scan blind to four IDEs

The doctor hardening closed the hot path and left a lint standing over an
explicit remainder; this closes three of those exemptions. `session_metrics`'s
DB writer computed its project root with `dirname×3(__file__)`, which actually
lands on the *profile* dir (`…/.claude`), so its first candidate
`<profile>/.claude/scripts/project.py` doubled the profile segment and never
existed — the record only ever succeeded through the `scripts/` fallback, and
worse, it ran the subprocess with `cwd=<profile>`, so `project.py` resolved
`.tausik/` under the profile instead of the project root: a silent DB-record
miss dressed as success. It now self-locates and runs with the true root as
cwd. The orphan-file audit hardcoded ignore-globs for `.claude`/`.cursor`/
`.qwen` — 3 of 7 profiles — so on the other IDEs the deployed engine copy was
either walked or reported as an orphan; the globs now come from
`ide_utils.all_profile_dirs()`.

The self-location both `session_start` and `session_metrics` need now lives
once in `hooks/_common.profile_dir` (the "resolve the project root" logic that
`_common`'s own comment warned had drifted across four copies); `session_start`
delegates to it rather than keeping a private fifth copy. The
`project_cli_extra` CLAUDE.md fallback was left deliberately unchanged — its
main path already resolves the onboarding file through `ide_utils`, and
generalising the remaining literal to a `get_rules_file` would change behaviour
for `AGENTS.md`/`.cursorrules`; its lint exemption is re-labelled a documented
fallback rather than deferred work. Three `_ALLOWED` exemptions updated
accordingly, with fail-then-pass coverage for the deployed/source/missing
layouts of the metrics writer.

### Adversarial review of the batch's own guards closed five holes in them

The three fixes above each shipped a mechanism meant to make its defect
mechanically unrepeatable. An adversarial pass over those mechanisms — the
discipline convention #276 names, review the fixes, not only the original —
found that two of the guards judged their own copy of the data (convention
#266), the exact failure the batch criticises elsewhere.

The pricing-coverage guard read the built-in `DEFAULT_FAMILIES`, never
`model_profiles.load_families(config)` — so a project that repointed a rank at
an unpriced Claude id through the documented config surface, or set a per-phase
`model_routing` override, kept metering it at $0.00 with the guard green. It now
reads the effective config and scans the routing overrides, with fail-then-pass
tests for both. The `.claude`-literal lint anchored its regex on the opening
quote, so `.claude` anywhere but the start of a string literal
(`"harness/.claude/foo"`) slipped past the very lint built to forbid hardcoded
profile paths; the regex now matches the segment wherever it sits, which
immediately surfaced three legitimate `~/.claude` HOME references (Claude
Code's own auto-memory, not a project profile) now exempt on the merits.

Three narrower holes closed too. `service_roles` had grown a `project_dir`
parameter to resolve deployed role profiles IDE-independently, but the caller
never passed it, so it still read `os.getcwd()` — an MCP server run from
elsewhere missed a profile that existed; the project directory is now derived
from the backend's own db path and threaded through, and only from the
canonical `<root>/.tausik/` layout so a non-standard db falls back rather than
guesses. `session_start._profile_dir()` located its profile by testing for a
`scripts/` directory two levels up — which the project ROOT also has, so a hook
run from source returned the project root as its "profile" and failed safe only
because that root happened to lack `mcp/`; it now requires a positive marker a
real profile carries. And the phantom-`/skill` lint scanned only hooks and
SKILL.md; it now covers all of `scripts/`, restricted via an AST pass to the
strings a user actually reads (print arguments and raised-exception messages) so
docstrings, comments, and URL literals like a Notion `/search` endpoint don't
register as false phantoms.

### Block messages that pointed nowhere: a phantom command and a shell-wrong CLI

The most-read message in the framework — `task_gate`, fired on every Write
without an active task — told the reader to `use /go`. There is no `/go` skill;
there never was. Following the framework's single most-common instruction did
nothing. The same phantom was in three more places, and the English message
otherwise offered only a Russian phrase as the way forward, to an audience the
README addresses in English. All four now point at commands that exist (`/plan`
to create a task, `tausik task start <slug>` to resume one), and a lint fails
if any `/skill` a hook or SKILL.md names is absent from `harness/skills/` — it
immediately found three more phantoms nobody had reported (`/go` in a fourth
hook, `/metrics` and `/next` in the start skill).

Every remediation line spelled the CLI `.tausik/tausik`, which is not
universally runnable on Windows. The product audit blamed a missing `.cmd`
extension; measuring it showed that was wrong — `PATHEXT` resolves the
extension on its own. The **separator** decides: `cmd.exe` rejects
`.tausik/tausik`, Git Bash rejects `.tausik\tausik` (backslash is an escape),
and PowerShell accepts either. No single spelling works everywhere, so the
choice is per-shell, not per-OS — a Windows developer in Git Bash needs the
opposite of one in cmd. `cli_invocation()` picks the form from the shell, and
the gate remediation lines use it.

Separately, `bash_firewall`'s `git reset --hard` warning told the reader to
"ask the user for explicit confirmation first" — describing an approval path
the hook never had. The user says yes and the block fires identically. It now
names the escape that exists: a non-destructive equivalent, or a single
`TAUSIK_SKIP_HOOKS=1`-scoped re-run that is recorded as a supervision bypass.

### `tausik doctor` failed healthy projects on six of seven supported IDEs

`ide_utils` has been a complete IDE abstraction for a long time — seven
profiles, directory and skills resolution — with almost no callers, while
`.claude` stayed spelled out as a literal across the engine. The health check
looked for `.claude/mcp/project/server.py` and `.claude/skills/`, so on a
Cursor, Qwen, Kilo or OpenCode install — where bootstrap deposits `.cursor/`,
`.qwen/`, `.kilo/` — a correctly installed project reported FAIL and exited 1,
taking any CI that ran it down with it. A health check that fails healthy
projects is worse than none: it teaches people to ignore the one command whose
whole job is being believed.

`doctor` now resolves the profile it is judging and says which one, so its
output names the directory it actually inspected rather than always claiming
`.claude`. When the detected profile is absent but another is deployed, the
message says so — "detected claude, but a cursor profile is deployed" beats
"re-run bootstrap", which is advice that repeats the same result. Role
profiles resolve the same way, and no longer read from the process working
directory either.

Two file scanners had hand-written skip lists naming `.claude` (one also
`.cursor`), so on the other profiles they walked a deployed copy of the engine
— roughly 300 generated files — treating it as project source. Both now derive
the set from the registry, so a profile added later is skipped the day it is
added.

Hooks could not use the abstraction at all: `ide_utils` lives in the very
directory a hook is trying to locate, so importing it presupposes the answer.
They locate themselves instead — a hook deployed at
`<profile>/scripts/hooks/x.py` knows its profile two levels up. That fixed a
silent one: the automatic skill rebuild resolved `.claude/scripts` on every
install, so on Qwen it imported nothing and did nothing, and the surrounding
`try/except` swallowed the failure. The same read found a dead loop variable in
the RAG-server probe, which tested the identical `.claude` path on both
iterations.

The literal is now linted. `tests/test_doctor_multi_ide.py` fails on a new
`.claude` in `scripts/`, every remaining exemption is listed with the reason it
is legitimate, and a second test fails if an exemption goes stale — an
exemption for a file that no longer contains the literal would silently license
the next one. The four genuinely-remaining cases are tracked as
`engine-claude-literals-followup`.

### Cost telemetry reported $0.00 for the model this project runs on

An architecture audit found `claude-opus-4-8` missing from the LLM price table
while `model_profiles` already routed the `opus` rank to it. `get_pricing`
returned `None`, `calculate_cost_usd` returned `0.0`, and `tausik metrics
--cost` reported a confident zero for every session — including this
repository's own. A silent zero in a cost meter is not a missing feature; it is
a wrong answer wearing the costume of a right one, which is the exact defect
class this release is about.

Verifying the fix turned up two more errors in the same table. Opus was carried
at $15/$75 against a published $5/$25 — a threefold overstatement on every Opus
session ever recorded — and Haiku 4.5 at $0.80/$4.00 against $1.00/$5.00. The
`[1m]` rows charged a 2× "long-context premium" extrapolated from a superseded
Sonnet tier; no such premium exists on the current Opus and Sonnet tiers, where
1M **is** the standard window at the standard rate. Those rows now sit at
parity with their base. Sonnet 5 and Fable 5 were added; the table records the
date it was verified against published pricing.

The existing tests had asserted all of this wrongly — $15/$75, the phantom
premium — so the suite stayed green over a meter that was wrong in both
directions and blind to the default model. Correcting expectations is not the
fix, though: a table maintained by remembering is a table that drifts. Coverage
is now mechanical — `models_missing_pricing()` reads the three tables that
actually decide which model runs (`model_profiles`, the routing matrix, the
delegation default) and a test fails if any Claude id among them has no price.
Adding a model to routing without pricing it now breaks the build instead of
quietly zeroing the meter. Non-Claude families are excluded deliberately and
say so: GLM is not billed at Anthropic rates, and an invented price would be
worse than an absent one.

### The changelog gate now reads what was written, not whether bytes moved

An adversarial review of the gate shipped hours earlier found it proving the
wrong thing. Its evidence was `git status --porcelain` — "did these bytes
change" — which a single appended blank line satisfies. A close could append
whitespace to both changelog files, pass the gate, and have "Changelog gate:
verified" written into its own task notes: compliance theatre, with convention
#275 unmet and the journal asserting otherwise. The proof required is now
content: at least one ADDED line with characters on it, per configured file.

A product review of the same batch caught the complementary defect from the
other side. The gate demanded an *uncommitted* diff, while the framework's own
`/ship` skill commits at step 7 and closes the task at step 8 — so under the
canonical close path the changelog diff was always already committed, the gate
always blocked, and `--no-changelog` was the only way through. A rule whose
sole passable route is its own bypass teaches the bypass. Commits made during
the task (the window opens at `started_at`) now count, alongside working-tree
and staged edits and brand-new untracked changelog files. The time window is
weaker than "this task wrote it" — in a release-accumulation workflow another
task's commit inside the window can satisfy it — and that is the deliberate
trade against a gate nobody can legitimately pass.

Two more corrections in the same gate. A malformed `task_done.changelog_gate`
block — `{"enable": true}`, a bare string where a list belongs, an unreadable
config — used to fail OPEN, justified in a docstring by a `tausik doctor` check
that does not exist; a typo therefore retired the policy silently while the
project believed it enforced. A policy that cannot be read is unknown, not off,
so it now fails closed and names the defect; an ABSENT block still means a
quiet, deliberate opt-out. And the gate's config is read for the project the
service speaks for, not from the process working directory.

### Git worktrees are repositories again

`verify_git_diff` tested for a `.git` DIRECTORY. In a linked worktree or a
submodule `.git` is a FILE, so both were classified "not a repository" —
which every consumer treats as unverifiable and then fails closed. An agent
working in a git worktree, the standard isolation for parallel agents and
something this harness ships tooling for, could therefore neither close a
fileless task nor pass the changelog gate at all. Existence, not file type, is
the question.

### Receipt commands stop resolving keys from the working directory

`tausik receipt show` and `receipt export` looked the project public key up in
`os.getcwd()`, so running either from a subdirectory reported a validly-signed
receipt as `UNVERIFIABLE` — the same CWD-dependence closed on the signing side
in this batch, still open on the reading side, and claimed fixed by the entry
below. Both now resolve the root from the service handle. Relatedly, the
signing-failure warning added earlier treated a CORRUPTED key as no key at all
(`load_public` raises either way), printing the benign "no project key" notice
for a real failure — the exact silent degradation that change existed to end.
Key PRESENCE now decides: a key file that exists means the project expects
signed receipts, and a receipt that then fails to appear is reported.

The four private spellings of "resolve the project root from the handle, never
from the cwd" are now one (`project_root.root_from_service`), which returns
`None` rather than guessing when there is no handle — a gate fails closed on
that, a read-only presentation command may degrade to the cwd, and the choice
stays with the caller.

### Receipt signing resolves the project root, not the working directory

An adversarial review of this batch caught a defect in the signing-observability
change: the CLI's key-presence check resolved the project from the database path
(correct, CWD-independent), but the actual signing call still used `project_dir='.'`
— the process working directory. Running `tausik verify` or `task done` from a
**subdirectory** therefore signed against a directory with no key: emission
silently produced no receipt, and the new observability code then printed a
*false* `Receipt: WARNING — signing failed` and logged a spurious
`receipt_sign_failed` event, because the two paths were looking in different
places. Signing now derives the project root from the database connection's own
file (`<root>/.tausik/tausik.db`), matching the key check exactly — which also
fixes the pre-existing latent bug where signing from a subdirectory produced no
receipt at all. An unreadable DB path falls back to the working directory,
best-effort. Separately, the continuous-changelog gate's `enabled` flag is now
read as a real boolean (`is True`), so a hand-edited `"enabled": "false"` string
no longer coerces to on via `bool("false")`.

### README narrative matches the code: a discipline rail, not a firewall

The README claimed "hard gates it physically cannot skip" and led with
"enforcement" — while the code's own docstrings were already honest
(`git_push_gate.py`: "a discipline rail, not a malicious-agent firewall";
`renar_conformance.py`: a signal it marks vacuously true). An architecture
review had tabulated the trivial bypasses — a Bash write (since closed),
declaring `complexity=simple`, narrowing `relevant_files`, self-recording an L3
review, reading the in-tree signing key — each of which "physically cannot
skip" contradicts. The narrative is now precise, not retreating: TAUSIK is a
**discipline rail with tamper-evidence against outside edits**, whose threat
model is silent drift by an honest agent, not a determined one working around
the rail. "The difference is one word" changed from *enforcement* to
*evidence*; both README mirrors and `architecture.md` were aligned, and a grep
for the overclaiming phrases now returns nothing. The framing matters legally,
not just editorially — EU AI Act logging obligations for high-risk systems
(August 2026) make an accurate claim load-bearing.

### Dropped: the Plotly visual cost dashboard (stdlib principle holds)

The long-deferred idea of a `tausik dashboard` — a Plotly/Dash mini-server
plotting tokens, cost, dead-end rate and throughput — is closed as won't-do
(`tausik decide` #164). It contradicts the project's declared Python-stdlib
stack and repeats the reasoning of an earlier dead end (#27, rejecting
ChromaDB): a heavy external dependency is not worth a visual alternative to a
capability that already exists. The text-mode `tausik metrics --cost` covers
the cost-observability need. An opt-in `extras` install was also declined —
even an isolated dependency carries CI and maintenance weight for a duplicate
of a working feature.

### Receipt signing: honest boundary, and failures are no longer silent

The signing key lives at `.tausik/keys/project.key` inside the working tree —
the same tree the agent whose work it signs can read (`0600` is best-effort on
POSIX, a no-op on Windows). The docs now state precisely what a signature
proves: **tamper-evidence against EXTERNAL edits** to `tausik.db` and the event
anchor, but **NOT attestation against the agent**, who can read the seed and
produce a signature the key accepts. The wording is deliberate — logging
obligations under the EU AI Act (high-risk systems, August 2026) make the claim
legally load-bearing. Relocating the key outside the agent's zone (managed path,
OS keychain, separate signer) is a cross-platform key-custody design of its own
and is deferred on the record (`tausik decide` #163); naming the boundary
honestly is the immediate integrity win.

Separately, a signing **failure** used to be invisible: `emit_signed_receipt`
returned an error status that the CLI dropped, so a project whose signing
silently broke printed the SAME "no project key" line as one that never had a
key — degrading to unsigned runs indistinguishably. `tausik verify` now tells
the two apart: a configured key that failed to sign prints a visible
`Receipt: WARNING` and records a countable `receipt_sign_failed` event, while a
genuinely absent key keeps its benign notice.

### Continuous CHANGELOG is now a gate, not a convention

Decision #161 asked every 1.8 task to update `CHANGELOG.md` and its Russian
mirror `CHANGELOG.ru.md` at close (convention #275). That discipline lived only
as a line in each task's acceptance criteria — a reviewer could see it skipped,
but nothing stopped the skip. A new QG-2 gate makes it mechanical: at `task
done`, git must show uncommitted changes in every configured changelog file, or
the close is blocked, naming the missing files and the escape flag.

Mechanism is generic, policy is configured. TAUSIK is a framework other projects
bootstrap; a hardcoded "a Russian and an English changelog must both change"
would permanently block any project that keeps no changelog, or one language
only. So the requirement reads from `config.task_done.changelog_gate`
(`{enabled, files}`), disabled by default; TAUSIK's own config turns it on with
both files. Fail-closed by the whole-tree-proof pattern (#157): an unavailable
git or a service that cannot resolve its own project directory blocks rather
than passes — a claim git cannot back never closes a task. Honest exceptions
(docs, cleanup, measurement) close with `task done --no-changelog`, which skips
the check and records a countable `bypass_changelog_gate` supervision event —
no silent bypass. Fileless closes (`--no-file-changes`) never reach the gate.

### Bash file writes no longer bypass QG-0 and scope

`task_gate` (no code without a task) and `scope_write_gate` (SENAR Rule 2 ACL)
were wired only to `Write|Edit`. A shell write — a `cat > f <<EOF` heredoc,
`sed -i`, `tee`, `dd of=`, `python -c "open(f,'w')"` — reached neither, so the
exact content the Write tool refuses landed unchecked. Demonstrated live twice
(#117, #118): the same file, blocked via Write, created via a heredoc without a
single objection. The gates held on the family of write tools, not on the act of
writing.

A new `bash_write_gate` (matcher `Bash`) parses the command for its write
targets — redirections including heredoc, `tee`, `dd of=`, `sed -i`, `cp`/`mv`,
`truncate`, `touch`, and a literal `open(…,'w')` in a `python`/`perl`/`ruby -c`
payload — resolves each against the project root, and applies the SAME QG-0 +
scope verdict the Write gates apply, by importing their functions rather than
copying the rule (a second copy would drift from the first). Targets outside the
tree — scratchpad, `/tmp`, `/dev/null`, another repository — stay allowed, as
they are for Write. `MultiEdit` and `NotebookEdit`, also previously ungated by
QG-0, were added to the write matchers.

The boundary is stated, not hidden. Obfuscated writes are not caught — a path
built in a shell variable, `base64 -d | sh`, a wrapper-hidden `sudo tee`,
arbitrary interpreter code beyond a literal `open(…)` — because shell is
Turing-complete and a total gate is impossible. The gate raises the cost of a
bypass from "a trivial heredoc" to "deliberate obfuscation" and names what
remains (`docs/ru/agent-contract.md`, `docs/ru/hooks-events.md`). A gate that
pretended to total coverage would be worse than one that is honest about its
edge.

Separately, the scope gate's adoption rule was tightened. A co-active task that
declared no scope no longer nullifies a sibling's ACL: enforcement begins as soon
as ANY active task declares a scope, and the legacy "undeclared = unrestricted"
freedom applies only when nobody has declared one at all. Keeping one undeclared
task active had been a standing escape hatch out of scope enforcement; it is
closed, while the conservative early-adoption case (no scopes anywhere) is left
untouched.

### The deprecation gate stopped failing on honest text

The gate's own docstring states the principle: documentation *may* mention the
deprecated primitives, code may not *use* them. Half the file kept that promise
and half did not.

The AST half was fine. The other half searched for protocol-level strings by
plain substring match over raw source lines, so an honest comment — `# older
clients still send "roots/list" over the wire; we ignore it` — failed the build.
That is the exact outcome the docstring warns about: a gate that fails on its
own documentation gets switched off, and a switched-off gate is worse than an
absent one because it still looks like protection. Separately, the AST half
flagged bare names as well as attribute access, so an unrelated local function
called `list_roots` — a plausible name generally, and "roots" appears in an MCP
server for other reasons too — failed with a message about a deprecated API.

The promise was kept and the code brought under it, rather than the reverse.
Protocol strings are now looked for only where they actually participate in the
code: comments never enter the AST at all, and docstrings are excluded by
identity. Attribute access is the only usage form matched.

Narrowing to attribute access would have opened a hole the size of the one it
closed — `from mcp.server.session import list_roots` contains no attribute
access — so direct imports are matched by their own branch. Both sides of both
defects are tested: a comment and a docstring stay silent, a literal in code
(including inside an f-string) still fires, a bare name stays silent, attribute
access and direct import still fire. Checking that false positives went away
without checking that real violations still fire would have traded a noisy gate
for a blind one.

### A stack that declares file extensions must have a gate that can run

Flutter was declared a stack — extensions, detection signature, a guide with a
review checklist — and not one gate in the registry named it. The same was true
of Swift. For a task touching `.dart` or `.swift` files nothing ran: no linter,
no compiler, no tests, only the universal built-ins. `task done` reported green.

That is worse than a missing feature. It is a green verdict that means nothing,
and it is indistinguishable from a real one: when a gate is skipped it at least
says so, but a gate that was never declared leaves no trace at all in the
output. Nothing in the report tells you whether the code was checked or whether
there was nothing to check it with.

The measurement, not the impression: of twenty-five built-in stacks, twelve
declare no `gates` key — but nine of those are covered by a parent and the
coverage is legitimate. Django, FastAPI and Flask are caught by `pytest` from
python; React, Next, Nuxt, Vue and Svelte by eslint/tsc from javascript and
typescript; Laravel by the php gates; Blade through the `.blade.php` mapping.
Exactly two were orphans, and both are now declared: `dart analyze`,
`dart format`, `flutter test` for Flutter; `swift build`, `swiftlint`,
`swift test` for Swift. All ship disabled by default — the build machine has
neither toolchain, and a gate enabled by default would fail for everyone.

The point, however, is not the two files. Adding them does nothing to stop stack
twenty-six arriving with the same hole, so the rule is now mechanical: a stack
declaring `extensions` must have at least one gate reachable for its files.
Reachability is computed by the production code path rather than a second copy
of the rule, and inheritance counts — demanding that every stack own its gates
would have forced nine pointless edits and made the check the first thing anyone
switched off.

Checked by introducing an orphan rather than by assertion that it works. A gate
that has never caught anything is a hypothesis about a gate.

One thing surfaced on the way: `tausik stack lint` validates only user overrides
in `.tausik/stacks/`. Built-in declarations were never validated against
`stacks/_schema.json` at all — an invalid one would simply have been skipped on
load. They are now checked as a suite.

### A drift gate that was hiding drift

The DDL-parity gate exists to make silent divergence loud, and it had gone
silent itself in two places — both found by adversarial review during the
periodic audit, both in code written one session earlier.

The exemption marker (`# ddl-parity: historical — <reason>`) was attached to its
block by walking upwards and treating any line ending in `(` as a continuation.
That is enough for the marker to jump an unrelated chain of wrapper calls and
release a *distant* block that genuinely diverged: the drift was there, the gate
said nothing. The test that was supposed to cover this gave false confidence —
it placed the first block's SQL between marker and target, and on that line the
walk honestly stopped. The chain of open parens was never exercised, though the
style is common in this very repository.

The marker is now bound structurally: the block is matched to the statement
containing it via AST, and the marker is looked for in that statement's own
lines or the comment run directly above it. An unparseable file exempts nothing.

The second defect was the column counter, which split on commas without
excluding SQL comments — and the canonical definitions are full of them. It
read eighteen columns where `verification_runs` has thirteen. Since the
foreign-key stub exemption depends on that number, a legitimate two-column stub
with an explanatory comment containing a comma would have been counted as four
and failed for no reason. Counting is now done by SQLite itself: execute the DDL
in `:memory:` and read `PRAGMA table_info`. DDL that will not execute reports
"unknown" rather than zero, so it cannot slip into the stub range and be
released silently.

### The MCP thread is checked against the primitives the spec deprecates

The MCP specification of 2026-07-28 deprecates sampling, logging and roots
(SEP-2577) — annotation-only, with at least twelve months before removal. Two
P0 items of the 2.0 roadmap are built on roots, so the question worth answering
before spending person-weeks was how much of the tree actually depends on them.

Measured rather than assumed: nineteen Python files across three servers
(project, brain, codebase-rag), zero uses of the deprecated API, zero
protocol-level strings, zero advertised capabilities. The servers register
exactly four handlers — `list_tools`, `list_prompts`, `list_resources`,
`call_tool` — and since the SDK derives capabilities from registered handlers,
`get_capabilities()` reports `logging=None`. The spec's own estimate for local
stdio servers ("close to nothing to migrate") holds here exactly: there is
nothing to migrate, because nothing uses them.

That answer is now a gate rather than a sentence. A one-off finding is a claim
about yesterday's tree; without a test it expires at the next commit and the
next person to ask has to look again. The check parses code with AST instead of
grepping it, because `create_message` in a docstring and
`session.create_message(...)` in code are different events — a gate that cannot
tell them apart would either be blind or fail on its own documentation, and a
gate that fails on its own documentation gets switched off.

### Fixture-vs-schema drift is now checked for every table, not one

A test that writes its own `CREATE TABLE` proves the code matches *the copy*,
and the copy drifts silently. That had already cost twice, both times on
`verification_runs`: adding two columns meant hand-editing nine handwritten
blocks, and a fixture missing `CHECK(scope IN (...))` let twenty tests pass
green while the feature raised `IntegrityError` on every write to a real
database. The gate built in response covered exactly one table out of nineteen.
The other eighteen had the same failure mode and nothing watching it.

The table list is now derived from `SCHEMA_SQL` rather than written out here —
enumerating it by hand would be the same defect one floor up (convention #214),
blind to any table added after the gate was written.

Two exemptions are declared by name rather than skipped silently. Migration
tests must declare historical schemas: they run v1 → v2 → v3, so an old table
is the *input*, and migrating from canon to canon would test nothing. A test
asserts that file still declares a v1 schema, so the exemption cannot outlive
its reason.

Generalising the check found seven fixtures declaring a table far narrower than
production — three to seven columns where the schema has eight to forty-two.
That is the dangerous direction: a narrow fixture accepts inserts production
would reject on `NOT NULL`, so the test passes and proves nothing.

Taking those seven apart showed they were not one thing. Five were real drift
and now build their tables from `canonical_ddl`. One of the five was hiding a
live defect: a test asserted that `run_type='l3'` satisfies the L3 review gate,
and it passed only because the fixture omitted
`CHECK(run_type IN ('L1','L2','L3'))`. Production rejects that row twice over —
argparse pins `--type` to the three uppercase values, and the constraint would
refuse it anyway — so the test covered a branch unreachable in production, and
the module docstring promised a `--run-type l3` flag that does not exist. Both
are corrected; the test now pins what is actually true, that the row cannot be
stored at all.

The other two were deliberately historical: they build a v31-shaped or pre-v34
database precisely so there is something to migrate, and canon would destroy
the test. A file-level exemption list cannot express that, because both files
mix canonical and historical blocks. Such a block is now exempted where it
lives, by a `# ddl-parity: historical — <why>` line in its preamble. The reason
is mandatory and checked: a bare marker exempts nothing, so it cannot become a
one-line indulgence. The marker binds to the block it adjoins, not to the file,
and a test plants drift ten lines below a marked block to prove it does not
leak. The ratchet is gone — there is no remaining debt to ratchet.

### Fixtures matched the fresh schema; real databases are migrated ones

The parity gate above compares fixtures against `SCHEMA_SQL` — the schema of a
database created from scratch. A live project's database is that shape exactly
once, at init; thereafter it is a database carried forward by migrations. If
the two paths diverge, every fixture proves conformance to a shape almost no
real database has.

They diverge. A new gate builds both — fresh from `SCHEMA_SQL`, migrated from
the v1 baseline through `run_migrations` — and compares every table. Two
differences, both real:

`tasks.model_mismatch` is `NOT NULL DEFAULT 0` in the fresh schema and
nullable on the migration path. On any upgraded database the column can hold
`NULL`, and `WHERE model_mismatch = 0` silently drops those rows — green where
it is tested, wrong where it runs. Nothing writes a `NULL` there today, which
is luck rather than protection. Recorded as a ratchet with a named successor
task; a test fails if the entry ever goes stale.

Column *order* differs too, for `tasks` and `memory`, because
`ALTER TABLE ADD COLUMN` appends. That one is not worth fixing — it would mean
rebuilding tables — but its consequence is: a positional
`INSERT INTO t VALUES (...)` binds to column order, so it means different
things on a fresh and an upgraded database. Production code is now checked to
contain none, and the fixtures converted above list their columns by name.

### A skipped gate no longer reports itself as a pass

`verification_runs.summary` described a skipped gate as `PASS`. The
`gate_runs` rows of the very same run recorded `skipped=1` honestly — the two
records of one run contradicted each other. The formula never asked about
`skipped`, and `run_gates` marks a skipped gate `passed=True` so the verdict
can be computed from the gates that did run.

The machine guards were never fooled: `has_real_pass`, the `no-test-mapped`
block and the `noncacheable|` prefix all keep such a run from being reused. But
they protect the *cache*, not the reader. `summary` is what a human reads and
what lands in the agent's closing report, and a line saying
"hadolint=PASS, pytest=PASS" while both gates showed `[SKIP]` is what convinced
an agent a run was green and kept an open hole alive for an extra session.

Naming a gate's outcome is now one function, `gate_runner.gate_verdict`, with
`SKIP` as a third state rather than a flavour of `PASS`. It had been written
six times: three copies lied, three were correct. That the same three words had
already drifted in *both* directions is the argument against fixing three call
sites — a seventh copy was only a matter of time — so a gate now fails when any
module spells a gate verdict itself. It distinguishes a verdict about a *gate*
from one about an exit code, which is a different question and stays where it
is.

The sixth copy was found by that gate, not by reading: it renders the signed
receipt. It could not actually mislabel anything, because receipts carry only
gates that ran — but its correctness rested on an invariant enforced in another
module, which is correctness with an expiry date. It goes through the shared
verdict too.

Historical rows are left exactly as they are. A recorded run is a fact about
what was written, not a claim to be corrected later; the row that said `PASS`
about a skip is the evidence that this defect was real, and rewriting it would
erase the only trace of why an agent once got it wrong.

The change pushed `verify_cached_run.py` past the 400-line filesize gate, so
the envelope-timeout machinery moved to `verify_envelope.py`. The cut follows a
responsibility boundary rather than a line count: everything there answers "run
this with a wall-clock bound and fail legibly if it overruns" and knows nothing
about the cache, the declared scope or `verification_runs`. `run_gates` is
handed to it as an argument rather than imported inside it, so the suite's
patching of that import keeps working (memory #243). The three public names are
re-exported, so every existing caller and test is unaffected.

### Hook messages read the same everywhere, and a gate keeps them that way

A hook warning about a budget overrun emitted `2× hard cap reached — stop and
re-plan`. The `×` and `—` left in the machine's locale encoding —
`b'2\xd7 hard cap reached \x97'` on Windows — because the interpreter running
the hook had not been started in UTF-8 mode.

The generated host configs do pass `-X utf8` on every hook invocation, so
production was in fact covered. But it was covered by the *launcher*, not by
the hook: one line per host profile in `bootstrap/` decided it, and a hook run
any other way — a test, a manual invocation, a host profile added later — was
never covered at all. Hooks now call `force_utf8_io()` themselves, so a
supervision message no longer depends on how the supervisor was launched.
`errors="replace"` is deliberate: the mechanism that reports budget overruns
and policy blocks must degrade to a replacement glyph rather than crash while
trying to warn.

The reading end was wrong too. Tests called `subprocess.run(..., text=True)`
with no `encoding=`, so they decoded the child's output using whatever the
parent happened to use. Usually the two matched and everything was green. Under
`python -X utf8 -m pytest` the parent decoded UTF-8 while the child wrote
cp1251, and the `UnicodeDecodeError` landed in a reader thread — turning
stdout/stderr into `None`, so the visible failure was
`TypeError: argument of type 'NoneType' is not iterable`, which points at
nothing. 59 call sites across 36 test files now pass `encoding` explicitly.

Fixing 11 hooks by hand would have lasted until the twelfth
(convention #236), so the sweep is enforced rather than performed.
`tests/test_hook_encoding.py` fails, naming offenders individually, when a hook
emits non-ASCII to a stream without forcing UTF-8, when a test decodes a
subprocess in the parent's encoding, or when a hook invocation loses `-X utf8`
— checked in both generated host profiles *and* in the `bootstrap/` functions
that build those commands, so a regression is caught at the source rather than
one bootstrap run later. Docstrings and comments are excluded via AST, since
neither ever reaches a stream; pure-ASCII hooks and binary-mode subprocess
calls are not offenders, and tests assert that they are not — a gate that cries
wolf gets switched off.

The full suite is now green under both `python -m pytest` and
`python -X utf8 -m pytest`. It previously passed under one and failed five
tests under the other, which meant "the tests pass" was a statement about the
runner, not about the code.

### A verify run whose evidence was not written is no longer green

`verify` could report PASSED while nothing had been recorded. The single write
point wrapped the insert in `except Exception`, logged a warning, and returned
`None` — leaving the caller's verdict untouched. What reached `task done`, the
agent's report and the CLI was a green indistinguishable from a green with
evidence behind it.

This was worse than an ordinary fail-open. `gate_run_record` is deliberately
fail-closed and says so in its docstring: *"a write that cannot happen raises …
a run that looks recorded but is not is expensive, because it is
indistinguishable from a real one afterwards"*. The `except` above it caught
precisely the exception that guarantee is built from, so the contract was
annulled one level up.

It was not theoretical. During the session that fixed the entry below, a write
failed against a CHECK constraint on a live database and the CLI printed
`Verify PASSED — NOT recorded.` — the word PASSED standing next to the
admission that no proof existed. The task was one unrelated debug line away
from being closed on a run that certified nothing.

`_record_verification` now raises `VerificationRecordError`, and every caller
turns it into a blocking verdict: `passed=False`, cache status `record-failed`,
and a synthetic blocking gate result named `verify-record` naming the database
error. `task done` sees it in `blocking_failures` and refuses to close.

Two branches already blocked for their own reason (`scope-security-mismatch`,
`no-test-mapped`). There the verdict is not escalated — a different block adds
no safety — but the lost write is reported alongside the primary reason, since
convention #242 exists because a verdict that stops a closure has to leave a
trace, and that is exactly what failed. The `--no-tests-expected` branch is the
opposite case and does flip to red: it rests *entirely* on the row, because no
gate executed and `no_tests_declared = 1` is the only thing making the closure
auditable.

A transient lock is retried — three attempts with backoff — then fails
honestly. A permanent error (IntegrityError, `no such table`) is not retried:
that only delays the same failure and buries its cause under a pause. The
connection is rolled back between attempts, so a retry cannot report a second,
unrelated error as the reason. A run in which no gate executed at all writes
nothing and is unaffected: "nothing to record" is not "failed to record".

### A task with no tests can be closed, and saying so leaves a mark

Closing the CLI bypass below turned a hole into a dead end. A run in which every
gate is `[SKIP]` blocks — correctly, it proves nothing — but documentation,
config and migration tasks map to no test and never will, so there was no way to
close them at all. That class is not marginal: most of the remaining
documentation work in this release sits in it.

`tausik verify --task X --no-tests-expected` declares, for that run, that no
test is expected. The run is then recorded green under
`no_tests_declared = 1`. The flag buys visibility, not permission — the
closure still rests on no executed gate, and the point is that it is now
countable rather than indistinguishable from a verified one:

```sql
SELECT task_slug, ran_at FROM verification_runs WHERE no_tests_declared = 1;
```

No extension allowlist and no inference from file type: an implicit exemption
would restore exactly the invisibility the entry below removed. Without the flag
nothing changes, and the flag applies only to *skipped* gates — a failing gate
stays red.

The block message also named a way out that did not exist. It suggested
`--no-knowledge`, which governs knowledge capture on `task done` and has no
effect on gates whatsoever; an agent following it would have gone in a circle.
It now names `--no-tests-expected`.

Schema goes 39 -> 40: one additive `ALTER TABLE ADD COLUMN` plus its index,
no rebuild, historical rows default to 0. The first cut tried to avoid the
migration by encoding the marker as a `scope` value; `scope` is CHECK-
constrained to the SENAR tiers, so every write raised IntegrityError on a real
database. Tests missed it because their `verification_runs` DDL is a
hand-written copy without the constraint, and the failed write was swallowed
into a log warning while `verify` still printed a pass. Three holes had to line
up for a broken feature to look green, and they did; the fixture in
`tests/test_cli_verify_guards.py` now derives its DDL from `backend_schema`.

That one-off is closed as a mechanical gate rather than a one-off edit.
`tests/conftest.py` exposes `canonical_ddl(table)`, ten fixtures were moved onto
it, and `tests/test_ddl_fixture_parity.py` fails if any test file declares
`verification_runs` as a copy that differs from `backend_schema.SCHEMA_SQL`.
Id-only stubs that exist purely as foreign-key targets stay allowed.

### `tausik verify` no longer has its own, weaker rules

There were two paths that wrote into `verification_runs`. One —
`service_verification.run_gates_with_cache` — is what `task done` and MCP
verify use, and it holds the guards: refuse to cache a run in which no gate
actually executed, block when declared files map to no test at all, refuse to
cache an empty declared scope. The other was the `tausik verify` CLI, which
called `run_gates` and `record_run` directly and therefore had none of them.

The consequence was not theoretical. A run in which *every* gate was `[SKIP]`
was recorded as a fully cacheable green — a skipped gate reports `passed=True`,
so the summary read `hadolint=PASS, pytest=PASS` and the exit code was 0. For
any task whose `relevant_files` map to no tests (documentation, config,
migrations), the CLI minted a certificate that the service path would have
refused, and the next `task done` closed on it via an exact cache hit.

The CLI is now a presentation layer over `run_verify_for_task`: it formats
output and decides nothing about what is recorded. That also removed a second
copy of the `relevant_files` / `started_at` resolution, which had been
duplicated in both files. Rules that exist in two places drift; the point of
the fix is that there is now one place, not two agreeing ones.

Two blocking verdicts turn out never to have been recorded at all. Both
`no-test-mapped` and `scope-security-mismatch` returned before reaching the
single `record_run` call, so the verdict that *stops* a closure left no trace
while the permissive runs beside it were written down — the same argument as
the entry below, in two places it had not been applied. Both now record with
`exit_code=1` and a `noncacheable|` prefix. The `no-test-mapped` row keeps the
skipped gates alongside the synthetic failure, because "every gate was skipped"
is the evidence for the verdict.

Internal layout: `run_gates_with_cache` moved to `scripts/verify_cached_run.py`
and `_record_verification` — now the single write point — sits next to
`record_run` in `scripts/verify_run_record.py`. `service_verification` remains
a facade that re-exports both, so every existing import keeps working. Tests
that monkeypatch `describe_declared_scope` must now target
`verify_cached_run`, the module that calls it, rather than the facade that only
re-exports it.

### Every gate run is now written down, failures included

Gate outcomes used to be transient. A run was recorded only when it was also
eligible for the cache (`passed and cache_ok and has_real_pass`), which tied
observability to reuse and meant a blocking failure from the service path was
never written at all — so "how often does this gate actually block?" was
unanswerable for exactly the runs that matter most. Recording now happens
whenever gates actually ran.

What changes for an existing project: every gate failure lands in
`verification_runs` with `exit_code=1`, security-bypass runs are recorded too,
and a new `gate_runs` table holds one row per gate execution (name, severity,
pass/fail, duration) linked to the run that produced it. Expect the database to
grow faster than before — this is write volume that previously did not exist.
Two guards keep a recorded run from being replayed as a green: failures carry a
non-zero exit code and the cache lookup filters on `exit_code = 0`, and a run
that passed without being cacheable is stamped `noncacheable|`.

The run row and its gate rows are written in one transaction, and nothing on
that path is best-effort: a write that cannot happen raises and takes the whole
run down with it, rather than leaving a run that looks recorded but is not
(convention #221). Losing one verify run is cheap; a claim with no evidence
behind it is expensive, because afterwards it is indistinguishable from a real
one.

Schema goes 38 → 39. The migration is additive — it creates one table and three
indexes, alters nothing, and backfills nothing, because there is no historical
gate data to recover: the outcomes it records were never written down. Existing
databases therefore start empty and accumulate from the next verify onward, so
metrics read immediately after the upgrade legitimately report zero runs for
every gate, with the configured gate set listed alongside under `never_fired`.
That is the honest answer rather than a defect.

**On rolling back.** The migration is not reversible, and there is no guard for
running older code against a newer database: `backend_init` migrates only when
the stored version is *below* the code's, and takes no branch at all in the
other direction — a downgraded checkout opens a v39 database without warning.
A `.tausik/tausik.db.bak.v38` copy is written before the migration runs. Note
also that the CLI executes the `.claude/` mirror rather than `scripts/`, so any
schema change leaves the two out of step until `python bootstrap/bootstrap.py`
is run; that is the repair for a CLI that starts failing right after a
schema-touching change.

### BREAKING: a verify run with no declared scope no longer certifies anything

`tausik verify --task X` run before the task declared its `relevant_files`
recorded a green against an empty file set. Two properties combined into a
hole. `gate_runner` SKIPS the scoped gates when no files are declared, so the
run proved nothing about any file — and `compute_files_hash([])` returns a
stable empty-marker that no edit ever moves, so the green stayed valid for the
whole TTL no matter what changed in the tree afterwards. The sequence verify →
edit → `task done` therefore passed QG-2 on a green taken before the edit.

An undeclared scope is now treated as "unknown", not "verified empty"
(convention #226), and a check that could not compute its own coverage does not
certify (#221). Concretely: an empty-scope run is recorded `noncacheable|` so
it stays observable but unusable for reuse, and both the strict lookup and
`run_gates_with_cache` refuse it on the read side as well — the write-side
stamp alone would leave rows written by earlier versions still honoured.

Two further leaks are closed with it. The relaxed fallback that accepted a
"manual scope" row as a broad-pass certificate for an explicit file set is
gone: its premise — that naming no files means a *wider* run — was backwards.
And the relaxed lookup inside `run_gates_with_cache` was called without a
`command_prefix`, so it matched rows already stamped `noncacheable|` and rows
from the `task-done` bucket; the comment a few lines below it claimed neither
lookup could do that. `lookup_any_fresh_run_for_task` is removed with its last
caller.

The rule is enforced ahead of the `task_done.auto_verify` opt-out, not after
it. That path runs the gates inline, so with no declared files `gate_runner`
skips the scoped ones and a scope-independent gate going green closed the task
on a run that examined nothing — measured directly: with the check moved back
after the branch, `auto_verify=true` plus an undeclared scope returns `ok:
True` and zero blocking failures. `.tausik/config.json` travels with the
repository, so a legacy opt-out is not a safe place to keep a bypass.

**Migration.** A task must declare `relevant_files` to close on a verify green;
closing on an undeclared scope now blocks, with a message naming that as the
reason instead of asking for another `tausik verify` that could never succeed.
Full-suite `tausik verify` without `--task` is unaffected (it was never
cached), and no task has to declare its files twice.

### A default gate can no longer be neutered by swapping its command

The executable allow-list answered "is this binary tolerable at all?", never
"is this still the gate it is named after?". Every entry on the list is
legitimate, so `gates.ruff.command = "python -c pass"` passed validation and
left a gate that was enabled, fired on its triggers, and was green forever.
`.tausik/config.json` travels with the repository, so a clone could neuter the
framework's own supervision without tripping anything.

An override of a default gate's command must now invoke the same tool as the
default. Arguments, paths and runner wrappers stay free: `vendor/bin/phpstan
analyse --level=8` is accepted, and so is `eslint {files}` against a default of
`npx eslint {files}` — wrappers (`npx`, `npm run`, `python -m`) are seen
through. Swapping the tool itself is refused: the gate keeps its default
command and a warning is logged. Built-in gates (`filesize`, `tdd_order`,
`renar_drift_*`) have no command at all, and an attempt to add one is likewise
refused.

The residual vector is recorded honestly in the threat surface rather than
papered over: an inert invocation of the SAME tool (`ruff --version`,
`pytest --collect-only`) is fundamentally invisible to this check — there is no
machine-checkable definition of "this command does real work", and a
default-prefix rule would break both legitimate cases above. See "Limits of
these guarantees" in `docs/en/security.md`.

### The static audits stopped reporting files git does not track

`audit_stale_docs` reported three candidates and all three were false, for two
different reasons. One lived under `docs/research/_internal/`, which is
gitignored: it references nothing by definition and cannot be "fixed", so it
was permanent noise — and the report printed its filename, which is exactly
what keeping internal research in a gitignored directory is meant to prevent.
The other two lived in `docs/research/`, the research home, while the exclude
list named only its `docs/en/` and `docs/ru/` twins.

The audits walked the filesystem with `rglob` while their own docstrings
claimed to report on *tracked* files. `scripts/audit_tracked_files.py` now
answers that question once, from `git ls-files`, for `audit_stale_docs`,
`audit_orphan_files`, and `audit_unused_python` alike. It returns "unknown"
rather than an empty set when git cannot be consulted — an empty set would
make every audit declare the whole tree unreferenced the moment git hiccups.
On unknown, the audits warn to `stderr` and fall back to the filesystem walk.

An audit whose output is permanently false stops being read, and a real
finding drowns with it.

### A receipt now states whether its own scope was complete

The git cross-check has been wired since v1.3.4, and it worked: declare
`relevant_files=[README.md]` during a broad edit and the verify cache was
refused. That was the whole of its effect. The gates then ran against the same
narrow declared list, and `record_run` signed a receipt for that narrow scope.
The divergence existed only as a return value and a line of free text in the
task notes — `record_run` had no parameter for it at all. The system detected
the problem and left it out of the artifact of proof, which is the one place it
mattered.

Two columns (`declared_scope_status`, `undeclared_files`, schema v38) and three
receipt fields now carry it. `declared_scope_status` is deliberately tri-state:
`complete`, `under-declared`, and `unknown` for the cases where the comparison
could not be made — no git repo, empty `relevant_files`, missing
`task_created_at`, failed git call. A boolean would have merged "verified
complete" with "could not check", which is the same silent green in a new
place. Receipts predating this change (`tausik-receipt/v1`) have no such fields
and their scope reads as unverified, never as complete.

**Divergence still does not block, and that is measured rather than assumed.**
Both closures of the previous session diverged from git, and both were honest —
CHANGELOG, docs, generated constants, README badges and five IDE mirrors edited
beyond the declared set. A rule firing on essentially every honest closure would
be switched off on first contact and would leave the project worse off than no
rule. The one exception is an undeclared file matching the security predicate:
scoped gates run against the declared list, so an undeclared `scripts/auth.py`
would be verified by nothing at all. That case now fails with
`scope-security-mismatch` and names the files to add. The same predicate was
replayed against the previous session's undeclared set to confirm it stays
silent on honest work.

The receipt schema moves to `tausik-receipt/v2`. Existing v1 receipts remain
cryptographically valid — verification re-canonicalizes the stored payload
rather than rebuilding it from the current code.

Settled alongside: the 4 KiB content window in `compute_files_hash` is a
deliberate compromise, not an open hole, and now says so in its docstring. The
sample is hashed together with `mtime_ns` and `size`, so a collision needs a
same-length edit past 4 KiB *plus* an mtime restored to the nanosecond — an
actor already running code in the working tree, who can equally edit the file
one moment after a legitimate verify.

### Configuration trust tiers — a project may only tighten enforcement (BREAKING)

The enforcement switches lived in `.tausik/config.json`, an ordinary file inside
the repository. `qg0.scope_hard_gate`, `risk.l3_block_on_high`,
`task_done.auto_verify`, per-gate `enabled` and `severity` — one write to a
git-tracked file removed the supervision. An agent could disable its own
oversight; a pull request could turn the gates off on the reviewer's machine.

Config now resolves across three tiers — project (`.tausik/config.json`), user
(`~/.tausik/config.json`), managed (`$TAUSIK_MANAGED_CONFIG`). Higher tiers win,
and a guarded key from the project tier applies only if it is at least as strict
as what the trusted tiers established. Tightening still passes through untouched;
weakening is replaced with the enforced value and named in `tausik doctor`.
`gates disable` on a guarded gate now says it did not take effect instead of
reporting a success that never happened.

**Guarding `enabled` alone would have been decorative.** An adversarial pass
against the new control found three ways to turn a gate off by another spelling,
each of which worked before the fix: emptying `trigger` (the gate stays
"enabled" and never fires), narrowing `file_extensions` until nothing matches,
and overriding a built-in gate's `command`. `trigger` and `file_extensions` are
now set-valued guards — a project may extend them, never shrink them.

The `command` finding was worse than a bypass. `_validate_custom_gate` ran only
for gate names absent from `DEFAULT_GATES`, so overriding `gates.ruff.command`
skipped the allowed-executable check entirely — a cloned repository could point
a built-in gate at any binary and the runner would execute it. Every command an
override supplies is validated now, built-in or not; a refused command falls
back to the default and the rest of the override still applies. A project can
still neuter a gate with an *allowed* but inert command (`python -c pass`);
that vector is tracked in `l26-gate-command-neutering` and named in the docs
rather than left implied.

### Verify-First now fails closed on a config it cannot read

Found by the same adversarial pass, and independent of the tiers.
`_enforce_verify_first` caught every config-load error and continued with an
empty gate list — indistinguishable from "this project configured no verify
gates". One malformed entry in the `gates` object therefore skipped the entire
Verify-First Contract in silence, while `tausik doctor` still reported a clean
config. The framework documents its gates as fail-closed; this one was not.
A config that cannot resolve is now a blocking failure with remediation.

Two supporting fixes: `cfg.get("task_done", {})` returned `None` when the key
was present and explicitly `null` (the default never applies), crashing
`task done` on a one-key typo — the value's type is checked now, not the
container's. And `tausik doctor`'s gate check only counted `DEFAULT_GATES`, a
number that cannot fail; it resolves the project's actual gates now, so this
class of defect is visible before it reaches a closure.

**BREAKING — projects that disable gates in `.tausik/config.json`.** That is now
rejected: the gate stays on and `tausik doctor` names the key. If you have a
legitimate reason to turn a gate off — a sandbox, a CI image, a project where a
gate genuinely does not apply — move that setting to `~/.tausik/config.json`
(per machine) or to a file pointed at by `$TAUSIK_MANAGED_CONFIG` (per fleet).
Nothing else changes; tightening from the project tier works exactly as before.

**What this does not do**, stated here rather than left to be assumed: an agent
that can run shell commands can write the user tier itself. Tiers are not a
sandbox. They make a repository unable to grant itself authority, and they force
weakening out of the diff and into the open. See
[`docs/en/config-trust-tiers.md`](docs/en/config-trust-tiers.md) for the full
threat boundary and for the two keys (`gates.filesize.exempt_files`,
`verify_cache_ttl_seconds`) deliberately left unguarded.

Split out of `project_config` at the 400-line cap: custom-gate command security
now lives in `scripts/gate_command_policy.py`, re-exported for existing callers.

## [1.7.0] — 2026-07-16

OpenCode support — and the reason it took three tasks to ship one IDE.

A user's OpenCode host died with `ConfigInvalidError` and `ERR_MODULE_NOT_FOUND`.
The config that killed it was not written by TAUSIK: no such code existed. It was
written by an agent, by hand, because our docs listed OpenCode as a supported
platform while `bootstrap` had no branch for it. The agent found "supported" and
found nothing configured, and closed the gap by guessing — inventing a `tools.qg0`
object (the key is boolean-only) and a plugin importing `@opencode-ai/plugin` (a
package that does not exist at that version).

**A support claim with no code behind it is not a harmless inaccuracy. It is an
instruction to improvise.** So this release ships the code first and the claim last.

> **What is verified, and what is not.** Everything below is covered by the test suite
> (both lanes green: 4694 full / 4578 fast) and by `tausik doctor`. Three things are
> **not** verified and are stated here rather than left for a user to discover:
> the QG-0 plugin has never run under a real Bun/OpenCode host — its behaviour is
> exercised under Node against a faked Bun shell; the `OPENCODE_DIR` / `OPENCODE_BIN_PATH`
> environment variables are taken from OpenCode's documented behaviour and were not
> confirmed against a live build (auto-detection does not depend on them — the
> `.opencode/` directory check does); and the `-32601` log noise is confirmed gone by
> code inspection and tests, not by watching a restarted host's log. Live OpenCode
> validation is deferred to QA. The compression figure caveman reports for itself
> (~65%) is likewise **their** measurement, not ours.

### Added

- **OpenCode is a scaffolded IDE.** `bootstrap.py --ide opencode` writes
  `opencode.json` (MCP servers + the `instructions` key), installs the rules at
  `.opencode/tausik-rules.md`, and deploys command stubs. Every path in the MCP
  command is absolute: OpenCode expands no `${workspaceFolder}` — copying Kilo's
  portable paths would have produced a config that points at a literal directory
  named `${workspaceFolder}`.

- **QG-0 enforcement for OpenCode** (`.opencode/plugins/tausik-qg0.js`, note the
  plural — a singular `plugin/` directory never loads and never says so). The
  plugin implements `tool.execute.before` and refuses `write`/`edit`/`apply_patch`
  when no TAUSIK task is active, the same contract as Claude Code's PreToolUse
  hook. It has **zero imports** — not even a type-only one — because the import is
  what killed the user's host. Types come from JSDoc; it runs with nothing
  installed.

  Its active-task verdict is cached against a signature of the DB files
  (`tausik.db` + the WAL), not against a bare TTL: `task done` moves the WAL, so a
  cached "allow" cannot outlive the task that justified it. The cache may only ever
  err toward strictness. When the CLI cannot be reached the gate fails **open** — a
  broken CLI must not brick an editor — but never in silence: it warns that QG-0 is
  degraded and names `TAUSIK_HOOK_FAIL_SECURE=1` as the way to invert the policy.

- **`tausik doctor` validates OpenCode installs.** It catches the three ways this
  host fails quietly: an object under `tools` (fatal to the host at startup), a
  missing or singular-directory plugin (enforcement simply absent), and
  `instructions` pointing at a file that does not exist (rules simply never load).
  It also refuses to report "writes are refused" unless the CLI wrapper the plugin
  queries actually exists — a guarantee doctor cannot verify is a guarantee it will
  not make.

- **Guard: an IDE cannot claim to be scaffolded without a dispatch branch**
  (`tests/test_scaffold_dispatch_backed.py`). Parsed from the AST, so a comment
  naming an IDE cannot satisfy it. Without this, `--ide <name>` would copy the
  skills, print `Done!`, configure nothing, and exit 0 — the silent no-op that
  started this whole story.

- **Output-economy mode (`output_mode: caveman`, opt-in).** Orthogonal to `context_tier`:
  the tier compresses the **input** rules TAUSIK injects, this compresses the agent's
  **output**. When enabled, bootstrap appends a short directive — inspired by the
  [caveman skill](https://github.com/JuliusBrussee/caveman) — telling the agent to answer
  in terse prose while keeping code, commands, tool output and error messages byte-exact,
  and acceptance-criteria evidence, decisions and SPEC/ADAPT full (future agents parse
  those). Shipped as our own rule via `build_full_body`, so it reaches all five IDEs from
  one source — deliberately **not** through caveman's own installer, whose Claude-Code
  hooks and `settings.json` merge would collide with TAUSIK's SessionStart hook and its
  ownership of that file. The directive is length-capped and guarded: it is injected every
  session, so a bloated directive would cost more input than the terse output saves.
  Default `off`; a bad value falls back to `off` without crashing. caveman's own
  "~65% reduction" is *their* figure — unmeasured in TAUSIK's harness, so not restated as
  ours. `tausik doctor` reports coexistence when the real caveman skill is also installed,
  and warns if a caveman hook is wired into the `.claude/settings.json` TAUSIK manages.

### Changed

- **`OPENCODE_DIR` no longer detects as Codex.** They are different hosts with
  different configs; an OpenCode session was being handed `.codex/` paths that
  OpenCode never reads.

- **Rules reach OpenCode through `instructions`, not `AGENTS.md`.** OpenCode
  resolves AGENTS.md first-matching-file-wins, so a user's own file would shadow
  ours forever; `instructions` files are merged with it instead. Consequently
  `--ide opencode` generates no AGENTS.md — it would put identical rules in the
  context twice.

- **The platform table is now enforced against the code.** The `Scaffolded` column
  in `docs/*/model-providers.md` is checked against `SCAFFOLD_IDES`; the table and
  the code cannot drift apart in either direction.

### Removed

- **`harness/cursor/mcp/` — 19 files, deleted.** It was a byte-for-byte copy of
  `harness/claude/mcp/`; `diff -r` across the whole tree returned exactly one
  difference, a single word in one docstring. Nothing generated it. It was kept in
  sync by hand, and a project convention existed telling agents to keep doing so.

  The danger was never the duplication itself — it was the precedence. `copy_mcp`
  prefers `harness/<ide>/mcp/` over the canonical tree when it exists, so the first
  time anyone patched only the Claude copy, Cursor users would have silently kept
  running the old server, and no test would have noticed: each mirror passed its own
  checks in isolation.

  Cursor now receives the canonical tree through the fallback that Kilo, Qwen and
  OpenCode have always used. Verified equivalent: `copy_mcp` hands all three servers
  to all five IDEs. A guard (`tests/test_mcp_single_canonical_tree.py`) refuses any
  file under `harness/<ide>/mcp/` that is byte-identical to its canonical counterpart
  — an IDE may ship a genuinely different server, it may not ship a copy of ours.

### Fixed

- **MCP servers answer `prompts/list` and `resources/list`** instead of `-32601`.
  The error was harmless — tools worked fine — but it filled the host log with a
  message that reads exactly like a dead server, and it did: a user reported the
  MCP as broken when it was not. All three canonical servers (`project`,
  `codebase-rag`, `brain`) now return an empty list — and since `copy_mcp` hands that
  one tree to every IDE, every host gets the fix.

- **`opencode.rules_path` can no longer escape the project.** `.tausik/config.json`
  travels with a repository, so a tampered one would have turned the next bootstrap
  into an arbitrary-file-write. Escaping, absolute and drive-qualified overrides are
  refused — loudly, and without crashing: the containment check itself used to raise
  (`os.path.commonpath` throws on a foreign Windows drive), and a crash is not a guard.

- **Bootstrap no longer reports success on a config that cannot start.** The project
  that triggered this whole release still holds the config that killed it — a `tools`
  object, and a plugin under the singular `.opencode/plugin/`. Re-running bootstrap
  merged our stanzas in beside them and printed a cheerful "Done!", while OpenCode went
  on refusing to boot for exactly the same reason as before. TAUSIK does not delete
  those (they are the user's file), but it now says plainly what is fatal and what to
  remove, and `tausik doctor` fails on the same conditions.

- **The QG-0 plugin can actually be upgraded.** Plugin resolution preferred the copy
  already installed in the project, which exists after the first bootstrap — so every
  later run resolved source == destination and skipped the copy. A user upgrading TAUSIK
  to get a *fixed* gate would have run bootstrap, seen it succeed, and kept running the
  broken one: the enforcement artifact was the single file an upgrade could never reach.
  The library copy now wins.

- **`tools` as a list or a string is caught too.** The doctor check only inspected
  objects, so `"tools": ["qg0"]` sailed past it and doctor printed *"valid — no `tools`
  object"*: an OK that affirmed the very thing that was broken.

- **The docs no longer name an npm package that does not exist.**
  `@anthropic-ai/opencode` was never real (OpenCode is SST's `opencode-ai`). Docs
  that name a nonexistent package teach agents to invent module names by analogy —
  which is precisely how `@opencode-ai/plugin@local` ended up in a user's project.
  A guard now fails the build if any doc puts a bogus package on an install line.

## [1.6.1] — 2026-07-11

Tooling and CI hardening. No runtime behaviour changes — this release is entirely
tests, gates and the development pipeline. It exists because every 1.6.0 finding
shared one shape: **code that could not fail where it was run.**

### Added

- **CI is back on the development remote.** Development happens on GitLab, where
  there were no tests: `.gitlab-ci.yml` had vanished with the site extraction, so
  the suite first saw a commit only after it was merged, tagged and mirrored to
  GitHub — the gate stood behind the door. The CRLF bug walked straight through
  it: green on the maintainer's Windows box, broken on every Linux clone. A Linux
  pipeline now runs on every push and merge request. The GitHub matrix
  (ubuntu/windows/macos × 3.11–3.13) stays as release verification.

  It earned its place before its first green: the opening runs caught a `ruff`
  error already on `main`, three tests that only passed because of tools present
  on one machine, and a `file:///` + path join that yields four slashes on POSIX.

- **The skill store verifies its own signatures on Linux.** A new CI job in the
  store repo re-clones it the way the most hostile consumer would (`autocrlf=true`)
  and checks all 39 signatures reproduce. A signature's whole value is that it
  reproduces where it was not made; now that is exercised, on the platform that
  broke.

### Fixed (the silent-error class)

- **External-binary flags are verified against the real binary, not a mock.**
  `--no-config` (which no pip accepts) shipped across two minors because the test
  mocked `subprocess`. Flags handed to git, and to the per-stack gate commands,
  are now probed against the actual tool. This caught `cargo clippy — -D warnings`
  in the rust stack: an em-dash (U+2014) instead of `--`, so `-D warnings` never
  reached the driver.

- **A gate that advises "run X" must have X actually fix it.** `check_docs` told
  you to run `gen_doc_constants.py`, which only rewrote `constants.json` and left
  the README counts — so following the advice kept the gate red. `--write` now
  repairs every cross-file drift (badges, prose, version refs) and re-checks
  itself; a meta-test proves the advice greens the gate. Widened the count
  patterns to the forms that were never scanned (the badge URL, all Russian
  forms) — which is why a stale "4341 тестов" had sat in the README for releases.

- **A discarded `subprocess.run(...)` must state `check=` explicitly.**
  `pin_eol_config` ran `git config` and threw the result away; if the pin failed
  to write, the next `git pull` re-converted line endings and signatures broke
  again, silently. A discarded run now has to opt in (`check=True`) or opt out
  (`check=False`) — the swallow is no longer the default. The broad "never
  discard" rule was rejected as noisy (metrics, formatters, background launches
  legitimately fire-and-forget).

### Notes

- Everything above is post-1.6.0 work; the 1.6.0 tag does not contain it. 1.6.1
  makes the tag match `main`.

## [1.6.0] — 2026-07-10

Skill supply-chain release. Several mechanisms were specified, covered by green
tests, and had never once worked. Each is now pinned by a test that fails without
the fix, and each was verified against a real environment rather than a mock.

**Minor, not patch:** `skill sign` now refuses a converted worktree and
`skill install` exits non-zero when dependencies fail. Both change the behaviour
of existing commands.

### Breaking

- **`tausik skill install` now fails when `requires` cannot be installed.** It
  used to print "Skill 'x' installed ... but dependency installation failed" and
  return **exit 0**. The skill sat in the tree unable to run, and anything reading
  the exit code — CI, MCP, a shell script — saw success. A direct violation of the
  project's first principle. It now raises `SkillManagerError`, the CLI exits
  non-zero, the copied files are removed and nothing is written to
  `installed_skills`. Installation is atomic: either the skill is there and works,
  or it is not there. The signature verdict and the manual-install command stay in
  the message.

- **`tausik skill sign` refuses to sign a converted worktree.** If the worktree
  bytes differ from the bytes the repository stores, no signature is written and
  the offending files are named. Sign such bytes deliberately with
  `--allow-eol-drift`.

- **`scripts/project_cli*.py` refuse to be run directly** (exit 2). All 26 modules
  are libraries; there is one entry point, `.tausik/tausik`.

### Fixed

- **A skill's `requires` was never installed.** `install_skill_deps` imported
  `bootstrap_venv` from a sibling `bootstrap/`. A bootstrapped project receives
  only `scripts/`, the sibling is not there, and the `ImportError` was swallowed:
  `return False` without a single line of output. Tests never saw it because they
  run from the core checkout, where the sibling exists. The venv python is now
  resolved across several candidates, and when core is out of reach it is derived
  directly — the `.tausik/venv` layout is fixed.

- **`--no-config` is not a flag in any version of pip.** The v1.3.4 hardening
  (`med-batch-1-hooks #2`) crashed pip with `no such option` and rc=2 — confirmed
  on 22.3.1 (what `ensurepip` ships with Python 3.11) and on 26.0.1; the flag is
  absent from `pip install --help` in both. The "hardening" therefore broke every
  dependency install instead of protecting it. Index-substitution defence now
  rests on two things, read out of `pip/_internal/configuration.py` rather than
  assumed:

  - `--isolated` (real, present in both versions) skips USER config and every
    `PIP_*` environment variable;
  - an explicit `--index-url` argument — config values become optparse *defaults*
    (`cli/parser.py::_update_defaults`), and a command-line argument overrides a
    default.

  Residual risk, accepted knowingly: an `extra-index-url` in a GLOBAL/SITE
  `pip.conf` still adds a second index. Only `--no-index` suppresses that, and it
  would forbid installing anything. `iter_config_files` yields GLOBAL and SITE
  unconditionally — no flag and no variable disables them, contrary to what the
  old `PIP_CONFIG_FILE` comment claimed.

- **A test pinned a nonexistent flag through a mock.** `assert "--no-config" in
  cmd` stayed green precisely because it mocked `subprocess` and never asked a
  real pip. The new `TestPipFlagsAreRealFlags` validates every flag we pass
  against a real pip offline (`pip install <flag> --help` returns rc=0 for a real
  flag and rc=2 for an invented one) and guards the probe itself with its own test.

- **A dependency failure lost the signature verdict.** The message said nothing
  about whether the skill was signed. The verdict is back, together with the
  command to install the dependencies by hand.

- **The `keyword_detector.py` Stop hook swallowed the agent's turn and re-armed
  itself.** The rag-first nudge matched regexes against the last user message, and
  Claude Code feeds the `reason` from `{"decision":"block"}` back into the
  conversation as a role=user message. The nudge text quoted its own triggers
  (`'where is X'`, `'how does Z work'`, `'где определ…'`), so every block armed the
  next one: `_has_search_intent(SEARCH_RECOMMENDATION)` returned `True`. The escape
  hatch was unreachable too — transcripts store one entry per content block, so
  `_read_last_message` returned the first `assistant` entry, often a `tool_use`
  with no text, and `"search_code" not in last_assistant` never cleared. *Calling*
  the tool did not count; only writing the word in prose did. The harness renders a
  blocked Stop as a hook error and swallows the turn's output — hence turns that
  ended in silence.

- **The drift guard was blind on turns ending in a tool call.** The same transcript
  walk handed it an empty string. Entries with no text are now skipped, so prose is
  found behind a trailing `tool_use`.

- **A skill signature reproduced only on the platform that made it.** The manifest's
  `sha256` is taken over raw bytes, and `core.autocrlf` rewrites line endings on
  checkout. A Linux clone got LF, the hashes disagreed, and the install refused an
  untouched file with `modified: SKILL.md`.

  It is **core** that clones, not the publisher, so the consumer half is fixed here:
  `clone_repo` invokes git with `-c core.autocrlf=false -c core.eol=lf` and also
  writes the pin into the clone's local config — otherwise the next
  `git pull --ff-only` re-reads the user's global `core.autocrlf` and converts the
  freshly fetched blobs (verified experimentally; `-c` covers only the `clone`
  command itself). Vendor clones made before this fix are re-cloned rather than
  served silently.

  The publisher half is the `skill sign` refusal, see Breaking. The check compares a
  file's bytes against `git cat-file blob :<path>` rather than reading
  `git ls-files --eol` codes: it is exact and catches any clean/smudge filter.
  `git status` is useless here — with `core.autocrlf=true` it normalises before
  comparing and reports a clean tree. The signature stays a signature of raw bytes:
  normalisation was rejected because a skill is executable content (decision #129).

- **Re-adding a skill repo dropped the pinned publisher key.**
  `update_config_repo_add` did `repos[name] = {"url": url}` — it replaced the whole
  entry and lost the sibling `pubkey`. The next install printed
  `Installing UNVERIFIED` and nothing explained why. The bug was wider than
  `--force`: any re-add un-pinned the key, builtin URLs included. Fields are now
  merged; a changed URL still drops the pin — it is a different repository — but
  loudly, with the command to re-pin.

- **`skill repo remove` failed on Windows and left the cache alive.**
  `shutil.rmtree` without a handler tripped over git's read-only pack files
  (`PermissionError`), and it raised **before** the config was updated: the repo
  stayed configured, the vendor cache kept serving the stale skill — which is how a
  freshly pushed signature was still reported `UNSIGNED`. Removal now clears the
  read-only bit and retries; on failure the command exits non-zero instead of
  printing a false success.

- **CLI library modules silently exited 0.** `python .claude/scripts/project_cli.py
  skill sign <dir>` defined the handlers, called none of them, printed nothing and
  exited 0 — indistinguishable from success. Not one of the 26 modules had a guard;
  fixing only the one someone tripped over would have left the trap on the other 25.

### Changed

- **The rag-first nudge moved from `Stop` to `UserPromptSubmit`.** The placement was
  wrong on the merits, not merely buggy: `Stop` fires *after* the agent has already
  run Grep/Read, so it cannot steer the turn it interrupts — it can only spend the
  next one. On `UserPromptSubmit` the nudge is injected as `additionalContext`,
  costs no turn, and only ever sees genuine human prompts. A new `_is_machine_prompt`
  filter drops anything carrying `[TAUSIK `, `<command-name>`, `<command-message>`,
  or a leading `/`. The nudge text no longer quotes its own triggers. Only the drift
  guard remains on `Stop`, where the agent's last message is genuinely needed.

  This also closes `/start` shooting itself: its `SKILL.md` body contains the literal
  string `"where is X used"`, so the slash command silenced its own turn.

- **`scripts/skill_deps.py` and `scripts/skill_git.py` split out of
  `skill_manager.py`.** The module hit the filesize gate (469 lines against a 400
  cap). `skill_deps` took `_resolve_venv_python`, `install_skill_deps`,
  `DEFAULT_PIP_INDEX_URL` and `_SAFE_PKG`; `skill_git` took `rmtree_force` and the
  line-ending pin. `skill_manager` re-exports them, so imports are intact.
  `_SAFE_PKG` also stopped being recompiled on every call.

- **`docs/{ru,en}/skill-spec.md` gained a section on signing and line endings**,
  requiring a `.gitattributes` with `* -text` in the skill repo. The docs used to be
  silent while the mechanism was quietly platform-dependent.

- **The version-ref scanner no longer demands that history be rewritten.**
  `scan_version_refs` flagged every `vX.Y`, without distinguishing an "as of the
  current release" marker from a record of *when a thing landed*. Bumping 1.5 → 1.6
  made the gate demand edits to `tausik_session_open (v1.5)`,
  `hooks/check_docs.py (v1.5)` and "like in pre-v1.5 releases" — all three would have
  become false statements. A separate `VERSION_SCAN_TARGETS` now says where a version
  ref means "current": `README.md`, `README.ru.md`, `AGENTS.md`, `CLAUDE.md`.
  `architecture.md` and `mcp.md` are out of the version scan — their MCP tool counts
  are still checked — and the doc-wide version markers were removed from their
  headings so nothing rots silently. The same move was already made for four other
  docs via `MCP_COUNT_EXTRA_TARGETS`; the list simply missed these two.

### Notes

- Full suite: 4540 tests. `docs/_generated/constants.json` and the four doc-count
  sites in the READMEs were regenerated.
- `gen_doc_constants.py` only updates `constants.json`; the README counts are edited
  by hand, even though the `check_docs` gate tells you to run that very script.
  Filed as a separate task.
- `skill_manager.py` sat exactly at the 400-line cap on `main`, and commit `c3e7ed9`
  pushed it to 454 — the branch was already failing the filesize gate before the pip
  fix, so `task done` could never have passed on it.
- `TestCloneRepo::test_existing_repo_pulls` passed by accident: it looked for the
  substring `"pull"` in `str(cmd)`, and pytest names `tmp_path` after the test
  (`test_existing_repo_pulls0`), so the repo path contained it whatever git
  subcommand ran. Rewritten to assert on `argv[1]`.
- Left out: the dead `sources` section in `skills.example.json` (needs a decision —
  wire it up or remove it), bundles from a skill repo (architecture), the store's
  `LICENSE` (someone else's repository). All filed as tasks.

## [1.5.9] — 2026-07-08

Docs release. Surfaces **z.ai GLM as a first-class model under Claude Code** —
not a Kilo-only feature. GLM already ran under Claude Code via the
Anthropic-compatible endpoint (host unchanged → every SENAR gate keeps firing);
this makes that path discoverable and documents it as a **subscription** (not
per-token) option. Part of the `universal-vscode-extension` epic, where
GLM-by-subscription is deliberately decoupled from the extension itself.

### Changed

- **`docs/{en,ru}/kilo-zai.md` reframed host-agnostic.** The intro no longer
  presents GLM as a Kilo-only capability. A new §1 — "GLM under Claude Code
  (recommended — subscription, full gates)" — documents the two env vars
  (`ANTHROPIC_BASE_URL=https://api.z.ai/api/anthropic` + `ANTHROPIC_AUTH_TOKEN`),
  states that keeping Claude Code as the host preserves every enforcement gate
  (QG-0 / QG-2 / scope / secret / firewall), frames the GLM Coding Plan as a
  flat-fee subscription rather than metered tokens, and adds a **billing
  smoke-test caveat** (confirm the Coding-Plan quota bills through `/api/anthropic`
  and not a pay-as-you-go wallet). The filename is unchanged, so existing README /
  quickstart / architecture links still resolve.

- `__version__` bumped `1.5.8` → `1.5.9` (`scripts/tausik_version.py`,
  `pyproject.toml`, `docs/_generated/constants.json`, README badges ru+en).

## [1.5.8] — 2026-07-06

Reliability release from a field-test: `/start` could freeze forever on a large
project. Hardens the `tausik_session_open` compound RPC so it can never hang.

### Fixed

- **`/start` froze on "Generating…" on large projects.** `tausik_session_open`
  bundles five sub-calls (session start+current, status, handoff, tasks,
  self_check) for `/start` Phase 1. Each was wrapped only in `try/except`, which
  catches exceptions but **not a blocked call** — so a sub-operation that *hangs*
  rather than raises (a DB write contending with sibling MCP servers, a
  self_check subprocess wedged past its own timeout, a pathologically large
  repo) froze the whole envelope and the IDE sat on "Generating…" indefinitely.
  Each sub-call now runs under `_section_with_timeout` — a daemon-thread watchdog
  (6 s) that returns `{"error": "<section> timed out after 6s"}` for the wedged
  section instead of blocking. `/start` degrades to a visible, self-diagnosing
  dashboard rather than hanging, and the error names the culprit section.
  Cross-thread DB use is safe (the connection is opened `check_same_thread=False`
  with `busy_timeout=5000`). (P1)

## [1.5.7] — 2026-07-06

Field-fix release. The v1.5.6 UTF-8 hardening covered the **encode** side
(writing Cyrillic / ✓ output on Windows); this covers the **decode** side —
hooks and gates that *read* TAUSIK CLI or git output back.

### Fixed

- **SessionStart hook (and other CLI readers) crashed on Windows when the
  captured output contained Cyrillic.** `subprocess.run(..., text=True)` decodes
  the child's stdout with the OS locale codec (cp1252 on a typical RU Windows),
  which chokes on UTF-8 Cyrillic bytes (e.g. `0x81` is undefined in cp1252). The
  reader thread raised `UnicodeDecodeError`, leaving `result.stdout = None`, and
  the subsequent `.strip()` raised `AttributeError` — outside the caught
  exception tuple — so the entire hook aborted with a traceback and no session
  context was injected (framework "silently broken" on affected projects). Every
  `text=True` subprocess reader of CLI/git output now passes
  `encoding="utf-8", errors="replace"` — 12 call sites across `session_start`,
  `_common`, `auto_format`, `task_done_verify`, `session_metrics`, `check_docs`,
  `project_cli_extra`, `project_cli_renar`, `pytest_test_count`,
  `service_session`, and `verify_git_diff`. The last two also affect the
  `task done` / verify gates on repos with Cyrillic filenames or `git user.name`.
  (P0)

## [1.5.6] — 2026-06-19

Fine-tune release from a live Kilo Code + z.ai (GLM) field test. The structural
root was three drifted IDE lists; they are now two named constants.

### Fixed

- **Kilo-only installs got "no scripts dir found" from the CLI.** The wrapper's
  IDE-discovery loop hardcoded `claude cursor qwen windsurf codex` — no `kilo` —
  so `bootstrap --ide kilo` produced a `.tausik/tausik` that couldn't find
  `.kilo/scripts`. The loop is now **injected from `bootstrap_config.IDE_DIRS`**
  (the single source of truth) into the wrapper template at install time via an
  `__IDE_LIST__` placeholder; add an IDE to `IDE_DIRS` and every consumer picks
  it up. `--ide all` and the `--ide` argparse choices now derive from a sibling
  `SCAFFOLD_IDES` constant. (P0/P4)
- **Windows UnicodeEncodeError on Cyrillic / ✓ output.** Layered UTF-8 hardening:
  the CLI wrapper exports `PYTHONUTF8=1`; every hook runs via `python -X utf8`
  (one injection point in the hook-command builder, covering all hooks); and the
  standalone entry points — `bootstrap.py` and all MCP servers — call
  `fix_stdio_encoding()` at startup. Note: `PYTHONUTF8`/`-X utf8` fix the locale
  default but do not override an explicit `PYTHONIOENCODING`; the runtime
  reconfigure does. (P1)
- **Skill/rules paths resolved to `.claude` under Kilo/Qwen.** The runtime IDE
  layer (`ide_utils`) only knew claude/cursor/windsurf/codex, so under a
  Kilo-only install `detect_ide()` fell back to claude and skill install /
  SessionStart profile rebuild targeted `.claude` instead of `.kilo`. `qwen`
  (`.qwen`/`QWEN.md`) and `kilo` (`.kilo`/`AGENTS.md`) are now registered and
  detected via their project dirs + `TAUSIK_IDE`. (Env-var auto-detection for
  kilo/qwen is intentionally deferred until verified on a live build.) (P5)

### Added

- **`task quick --ac/--acceptance`.** Quick-create a task with its acceptance
  criteria in one command, so it is QG-0-ready (goal + AC) without a follow-up
  `task update`. Blank/whitespace AC is ignored — QG-0 is unchanged. Exposed on
  the `tausik_task_quick` MCP tool as well. (P2)
- **`tausik doctor` validates the Kilo MCP config.** When a `.kilo/`/`.kilocode/`
  install is present, doctor checks that `kilo.jsonc` / `mcp.json` parse (JSONC
  tolerated), carry a `tausik-project` `mcp` stanza with a `command` array, and
  that the referenced `server.py` resolves (`${workspaceFolder}` expanded). Each
  finding tells you to re-bootstrap and restart Kilo. Silent for non-Kilo
  projects. (P3)

### Internal

- Guard tests lock the IDE single-source invariant (`SCAFFOLD_IDES ⊆ IDE_DIRS`,
  argparse choices and `--ide all` derive from the constants, no hardcoded IDE
  list literal in `bootstrap/`) and the Unicode-stdio fixes (wrapper, hooks, MCP
  servers, bootstrap).

## [1.5.5] — 2026-06-19

### Added — Kilo Code + z.ai (GLM) first-class support

- **`--ide kilo` bootstrap target.** `bootstrap.py --ide kilo` re-exposes the
  TAUSIK MCP server inside Kilo Code (VSCode addon + CLI). The MCP stanza is
  written to **both** known Kilo config paths — `.kilo/kilo.jsonc` and
  `.kilocode/mcp.json` — so it works across Kilo versions (Decision #120). Format
  is Kilo-native (`mcp` key, `command` as an array, `type: local`, `enabled`);
  existing servers are merged, not overwritten; re-runs are idempotent. Override
  the target paths via `.tausik/config.json` `kilo.config_paths`.
- **Model profiles as data — z.ai GLM routing with no code change** (Decision #119).
  New `scripts/model_profiles.py` maps vendor families (`claude`, `glm`) ×
  capability ranks → concrete model ids, overridable/extendable in
  `.tausik/config.json` `model_profiles.families`. `suggest_model(family=…)` and
  the task-start banner now recommend **within the active model's family**: a
  z.ai GLM session (Anthropic-compatible endpoint → transcript reads `glm-*`)
  routes to GLM models and gets correct under/over-powered verdicts. Optional
  `model_profiles.default_family` pins the family when detection is unavailable.
- **Provider registry** (`scripts/providers/`) abstracting runtime/IDE detection
  (claude/cursor/kilo/qwen). Kilo reads the active model from `KILO_MODEL` /
  `.kilo` config; Claude delegates to the existing transcript parser.
- **Docs:** [Kilo + z.ai](docs/en/kilo-zai.md) (+ RU mirror) — setup, model
  switching, secret hygiene; architecture two-axis (runtime × model) table.

### Changed — rename-proof generated configs

- Generated MCP configs and Claude hooks no longer embed absolute project paths,
  so **renaming the project folder no longer breaks the framework**. In-project
  paths use the host's workspace variable — `${CLAUDE_PROJECT_DIR:-.}` (Claude
  `.mcp.json`), `${CLAUDE_PROJECT_DIR}` (Claude hooks), `${workspaceFolder}`
  (Cursor, Kilo); paths outside the project (system venv, external lib) stay
  absolute. Shared helper `bootstrap/bootstrap_paths.py`. Qwen Code is unchanged
  (no workspace variable in its config format) — tracked as a follow-up.

### Fixed

- Provider scaffold rewritten: removed a syntactically broken `claude.py`,
  inconsistent registration, and a `model_routing` import that silently nulled
  active-model detection.

## [1.5.3] — 2026-06-15

### Fixed (Windows)

- **CLI wrapper failed on every command (critical regression).** A literal `(` / `)` in the "no scripts dir found" error text sat *inside* the `if not defined SCRIPTS (...)` block in `tausik_wrapper.cmd`, closing the block early — so `exit /b 1` ran unconditionally and `.tausik/tausik.cmd <anything>` exited 1 right after bootstrap. Rewritten to `goto :noscripts` (no inline block to break) with an explicit `exit /b %ERRORLEVEL%` so the wrapper propagates Python's exit code. Now covered by a Windows `.cmd` smoke test (passthrough + negative).
- **RAG index silently empty on projects with reserved-name paths.** A path component that is a Windows reserved device name (`con`/`prn`/`aux`/`nul`/`com1-9`/`lpt1-9`, with or without an extension) makes `os.path.relpath` raise `ValueError`, which aborted the entire `os.walk` in `codebase-rag`'s `get_file_list` → an empty code index with no error. Added `_is_reserved_name` pruning (dirs and files) plus defensive `try/except ValueError` around both `relpath` calls; mirrored into the Cursor harness copy.

## [1.5.2] — 2026-06-15

### Security / housekeeping (public-release readiness)

- **Removed confidential material from the tree.** `docs/audit/` (internal GTM/COI strategy, private-repo paths, a 1.7MB audit PDF) and `site/_archive/` (a leaked internal GitLab URL) are deleted and gitignored — they should never have shipped in the public mirror. (Earlier 1.5.x tarballs still contain them; this is the first clean release.)
- **Onboarding fixes.** The Windows quickstart command pointed at a nonexistent path → `.tausik/tausik.cmd status`. The CLI wrapper now resolves `.qwen/.windsurf/.codex/scripts` (Qwen/others were broken).
- **Doc accuracy.** Corrected showcase counters (tests 4341, MCP 124, 20 official / 13 core skills, matrix v1.5.1) and added the RU coverage badge.
- **Community health files.** Added SECURITY.md, CODE_OF_CONDUCT.md, issue/PR templates.

All driven by a multi-agent public-release-readiness audit.

## [1.5.1] — 2026-06-15

### Fixed

- **CLI broken on a clean install (critical).** Every `tausik` command crashed with `ModuleNotFoundError: No module named 'yaml'` on a fresh clone: `project.py` imports the RENAR CLI unconditionally and the renar modules did a module-level `import yaml`, but PyYAML is an OPTIONAL dependency (the core CLI is stdlib-only). yaml is now lazy-imported inside the renar functions that emit it — the core CLI (`init`/`status`/`task`/…) loads stdlib-only, and `renar conformance/export` degrade with a clear `pip install pyyaml` hint when it's absent. Guarded by an AST test + a release-checklist fresh-clone smoke. Found by the post-1.5.0 fresh-clone smoke.

## [1.5.0] — 2026-06-15

The pre-2.0 hardening release. Cryptographic verification receipts, fail-closed gates, scope ACL, closure-risk scoring + external review, the AIDD layer, orchestrator-worker delegation, advisory-first RENAR, and "no silent errors" enforcement.

### AIDD layer — cross-IDE parity

- **`tausik aidd autogen [--write] [--force]`.** Drafts a `vision.md` pre-seeded from repo signals (package name/description, README title/intro, top-level dirs, detected languages, test framework). Stdlib-only, no LLM; missing signal → placeholder, never crashes; reuses the scaffold conflict prompt. Bootstrap now bundles `harness/aidd-templates` into the generated tree (also fixes `init --template aidd` via the CLI wrapper).
- **`tausik aidd validate`.** Checks `conventions.md` machine-checkable claims (language/version pin, lint/format tool, testing framework, max file-size) against the repo: ok / drift / unverifiable; exit 1 on hard drift, 2 if missing. Numeric version + word-boundary tool matching (no substring false-positives).

### Memory strictness & agent-UX

- **Context memory surfaced at session start.** `context`-type memories (durable env facts: hosts, machines, access, paths) now appear in the CLAUDE.md memory tail every session, plus a hard **memory-first** rule: `memory_search` before asking the user for / guessing an established project fact.
- **`update-claudemd` syncs AGENTS.md** dynamic section alongside CLAUDE.md.
- **Threshold-gated FTS optimize** on session end (events-churn proxy, best-effort).
- **Coverage badge** (76% baseline) + CI `coverage.json` artifact upload.
- Fix: dropped a phantom `diff` extension skill (no more `skills not found: diff` on bootstrap).

### No silent errors — enforced

- **ruff BLE001 enabled** across the tree: every blind `except Exception` is now justified with `# noqa: BLE001 — <why>` or narrowed; new unjustified blind catches fail CI. Makes the "нулевая толерантность к тихим ошибкам" principle real.

### Orchestrator-worker — model auto-switch via sub-agents

- **`tausik task delegate <slug>`** marks a complexity≤medium task delegated to a worker sub-agent (records the recommended model + parent session in the `meta` kv — no schema migration); complex tasks are refused (they stay with the coordinator). `task undelegate` clears it.
- **`tausik task handoff <slug>`** prints the deterministic worker contract (goal/AC/scope/scope_exclude/model + trimmed `WORKER_SKILLS`) the coordinator passes to the Agent tool.
- **In-session recognition:** `task start` on a delegated task surfaces worker mode and suppresses the orchestrator-only model banner. **Scope hard-gate:** a delegated worker is blocked from editing outside its `scope_paths` (and blocked until it declares one).
- **`tausik task summary-back <slug> "<summary>"`** returns a structured worker result (stored in `meta`, surfaced in `task show`) so the coordinator picks it up without the worker transcript. CLI-first; full workflow documented in `architecture.md`.

### RENAR adoption — advisory-first ("lite")

- **`tausik renar export [--out] [--check]`.** Deterministic, one-way derived view of the SQLite project into a `renar/` tree (README + conformance + specs + adapts). `--check` is a CI drift gate; the export is date-free and pinned to `eol=lf` (`.gitattributes renar/**`) for stable diffs, with a containment-guarded `--out` target.
- **RENAR SPEC + ADAPT substrate.** 17 MCP tools (`tausik_spec_*` ×8, `tausik_adapt_*` ×9): formal requirements (SPEC, 9 closed types) and TZ-interpretation (ADAPT §7) with forward-interpretations, closed-list backward findings, and dual ed25519/name signatures. Documented in `docs/ru/mcp.md`.
- **First self-applied SPEC-ARCH + ADAPT.** TAUSIK reached **RENAR-1** on honest data (blocked at RENAR-2 — ADAPT left draft, no faked client signature); `tausik renar conformance` self-assesses the level.
- **QG-0 advisory (lite, rung 2).** A non-blocking nudge when a high-stakes task (tier `substantial`/`deep`, or `complex`) starts without a linked SPEC/ADAPT — toggle `renar.qg0_advisory`. RENAR is adopted advisory-first by design (lightweight framework); hard-gate (rung 3) and signed/immutable RENAR-2 (rung 4) are 2.0 work. See the adoption ladder in `architecture.md`.

### Evidence attestation — cryptographic receipts

- **Signed verification receipts.** `tausik verify` emits an ed25519-signed receipt (`tausik-signed/v1`) bound to the gate signature and HEAD sha; `task done` (QG-2) validates the signed receipt before closing, so a green cannot be forged or replayed.
- **Portable receipts + offline verify.** Export a receipt and verify it with no SDK: a stateless HTTP verify endpoint plus a CI-tested no-SDK example guide.
- **Supply-chain signing.** Skill and stack releases are signed; skill installs verify the signature before writing.

### SENAR hardening

- **Rule 2 scope ACL.** Tasks declare `scope` / `scope_exclude`; a write-enforcement hook blocks edits outside the declared surface; the QG-0 scope warning is now a hard gate.
- **Closure-risk scoring.** A composite risk model computes + persists a closure-risk score on `task done`, surfaced in `metrics` / `status`; measured-high closures require an L3 adversarial review before they can close.
- **Rule 4 external validation.** A `tausik-external-reviewer` subagent (different model, read-only — separation of duties) gates high-risk closures; a domain-challenge question was added to the QG-2 checklist.
- **Rule 5 checklist hard gate** for substantial/deep planning tiers (escalating nudge for smaller tiers).
- **Rule 7 root cause.** Fail-closed keyword gate (defect tasks cannot close without a documented cause) plus a **structured** layer — closed-list categories + parser + coverage metric in `metrics` + an advisory escalating nudge toward `Root cause (category): … Prevention: …`.
- **Fail-closed gate policy** across the QG-2 surface (a gate that cannot evaluate blocks rather than passes).

### Reliability, routing & drift

- **Shell-less gate runner.** `shell=True` dropped — gate commands are tokenized (shlex) and only `&&` / `|` are honoured; every other shell metacharacter fails safe (command-injection fix for custom-stack templates).
- **Escalating nudges framework** (silent → hint → warning → strong) — soft invariants get louder per breach and reset on compliance, replacing the tuned-out fixed reminder.
- **Model routing.** Tier-aware verdict (haiku < sonnet < opus < fable) kills the false `MODEL MISMATCH` banner for capable models on medium/complex tasks.
- **Doc-drift gate.** `gen_doc_constants --check` now scans cross-file version refs, MCP tool counts, test counts, and repo-state counts, plus an MCP-description cache-bust hash.
- **Memory lint.** `tausik memory lint` flags contradictions, superseded entries, and stale file references.

### Fixed

- **MCP `task_done` / `verify` hang (Windows).** Restored `stdin=subprocess.DEVNULL` on git subprocesses (`risk_compute`, `verify_receipt_emit`, `cli_push_ok`) — a reintroduction of `v14b-defect-mcp-task-done-stdin-hang` where git, inheriting the MCP JSON-RPC stdin pipe, blocks on a paginator/credential probe. Added an AST class-guard test that fails on any `scripts/` top-level `subprocess` call missing a `stdin` argument, so the class cannot silently return again.

## [1.4.2] — 2026-05-15

### Site

- **Landing rework — honest slogan + concrete Without/With + enforcement-in-hero.** The v1.4.0 slogan ("Git for AI workflow") was clever but misleading — Git is version control for source files; TAUSIK is a discipline layer over coding agents. Replaced with a direct, pain-point slogan: **"AI agents that can't fake 'done'."** (EN) / **"AI-агенты, которые не врут «готово»"** (RU). Eyebrow shifted from the generic "AI development framework" / "Фреймворк AI-разработки" to **"Discipline layer for AI coding agents"** / **"Discipline-слой для AI-кодинг-агентов"** — first-time visitors now read what TAUSIK *is* in the first six words. Hero lede tightened to name the two failure modes the framework intercepts: "starting a task without a goal, and claiming completion without proof." Hero terminal demo now opens on a **BLOCKED — no active task** line (red, weight 600) showing enforcement before showing the happy path; the previous version led with the happy path and never demonstrated a block.

- **Without/With rows rewritten with concrete agent phrases.** Each of the six rows was abstract ("Agent starts coding immediately"). Now each is a concrete agent-quote + the matching hook output — e.g. `'Agent says "I'll quickly refactor this" and edits 30 files.'` → `'task_gate.py hook returns: BLOCKED — no active task (SENAR Rule 9.1).'`. Six rows, six concrete failure modes, six named code paths (task_gate.py, task_done_verify, SessionStart hook, tausik dead-end, tausik verify, tausik metrics + events log). EN + RU.

- **Three-message cycle: section name → "Task lifecycle".** Eyebrow + title (EN: "Task lifecycle / Three messages. Full lifecycle." | RU: "Жизненный цикл задачи / Три сообщения. Полный цикл.") so the section reads as "what TAUSIK organises" rather than "the pitch line". Cycle.sub rewritten to: "You describe what you want. The framework forces the steps you skip when you trust the agent too much." — names the actual problem the framework solves (skipping under trust) rather than the abstract "you describe what you want; framework enforces how it gets done".

- **Stats reframed — main framework promise made visible.** Old stats tiles: `732 tasks completed / 73 sessions / 3,378 tests / 0 core dependencies`. The 73-sessions and bare 732-tasks numbers are dogfood trivia, not framework-trust signals. New tiles surface the gate-truth headline: `732 tasks closed — every one with a goal + AC / 0 closed without verify evidence (accent) / 3,400 tests passing / 0 core dependencies / phone-home calls`. Same numbers, different framing: visitor now reads how the framework was actually used. EN + RU.

### Internal

- pyproject.toml: 1.4.1 → 1.4.2. docs/_generated/constants.json regenerated. README badges unchanged (test_count stable at 3400).

## [1.4.1] — 2026-05-15

### Fixed

- **`tausik_search` FTS5 syntax error on `.` in query (`bug-tausik-search-fts5-syntax-error-on-dot`).** `tausik_search "tausik.tech site"` (and any query with `.`, `-`, `/`, `@`, `#` inside a token) raised `sqlite3.OperationalError: fts5: syntax error near "."` because the previous `_sanitize_fts5` stripped only `"`, `(`, `)`, `*`, `:`, `^` and the boolean keywords `AND` / `OR` / `NOT` / `NEAR`. FTS5 then read the leftover dot as a column separator (`col.match` syntax) and aborted. Fix wraps any token that contains one of those special characters in phrase quotes — `tausik.tech` becomes `"tausik.tech"`, which the default `unicode61` tokenizer renders as the phrase `"tausik" "tech"`. Bare alphanumeric tokens still go through unquoted (so implicit AND between words is preserved), and the existing `"quoted phrase"` extraction still works first. Internal: `scripts/backend_queries.py` `_sanitize_fts5`. Tests: `tests/test_fts5_sanitizer.py` (22 cases — plain query, empty, dot in token, hyphen, slash, trailing dot, quoted passthrough, boolean operator stripping, paren/star/colon/caret, mixed phrases + tokens, `@` / `#`, plus a parametrized end-to-end matrix that runs each shape against a real FTS5 virtual table and asserts no `OperationalError`). Surfaced on the live `tausik_search("tausik.tech")` query that motivated the bug ticket — it now returns rows. Affected callers: `tausik_search` (MCP + CLI), `memory_search`, `decisions search`, `task list` FTS lookups — all consume the same sanitizer.

### Site

- **Dockerfile build context fix.** v1.4.0's `site-numbers-truth` commit wired `HomeLanding.vue` to import `docs/_generated/constants.json` for the live counts on the landing, but the Dockerfile copied only `docs/en` and `docs/ru` into the build context. Vite/rollup failed at `pnpm build` with `Could not resolve "../../../../docs/_generated/constants.json"`, killing three consecutive deploys (pipelines 2273, 2275, 2276) and stranding `tausik.tech` on the previous release commit. Fix adds `COPY docs/_generated docs/_generated` between the existing `COPY docs/ru` and `COPY site/` lines; `.dockerignore` does not exclude `_generated`. CI on the fix commit (`a7aa6d4`) reached `deploy success` in 24s. No code path changed; the bug was purely in build wiring.

- **Honest landing-numbers + audit-driven doc refresh.** v1.4.0 polish that landed in the same release window: HomeLanding numbers (review_agents_count, hooks_count, skills_core_count, mcp_main_tools, test_count, stacks_count) read from `docs/_generated/constants.json` via a new `scripts/code_counts.py` helper; "0 dependencies" → "0 core dependencies"; "5-agent review" → "6-agent review"; "19 real-time hooks" → "20 real-time hooks"; "25 stack-aware checks" → "25 stack-aware verify suites"; release-snapshot label on the 732/73 stats tiles. 4-agent documentation audit found and closed 58 defects (32 WRONG, 22 DRIFT) across `architecture.md` (Schema v18→v27, 16→25 gates, 117→138 source files, 2590→3378 tests), `hooks.md` (full lifecycle rewrite — 20+1 hooks, 3 missing PostToolUse rows, brain_search_proactive moved out of UserPromptSubmit), `cli.md` (+9 missing commands), `mcp.md` (98→103, +3 missing tools), `troubleshooting.md` (CouchDB/Meilisearch/Raven legacy purged, replaced with Notion-flow), `plan-stacks.md` (18 phantom rows removed, 13 real stacks added — `/plan` skill now reads truth), `skill-spec.md` + `skill-profiles.md` (11 core skills, two-axis claim qualified), `shared-brain.md` ("Still TODO" of 14 already-shipped modules removed), `environment.md` (full TAUSIK env-vars reference for the first time, 50+ vars), `troubleshooting.md` Brain section rewritten under the Notion architecture. EN+RU sidebars surface 12 previously-orphan pages. Landing also gained a **TAUSIK is NOT** section (5 bullets — not SaaS / not a model / not a Cursor replacement / not junior onboarding / not auto-merging), a **comparison table** vs Aider / Cursor Rules / Continue / Claude Skills, and a **FAQ** (5 questions). Hero lede rewritten to a concrete product-shape sentence; quickstart eyebrow now reads "Quick start — 10 minutes (after your AI IDE is set up)" with a Windows-wrapper note in the side-bullets. Live: https://tausik.tech / https://tausik.tech/ru/.

### Planned (v1.5)

- **Cursor MCP integration rework.** Composer / workspace MCP filesystem mirror (`mcps/` lease snapshot) in Cursor 3.2.x **does not currently publish project stdio servers** (`tausik-project`, `codebase-rag`, `tausik-brain`) into the same snapshot path as the built-in browser MCP — they appear in `lease_server_status` but **`cursor_mcp_lease_snapshot_store` lists only `cursor-ide-browser`** (see investigation: [`docs/en/research/tausik-1.5-mcp-cursor-rework-2026-05-08.md`](docs/en/research/tausik-1.5-mcp-cursor-rework-2026-05-08.md), RU: [`docs/ru/research/tausik-1.5-mcp-cursor-rework-2026-05-08.md`](docs/ru/research/tausik-1.5-mcp-cursor-rework-2026-05-08.md)). v1.5 backlog: host contract matrix, optional HTTP/SSE bridge or extension registration, diagnostic script, upstream report — **without** dropping the supported **`.tausik/tausik` CLI** fallback.

## [1.4.0] — 2026-05-07

### Added

- **Push-ticket flow replaces broken env bypass (`replace-broken-git-push-gate-env-bypass-with-ticke`).** New CLI `tausik push-ok [--ttl SECONDS]` writes a single-use ticket at `.tausik/.push_ticket.json` (schema_version=1, default 60s TTL, atomic write with temp-then-rename) bound to current HEAD SHA + branch. `scripts/hooks/git_push_gate.py` rewritten to consume the ticket on a valid match (schema + non-expired + HEAD-SHA match) and re-block on missing / expired / malformed / mismatched / already-consumed. The historical `TAUSIK_ALLOW_PUSH=1` env path is **removed** — it never worked across IDEs because PreToolUse hooks run in the harness process, not the Bash subprocess (Claude Code, Cursor, Qwen Code all share this constraint), so inline `VAR=val git push` env never reached the hook. Skills `/commit` (step 8) and `/ship` (sonnet/haiku variants) updated to run `tausik push-ok && git push` after user "y". `TAUSIK_SKIP_PUSH_HOOK=1` retained as a debug-only bypass; new `TAUSIK_PUSH_TICKET_PATH` env override added for tests. Single-use + short TTL + bound-to-HEAD reduce the accidental-push window; this is a discipline rail, not a malicious-agent firewall (that role belongs to `bash_firewall.py` for force-push and IDE permissions). New: `scripts/cli_push_ok.py` (~110L), `tests/test_push_ok_cli.py` (10 tests — atomic write + temp leftover + overwrite + nested mkdir + detached-HEAD normalization + TTL math + zero/negative TTL rejection + E2E subprocess via `project.py push-ok`). Modified: `scripts/hooks/git_push_gate.py` (full rewrite — env check removed, ticket validation + consumption added), `scripts/project.py` (dispatch wire), `scripts/project_parser.py` + `scripts/project_parser_ops.py` (subcommand registration), `tests/test_hooks.py::TestGitPushGate` (13 tests — ticket happy / missing / expired / SHA-mismatch keeps ticket / malformed / wrong schema_version / one-shot second push blocked / SKIP_PUSH_HOOK still bypasses / old ALLOW_PUSH env no longer bypasses). Skills: `harness/skills/commit/SKILL.md`, `harness/skills/ship/SKILL.md`, `harness/skills/ship/variants/model/{sonnet,haiku}.md`. Docs: `docs/{en,ru}/hooks.md`, `docs/en/security.md`, `docs/ru/troubleshooting.md`, `docs/ru/environment.md`.

- **Mass test parametrize, batch 1 (`v14c-mass-parametrize-batch-1`).** [partial completion — long-tail in same task, 1.4 closure target] Collapsed 25+ pytest dedupe groups from the regenerated 2026-05-07 audit (212 groups / 587 tests, supersedes 2026-05-02) into `@pytest.mark.parametrize` blocks across 19 test modules. ~125 `def test_*` functions removed in source; no production code changed; no behaviour regression (3345 passed). Cross-file groups handled per-file (no test moves between modules). G7+G13 merged together (12→1, two audit groups eliminated in one edit). G15 lifted cross-class to a module-level parametrized `test_generator_emits_required_markers` in `test_bootstrap_generate.py`. Auto-format hook applied during edits. G8+G18 in `test_hooks_common.py` (12 negative-bypass cases including U+2028/U+2029/U+0085 invisible separators) merged via a byte-aware Python script that preserves the unicode bytes in test text — Edit-string match could not preserve them, so the merge runs through `re.sub` on the file content with utf-8 round-trip. Spawned two defect tasks for pre-existing failures discovered during full-suite verification but unrelated to this batch: `v14c-defect-mcp-tool-handler-drift` (test_every_tool_name_has_handler) and `v14c-defect-bulk-decisions-stress` (test_bulk_decisions). New: `docs/ru/research/tausik-1.4-pytest-dedupe-2026-05-07.md` (regenerated audit baseline). Modified: `tests/test_ac_evidence_json.py`, `tests/test_audit_orphan_files.py`, `tests/test_audit_stale_docs.py`, `tests/test_audit_unused_python.py`, `tests/test_bootstrap_generate.py`, `tests/test_brain_fallback.py`, `tests/test_brain_hook_utils.py`, `tests/test_brain_schema.py`, `tests/test_brain_search.py`, `tests/test_brain_universality.py`, `tests/test_doctor_drift_baselines.py`, `tests/test_edge_cases.py`, `tests/test_memory_cleanup_cli.py`, `tests/test_model_routing.py`, `tests/test_qg0_dimensions.py`, `tests/test_rag.py`, `tests/test_rag_edge.py`, `tests/test_senar.py`, `tests/test_service_verification.py`, `tests/test_session_cleanup_check.py`, `tests/test_skill_manager.py`, `tests/test_skill_profile_detect.py`, `tests/test_stack_go_rust.py`, `tests/test_stack_iac.py`, `tests/test_stack_php_js.py`, `tests/test_task_start_model_banner.py`.

- **Per-task cost / token budget with runaway protection (`v14c-token-budget-task`).** Sister to `call_budget`. Adds USD-spend and token-total caps per task, with two enforcement points: at `task_done` (write actuals back + 1.5× warning) and after every tool call (`PostToolUse` hook emits stderr at 1.5× WARN / 2.0× BLOCKER). **Schema v27** adds 4 nullable columns to `tasks`: `cost_budget_usd REAL`, `cost_actual_usd REAL`, `token_budget INTEGER`, `tokens_actual INTEGER`. Existing rows get NULL — feature is opt-in per task. **CLI**: `tausik task add|update --cost-budget <USD float> --token-budget <int>`. Validation in `service_validation.validate_task_add_inputs` rejects negative values with descriptive errors; non-numeric is type-coerced via `float()`/`int()` raising `ServiceError`. **Backend setters**: `task_set_cost_budget` / `task_set_cost_actual` / `task_set_token_budget` / `task_set_tokens_actual` in `backend_crud.py` (mirror of existing `task_set_call_*` shape). **Rollup helper**: `usage_events_cost_rollup_for_task(slug, since=task.started_at)` in `backend_queries_usage.py` — same safety contract as `usage_events_cost_rollup_by_task` (`task_slug = ?` filter excludes session_record NULL-slug double-count rows automatically). Returns `{task_slug, event_count, tokens_total, cost_usd}` — zero-event case yields zeros, never None. **`task_done` flow**: new `service_recording.record_cost_actual` runs after `record_call_actual`, rolls up usage for the task's started_at window, writes `cost_actual_usd` + `tokens_actual` back to the row, returns warning string when actual > 1.5× of cost_budget OR token_budget (independent triggers). Never raises — DB / type errors return empty warning so `task_done` lifecycle never breaks. **PostToolUse hook** `scripts/hooks/task_cost_budget_check.py` (~230L): after every tool call, finds the SINGLE active task with at least one budget set, rolls up `usage_events`, classifies into `WARN` (1.5× ≤ ratio < 2.0×) / `BLOCKER` (≥ 2.0×) / None. Emits one stderr line per tool call at the chosen level, throttled to 1 emission per 30s per `(slug, level)` via atomic write to `.tausik/.cost_budget_throttle.json` (write-temp-then-rename, leftover .tmp cleanup on error). Silent no-op when `TAUSIK_SKIP_HOOKS=1`, 0 or ≥2 active tasks (multi-agent ambiguity — same policy as `task_call_counter`), active task has neither budget set, DB missing or locked, or stdin malformed. Never raises (subprocess exit 0). **Bootstrap**: registered in both `bootstrap_hooks.py` (Claude — wide PostToolUse matcher `""`) and `bootstrap_qwen.py` (Qwen parity). `tests/test_bootstrap_hooks_parity.py` required-set extended. **Hard caps are advisory** — Claude Code hooks can't physically stop the agent; the BLOCKER message is a "stop and re-plan" signal the agent honors next turn. **Out of scope** (separate tasks): session-level token cap (mirror of `session_capacity_calls`), HUD/status display, token-tier mapping in `/plan` SKILL.md. **task_show** detail printer surfaces `cost: actual=$X / budget=$Y` and `tokens: actual=N / budget=M` lines when the new columns are set. New: `scripts/hooks/task_cost_budget_check.py` (~230L), `tests/test_cost_budget_task.py` (37 tests — schema migration, validation reject/accept matrix on add+update, rollup happy/zero-event/cross-slug/since-filter, record_cost_actual writes-back + warn at 1.5×/no-warn within / no-warn without, hook subprocess: 7 silent no-op variants + WARN/BLOCKER for both cost and tokens + throttle dedupes + atomic write integrity, hook unit-level: classify/should_emit/format_msg). Modified: `scripts/backend_schema.py` (v27 + canonical CREATE TABLE), `scripts/backend_migrations.py` (v27 ALTER), `scripts/backend_crud.py` (4 setters), `scripts/backend_queries_usage.py` (rollup_for_task), `scripts/service_validation.py` (negative-budget rejection), `scripts/service_task.py` (task_add/update wiring), `scripts/service_recording.py` (record_cost_actual), `scripts/service_task_done.py` (call after record_call_actual), `scripts/project_parser_task.py` (--cost-budget / --token-budget flags), `scripts/project_cli_task.py` (CLI dispatch + task_show printer), `bootstrap/bootstrap_hooks.py` + `bootstrap/bootstrap_qwen.py` (hook registration), `tests/test_bootstrap_hooks_parity.py` (required-hook set), `docs/{en,ru}/cost-telemetry.md` (Per-task cost/token budget section). Pytest scoped on cost-budget suite: 37 PASS.

- **Semantic universality layer + 4 new regex topics (`v14c-ai-classifier-universality`).** Closes the gap left by B3 (regex-only `brain_universality.py`) — synonyms ("access control" → `rbac`, "token bucket" → `rate-limit`) were silently missed because the regex layer is literal-keyword bound. **Two changes, one combined hint pipeline.** **(1) Regex extension**: `_TOPIC_PATTERNS` gains 4 new entries — `csrf` (CSRF, XSRF, Cross-Site Request Forgery), `graphql` (GraphQL, gql query/mutation/subscription/schema/resolver), `feature-flag` (feature flag/toggle), `circuit-breaker` (circuit breaker, bulkhead pattern). All four use `\b` word-boundary regexes with explicit false-positive tests (`xcsrfx`, `photographqlike`, bare `feature`, electrical `circuit`). New `KNOWN_UNIVERSAL_TOPICS` frozenset (= `_TOPIC_PATTERNS.keys()`) exported for the semantic layer. **(2) Semantic layer**: new `scripts/brain_universality_semantic.py` (288L) — pure stdlib, zero new deps. `find_similar_universal(content, conn, threshold, limit)` tokenizes content (lowercase, stopwords filtered, length ≥ 4, deduped, capped at 8 distinct tokens), runs each token through `brain_search.search_local` (existing FTS5 + bm25 infra), aggregates hits by `(category, notion_page_id)` keeping the best score per row, then filters: keeps only rows whose `tags` overlap `KNOWN_UNIVERSAL_TOPICS` AND whose bm25 score ≤ threshold (default 8.0; lower = better). Returns `[(topic, best_score), ...]` sorted ascending. `emit_semantic_universality_hint(text, cfg)` gates on `brain.enabled` AND `brain.semantic_universality_enabled` (new config knob, default True) AND mirror file existing on disk; topics already caught by the regex layer are deduped out so users see only NEW signal; never raises, never blocks. **(3) Wire**: `emit_universality_hint` (the public API called from `service_knowledge.memory_add`, `brain_runtime.try_brain_write_decision`, `brain_runtime.try_brain_write_web_cache`) now invokes both layers — regex first (fast, synchronous), semantic second (opt-in, FTS5). All 3 call-sites unchanged at source level. Memory dead-end #27 (ChromaDB rejected as too heavy) and CLAUDE.md stdlib rule both honored — no ML, no embeddings, no new deps. Future ML extension is explicitly **out of scope** for 1.4 — captured as separate v1.5 backlog if ever needed. New: `scripts/brain_universality_semantic.py` (288L), `tests/test_brain_universality_semantic.py` (32 tests — token extraction edge cases, find_similar_universal happy/empty/threshold/exception/tag-filter paths, emit_semantic gating across enabled/disabled/missing-mirror/empty-text/dedupe-vs-regex/new-topic-detection/pathological-input, integrated `emit_universality_hint` triggering both layers when brain enabled). Modified: `scripts/brain_universality.py` (new topics + `emit_universality_hint` invokes semantic), `scripts/brain_config.py` (new `semantic_universality_enabled: True` default), `tests/test_brain_universality.py` (+9 cases — 8 new-topic positives + 6 false-positive guards + universe sanity check), `docs/{en,ru}/memory-merge-guidelines.md` (semantic-layer section + 4 new topics in the table). Pytest scoped on universality suite: 88 PASS.

- **Persisted per-task model recommendation (`v14c-auto-switch-model`).** Phase B already prints a `Model recommendation` banner on `tausik task start`, but the suggestion is one-shot — it scrolls past, gets ignored, and Claude Code can't switch model mid-session anyway. This task makes the recommendation outlive the print: a new `scripts/model_routing_session.py` (~140L) records the suggestion as `.tausik/.task_recommendation.json` (`{schema_version, slug, complexity, model, display, recorded_at}`) when a task starts and clears it when the task closes. Storage is intentionally separate from `.session.json` (skill_profile_session): that file's `model` key tracks the AGREED profile (env > config > auto), while this file tracks the SUGGESTED profile for the active task — different question, different lifetime, different file. `service_task.task_start` calls `record_active_task_recommendation(find_tausik_dir(), slug, complexity)` after the banner, `task_done` calls `clear_active_task_recommendation`. Both calls are wrapped in `try/except: pass` so persistence IO never blocks task lifecycle. The banner itself gains a fourth line on MISMATCH: `↪ Persist for next session: `tausik config set model_profile <slug>`` — names a concrete next action instead of relying on the agent to remember `/fast` exists. Profile slug derives from the routing model id via a small whitelist (`claude-haiku-4-5`→`haiku`, `claude-sonnet-4-6`→`sonnet`, `claude-opus-4-7`→`opus`); GPT/Qwen variants come from upstream profile work, not suggest_model, so they're omitted on purpose. Env knob `TAUSIK_DISABLE_TASK_RECOMMENDATION=1` makes record/read/clear all no-ops without raising — useful in CI or sandboxes that don't tolerate writes under `.tausik/`. Defensive: malformed JSON, non-object payload, missing required fields (`slug`, `model`, `display`, `recorded_at`) all read as None — partial writes / hand edits are treated as missing rather than yielding a half-broken dict. New: `scripts/model_routing_session.py` (140L), `tests/test_model_routing_session.py` (14 cases — record/read/clear roundtrip across simple/medium/complex, env-disable on all three operations, malformed/partial/non-object JSON read as None, isolation from `.session.json`, overwrite semantics on consecutive task_start calls, atomic write leaves no `.tmp` leftover). Modified: `scripts/service_task.py` (start/done hooks), `scripts/model_routing.py` (banner persist hint + `_model_id_to_profile_slug` mapping). Full pytest: scoped on new + model_routing + skill_profile = 45 PASS.

- **Setup-heavy fixture extraction (`v14c-setup-heavy-fixtures`).** Two test modules with repeated setup boilerplate trimmed without changing the assertion surface. **`tests/test_brain_sync.py`**: introduced compact Notion property helpers (`_title`, `_rich_text`, `_url`, `_date`, `_number`, `_select`, `_multi_select`) — each returns the exact dict shape that `map_page_to_row` inspects, so the title-vs-rich_text-vs-select-vs-multi_select type discriminators are still load-bearing — and a `_web_cache_page(**property_overrides)` builder with sensible defaults. `test_map_web_cache` shrinks from a 38-line inline page dict to a single `_web_cache_page()` call (full assertion block intact); `test_map_web_cache_default_ttl_when_missing` keeps its sparse skeleton (TTL Days / URL / Domain absent — exercises the 30-day fallback path) but each property is now a one-line helper call. **`tests/test_audit_pytest_dedupe.py`**: subprocess wrapping in `TestCli.test_real_repo_runs` (venv-python lookup + `subprocess.run` with UTF-8 env, ~13 lines) extracted to module-level helpers `_venv_python(repo)` + `_run_audit_script(repo, *args)`. Future subprocess tests that drive the audit CLI can reuse the helper without re-deriving the venv path or repeating the `PYTHONIOENCODING` env tweak. Pytest scoped on both files: 30 passed in 0.79s. Test coverage unchanged — same `assert row[<field>] == ...` checks, same return-code/stdout assertions on the CLI smoke. Note: `test_brain_runtime_web_cache.py` was originally in this task's scope but its patch-block consolidation (the `_patched_store` contextmanager) landed earlier in `v14c-rewrite-brittle-tests`; this task therefore proceeds with the narrowed two-file scope.

- **Brittle-test rewrite (`v14c-rewrite-brittle-tests`).** Replaced 5 implementation-detail tests with behaviour/structural equivalents that survive non-semantic refactors. **(1)** `tests/test_audit_pytest_dedupe.py::TestArtifactExists::test_research_artifact_committed` — pinned filename `tausik-1.4-pytest-dedupe-2026-05-02.md` swapped for a `glob("tausik-1.4-pytest-dedupe-*.md")` lookup so re-runs of the audit script (with a fresh date) don't break the test. **(2)** `TestRenderMarkdown::test_empty_groups_clean_message` (renamed → `test_empty_groups_omits_per_test_rows`): two literal-string asserts (`"No duplicate test scenarios detected"`, `"Documented false positives"`) replaced with an empty-vs-populated behavior contrast — empty input must NOT enumerate per-test rows, populated input MUST; copy can change without churning the test. **(3)** `tests/test_brain_sync.py::test_allowed_cols_matches_schema` — bespoke `re.compile(r"CREATE TABLE IF NOT EXISTS\s+(brain_\w+)\s*\((.*?)\);", re.DOTALL)` parse + handcrafted line-skipping for CHECK/FOREIGN KEY clauses replaced with `sqlite3.connect(":memory:").executescript(SCHEMA_SQL)` + `PRAGMA table_info(<table>)` — uses the actual SQLite parser so multi-line declarations, quoted identifiers, and constraint clauses are handled by the engine. **(4)** `tests/test_brain_hook_utils.py::test_multi_row_mixed_iso_formats_picks_freshest` — original case (`'.000Z'` vs `'Z'`) preserved, but parametrized with two additional ISO format pairs (microsecond `'.000000Z'`, fractional `'.5Z'`) so the epoch-vs-text correctness gate covers a wider tolerance band. **(5)** `tests/test_brain_runtime_web_cache.py` — 7 tests had near-identical 6-line `with patch("brain_notion_client.NotionClient", autospec=True), patch("brain_mcp_write.store_record", return_value=...)` blocks; consolidated into a `_patched_store(return_value)` `@contextmanager` helper at module level. Net diff is shape-preserving — same patches, same return values, same call_args inspection — but the per-test scaffolding shrinks from 6 lines to 1. The exception-injection test (`test_exception_inside_returns_false`) keeps its inline `side_effect=RuntimeError(...)` patch since it doesn't use `store_record`. Pytest scoped on the 4 files: 65 passed in 2.94s. No production code changed.

- **Skill bundles marketplace (LOCAL scope) (`v14b-skill-bundles-marketplace`).**
  Logical grouping layer over `skills-official/` vendor skills. New `skills-official/bundles.json` defines 6 bundles: `integrations` (jira/bitrix24/confluence/sentry), `data-formats` (excel/pdf/markitdown), `quality-pro` (audit/security/optimize/zero-defect/ultra), `automation` (run/loop-task/dispatch), `workflow-helpers` (daily/retro/presale/skill-test/docs), `ru-locale` (empty placeholder for future RU-specific skills). Physical layout stays flat — `tausik skill install <name>` keeps working for the 20 individual skills. New `scripts/skill_bundles.py` service module (load/list/show/install/uninstall + format helpers). New CLI `tausik skill bundle [list|show|install|uninstall] [--json]`: bundle install routes each skill through the existing `skill_install` pipeline (continues on per-skill error; skips deprecated names with migration message; placeholder bundles return clean no-op). **5 deprecated skills removed** from `skills-official/` and `registry.json`: `go` (use `/plan` + `/task`), `next` (use `tausik task next` CLI), `diff` (use `git diff` + `/review`), `onboard` (use `/start`), `init` (use `bootstrap.py --init`). Each removal includes a migration message in `bundles.json::deprecated`. **Final push to `Kibertum/tausik-skills`** (public marketplace publication) is **deferred to post-1.4** per polish moratorium — local CLI works against the in-tree mirror today and will read the GitHub raw URL once the push lands. New: `scripts/skill_bundles.py` (243L), `tests/test_skill_bundles.py` (22 tests — schema, deprecation removal, install/uninstall callback routing, error continuation, placeholder no-op, format helpers), `docs/{en,ru}/skill-bundles.md`, `docs/{en,ru}/skill-bundles-migration.md`. Modified: `scripts/project_cli_skill.py` (bundle subcommand dispatch), `scripts/project_parser_ops.py` (argparse). Live smoke: `tausik skill bundle list` → 6-row table; `bundle show integrations` → 4 skills; `bundle show ru-locale` → empty placeholder; `bundle show nope` → clean error.

- **`/start --lite` mode + tool-output truncation nudge (`v14b-start-lite-tool-truncation`).**
  Salvageable remainder of the dropped `tier2-architectural` task (CLAUDE.md split is explicitly out of scope). Two pieces. **(1) `/start --lite`** (or `/start lite` arg): `harness/skills/start/SKILL.md` Phase 3 gains a Lite Mode contract — render ≤ 50 lines (counts only, MCP Health if drifting, one-sentence Suggested Next, no handoff body / no per-task title / no warning prose). Default `/start` flow unchanged. **(2) Tool-output truncation nudge** (`scripts/hooks/tool_output_truncation_nudge.py`, NEW): PostToolUse coaching hook on `Read|Grep|Bash|Glob`. Counts lines in `tool_response`, emits a single stderr line like `[TAUSIK truncation nudge] <Tool> returned <N> lines (threshold 250, +N over). Prefer narrower scope: search_code / Grep with glob/path / Read with offset/limit.` when output exceeds the threshold. Threshold lookup: `.tausik/config.json::tool_output_truncation_threshold` (int) → env `TAUSIK_OUTPUT_TRUNCATION_THRESHOLD` → hard default 250. Hook NEVER modifies tool output (built-in head_limits already truncate content) — coaching signal only. Defensive: malformed stdin, missing tool_response, IO error → silent exit 0 so the harness never breaks. Skipped via `TAUSIK_SKIP_HOOKS=1`. Bootstrap registers it as a 7th PostToolUse hook in both `bootstrap_hooks.py` (Claude) and `bootstrap_qwen.py` (parity test enforces this). Tests: 24 cases (12 unit on threshold resolution + line counting + payload extraction; 7 subprocess integration on stderr behavior across thresholds, watched-tool filter, malformed inputs, env skip; 5 SKILL.md content checks for Lite Mode contract).

- **Sub-agent: `tausik-gate-fixer` (`v14b-subagent-gate-fixer`).**
  Read-only PLAN agent invoked from `/debug` when a `tausik verify` gate fails. New `harness/claude/subagents/tausik-gate-fixer.md` (2878B; sonnet; Read+Grep+Bash). Reads gate stderr + `docs/en/troubleshooting.md` + `docs/en/architecture.md` at runtime, returns 1-3 step JSON fix plan `{gate, family, plan: [{step, action, target, change, why}], meta}`. Action vocabulary fixed (closed set): `edit`, `extract_module`, `add_test`, `move_file`, `delete_dead_code`, `re_run_gate`. Sub-agent NEVER applies edits — invoker re-runs `tausik verify` after the plan is applied. `/debug` SKILL.md adds Step 7 documenting the auto-helper invocation pattern; `docs/{en,ru}/troubleshooting.md` add a "Failed verify-gate → tausik-gate-fixer" section; `docs/{en,ru}/skill-ecosystem.md` add a row to the Claude-native sub-agents table. Reuses the `copy_subagents()` deploy pattern landed in `v14b-subagent-reviewer`. Smoke test: synthetic ruff E501 stderr → simulated agent returned valid JSON with `edit` + `re_run_gate` plan; agent caught a stderr-line drift (formatter shifted lines) by re-reading the file and re-locating the offender. Tests: 7 cases (frontmatter contract, < 3KB size, runtime-doc citation, action vocabulary present, JSON-only enforcement, /debug skill mention, file existence).

- **Sub-agent: `tausik-reviewer` + Lite review mode (`v14b-subagent-reviewer`).**
  Claude-native sub-agent for code review. New `harness/claude/subagents/tausik-reviewer.md` (2854B; sonnet; Read+Grep+Bash) reads `harness/skills/review/agents/quality.md` + `docs/en/security.md` + `docs/en/security-checklist.md` at runtime (NOT embedded — keeps the definition under 3KB) and returns structured JSON `{scope, critical[], high[], medium[], low[], meta}`. Bootstrap deploys via new `bootstrap_copy.copy_subagents()` (Claude-only, copies `harness/claude/subagents/*.md` → `<target>/agents/*.md`; no-op for Cursor/Qwen which lack named-subagent concept). `/review` SKILL.md adds **Lite Mode** (`/review lite` or `/review src/ lite`): single sub-agent invocation instead of the default 6-agent fork. Token-economy alternative for low-stakes diffs; default 6-agent flow unchanged. AC #6 (≥30% main-context token reduction) DEFERRED — requires ≥10 baseline sessions of `token_metrics.jsonl` data; will be re-measured once baseline matures. Smoke test: planted SQL injection + cleartext-token logging → agent returned critical[] + high[] correctly. `docs/{en,ru}/skill-ecosystem.md` document the new "Claude-native sub-agents" section + add-pattern. Tests: 8 cases (file existence, < 3KB size, frontmatter contract, runtime-doc citation, JSON schema, copy_subagents deploys to claude only, no-op for non-claude IDEs, no source dir handled).

- **Brain sync display key fix (`v14b-followup-brain-sync-cursor-pulls-zero`).**
  `scripts/brain_cli_ops.py:93` was reading `payload.get("upserts")` (typo, missing 'd') and `payload.get("pulled")` (never-existed key) from `sync_category()` results, falling through to `0` and reporting `pulled 0` for every category even on successful syncs. Data was correctly written to the local mirror — only the CLI display lied. Fix: read `payload.get("upserted", payload.get("fetched", 0))` — uses the actual key names returned by `sync_all`. Original investigation hypothesized the bug lived in the delta-cursor / `--join-existing` flow; live read disproved that — sync_state populates correctly and `iter_database_query` returns pages. Sub-agent diagnosis bypassed the wrong-hypothesis trap by going straight to the return contract. Regression test in `tests/test_brain_sync.py` pins the dict-key contract between `sync_all` and `cmd_brain` (would have caught the typo at PR time).

- **Research dump audit (`v14b-junk-research-archive`).**
  Re-scoped from a manual one-time move (NOT READY: all 4 research files in `docs/{en,ru}/research/` were 3-6 days old at task time, criteria required >30) to an automated audit script. New `tausik audit research [--min-age-days N] [--json]` walks `docs/{en,ru}/research/`, filters by file age + absence of references in `tests/`, `scripts/`, `CHANGELOG.md/.ru.md`, `README.md/.ru.md`, and surfaces stale unreferenced files as cleanup candidates. Read-only — no moves, no deletes. Helper `scripts/audit_research_dump.py::audit_research_dump(repo_root, min_age_days=30)` returns `{candidates, skipped_recent, skipped_referenced, scanned}`. Replaces the manual 2026-06-02 review in the original task notes — rerun any time and act when candidates appear. Tests: 7 cases (empty dir, recent skip, old + referenced skip, old + unreferenced is candidate, age threshold boundary, multi-locale scan, CHANGELOG ref skip). docs/{en,ru}/cli.md document the new subcommand.

- **Vendor cleanup audit (`v14b-junk-vendor-usage-audit`).**
  New `tausik audit vendors [--json]` — read-only static cross-check of `.tausik/vendor/<name>/` against `installed_skills` in `.tausik/config.json`. Classifies each cloned vendor repo as `installed` (≥1 skill in config) or `vendored_unused` (cleanup candidate); errors land in `unknown` bucket. Surfaces removal command (`tausik skill repo remove <name>`) for review — audit itself NEVER deletes. Re-scoped from telemetry-based design (original AC assumed `usage_events` tracked skill invocations, but that table tracks tokens/cost only — finding logged in task notes). Helper `scripts/audit_vendor_usage.py::audit_vendor_usage(vendor_dir, config_path)` returns `{installed, vendored_unused, unknown}`. Tests: 9 cases (empty vendor dir, single installed, single unused, mixed, missing config, malformed config, vendor without skills, read-only invariant, last-modified ISO format). docs/{en,ru}/cli.md document the new subcommand.

- **GPT model profile overlays — gpt-4 / gpt-5 / gpt-5-5 (`v14b-gpt-model-profile`).**
  Unblocked by B8-pre. Added 9 telegraphic delta overlays under `harness/skills/{plan,task,ship}/variants/model/{gpt-4,gpt-5,gpt-5-5}.md`. Style: imperative voice, ≤25 lines each, **delta-only** (no base SKILL.md restatement) — encodes GPT-specific behavior nudges (aggressive parallel tool calls esp. for gpt-5/gpt-5-5, zero narrative reasoning, single-turn task completion, heredoc commit messages). Resolved via two-axis `merge_skill_markdown(skill_dir, ide=..., model="gpt-5")`. Form `gpt-5.5` (with dot) normalizes to slug `gpt-5-5` via `normalize_model_profile_slug` and resolves the `model/gpt-5-5.md` overlay automatically. Tests: parametrized 9 cases (3 skills × 3 gpt profiles) + unknown-profile fallback (`gpt-99` → base only) + dot-form normalize (`gpt-5.5` → `gpt-5-5`). docs/{en,ru}/skill-profiles.md document the GPT additions and design intent.

- **Skill profile auto-detect + two-axis variants/ + disk pre-merge (`b8-pre-model-profile-auto-detect-interactive-promp`).**
  Resolved B8 axis decision: `variants/` now has two independent subdirs — `variants/ide/{claude,cursor,qwen,codex}.md` and `variants/model/{opus,sonnet,haiku,gpt-4,gpt-5,gpt-5-5,qwen}.md`. Two-axis merge order: `base + ide overlay + model overlay`. Either or both overlays may be missing — silently skipped. Backward compat: legacy flat `variants/<slug>.md` still works via `merge_skill_markdown(skill_dir, requested_profile=<slug>)` for external skill repos. Migration of `harness/skills/{plan,task,ship}/variants/{sonnet,haiku}.md` → `variants/model/<slug>.md` and `_profile-demo/variants/{claude,codex}.md` → `variants/ide/<slug>.md`. New `scripts/skill_profile_detect.py` (`detect_ide`, `detect_model`, `normalize_model_profile_slug`, `VALID_IDES`, `VALID_MODELS`) reads env (`CLAUDE_CODE_*`, `CURSOR_*`, `QWEN_*`, `CODEX_*`, `ANTHROPIC_MODEL`, `OPENAI_MODEL`, `QWEN_MODEL`, `TAUSIK_MODEL`); model is `None` when host doesn't expose it (Cursor/Qwen UI selection). New `scripts/skill_profile_session.py` (`load_session_state`, `save_session_state`, `resolve_profile`) implements precedence env > config.json > auto-detect, persists `(ide, model, source, last_rebuild_at)` in `.tausik/.session.json` (schema_version: 1). New `scripts/skill_profile_rebuild.py` (`rebuild_skills`) walks `.claude/skills/` with sha256 cache — writes only when merged content differs (cache hit = no-op, microseconds; preserves mtime for git/watcher safety). `merge_skill_markdown` adds `_strip_existing_overlays` (idempotency: re-merging an already-merged SKILL.md never accumulates overlay sections). SessionStart hook (`scripts/hooks/session_start.py::_auto_rebuild_skills`) auto-runs detect + rebuild before context injection — silent on cache hit, never blocks. New CLI: `tausik skill rebuild [--force]`, `tausik config set {ide,model}_profile <slug>`, `tausik config show`. New scripts/project_cli_config.py keeps service code under filesize gate. `harness/skills/start/SKILL.md` Phase 0 documents the auto-rebuild contract. Tests: 56 cases (21 detect, 11 rebuild, 11 session_state, 13 skill_profile two-axis + backward compat). Local copy of `parse_skill_frontmatter` inlined into `skill_profile.py` (scripts/ no longer depends on bootstrap/ at runtime). Unblocks `v14b-gpt-model-profile` (B8): GPT model profiles can now be authored as `variants/model/{gpt-4,gpt-5,gpt-5-5}.md` overlays. docs/{en,ru}/skill-profiles.md fully rewritten.

- **Universality heuristic for brain artifact suggestions (`v14b-brain-universality-heuristic`).**
  New `scripts/brain_universality.py` — pure stdlib regex/keyword detector for 8 well-known cross-project topics: `rbac`, `jwt`, `oauth`, `rate-limit`, `pagination`, `retry`, `idempotency`, `webhook`. Public API: `detect_universal_patterns(content) -> list[str]` (sorted unique slugs, `[]` on empty/non-string) and `format_universality_hint(topics) -> str` (single-line stderr-friendly hint pointing at `brain_draft_artifact`). Word-boundary aware regexes guard against false positives like `aggregate` triggering `rate-limit`. Wired into three call sites (advisory only — never blocks): `service_knowledge.memory_add` (always, since memory has no brain auto-routing) and `brain_runtime.try_brain_write_decision` / `try_brain_write_web_cache` success paths. Hint format: `Universal pattern(s) detected: jwt, retry — consider promoting via \`brain_draft_artifact\` (or skip with \`confirm: cross-project\`).`. Tests: 33 unit cases (per-topic positives, project-specific negatives, false-positive guards for `aggregate`/`oauthorization`, multi-topic dedupe + sort, case-insensitivity, format helpers, pathological-input safety) + 8 integration cases (memory_add emission, brain_runtime success paths, detector-blowup never breaks the write). docs/{en,ru}/memory-merge-guidelines.md document the heuristic and topic list.

- **Skill discovery catalog (`v14b-skill-catalog`).**
  `tausik skill catalog [<repo>] [--json]` lists skills offered by configured/cloned skill repos: `name`, `category`, `repo`, `description`, plus `triggers` and `requires` in JSON mode. Without args it scans every repo in `.tausik/vendor/`; with a repo name it filters to one. New helper `skill_repos.repo_catalog()` (also drives the existing `repo_list_all_skills`) reads each repo's `tausik-skills.json` manifest, surfacing optional `category` field with empty-string fallback. Service entry `ProjectService.skill_catalog(vendor_dir, repo_name=, config_path=)` raises `ServiceError` for unknown repo names (not configured AND not cloned). New MCP tool `tausik_skill_catalog` with optional `repo` + `as_json` params (project tool count 95→96, main 102→103, with-rag 109→110). Mirrors landed in claude + cursor handlers/tools. Tests: 10 cases (multi-repo discovery, single-repo filter, empty vendor, unknown-repo error, configured-but-not-cloned passes, category fallback, JSON mode, repo_list_all_skills delegation). docs/{en,ru}/cli.md + docs/{en,ru}/mcp.md document the new command.

- **Memory hygiene CLI (`v14b-memory-cleanup-cli`).**
  Two new commands for long-running projects whose memory FTS has accumulated noise. `tausik memory archive --before <duration> [--confirm]` soft-archives memory rows older than the given duration (`90d` / `12w` / `2m` / `1y`); dry-run by default, idempotent on `--confirm`. `tausik memory dedupe [--threshold 0.85] [--limit 200]` lists near-duplicate pairs above the similarity threshold using `difflib.SequenceMatcher.ratio()` over `title || content`, scoped to same `type` (so a `pattern` is never suggested to merge with a `gotcha`); read-only — consolidate manually via `memory show` + `memory delete`. `memory list` / `memory search` filter `archived_at IS NOT NULL` by default; `--include-archived` (CLI) and `include_archived: true` (MCP `tausik_memory_list` / `tausik_memory_search`) opt back in. New MCP tools: `tausik_memory_archive`, `tausik_memory_dedupe` (project tool count 93→95). Schema migration v26 adds nullable `archived_at TEXT` + `idx_memory_archived_at` on the `memory` table; archived rows stay queryable via `memory show <id>` so content can be recovered before deletion. Helper module: `scripts/memory_cleanup.py` (`parse_duration_to_days`, `find_dedupe_candidates`). Tests: 18 cases across duration grammar, archive lifecycle (dry-run, --confirm, idempotency), list/search filter symmetry, and dedupe (skips different types, rejects bad threshold, ignores archived). docs/{en,ru}/memory-merge-guidelines.md document both commands.

- **Soft-archive of stale done tasks (`v14b-hygiene-archive-confirm`).**
  `tausik hygiene archive --confirm` now actually writes — it stamps `archived_at` (UTC ISO8601) on done tasks whose `completed_at` is older than `task_archive.done_age_days` (config-gated, idempotent). The row stays in `tasks` (`status='done'` unchanged) so FTS, `task_show`, decisions, and metrics keep seeing it; `tausik task list` filters `archived_at IS NOT NULL` by default and a new `--include-archived` flag (CLI + `tausik_task_list` MCP `include_archived: bool`) opts back in. Schema migration v25: `ALTER TABLE tasks ADD COLUMN archived_at TEXT` + `idx_tasks_archived_at`. `--confirm` does NOT bypass `task_archive.enabled=false`. Tests: +8 cases (apply stamps timestamp, idempotent re-run, disabled config blocks --confirm, recent done untouched, default list hides archived, --include-archived shows them, task_show still works on archived row, v25 migration adds nullable column). Spec docs/{en,ru}/task-archive-spec.md rewritten — removed "future implementation" framing.

- **Cross-file pytest test-count consistency check (`v14b-doc-gen-test-count`).**
  Follow-up to `v14b-doc-gen-mcp-tool-counts`. New `scripts/pytest_test_count.py` runs `pytest --collect-only -q --override-ini="addopts="` (60s timeout, `stdin=DEVNULL` per gotcha #88) and parses the trailing `N tests collected` summary — returning the FULL suite size independent of the fast-lane `-m 'not slow'` filter. `gen_doc_constants.py` adds `test_count` to `constants.json` (with prior-value preservation if collection fails so a transient pytest error doesn't poison the payload). Cross-file scanner extended with 4 narrow context-tight patterns: `pytest suite (N tests)`, badge URL `tests-N%20passed`, badge alt-text `[!N tests]`, markdown bold `**N tests**` — deliberately narrow to avoid noise on illustrative phrases like "Never add 5 tests where one parametrized test covers". New `--skip-test-count` CLI flag isolates the new scan; `--skip-cross-files` skips all three. First run on the live tree surfaced two real drifts: README.md + README.ru.md badges showed `2590 tests` (actual 3056) and `AGENTS.md` repo-layout `pytest suite (2590 tests)` — fixed in all four. AGENTS.md drift was inside a fenced code block (stripped by scanner); manual fix kept since scanner is intentionally fence-blind for false-positive control. Tests: +6 cases (clean-when-all-match, pytest-suite drift, badge URL+label drift, fenced-code skip, illustrative-numbers safety, `--skip-test-count` isolation). pytest 3050 → 3056 passed; ruff + mypy clean.

- **Cross-file MCP tool-count consistency check (`v14b-doc-gen-mcp-tool-counts`).**
  Follow-up to `v14b-doc-gen-cross-files`. `scripts/gen_doc_constants.py --check` now also flags drift in MCP tool-count phrasings across `README.md`, `README.ru.md`, `AGENTS.md`, `CLAUDE.md`, `docs/{en,ru}/architecture.md`, `docs/{en,ru}/mcp.md` (last two added to scan targets) — comparing every match of `**N tools**`, `N project tools`, `N brain tools`, `(N project + M brain`, ``` `tausik-brain`, N tools ``` against `constants.json` (`mcp_project_tools` / `mcp_brain_tools` / `mcp_main_tools`). Patterns are RU/EN-aware (matches `tools?` and `инструмент(а|ов)?`). Fenced code blocks are stripped before scanning so doc examples (e.g. `90 project tools (legacy example)`) don't trip the scanner. New `--skip-mcp-counts` CLI flag opts out of the new scan while keeping version-ref scan on; `--skip-cross-files` still skips both. First run on the live tree surfaced two real drifts in `docs/{en,ru}/mcp.md`: the `## Shared Brain (`tausik-brain`, 6 tools)` header was stale (actual count is 7) and the table was missing `brain_draft_artifact` — both fixed and the trailing "is 6" prose corrected. Tests: +6 cases (clean-when-all-match, brain-header drift, project drift, project+brain pair drift, fenced-code skip, `--skip-mcp-counts` flag isolation). pytest 2917 → 2923 passed; ruff + mypy clean.

- **Compound RPC `tausik_session_open` for `/start` Phase 1 (`v14b-session-open-compound-rpc-impl`).**
  Single MCP call returns one JSON envelope with `{session, status, handoff, tasks{active,blocked}, self_check}` — replaces 5 sequential calls (session_start + status compact + last_handoff + task_list active+blocked + self_check) with one round-trip. Each sub-section is best-effort: a sub-call failure surfaces an inline `error` key without aborting the envelope, so `/start` still renders a degraded dashboard. MCP tool count: 99 → 100 (93 project + 7 brain). `/start` SKILL.md Phase 1 collapses from "5 parallel tools" to "single compound call"; drift fallback to CLI on `self_check.drift_detected=true` is preserved.

- **Cross-file version-ref consistency check (`v14b-doc-gen-cross-files`).**
  `scripts/gen_doc_constants.py --check` now also walks README.md,
  README.ru.md, AGENTS.md, CLAUDE.md, docs/en/architecture.md,
  docs/ru/architecture.md and verifies every `vX.Y` / `vX.Y.Z`
  occurrence outside fenced code blocks against
  `constants.json["tausik_version"]`. 2-part refs (`v1.4`) match by
  major+minor only; 3-part refs (`v1.4.0`) require exact match.
  Foreign version timelines (`SENAR vX`, `Python vX`, `OWASP vX`) are
  detected via a 24-char lookback window and skipped — those
  products version independently. Fenced code blocks are stripped
  with line-number-preserving whitespace so reported `file:line`
  positions point at the original source line. New `--skip-cross-files`
  CLI flag preserves the prior single-file check behaviour for
  contexts where doc-scan runs separately. First run on the live
  tree surfaced 4 stale `v1.3` refs in
  `docs/{en,ru}/architecture.md` (the Scripts section was claiming
  "73 source files (v1.3)" — current count is 117 in v1.4) plus 2
  parenthetical `v1.3 CLI handlers` notes. All four updated to
  reflect current state. Tests: +7 cases — clean-when-all-match,
  minor-drift detection, patch-drift detection, foreign-version
  skip (SENAR/Python/OWASP), fenced-code-block skip, run_main
  cross-file drift exit-1, --skip-cross-files preserves legacy.
  pytest 2910 → 2917 passed; ruff + mypy clean.

- **Translation-drift audit: skip-marker + code-fence awareness (`v14b-audit-translation-skip-marker`).**
  Two improvements to `scripts/audit_translation_drift.py` that close
  the remaining 3 deferred pairs from the RU-mirror sweep without
  forcing structural parity on intentionally-abbreviated docs. (a)
  The audit now honors an HTML comment marker
  `<!-- audit-translation-drift: skip -->` placed in either side of
  a pair — those pairs are listed in a new "Intentionally abbreviated"
  section and excluded from drift counting (and from `--check` exit-1
  triggering). The marker is added to the three RU summaries that
  already explicitly point to the long-form EN doc:
  `docs/ru/claude-md-guide.md`, `docs/ru/brain-db-schema.md`,
  `docs/ru/environment.md`. (b) The heading regex now strips fenced
  code blocks before counting — `# BAD` / `# GOOD` lines inside
  ` ```markdown ... ``` ` examples no longer count as document
  headings (false positive that previously inflated EN heading counts
  in tutorial-style docs). `audit_pairs()` now returns a 4-tuple
  `(drifts, en_only, ru_only, abbreviated)`; renderers accept the
  new optional `abbreviated` arg and add an "Intentionally
  abbreviated" section. Tests: +7 cases (skip marker EN/RU side,
  code-fence heading exclusion, fence-close sanity, abbreviated
  list-rendering, --check exit-0 with only abbreviated pairs,
  has_skip_marker shape) — pytest 2903 → 2910 passed; ruff + mypy
  clean. Final audit state: zero paired drift, 3 intentionally
  abbreviated, 4 EN-only + 1 RU-only unpaired (informational). The
  full v14b RU-mirror sweep (8 originally drifted pairs) now closes
  out across 3 commits.

- **RU-mirror sweep batch 2: 2 of 5 deferred pairs cleared bilaterally (`v14b-ru-mirror-sync-batch-2`).**
  Second pass through the drift report. Resolved bilaterally:
  `architecture.md` (Δ-2 hd / +2 tbl) — removed a broken empty 3-col
  table from EN at line 51-52 (header + separator with no rows; the
  new audit script surfaced it as a doc bug); changed EN line 18 ASCII
  art `|                |` to `v                v` so the audit regex
  no longer treats vertical-pipe diagram lines as table separators
  (false-positive); added `## Hooks (anti-drift)` and `## Memory
  Aggregates` sections to EN, translated from existing RU content
  that documented `scripts/hooks/` registration and
  `service_knowledge_aggregates.py`. `security.md` (Δ-10 hd / -2 cb)
  — backported 4 RU-only sections to EN: `## Authentication` (Password
  requirements + Cookie security), restructured `## Secrets
  management` with Never / Do this instead / `.gitignore` subsections
  and a fenced `.gitignore` example, restructured `## Audit logging`
  with What to log / What NOT to log subsections, new `## Checklists`
  with Pre-commit / Pre-deploy lists. Added `## Гарантии TAUSIK`
  section to RU translated from EN's existing `## TAUSIK-specific
  guards`. Both pairs now at zero drift.

  Deferred to `v14b-audit-translation-skip-marker`: the remaining 3
  pairs (`claude-md-guide.md`, `brain-db-schema.md`, `environment.md`)
  are intentionally-abbreviated RU mirrors that explicitly point
  readers to the full EN version. Forcing structural parity defeats
  their design. The follow-up adds two improvements to the audit
  script: (a) honor a `<!-- audit-translation-drift: skip -->`
  HTML-comment marker so abbreviated mirrors are listed in their own
  section rather than as drift; (b) heading regex tracks fenced-code-
  block context so triple-backtick markdown examples (`# BAD` /
  `# GOOD` lines inside code fences) no longer count as real headings.

  Audit drift count: 5 → 3 paired (after batch 1's 8 → 5 + batch 2's
  5 → 3); pytest 2903 passed; ruff + mypy clean.

- **RU-mirror sweep batch 1: 3 of 8 drifted pairs cleared (`v14b-ru-mirror-sync-batch`).**
  First pass through the drift report from the new translation-drift
  audit script. Resolved: `docs/ru/stacks.md` (removed RU-only
  `## DEFAULT_STACKS (25)` list — TODO followup: add this 25-stack
  list to `docs/en/stacks.md`); `docs/ru/upgrade.md` (removed RU-only
  `## Версионная политика` semver section + `## См. также` cross-link
  block — TODO followup: backport both to `docs/en/upgrade.md`);
  `docs/ru/senar-compliance-matrix.md` (added missing
  `### Gaps и план закрытия` subsection with the gap-tracking table
  to match EN's `### Gaps and Plan to Close`). Deferred to
  `v14b-ru-mirror-sync-batch-2` with per-file rationale: `architecture.md`
  (EN has a broken empty table at line 51-52 — fixing parity requires
  editing EN, blocked by one-direction-sweep AC), `security.md` (RU
  has 10+ extra sections — informed review needed whether RU is stale
  or EN dropped content), `claude-md-guide.md` (+21 heading delta),
  `brain-db-schema.md` (+10 hd / +6 tbl), `environment.md` (+43 hd /
  +12 cb / +4 tbl) — last three need real translation scoped to a
  dedicated session. Audit count: 8 → 5 paired drift; full pytest
  suite still green (zero regression on markdown-only edits).

- **Translation-drift audit script (`v14b-junk-translation-drift-audit`).**
  New `scripts/audit_translation_drift.py` reports structural drift
  between EN/RU mirror docs (`docs/en/foo.md` ↔ `docs/ru/foo.md`)
  by comparing three coarse metrics per pair: ATX heading count
  (`#`..`######`), fenced code-block count (triple-backtick fences),
  markdown-table-separator count (`|---|---|` rows). Pairing by
  basename — `paired-with-drift`, `en-only`, `ru-only` rendered as
  separate sections. Three modes mirroring `audit_stale_docs.py`:
  default markdown report, `--json`, `--check`. Default mode is
  always advisory (exit 0 even when drift exists). `--check` exits
  1 only when paired drift is found, never on unpaired files alone
  — those are informational. Pure-stdlib (`re` + `pathlib` +
  `argparse` + `json`); no NLP, no semantic comparison, no auto-fix,
  no integration into pre-commit hooks or `gate_runner.py`. First run
  against the live tree surfaces 8 drifted pairs (architecture,
  brain-db-schema, claude-md-guide, environment, security,
  senar-compliance-matrix, stacks, upgrade) plus 4 EN-only and 1
  RU-only docs — exactly the visibility the spin-off was scoped for.
  Tests: 14 cases in `tests/test_audit_translation_drift.py` cover
  metric counting, drift detection per metric, unpaired
  categorisation, exit-code semantics, and JSON shape. ruff + mypy
  clean; full pytest 2889 → 2903 passed (+14, zero regression).

- **Mass test parametrize, batch 3 long-tail: WONT FIX in v1.4.0 (`v14c-mass-parametrize-batch-3`).** The size=2 long-tail (~145 groups / 290 tests, audit groups #68-212 from 2026-05-07) is **not processed** in 1.4 and is **not deferred** to 1.4.1 (per the user's "не дробить минор" guidance against patch-release polish churn). Decision #83 recorded via `tausik decide` with full cost-benefit rationale. Why: 2-test audit groups are HIGH false-positive rate — by structural hash, `test_X_returns_true` + `test_X_returns_false` and other legit happy/sad pairs look identical to actual duplicates, requiring per-group semantic review (~5 min each → ~12h for all 145). Even at perfect collapse the gain is ~4% test-count reduction (-145 tests of ~3360), diminishing returns after batches 1+2 already removed ~110 high-confidence dupes. **What 1.4 ships for dedupe:** batch-1 (size≥4, 25+ groups) + batch-2 (size=3, 33 groups) cover the high-confidence slot where structural identity ≈ semantic identity. **Rollback path for post-1.4:** if a future audit cycle re-flags specific size=2 pairs as real dupes, point-fix them in a 1.4.x patch instead of resurrecting the bulk task. **If ever revisited (post-v1.5+):** explore-first sampling pass to compute true false-positive rate before any batch processing. Modified: `CHANGELOG.md`, `CHANGELOG.ru.md`. Decision id: #83.

- **Mass test parametrize, batch 2 (`v14c-mass-parametrize-batch-2`).** Consolidated dedupe groups #35-67 (size=3) from the 2026-05-07 audit into `@pytest.mark.parametrize` blocks across 22 test modules. Cross-file groups handled per-file (tests in the same file parametrized together; lone tests in a single file from a cross-file group left alone — can't parametrize a sample size of 1). Test count moved from 3355 → 3362 collected with batch-2 collapses (full-suite pytest: 3234 passed, 8 skipped, 120 deselected slow-lane in 103.82s). README badges (`README.md` + `README.ru.md`) and `docs/_generated/constants.json` regenerated to match. Ruff: 3 errors in tests/ pre-changes → 2 after (both pre-existing, untouched). Mypy: tests/ baseline 396 → 397 errors (delta +1 import-not-found from a new monkeypatch import — same pattern as existing tests, not a new violation class). Modified test files: `tests/test_audit_unused_python.py`, `tests/test_bootstrap_frontmatter.py`, `tests/test_bootstrap_generate.py`, `tests/test_brain_classifier.py`, `tests/test_brain_mcp_handlers.py`, `tests/test_brain_search.py`, `tests/test_cost_pricing.py`, `tests/test_cq_client.py`, `tests/test_edge_cases.py`, `tests/test_gen_doc_constants.py`, `tests/test_hooks.py`, `tests/test_hooks_common.py`, `tests/test_ide_utils.py`, `tests/test_project_mcp.py`, `tests/test_senar.py`, `tests/test_service_verification.py`, `tests/test_session_cleanup_check.py`, `tests/test_task_done_verify_hook.py`, `tests/test_tausik_service.py`, `tests/test_tool_output_truncation_nudge.py`, `tests/test_v131_blind_review.py`. Auto-generated: `docs/_generated/constants.json`. Doc badges: `README.md`, `README.ru.md`. Lone-in-file cross-file fragments (groups #35/36/43/45/64) kept as-is — flagged for batch-3 follow-up if dedupe is wanted at module level.

- **Gate B (sub-agent token remeasure): KEEP-pending-remeasure (`v14b-post-subagent-remeasure`).** Both sub-agents (`tausik-reviewer` + `tausik-gate-fixer`) confirmed staying in v1.4.0; the quantitative input-token reduction remeasure (AC-3 threshold: keep ≥15%, revert <15%) is **DEFERRED to post-1.4 telemetry sweep** because the prerequisite ≥10 sample sessions with sub-agents enabled have not yet accumulated in `.tausik/token_metrics.jsonl`. Decision #82 recorded via `tausik decide` with full rationale: (a) qualitative validation already in (smoke tests caught SQLi/cleartext-token in `/review`, valid JSON plan from `/debug` auto-helper), (b) `/review lite` is opt-in so the default 6-agent flow is unaffected, (c) <3KB definition files per sub-agent — carrying-forward cost is negligible, (d) reverting now would be more disruptive than waiting one telemetry cycle. Follow-up task `v14b-followup-subagent-remeasure-quant` created for post-1.4 quantitative sweep — when ≥10 sessions accumulate, that task runs `tausik metrics tokens`, computes reduction %, records FINAL Gate B decision, and triggers the 1.4.x revert recipe (`.claude/agents/*.md` removal + `/review` revert to inline) if reduction <15%. Modified: `CHANGELOG.md`, `CHANGELOG.ru.md`. Decision recorded: id #82.

### Fixed

- **Stress test `test_bulk_decisions` — local-DB assertion vs brain routing (`v14c-defect-bulk-decisions-stress`).**
  `tests/test_stress.py::TestStressMemory::test_bulk_decisions` was failing with `assert 1 == 300` — the loop inserted 300 decisions via `svc.decide(...)` but only 1 row landed in the local DB, and the run took ~270s. **Root cause:** the test was written before the brain integration (Epic v14-brain-snippets / `service_knowledge.decide`) added auto-routing. With brain enabled in real `.tausik/config.json` and a valid `NOTION_TAUSIK_TOKEN` in env, `svc.decide(text, rationale=...)` calls `brain_classifier.classify` → routes to brain → writes to Notion → SKIPS the local `decision_add`. So 299/300 calls wrote to Notion (not local), and ~1/300 occasionally fell back to local on transient brain failures (the surviving "Decision 25", id=1). The 270s runtime was 300 sequential Notion HTTP round-trips. The bulk-stress test was always meant to measure local SQLite throughput, not brain routing — the brain detour was an unintended side-effect of the routing feature landing in `decide`. **Fix:** monkeypatch `brain_config.load_brain` to return `{"enabled": False}` in the `svc` stress fixture (same pattern as `tests/test_service_knowledge_decide.py::svc`, which is the canonical guard for tests that don't want to touch live Notion). The stress fixture now forces local-only path, so all 300 inserts land in SQLite as the test assumed. Result: 270.10s → 0.21s (~1300× speedup), 300/300 rows asserted, 5 consecutive runs all green (no flakiness). Note: this is **not** a real bulk-insert bug — production behavior is correct (brain routing is the design); the test was outdated. The stress module already carries `pytestmark = pytest.mark.slow` (line 14), so this test is excluded from the default fast-lane and the drift slipped past CI default until the user ran the slow lane explicitly. Modified: `tests/test_stress.py` (svc fixture). Ruff clean; mypy errors match baseline (3 pre-existing import-not-found in this file via runtime sys.path — same pattern as `tests/test_service_knowledge_decide.py`, no new violations).

- **MCP test drift: `tausik_memory_archive` missing from skip_tools (`v14c-defect-mcp-tool-handler-drift`).**
  `tests/test_mcp_integration.py::TestMCPHandlerDispatch::test_every_tool_name_has_handler` was failing on `KeyError: 'before'` — the test loops every entry in `TOOLS` and dispatches to its handler with empty args, maintaining a `skip_tools` set for tools that legitimately require args (52 entries already). When `tausik_memory_archive` was added (handlers.py:501; tools.py:587 with `required: ["before"]`), the test wasn't updated to skip it. Production paths are unaffected — the MCP framework enforces the `required` schema before dispatch, and the CLI uses argparse with `--before` required at parse time, so neither agent nor user ever reaches the raw `KeyError`. The drift only surfaces in this test that bypasses both validation layers. Fix: one-line addition of `"tausik_memory_archive"` to the skip_tools set, alphabetically grouped with the other `memory_*` skips. Note: the test module carries `pytestmark = pytest.mark.slow` (line 12), so it's excluded from the default fast-lane and the drift slipped past CI default runs — caught only when the user ran the slow lane explicitly. Test now passes (`pytest -m "" tests/test_mcp_integration.py::TestMCPHandlerDispatch::test_every_tool_name_has_handler` → 1 passed in 1.95s). Modified: `tests/test_mcp_integration.py`. Ruff clean; mypy errors unchanged from baseline (11 pre-existing import-not-found / union-attr in this file, not introduced by the edit).

- **Model recommendation banner — drop incorrect `/fast` advice (`v14c-banner-fix-model-recommendation`).**
  Previous banner on `tausik task start` MISMATCH said `↪ switch to <model> via /fast or model picker for cost savings`. The `/fast` part is wrong — per Claude Code system prompt, `/fast` toggles fast-output on Opus 4.6 and does NOT downgrade to a smaller model. Following the wrong hint left the user/agent puzzled when `/fast` did nothing visible. Fix: replace the verdict line with `⚠ MODEL MISMATCH — recommended <model> for cost savings`, then append two clearly-labeled actionable hints — `ⓘ Mid-session switch: use the IDE model picker (Claude Code has no programmatic switch — `/fast` toggles fast-output on Opus only)` and `↪ Persist for next session: `tausik config set model_profile <slug>``. Module docstring (`scripts/model_routing.py`) updated to drop the `/fast` reference and document the IDE-picker reality. `bootstrap/bootstrap_templates.py` "Cost-aware model selection" paragraph rewritten the same way; `QWEN.md` synced (root `CLAUDE.md` / `AGENTS.md` / `.cursorrules` did not carry the buggy line). Test `tests/test_task_start_model_banner.py::TestFormatBanner::test_mismatch_loud_warning` updated — asserts on `IDE model picker` + `tausik config set model_profile` + slug instead of the literal `/fast`, plus a negative assertion that the wrong `switch to ... via /fast` substring is absent. Scoped pytest: model_routing + banner suite green. **Rationale for the rewrite over a quick edit:** the agent (not just the user) reads this banner — leaving a wrong "actionable hint" in machine-targeted output trains the model to suggest `/fast` to the user too. Modified: `scripts/model_routing.py`, `bootstrap/bootstrap_templates.py`, `QWEN.md`, `tests/test_task_start_model_banner.py`.

### Changed

- **Filesize debt paydown: `scripts/service_gates.py` 653 → 368 over
  three files (`v14b-service-gates-debt-paydown`).**
  Final filesize-debt candidate of the v1.4-tail thread (after
  `tools_extra` / `project_backend` / `bootstrap_copy` / `brain_init`).
  `service_gates.py` carried 253 lines over the 400-line gate. Split
  by responsibility, not line count (Pattern #91): the QG-0 Context
  Gate (`check_qg0_start` plus the `SECURITY_KEYWORDS` and
  `SECURITY_AC_KEYWORDS` keyword tuples it consults) extracted to a
  new `scripts/gate_qg0_check.py` (171 lines); the QG-2 acceptance-
  criteria, plan-completion, and SENAR Rule 5 checklist helpers
  (`verify_ac`, `verify_plan_complete`, `determine_checklist_tier`,
  `check_verification_checklist`) extracted to a new
  `scripts/gate_ac_check.py` (223 lines) as pure free functions that
  take the task dict and return warnings or raise `ServiceError`.
  Verify-pipeline + Verify-First Contract methods stayed in
  `service_gates.py` because they depend on `self.be._conn` /
  `self.be.task_append_notes`. `GatesMixin` keeps the same public
  method names (`_check_qg0_start`, `_verify_ac`,
  `_verify_plan_complete`, `_determine_checklist_tier`,
  `_check_verification_checklist`) — they're now 2-3 line delegators.
  `_check_qg0_start` threads optional `audit_check` /
  `session_check_duration` callbacks via `getattr(self, ..., None)`
  instead of the prior in-method `try/except (AttributeError, ...)`,
  so the pure function works outside `ProjectService` (e.g. on
  bare `GatesMixin` instances in unit tests). Backward compatibility
  preserved: `from service_gates import SECURITY_KEYWORDS`,
  `SECURITY_AC_KEYWORDS`, `has_negative_scenario`,
  `NEGATIVE_SCENARIO_KEYWORDS`, `qg0_dimensions_score`, and
  `check_qg0_start` all still work via `# noqa: F401` re-exports.
  Result: full pytest suite green (2889 passed / 7 skipped /
  120 deselected); 244 gate-related tests focused-pass; ruff + mypy
  clean across the three files; filesize gate PASS for
  `service_gates.py` (368 < 400) without exemption. The v1.4-tail
  filesize-gate `exempt_files` array stays empty — the entire debt
  thread is structurally clean.

- **Filesize debt paydown: `scripts/brain_init.py` 722 → 367 over four
  files (`v14b-followup-brain-init-filesize-debt`).**
  The brain init wizard module had a sticky 322-line filesize-gate
  exemption (entry in `.tausik/config.json` `gates.filesize.exempt_files`)
  ever since the v1.4 initial-discovery split landed `brain_discovery.py`.
  Paying it down without changing semantics meant carving up the wizard
  by responsibility, not by line count: schemas + Notion DB ops moved
  to a new `scripts/brain_init_schemas.py` (186 lines — `CATEGORIES`,
  `DB_TITLES`, four `_<category>_schema()` helpers, `_SCHEMAS` dispatch,
  `db_schema`, `PartialCreateError`, `create_brain_databases`,
  `verify_brain_databases`); the `--join-existing` branch + post-create
  config save migrated to `scripts/brain_init_join.py` (190 lines —
  `run_join_branch`, `_finalize_join`, full diagnostics for the
  integration-not-shared / non-canonical-titles cases); the
  `--force-create` / clean-workspace branch went to
  `scripts/brain_init_create.py` (138 lines — `run_create_branch`
  including parent_page_id / project_name prompts, registration,
  orphan-cleanup guidance for partial creates and post-create save
  failures). `brain_init.py` keeps the dispatcher: token resolution,
  `users.me()` pre-flight, workspace search, branch selection
  (Branch B/C refusals stay inline, Branch A/D delegate to the new
  modules), CLI IO classes (`WizardIO`, `ConfigOps`, `WizardError`,
  `CliIO`), shared helpers (`_print_orphan_cleanup_guidance`,
  `_has_existing_brain`, `_collect_explicit_join_ids`),
  `merge_brain_config`. All 19 public names that test code or other
  modules historically imported from `brain_init.*` (CATEGORIES,
  DB_TITLES, db_schema, create_brain_databases, verify_brain_databases,
  merge_brain_config, PartialCreateError, WizardError, WizardIO,
  ConfigOps, CliIO, run_wizard, _finalize_join, _has_existing_brain,
  _collect_explicit_join_ids, _print_orphan_cleanup_guidance,
  find_workspace_brain_databases, inspect_workspace_brain_databases,
  _extract_db_title) are re-exported via `# noqa: F401` so test code
  needs **zero** modifications. `import brain_project_registry` stays
  at module level in `brain_init.py` so the existing
  `monkeypatch.setattr(brain_init.brain_project_registry, ...)` call
  in `test_brain_init.py:559` keeps working — modules are singletons
  in `sys.modules`, so the patch propagates to `brain_init_create.py`
  through the same module object. Cycle is avoided by lazy imports of
  `run_join_branch` / `run_create_branch` inside `run_wizard`. Result:
  all 69 `tests/test_brain_init.py` cases green, plus 192 broader brain
  tests pass; ruff + mypy clean across the four files; filesize gate
  PASS for all four; `scripts/brain_init.py` removed from
  `.tausik/config.json` `gates.filesize.exempt_files` (dropped the
  string entry, leaving the array empty).

- **Filesize debt paydown: `bootstrap/bootstrap_copy.py` 420 → 311
  (`v14b-bootstrap-copy-debt-paydown`).**
  Skill-specific helpers (`parse_skill_frontmatter`,
  `validate_skill_frontmatter`, `_resolve_skill`, `_generate_stub`,
  `_load_registry`, plus `VALID_CONTEXT` / `VALID_EFFORT` constants)
  extracted to a new `bootstrap/bootstrap_skill_helpers.py` (139 lines).
  `bootstrap_copy.py` re-exports the names with `# noqa: F401` so all
  external imports keep working unchanged: `bootstrap.py` (uses
  `copy_skills` which closes over `_resolve_skill` via a local import),
  `scripts/skill_profile.py` (uses `parse_skill_frontmatter`),
  `tests/test_bootstrap_frontmatter.py` (uses both frontmatter
  functions), `tests/test_vendor.py`, `tests/test_v13_hardening.py`,
  `tests/test_copy_symlinks_disabled.py`. The `import re` import is
  also gone from `bootstrap_copy.py` — only the new helpers module
  needs it. Behaviour byte-for-byte identical: re-running
  `python bootstrap/bootstrap.py --ide claude --smart` against this
  repo produced zero `.claude/` diffs after the split. 76 bootstrap
  tests (frontmatter + vendor + non-destructive + symlink-disable +
  v13-hardening) green. Filesize gate clean for both files.

- **Filesize debt paydown: `scripts/project_backend.py` 403 → 327
  (`v14b-project-backend-debt-paydown`).**
  The 67-line `_init_schema` method (DDL bootstrap + version-guard +
  migration backup + FTS rebuild) extracted into a free function
  `init_schema(conn)` in a new `scripts/backend_init.py` (96 lines).
  `SQLiteBackend.__init__` calls it directly; the method is gone, no
  caller other than `__init__` ever referenced it. Behaviour byte-for-byte
  identical: same skip-DDL-on-current-version path, same `RuntimeError`
  on a newer-than-code on-disk schema, same idempotent `.bak.v<old>`
  backup before `run_migrations`, same FTS rebuild for
  `fts_{tasks,memory,decisions}`. The `shutil` + `run_migrations`
  imports moved to the new module — no longer referenced from
  `project_backend.py`. Full pytest 2889 passed (0 regressions).
  Ruff + mypy clean.

- **Preempt-split `harness/{claude,cursor}/mcp/project/tools_extra.py`
  (`v14b-tools-extra-preempt-split`).**
  The file was at 399/400 lines after the session-open compound RPC
  landed — one tool addition away from the filesize gate. Roles CRUD
  (`tausik_role_{list,show,create,update,delete,seed}`) and
  `tausik_stack_scaffold` extracted into a new
  `tools_extra_admin.TOOLS_EXTRA_ADMIN` list (admin / config-modifying
  tools, cohesive thematic group). `tools.py` imports both lists and
  extends `TOOLS` from each. After split: `tools_extra.py` 317 lines
  (was 399), `tools_extra_admin.py` 97 lines. Tool count unchanged
  (93 project + 7 brain = 100 total, sanity-checked: no duplicates, all
  7 admin tools resolvable post-split). Cursor mirror byte-identical.
  Bootstrap regenerates `.claude/mcp/project/tools_extra_admin.py`
  alongside the existing copy. Full pytest 2889 passed (mirror-sync
  tests `test_mcp_mirrors_in_sync` + `test_mirror_in_sync` initially
  failed pre-bootstrap, expected — re-run green after `.claude/` resync).

- **Source directory `agents/` renamed to `harness/` (`v14b-rename-harness`).**
  Eliminates the long-standing collision with Claude Code's native
  `.claude/agents/` namespace (sub-agent profiles). `git mv` preserves
  history; bootstrap scripts, doc strings, comments, tests, and CLI help
  text all updated to read from `harness/`. Clean break — no
  backward-compat alias for the old path. **Migration:** if you have a
  fork or local script that hardcodes the source path, replace
  `agents/skills/`, `agents/roles/`, `agents/stacks/`, `agents/{ide}/mcp/`,
  `agents/overrides/`, `agents/schemas/`, `agents/aidd-templates/` with
  the matching `harness/...` path. Three concepts are deliberately
  preserved as `agents/`: the host's `.claude/agents/` directory (Claude
  Code sub-agents), the vendor-skill `agents/` namespace inside vendor
  tarballs (still installs into the host's `.claude/agents/`), and the
  internal `harness/skills/review/agents/<name>.md` subfolder (parallel
  reviewer instructions inside the `/review` skill — distinct from
  framework-source `agents/`). Verified: full pytest 2812 passed,
  `tausik doctor` clean, bootstrap dry-run + real run regenerate
  `.claude/`, `.cursor/`, `.qwen/` from `harness/` cleanly.

### Changed

- **Dedupe `.tausik/config.json` path construction (`v14b-review57-followups` M2).**
  New helper `tausik_utils.tausik_config_path(project_dir)` is the single
  source of truth, replacing 8 inline `os.path.join(project_dir, ".tausik", "config.json")`
  call-sites across `bootstrap/bootstrap.py`, `bootstrap/bootstrap_modes.py`,
  `harness/{claude,cursor}/mcp/project/handlers.py` (cq-client lookup),
  `harness/{claude,cursor}/mcp/project/handlers_skill.py` (`_skill_paths`),
  `scripts/project_cli_extra.py`, and `scripts/hooks/session_cleanup_check.py`.
  A regression test (`tests/test_tausik_utils.py::test_no_inline_duplicates_in_production`)
  scans `scripts/`, `harness/`, `bootstrap/` and fails on any future
  inline rebuild.

- **`/start --brain` opt-in primer documents the `brain.ignored:` filter
  (`v14b-review57-followups` M1).** `harness/skills/start/SKILL.md` now
  tells agents to skip page ids that appear in
  `tausik_memory_list type=convention` with title prefix
  `brain.ignored:` — the same dismissal mechanic /task and /plan already
  honour. A regression test in `tests/test_tausik_utils.py` keeps this
  pointer present.

  /review session #57 L1 (preempt-split `scripts/project_cli_extra.py`
  before it crosses the 400-line filesize gate) is a no-op: the file
  measured 353 lines at follow-up time — well under threshold.

### Added

- **Structured `--evidence-json` for `task done` (`v14b-token-t15-evidence-json`).**
  New flag accepts agent-supplied JSON: `{"ac_evidence":[{"n":1,"status":"pass","evidence":"tests/foo.py::test_bar"}, ...]}`
  with optional `manual` / `negative` flags per item. The new helper
  `service_ac_evidence.evidence_json_to_prose()` converts JSON to the
  canonical "AC verified: 1. ✓ ..." prose form, which then flows
  unchanged through the existing `task_log` + `service_ac_evidence`
  parser pipeline. Mutually exclusive with `--evidence` (argparse
  enforces at the CLI; `_task_done_report` re-checks for MCP callers).
  MCP tool `tausik_task_done` gains an `evidence_json` arg with the
  same semantics; backward-compat is full — prose `--evidence` /
  `evidence` continues to work as before. Tests in
  `tests/test_ac_evidence_json.py` — 19 cases (5 positive incl.
  3-AC round-trip, 12 negative incl. malformed JSON / missing keys /
  invalid status / `n` as bool, 1 SQL-payload safety, 1 service-layer
  mutex).

- **AIDD project scaffold (`v14b-aidd-scaffold-basic`).** New CLI subcommand
  `tausik init --template aidd` copies three layered templates —
  `idea.md`, `vision.md`, `conventions.md` — from `harness/aidd-templates/`
  into the current project root. Conflict detection: each existing
  file triggers a 4-option prompt (overwrite / merge-append / skip /
  abort-all); empty input or unknown choice defaults to skip with a
  warning. `--force` bypasses prompting and overwrites every conflict.
  `merge-append` preserves the user's existing content and appends the
  template under a `<!-- merged from AIDD template -->` marker. New
  `scripts/project_cli_aidd.py` module (handler), `scripts/project_parser.py`
  + `scripts/project_cli.py` extended with `--template` / `--force`.
  v1.5 follow-ups recorded as stories under epic `v15-cross-ide-parity`:
  `v15-aidd-autogen` (autogen `vision.md` from existing code) and
  `v15-aidd-ai-validation` (drift detection between AIDD layers and
  shipped code). Tests (`tests/test_aidd_scaffold.py`): 14 cases —
  resolve-choice mapping (empty / first-letter / unknown), template-name
  whitelist, scaffold scenarios (clean dir, partial conflict, full
  conflict default-skip, `--force` overwrites all without prompt,
  explicit `o` / `m` choices, `abort-all` short-circuits remaining files),
  CLI dispatch (unknown template → exit 2 + stderr; happy path → exit 0).
  Smoke-tested end-to-end via `python scripts/project.py init --template aidd`
  in a clean tmp dir. Docs: `docs/en/cli.md` + `docs/ru/cli.md` document
  the new flags and conflict-prompt semantics.

- **Prompt-caching validation script + docs (`v14b-token-t13-prompt-caching-docs`).**
  New `scripts/validate_prompt_caching.py` parses a Claude Code transcript
  JSONL (`--auto` finds the latest, or pass an explicit path) and reports
  `cache_creation_input_tokens`, `cache_read_input_tokens`, hit rate, and a
  classification: exit 0 = caching active, 1 = prefix unstable (creation
  but no reads), 2 = API never returned cache fields, 64 = bad CLI / file
  not found. New `docs/{en,ru}/architecture.md` "Prompt Caching" section
  enumerates the cacheable surface (system prompt + tool schemas, CLAUDE.md,
  MCP tool descriptions, SKILL.md) and the invalidators (chiefly
  `tausik_update_claudemd` mid-session). New `docs/{en,ru}/troubleshooting.md`
  "Prompt caching not active" entry maps low / zero hit-rate symptoms to
  causes (third-party wrapper not sending `cache_control`, mid-session
  CLAUDE.md edit, agent artifacts edited in worktree). Hard prerequisite
  for `v14b-baseline-token-metrics` — that task measures tokens, this one
  pins down whether the measurement is coming from a stable cache regime
  or a noisy one. Tests: `tests/test_validate_prompt_caching.py` covers
  the parser (extracts both fields, handles missing fields, top-level
  vs nested usage, blank lines, explicit-zero cache field still counted),
  the classifier (3 exit-code states), and CLI dispatch (missing file,
  no args, active-cache happy path). 11 tests pass; mypy clean.

### Changed

- **Session active-time switched from "exclude" to "clip" semantics
  (`v14b-session-active-time`).** `compute_active_minutes` (and the new
  `compute_active_seconds` companion) used to drop any inter-tool-call
  gap ≥ `idle_threshold` from the active sum (gap → 0 contribution). The
  bounded-deltas intent in SENAR Rule 9.2 was always "each gap counts
  for at most threshold seconds", so a multi-day session that briefly
  works once a day would otherwise log near-zero active time and never
  trip the 180-min limit. v1.4 polish flips the SQL CASE branch from
  `THEN 0` to `THEN ?` (clipped to `idle_threshold_seconds`): a long
  AFK now contributes exactly `idle_threshold` (default 600 s / 10 min)
  to the active sum. Sub-minute precision exposed via
  `backend_session_metrics.compute_active_seconds`,
  `service_session_metrics.session_active_seconds`,
  `ProjectService.session_active_seconds`, and a new `active_seconds`
  field in both `tausik_status` MCP responses (claude + cursor handlers)
  alongside the existing `active_minutes`. `recompute_all_sessions`
  now also returns `active_seconds` per row. **Behavior change:**
  sessions that previously logged a 0-min "long AFK gap" will now
  show `~10 min` more active each — Rule 9.2 will now correctly enforce
  the 180-min budget on sessions that were previously under-counted.
  Tests: `test_backend_session_metrics::TestComputeActiveSeconds` adds
  9 cases covering AC scenarios (a) short session, (b) 30-min gap clipped,
  (c) 180-min triggers warning, plus negative scenarios (no events,
  long AFK keeps active low, non-monotonic timestamps best-effort,
  sub-minute precision, minutes-wrapper rounding). Existing
  `test_gap_above_threshold_excluded` renamed `_clipped_not_excluded`
  with assertion flipped from 10 → 20 min. `test_custom_threshold` updated:
  threshold-bound gap now contributes the threshold value (5 min), not 0.
  Docs: `docs/{en,ru}/session-active-time.md` rewritten around clip
  formula `Σ min(Δ, idle_threshold)`; `senar-compliance-matrix.md`
  + `agent-contract.md` (RU) Rule 9.2 row updated. 24 backend-metric
  tests + full fast lane pass.

- **`tausik_task_done_v2` MCP tool dropped — single `tausik_task_done`
  returns the structured JSON dict
  (`v14b-task-done-rename-drop-v2`).** The interim `_v2` alias added in
  1.3.7 (when the structured-JSON contract was being proven out) caused
  ongoing confusion: skills shipped fallback prose ("call v2; if absent,
  fall back to v1"), `/troubleshooting.md` had a whole "v2 vs v1" entry,
  and the PostToolUse matcher carried both names. Consolidation: the
  single MCP tool is `tausik_task_done` and it always returns the
  structured-response dict (`ok`, `gates`, `blocking_failures`,
  `cache_status`, …). Internal: `service_task.py::task_done_v2` method
  removed; the str-returning `task_done()` wrapper kept for the CLI
  command (`scripts/project_cli.py`) — backward compatible there.
  `agents/{claude,cursor}/mcp/project/handlers.py::_do_task_done` now
  calls `_task_done_report()` directly and JSON-encodes; `_do_task_done_v2`
  removed from both handlers and the `_DISPATCH` table; `tools.py` drops
  the duplicate `tausik_task_done_v2` tool definition (project tool count:
  93 → 92, total with brain: 100 → 99). `bootstrap_hooks.py` PostToolUse
  matcher: `tausik_task_done|tausik_task_done_v2` → `tausik_task_done`.
  `scripts/hooks/_common.py::_TASK_DONE_TOOL_NAMES` simplified to the two
  canonical forms only. Tests: `tests/test_task_done_v2_matcher.py` →
  renamed `test_task_done_matcher.py`, asserts no `_v2` alias remains;
  `test_project_mcp.py::test_task_done_v2_returns_structured_json` →
  `test_task_done_returns_structured_json` against the canonical name;
  `test_mcp_integration.py` and `test_verify_first_contract.py` updated.
  Skills (`/task`, `/ship` SKILL.md + variants/{haiku,sonnet}.md) drop
  the "fall back to legacy v1" guidance; docs (`mcp.md`, `troubleshooting.md`,
  `quickstart.md`, `hooks.md` EN+RU + AGENTS.md + QWEN.md + READMEs)
  scrubbed of `_v2` mentions and tool counts updated (100 → 99,
  107 → 106 with codebase-rag). **Breaking** for any agent or third-party
  tool that called `mcp__tausik-project__tausik_task_done_v2` directly —
  switch to `mcp__tausik-project__tausik_task_done` (same input schema,
  same structured-JSON return). Tests: 2741 passed, 7 skipped, 118 deselected.

### Fixed

- **Verify-First STRICT vs relaxed asymmetry between `has_fresh_verify_run`
  and `run_gates_with_cache` (`v14b-verify-first-relaxed-symmetry`,
  gotcha #111).**
  `service_verification.run_gates_with_cache` already accepted the
  one-direction relaxed match (Sharp edge #2: `tausik verify` ran with
  `files=[]` manual scope, follow-up `task done` arrives with explicit
  `relevant_files`), but `verify_cache.has_fresh_verify_run` — used by
  the QG-2 verify-first guard in `service_gates._enforce_verify_first` —
  did STRICT lookup only. Result: `task done <slug> --relevant-files
  scripts/foo.py` against a fresh `tausik verify --task <slug>` (no
  `--relevant-files` arg) returned `cache_status='git-mismatch'` even
  though heavy gates had just passed. Surfaced in three sessions before
  the structural fix. `has_fresh_verify_run` now mirrors the relaxed
  fallback after a strict miss: accepts a fresh exit-zero verify-trigger
  row with `files=[]` in the recorded command, rejects rows that named
  specific files (reverse direction stays strict so mtime / gate-signature
  invalidation keeps working) and rejects task-done-bucket rows
  (cache-bucket separation contract preserved). Security-sensitive paths
  are short-circuited by the existing `is_cache_allowed` check — never
  reach the relaxed branch.
  `verify_recent_lookup.lookup_any_fresh_run_for_task` gains an optional
  `command_prefix` parameter so the trigger filter applies in SQL — without
  it, an interleaved task-done bucket row between `tausik verify` and the
  follow-up `task done` would shadow the verify row by having a higher
  id under `ORDER BY id DESC LIMIT 1` (exact failure mode hit during
  dogfood verification of this fix).
  Tests: `tests/test_verify_cache.py` (9 cases —
  manual→explicit accept incl. multi-file, strict-priority-over-relaxed,
  reverse-direction reject, interleaved-bucket-shadowing, security
  short-circuit incl. strict row, no-row miss, red-row miss). Full
  pytest 2889 passed (was 2880, +9 new, 0 regressions).

- **Brain `--join-existing` discovery missed renamed databases
  (`v14b-defect-brain-enable-no-discovery`).**
  `find_workspace_brain_databases` matched candidate Notion databases
  exclusively by exact title equality with `DB_TITLES`
  (`Brain · Decisions / Web Cache / Patterns / Gotchas`). When the four
  BRAIN databases existed under any other title — UI rename, emoji
  prefix, translation, or because they were created outside the wizard
  with category-only names (`decisions` / `web_cache` / `patterns` /
  `gotchas`) — discovery returned `{}` and the wizard surfaced the
  misleading "integration not shared with the BRAIN page" error even
  when the integration could see the databases just fine.
  Discovery is now two-pass: title-match first (unchanged happy path,
  zero extra API calls), then a schema-fallback pass that scans
  unassigned visible databases and assigns the first one whose Notion
  `properties` contain the per-category required set. Discovery now
  also issues `search()` without `query="Brain"` — that pre-filter
  silently dropped databases without that word in the title. Branch A
  of `run_wizard` calls a new `inspect_workspace_brain_databases()`
  helper when discovery returns 0 hits and renders an enriched
  `WizardError` listing the visible candidates (id, title, parent
  page) plus two paths forward (rename canonically, or pass IDs
  explicitly), so users can self-diagnose without re-reading the
  source. The "integration not shared" message is preserved for the
  visible-zero case where it is still the right diagnosis.
  Discovery extracted to `scripts/brain_discovery.py` to keep
  `brain_init.py` focused. Tests: 69 passing in `tests/test_brain_init.py`
  (10 new — schema-fallback positive, mixed title+schema, schema
  conflicts, enriched error, share-via-Connections regression).
  Live evidence on this project: 4 dbs titled `decisions` / `web_cache`
  / `patterns` / `gotchas` (no `Brain ·` prefix) auto-discovered via
  `via=schema`, identical IDs to those previously wired by hand.

- **Token metrics never wrote in production
  (`v14b-defect-token-metrics-no-realworld-write`,
  defect_of=`v14b-baseline-token-metrics`).** `.tausik/token_metrics.jsonl`
  silently stayed empty across every real session because the original
  PostToolUse hook (`scripts/hooks/token_metrics.py`) read
  `tool_response.usage` from the harness payload — a field Claude Code
  never populates per-tool-call (token usage is message-level only). The
  hook was unit-tested against synthetic payloads that fabricated the
  field, so CI green and production silent. Per decision #61, capture
  moved to the existing SessionEnd transcript-parser
  (`scripts/hooks/session_metrics.py`): new `extract_token_rows` walks
  each assistant entry, splits message-level `usage` evenly across
  `tool_use` blocks (last block absorbs the integer-division remainder
  to keep totals exact), and `append_token_rows` writes the same
  schema `service_token_metrics.aggregate()` already consumes. The
  broken PostToolUse hook is removed from `bootstrap/bootstrap_hooks.py`
  + `bootstrap/bootstrap_qwen.py`; `scripts/hooks/token_metrics.py`
  remains as a no-op stub so live IDE instances with stale hook config
  don't error before restart (delete after IDE restart). Tests: 26
  cases in rewritten `tests/test_token_metrics.py` (aggregator, row
  extractor, appender, session_id resolver, end-to-end). End-to-end
  verification: ran on the live transcript of session #55 and got 73
  rows across 22 tools, `tausik metrics tokens` rendered the table
  correctly with cache_read dominating input_tokens (expected under
  prompt caching).
- **`tausik_self_check.sibling_mcp_count` chronic +1 false-positive on
  Windows venv (`v14b-defect-mcp-self-check-venv-launcher`,
  defect_of=`v14b-mcp-stale-module-detector`).** Every IDE restart left
  `sibling_mcp_count=1` even on a clean machine, repeatedly nudging the
  user toward "Restart your IDE" — the same symptom we'd been treating
  as real for sessions #49/#50/#51. Root cause: on Windows
  `venv\Scripts\python.exe` is a launcher SHIM that re-execs the real
  interpreter (`C:\Python311\python.exe`) as a CHILD process while
  keeping the same `CommandLine`; the parent therefore matches the same
  `mcp/project/server.py --project <project>` filter as the child and
  gets counted as a "sibling MCP". POSIX rarely shows this shape (venv
  resolves the real interpreter PID directly), but the guard is uniform.
  Fix: `_enumerate_sibling_mcps` captures `os.getppid()` at entry and
  excludes that PID from every introspection backend (wmic, PowerShell
  `Get-CimInstance`, `/proc` walk, `ps -A` fallback). Mirrored to
  `agents/cursor/mcp/project/self_check.py`. Regression test:
  `tests/test_mcp_self_check.py::test_enumerate_excludes_parent_pid_venv_launcher`
  mocks the PowerShell branch with three rows (parent + self + real
  sibling) and asserts only the real sibling is counted. Pre-existing
  6 self-check tests + the 2 windows-fallback tests unchanged. Project
  memory: gotcha #87 already documents the venv-launcher mechanism.
- **MCP `task_done_v2` 10-second silent hang — root cause after 5-day
  investigation (`v14b-defect-mcp-task-done-stdin-hang`).** `tausik_task_done_v2`
  consistently spent ~10s in the cache-lookup path before returning, observed
  for sessions #47–#51 across multiple users. Prior fixes (`tausik_self_check`
  diagnostics in `v14b-mcp-stale-module-detector`, wmic→PowerShell fallback in
  `v14b-defect-mcp-self-check-windows-fallback`) treated peripheral symptoms —
  none caught this real cause. Root cause traced via in-MCP timing probes:
  `is_declared_consistent_with_git_diff` in `scripts/verify_git_diff.py` calls
  `subprocess.run(["git", "log", "--since=...", ...], capture_output=True,
  timeout=10)` and `git diff --name-only HEAD`. `subprocess.run` with
  `capture_output=True` does NOT redirect stdin — the child inherits the
  parent's stdin. Inside the MCP project server's `asyncio.to_thread` worker,
  stdin IS the JSON-RPC pipe to the IDE. On Windows, git blocks reading from
  that pipe (paginator probe / credential prompt detection / generic stdin
  handling) until the 10s timeout fires; the except branch then defensively
  returns `None` and `is_declared_consistent_with_git_diff` returns `True`
  (its "git failed → assume cache OK" fallback), masking the hang as a
  successful-but-slow `cache_status=hit`. Fix: add `stdin=subprocess.DEVNULL`
  to the affected `subprocess.run` calls. Empirical measurement: MCP
  `task_done_v2` dropped from 10031ms to 63ms — **159× speedup** — in an
  end-to-end JSON-RPC harness against a fresh MCP server. Patched files:
  `scripts/verify_git_diff.py` (both git probes), `scripts/project_service.py`
  (session_metrics spawn), `scripts/project_cli_extra.py` (git branch detection),
  `scripts/skill_manager.py` (git pull, git clone, pip install). All four are
  reachable from the MCP project server's worker thread. Tests:
  `tests/test_verify_git_diff_stdin.py` (NEW) asserts `subprocess.run` is
  invoked with `stdin=subprocess.DEVNULL` on both git probes — protects
  against regression. Project memory: gotcha #88 documents the rule
  ("subprocess.run inside MCP worker MUST pass `stdin=subprocess.DEVNULL`")
  and detection recipe (grep for `subprocess\.(run|Popen)\(` lacking `stdin=`,
  triage by reachability from MCP handlers). Decision #56 sets the convention
  project-wide. **Lesson** (saved as gotcha): diagnostic toolchains can mask
  bugs that look like timeouts — when a 10s ceiling is suspicious, audit for
  defensive except-branches that swallow `subprocess.TimeoutExpired`.
- **Brain-enabled-but-misconfigured silent fallback
  (`v14b-defect-brain-decisions-empty`).** When `.tausik/config.json` had
  `brain.enabled=true` but `database_ids` were empty (or token env unset),
  `tausik_decide` silently fell back to local SQLite with a quiet "brain
  write failed: config_error: brain.database_ids.decisions is empty"
  reason. Users accumulated local-only decisions that should have been
  mirrored to Notion without realising their brain config was broken. Root
  cause: `brain_config.validate_brain()` existed and detected the issue,
  but no production code called it — only tests. Fix: (1)
  `service_knowledge.decide()` now invokes `validate_brain()` before any
  brain write attempt; on validation errors it still saves the decision
  locally (data preservation) but returns a LOUD multi-line warning
  prefixed with `⚠ Decision #N saved LOCALLY ONLY — brain mirror BLOCKED`,
  enumerates each config error, and gives explicit fix paths (`tausik
  brain init` OR `brain.enabled=false`) plus a `tausik brain move
  --to-brain` migration hint for accumulated local-only decisions. (2)
  `tausik doctor` gains a `Brain config` health row that surfaces
  `validate_brain()` errors at health-check time so misconfiguration is
  visible before the user makes any decisions. Tests:
  `tests/test_service_knowledge_decide.py` +1 case
  (`test_brain_enabled_with_empty_database_ids_returns_loud_warning`);
  three existing brain-enabled tests now also patch `validate_brain` to
  return `[]` (testing the post-validation path). One-time gap: existing
  local-only decisions from this defect are not auto-migrated — fix the
  config, then run `tausik brain move --to-brain` per decision (or per
  category) to backfill Notion.
- **Self-check sibling enumeration on Windows 11 24H2+ + remediation
  false-positive on `count=-1` (`v14b-defect-mcp-self-check-windows-fallback`,
  defect_of=`v14b-mcp-stale-module-detector`).** First live run of
  `tausik_self_check` on a Win 11 build 26200 host returned
  `sibling_mcp_count=-1` with `wmic introspection failed: WinError 2` —
  Microsoft removed `wmic.exe` from the modern Windows base image. The
  `collect()` remediation logic also conflated `count=-1` (introspection
  unavailable) with `count>0` (real sibling leak), so a healthy server on a
  modern Windows host would falsely scream "Restart your IDE". Two fixes:
  (1) `_enumerate_sibling_mcps` Windows branch now tries `wmic` first
  (legacy compat) and on `FileNotFoundError` falls through to PowerShell
  `Get-CimInstance Win32_Process` via `subprocess.run(['powershell',
  '-NoProfile', '-NonInteractive', '-Command', '<query>'])` parsing
  `pid|cmdline` lines; if PowerShell is also missing the error preserves
  that fact rather than overwriting it. (2) Remediation now distinguishes
  three states: drift OR `count>0` → "Restart IDE"; `count=-1` → "MCP
  modules in sync (drift check passed). Sibling-MCP check unavailable on
  this host"; clean → "no action needed". Tests:
  `tests/test_mcp_self_check.py` +2 cases (`test_remediation_silent_when_count_unknown`,
  `test_remediation_fires_on_real_drift`); existing 6 cases unchanged.
  Mirrored to `agents/cursor/mcp/project/self_check.py`.

### Added

- **Stale MCP module detector — root fix for silent task_done_v2 / verify
  hangs (`v14b-mcp-stale-module-detector`).** New MCP tool
  `tausik_self_check` returns the running MCP project server's startup
  time, a snapshot of watched-module mtimes captured at boot vs the
  current on-disk mtimes, a `drift_detected` flag, the list of stale
  modules (with `delta_seconds`), and `sibling_mcp_count` — the number of
  other MCP project servers running for the same project (window-leak
  signal). Watch list covers the service-layer modules that have caused
  hangs in the past: `service_verification`, `verify_cache`,
  `security_pattern`, `gate_runner`, `gate_command_runner`,
  `service_gates`, `service_task`, `project_service`, `project_backend`,
  `handlers`, `handlers_skill`. The watcher is implemented in a new
  `agents/claude/mcp/project/self_check.py` that eager-imports the watch
  list at MCP startup so the snapshot reflects what the server will
  actually call into later (lazy-imported modules would otherwise match
  current mtime by definition and mask drift). `/start` skill Phase 1 now
  calls `tausik_self_check` in the parallel batch; Phase 3 renders a
  prominent `⚠ MCP Health` block when drift or sibling MCPs exist, with
  `Restart your IDE` remediation. Companion to gotchas #77 (`tausik_verify`
  hang after editing `service_verification.py`/`gate_runner.py`), #79
  (`task_done_v2` hang on large evidence), #80 (root cause). Tests:
  `tests/test_mcp_self_check.py` (NEW, 6 cases — startup snapshot
  populated; no drift on unchanged tree; drift surfaces when mtime
  advances ≥30 s; missing files don't crash; sibling enumeration returns
  int (≥-1) without raising; handler returns valid JSON envelope). Docs:
  `docs/{en,ru}/mcp.md` registers the tool; `docs/{en,ru}/troubleshooting.md`
  gains a `Stale MCP modules (silent hangs)` section pointing at the
  remediation flow.

- **Skill core cleanup — bootstrap default = 12 + brain conditional
  (`v14b-skill-core-cleanup`).** Bootstrap previously auto-deployed all
  13 source skills plus every entry in `skills-official/registry.json`
  (~38 skills total → ~1,520 tokens in the system-reminder list every
  turn). v1.4.x default now ships **12 core skills** (`/start`, `/end`,
  `/checkpoint`, `/plan`, `/task`, `/ship`, `/commit`, `/review`,
  `/test`, `/debug`, `/explore`, `/interview`) plus `/brain`
  *conditionally* — only when `bootstrap_config.is_brain_enabled(cfg)`
  resolves to true (project has `brain.notion_db_ids` populated by
  `tausik brain init`). Empirical token impact: **−1,040 tokens/turn
  (−68%)** on the system-reminder skill list. Two new bootstrap flags
  bring back the v1.3.x set when needed: `--include-official` (full
  registry stubs) and `--include-vendor` (alias for symmetry with the
  vendor-skill terminology). `_profile-demo` stays in `agents/skills/`
  as an underscore-prefixed reference fixture (already filtered by
  bootstrap). `tausik status` now prints a one-line warning if the
  deployed skill set diverges from the flag (e.g. 38 deployed without
  `--include-official`) so unintended bloat doesn't go unnoticed.
  Negative tests pin the edge cases: `.tausik/config.json` missing or
  corrupt → brain skipped without crash; `installed_skills` config
  entries deploy regardless of the default; underscore-prefixed names
  in `installed_skills` get filtered. Source files: `bootstrap.py`,
  `bootstrap_config.is_brain_enabled`, `bootstrap_copy.copy_skills`
  (gated `builtin_names` loop + opt-in registry stubs),
  `project_cli._maybe_print_skill_set_warning`. Tests:
  `tests/test_bootstrap_skills_coverage.py` (8 cases, including 4
  negatives). Docs: `docs/{en,ru}/skills.md`,
  `docs/{en,ru}/architecture.md`, `README.md` + `README.ru.md` (new
  `## Token Efficiency` section before `## Functionality`).

### Added

- **Filesize debt paydown (`v14b-filesize-debt-paydown`).** Four
  oversized modules split into focused submodules; the
  `.tausik/config.json` `gates.filesize.exempt_files` list is now empty.
  Concrete moves:
  - `scripts/backend_queries.py` 536→397: usage_events / session_usage_metrics
    methods (`usage_event_append`, `session_usage_record`,
    `usage_events_cost_rollup_by_task`, `session_usage_summary`) extracted to
    new `scripts/backend_queries_usage.BackendQueriesUsageMixin`;
    `BackendQueriesMixin` inherits from it so the public surface on
    `SQLiteBackend` is unchanged.
  - `scripts/service_verification.py` 464→345: security pattern classifier
    (`is_security_sensitive` + `_SECURITY_PATH_TOKENS` / `_SEC_BASE` /
    `_SECURITY_BASENAMES` / `_SECURITY_EXTENSIONS`) extracted to
    `scripts/security_pattern.py`; cache helpers (`is_cache_allowed`,
    `resolve_gate_signature`, `_build_cache_command`, `has_fresh_verify_run`)
    extracted to `scripts/verify_cache.py`. Both names re-exported from
    `service_verification` so all existing imports keep working.
  - `scripts/gate_runner.py` 476→394: `run_command_gate` +
    `_SCOPED_SKIP_SENTINEL` (including the v14b TAUSIK_VERIFY_FULL injection)
    extracted to `scripts/gate_command_runner.py`; re-exported from
    `gate_runner` so `tests/test_gates.py` and other callers keep working.
  - `bootstrap/bootstrap_generate.py` 433→223: the giant settings hooks
    block extracted to `bootstrap/bootstrap_hooks.build_hooks_dict(_hook_cmd)`.
    `generate_settings_claude` now reads as the lean config builder it was
    always meant to be.
  Smoke test pins backwards compatibility: `tests/test_filesize_split_smoke.py`
  imports every moved symbol from its ORIGINAL module and asserts identity
  with the new location, plus a settings.json hooks-shape contract test
  that mirrors the existing per-hook coverage assertions.

### Added

- **Pytest fast lane (`v14b-pytest-fast-lane`).** Default pytest
  configuration in `pyproject.toml` now skips tests marked
  `@pytest.mark.slow` (`addopts = "-m 'not slow'"`). Heavy tests —
  bootstrap real/dryrun + skills coverage, MCP integration & project
  server, brain MCP handlers + installed-layout, stress (1000 tasks /
  100 sessions), bootstrap venv, RAG FTS5 benchmarks, Tausik CLI
  smoke, skill CLI help, model-profile bootstrap variants — and a
  single 7 s `posttool_usage_hook` lock-contention case carry the
  marker. Empirical impact on the TAUSIK repo: full suite went from
  **731 s (12:11) to 99 s (1:39)** — **7.4× speedup**, 118 tests
  deselected from the fast lane. Three escape hatches when the full
  battery is needed: `pytest --override-ini='addopts='`, `pytest -m ''`
  (or `-m 'slow'` for nightly), and the new
  `TAUSIK_VERIFY_FULL=1` env var that `gate_runner.run_command_gate`
  picks up to inject `--override-ini=addopts=` into the pytest gate
  command. Only the pytest gate is affected — other gates (ruff, mypy,
  filesize) are untouched. Tests cover the env-var injection path,
  the no-op for non-pytest gates, and the default unchanged-cmd case
  (`tests/test_gates.py:TestRunCommandGate`). Docs updated in
  `docs/{en,ru}/cli.md`.

### Fixed

- **CLAUDE.md size cap regression
  (`claude-md-trim-reference-line-fix-test-claude-md-s`).** The Reference
  line was extended in handoff #45 to keep three T2.2 drift tests green; that
  push spilled the static portion to 4113 B over the 4096 B cap enforced by
  `tests/test_claude_md_size.py::test_claude_md_static_under_size_cap`. Trimmed
  the prose without losing the `agent-contract.md` pointer or the anchor
  keywords (`estimation`, `SENAR matrix`, `roles`, `custom_stacks`, `QG-2`).
  All four CLAUDE.md tests now PASS.

- **QG-2 verify-first false-positive on hook/session files
  (`v14b-defect-qg2-security-substring-too-broad`).** `is_security_sensitive`
  in `scripts/service_verification.py` previously matched bare substrings
  ("session", "login", "signup", "scripts/hooks/", ...) which classified
  every TAUSIK harness hook (`scripts/hooks/session_start.py`,
  `posttool_usage.py`, `keyword_detector.py`, ...) and every hook test
  (`tests/test_session_start_hook.py`, `tests/test_session_metrics.py`)
  as security-sensitive. That set `is_cache_allowed=False`, so
  `has_fresh_verify_run` returned `(False, None)` and `_enforce_verify_first`
  blocked `task_done` with "no fresh verify run" even immediately after a
  green `tausik verify`. Hooks are infra, not auth surface. The fix
  narrows `_SECURITY_PATH_TOKENS` to directory-anchored entries only
  (`/auth/`, `/oauth/`, `/payment/`, `/webhook/`, …), drops bare
  substrings, and replaces the loose "session" / "login" basenames with
  explicit ones (`session_token.py`, `login_handler.py`, etc.).
  `_SECURITY_BASENAMES` now also covers `secrets.json`, `credentials.json`,
  `.npmrc`, `id_rsa`, `id_ed25519`. Full contract written into the
  `is_security_sensitive` docstring. New
  `tests/test_security_sensitive.py` (70 cases) pins both true-positive
  and false-positive sets, plus a regression case that records a green
  verify run on a hook file and asserts `has_fresh_verify_run` returns
  `(True, row)` — the exact failure mode that blocked the
  `v14b-rag-first-nudges` close. Audit of `verification_runs` showed only
  one task affected historically (the parent task that surfaced the bug);
  no re-verification needed.

### Added

- **RAG-first nudges (`v14b-rag-first-nudges`).** Skills `start`, `task`,
  `debug` now carry a "Code search hierarchy" section pointing the agent at
  `mcp__codebase-rag__search_code` as the first choice for symbol/pattern
  lookup, with `Grep`/`Read` reserved for known file paths. Skill `explore`
  rewrites step 3 to start every investigation with `search_code` over
  ranked chunks before reading whole files. The SessionStart hook
  (`scripts/hooks/session_start.py`) strengthens the auto-injected RAG
  summary with the explicit MCP tool name and adds a Reminders bullet
  ("Use `search_code` (RAG) before Grep/Read for unfamiliar code"). The
  Stop hook (`scripts/hooks/keyword_detector.py`) gains a second detector:
  when the user's last prompt contains code-discovery intent ("where is X"
  / "find Y" / "how does Z work" / "где определ…") and the agent's reply
  did not mention `search_code`, the hook blocks the stop with a
  rag-first recommendation. Drift guard keeps precedence; the loop-safe
  `stop_hook_active` short-circuit covers both detectors. Tests:
  `tests/test_keyword_detector_hook.py` (+8 cases for the new detector,
  including precedence and suppression-when-already-used),
  `tests/test_session_start_hook.py` (+1 case for the rag-first reminder).
- **Per-task token attribution (`v14b-usage-events-auto-write`).** New
  PostToolUse hook `scripts/hooks/posttool_usage.py` writes one
  `usage_events` row per tool call, attributed to the active task.
  Schema migration v24 adds `usage_events.tool_name` and extends
  `source` CHECK to include `posttool`. Pricing logic moved to a shared
  `scripts/cost_pricing.py` module — single source of truth for both
  the new hook and the existing `session_metrics.py` SessionEnd writer.
  Five graceful-degradation paths covered by tests (malformed stdin,
  no active task, unknown model, locked DB retry, missing
  `.tausik/tausik.db`). Docs: `docs/{en,ru}/cost-telemetry.md`.

## [1.4.0] — 2026-05-02 — Verify-First Contract + 1.4 epic batch

> Public-readiness release driven by a 1.4 audit and a 10-epic master
> plan (research artifacts removed pre-release; see commit history).
> Headline change: heavy verification (pytest, tsc, cargo, phpstan, …)
> is decoupled from `task done`. Closing a task is now a millisecond
> operation; verification is its own explicit, cached step.
> All 10 v14-* epics closed; the full backlog landed —
> `v14-brain-snippets`, `v14-model-prompts`, `v14-verify-integrity`,
> `v14-cost-telemetry`, `v14-framework-lean` shipped in the Composer
> batch (session #42); the remaining `v14-project-hygiene`,
> `v14-test-philosophy`, `v14-doc-automation`, `v14-dead-code-audit`,
> `v14-skill-store` followed in the Phase B follow-up before the
> release commit. See the session-#42 retro
> (`docs/ru/research/tausik-1.4-composer-retro-2026-05-02.md`).

### BREAKING (with opt-out)

- **Verify-First Contract.** Heavy quality gates moved from the `task-done`
  trigger to a new `verify` trigger. `task done` now refuses to close a
  task unless a fresh `tausik verify` green exists in `verification_runs`
  for that task (10 min TTL, configurable via `verify_cache_ttl_seconds`).
  Affected gates: `pytest`, `tsc`, `cargo-check`, `cargo-test`, `go-vet`,
  `go-test`, `phpstan`, `phpunit`, `javac`, `js-test`, `terraform-validate`,
  `helm-lint`, `kubeval`, `hadolint`, `ansible-lint`.
  - **Why:** in VS Code Claude Extension and similar hosts, synchronous
    multi-minute pytest runs inside `task_done` looked like the agent had
    hung. The new contract makes verification visible and interruptible.
  - **Opt-out:** add `{ "task_done": { "auto_verify": true } }` to
    `.tausik/config.json` to restore the v1.3 inline behavior (heavy gates
    fire inside `task_done`). Useful in CI where one long step is fine.
  - **Migration:** users only need to insert `tausik verify --task <slug>`
    before `task done`. Skill `/ship` and CLI docs updated.

### Added — Verify-First infrastructure

- `VALID_GATE_TRIGGERS` extended with `"verify"` (project_config + stack_schema).
- `service_verification.has_fresh_verify_run()` and
  `service_verification._build_cache_command(trigger, files)` — the cache
  bucket is now keyed by trigger so verify and task-done buckets never
  cross-satisfy.
- `service_gates._enforce_verify_first()` — synthesizes a blocking failure
  with explicit remediation when no fresh verify run is found.
- `tests/test_verify_first_contract.py` — 14 tests covering the contract
  end-to-end (block, unblock via cache, auto_verify opt-out, cache bucket
  separation, exempt projects, stack-gate migration sanity).
- Pytest marker `verify_first` and an autouse opt-out fixture in
  `tests/conftest.py` so legacy tests aren't blocked on the new contract.
- **Pipeline envelope timeout** (`verify_pipeline_timeout_seconds`,
  default 60s) — wall-time bound around the whole `run_gates` cycle so a
  hung gate cannot make `task done` look frozen. Set to `0` to disable
  (CI). On exceed: `GateEnvelopeTimeoutError` with explicit remediation
  (raise the limit, set `auto_verify=true`, or narrow `relevant_files`).
- **Recover relevant_files from recent verify-row.** When `task done` runs
  without a CLI/MCP `relevant_files` AND the task row has none, `service_task`
  now reads them from the most recent fresh verify-row (≤ TTL, exit 0) so
  `tausik verify --task X` followed by `tausik task done X` (no args) hits
  the cache. Security-sensitive paths (auth/payment/etc.) bypass the
  fallback — they always require an explicit list.
- **Relaxed cache hit on file-set mismatch.** Strict cache lookup keys on
  `(slug, files_hash, command)` so mtime / gate-signature drift correctly
  invalidates. The single Sharp edge it created — `verify --task X` with
  manual scope (`files=[]`) followed by `task done X relevant_files=[…]`
  used to miss and re-run `run_gates` — is closed: when the strict miss
  has a fresh exit-zero row that named NO files, accept it as "manual
  scope vouched for this slug". Mismatch where the recorded run named
  specific files still misses (mtime/signature invalidation preserved).
  Security-sensitive `relevant_files` bypass relaxed too.

### Added — Epic v14-brain-snippets (Shared Brain artifact pipeline)

- Logical schema `agents/schemas/brain-artifact-card.schema.json` —
  validated payload for patterns / gotchas before Notion write.
- `scripts/brain_artifact_taxonomy.py`, `scripts/brain_artifact_card.py`,
  `scripts/brain_store_format.py` — taxonomy (artifact / pattern / snippet),
  card validator, server-side store-format normalizer.
- `scripts/brain_publish_flow.py` + `scripts/brain_publish_cli.py` +
  `scripts/brain_cli_ops.py` — propose → audit → publish workflow with
  scrub-before-risk and explicit `confirm_high_risk` gate.
- MCP `brain_draft_artifact` (Claude + Cursor servers) for proposing
  artifacts before publish.
- Optional `external_repo_url` field on artifact cards (validated;
  not persisted to Notion props in v1).
- Stack-aware artifact ranking inside `brain_search`.
- EN/RU docs: `brain-artifact-taxonomy.md`, `brain-search-ranking.md`.

### Added — Epic v14-model-prompts (multi-model skill profiles)

- `scripts/skill_profile.py` — frontmatter + `variants/<model>.md`
  resolver with safe fallback on unknown profile.
- `agents/skills/_profile-demo/` — demo skill (`SKILL.md` + `variants/`)
  showing the format. The leading `_` makes bootstrap skip the demo
  in real generation.
- `bootstrap_copy.py` profile-aware skill copy (selects variant body).
- `bootstrap_qwen.py` + `.qwen/` + `QWEN.md` template — Qwen Code agent
  added as a target IDE alongside Claude / Cursor.
- `TAUSIK_MODEL_PROFILE` env → `model_profile` key in `.tausik/config.json`
  (validated on bootstrap; invalid values exit non-zero).
- Optional `task_next.model_hint` config key (off by default) — appends
  a non-blocking model recommendation (Haiku / Sonnet / Opus) on
  `task next` and `hud` based on complexity.
- AGENTS.md table mapping model → tool surface.
- EN/RU docs: `skill-profiles.md` plus updates to `skills.md`.

### Added — Epic v14-verify-integrity (anti-gaming QG-2)

- `doctor` subcommand surfaces a non-blocking warning when
  `auto_verify=true` is paired with an interactive profile (humans
  rarely want full pytest inside `task_done`). Tested in
  `tests/test_doctor_auto_verify_hint.py`.
- `tests/conftest.py` `_verify_first_autouse_compat_shim` documented:
  predicate helper `tests/verify_first_compat_predicate.py`
  declares which test paths bypass `_enforce_verify_first` and why.
- `scripts/verify_recent_lookup.py` — small compat shim for verify cache
  lookups outside `service_verification`.
- EN/RU docs: `verify-glossary.md` (opt-out vs bypass vs test shim —
  single source of truth).

### Added — Epic v14-cost-telemetry (token + dollar accounting)

- `usage_events` table (migration in `backend_schema.py`) — records
  model_id, input/output tokens, optional cost, task_slug, session,
  created_at. Negative tokens / unknown model rejected.
- `llm_pricing_usd_per_million` config key (validated by
  `normalize_llm_pricing_config`) — per-model USD price; missing model
  yields `UNKNOWN`.
- `usage_events_cost_rollup_by_task` + `usage_cost_rollup_by_task` —
  per-task / per-period cost aggregation. Empty windows return `[]`,
  not exceptions.
- `tausik metrics --cost` (CLI + MCP `tausik_metrics`) — tabular
  rollup with friendly empty-state message.

### Added — Epic v14-framework-lean (token-cost reduction)

- `context_tier` config key (`minimal` / `standard` / `full`) +
  `resolve_context_tier()` with strict validation. Bootstrap renders
  short / medium / full rules accordingly. Tested in
  `tests/test_context_tier.py`.
- `tausik status --compact` (CLI flag) and MCP `tausik_status({compact:
  true})` — single-line JSON reply for agents that don't need the
  human-formatted block. Default human output unchanged.
- AGENTS.md trim pass: removed duplication with skills without dropping
  any hard rule.

### Added — Doc automation (epic v14-doc-automation, partial)

- `docs/_generated/constants.json` — single source of truth for
  `tausik_version`, MCP tool counts (project / brain / RAG / total).
- `scripts/gen_doc_constants.py` — generator with `--check` mode
  (exit 1 on drift). Available as `tausik doc constants [--check]`.
- `scripts/mcp_tool_counts.py` — derives `mcp_*_tools` numbers from
  live `agents/{claude,cursor}/mcp/*/tools.py`. Tested in
  `tests/test_gen_doc_constants.py`, `tests/test_mcp_doc_tool_counts.py`.

### Added — Project hygiene & test-philosophy docs (partial)

- EN/RU docs: `task-archive-spec.md` (read-only archive policy for
  done tasks > N days), `memory-merge-guidelines.md` (when to merge
  memory entries vs. add a new one), `testing-principles.md`
  (criteria for adding a test; anti-pattern: copy-paste without new
  behavior), `skill-ecosystem.md` (one-pager for repo → install →
  activate flow).
- `agents/skills/_profile-demo/` showcased in `skills.md` — when to
  use multi-model variants.

### Changed

- `agents/{claude,cursor}/mcp/project/server.py`:
  - `chdir(args.project)` on launch with explicit non-directory check
    (exit 2, stderr message). Parity with `tausik-brain` server.
  - Tool exceptions now print full `traceback.format_exc()` to stderr while
    the agent-facing reply stays minimal (`Error: …`) — no stack-frame
    leakage into model context.
- `service_verification.run_gates_with_cache(..., trigger="task-done")` is
  now parameterizable; CLI `verify` and MCP `_handle_verify` pass
  `trigger="verify"`.
- Stacks `python`, `typescript`, `rust`, `go`, `php`, `javascript`, `java`,
  `terraform`, `helm`, `kubernetes`, `docker`, `ansible` updated:
  heavy `task-done` gates are now on `verify`.
- `bootstrap_templates.py` HARD_CONSTRAINTS, SENAR_RULES, COMMANDS, and
  QUALITY_GATES sections describe the Verify-First workflow so newly
  bootstrapped projects get the right CLAUDE.md / AGENTS.md / .cursorrules.
- `docs/{en,ru}/cli.md` and `docs/{en,ru}/quickstart.md` updated.
- Skills `/ship` and `/task done` insert an explicit `tausik_verify` step
  before closing a task.

### Fixed

- Pre-existing test bug: `tests/test_service_verification.py` lambdas
  mocking `gate_runner.run_gates` did not accept kwargs and silently
  failed against the real `progress_callback=` argument. Lambdas now
  carry `**_kw`. (4 tests unblocked.)
- Test pollution between `test_hud_cli.py`, `test_memory_block.py`,
  `test_memory_compact.py`, `test_qg0_dimensions.py` and any test that
  reads `.tausik/config.json` via `find_tausik_dir()`. The four files
  set `os.environ["TAUSIK_DIR"]` directly without cleanup, so the env
  var leaked into later tests pointing at a deleted tmp_path. Replaced
  with `monkeypatch.setenv` so cleanup is automatic. Surfaced by the
  new `tests/test_task_next_model_hint.py::test_hint_via_config_file`,
  which is the only test that exercises a real `load_config()` path.

### Tests

- Suite expanded **2318 → 2513** (`tests/`); full run green
  (`2506 passed, 7 skipped`).
- New test files: `test_bootstrap_model_profile`,
  `test_brain_artifact_external_repo`, `test_context_tier`,
  `test_doctor_auto_verify_hint`, `test_gen_doc_constants`,
  `test_llm_pricing_config`, `test_mcp_doc_tool_counts`,
  `test_skill_profile`, `test_task_next_model_hint`,
  `test_metrics_session_usage`.

### Versioning

- `__version__` bumped `1.3.7` → `1.4.0`.
- `pyproject.toml` `version` bumped `1.3.7` → `1.4.0`.
- `docs/_generated/constants.json` regenerated.

> All 10 v14-* epics closed in this release. The remaining 5 epics from the
> master plan landed alongside the Composer batch as their own scripts and
> tests, split below for parallel structure with the first five.

### Added — Epic v14-project-hygiene (long-running project hygiene)

- **`tausik hygiene archive`** (CLI, dry-run only in v1) — lists `done`
  tasks older than `task_archive.done_age_days`. Active / blocked /
  planning / review tasks are never included; `--confirm` is reserved
  for future destructive ops and rejected today. Sources:
  `scripts/project_cli_hygiene.py`, parser dispatch in
  `scripts/project_parser_ops.py::add_hygiene`.

### Added — Epic v14-test-philosophy (test discipline)

- **`scripts/audit_pytest_dedupe.py`** — AST-normalized signature
  grouping for test functions that share structure (copy-paste
  detector). Report artifact:
  `docs/ru/research/tausik-1.4-pytest-dedupe-2026-05-02.md`.

### Added — Epic v14-dead-code-audit (dead code & junk inventory)

- **`scripts/audit_orphan_files.py`** — Python files in `scripts/` that
  no other file imports and no doc references. Mirror partner / soft
  doc references included so standalone CLIs aren't false-positive.
- **`scripts/audit_stale_docs.py`** — markdown files under `docs/` with
  no inbound link. EN/RU mirror partners stay paired; research and
  release-notes archives excluded by glob.
- **`scripts/audit_unused_python.py`** — top-level `def` / `class`
  symbols never referenced in the repo. Exempt modules + private
  helpers excluded; documented false-positive policy.

### Added — Epic v14-doc-automation (doc generation & drift checks)

- **`scripts/hooks/check_docs.py`** — pre-commit / CI hook wrapper
  around `gen_doc_constants.py --check`; gracefully skips when no
  `pyproject.toml` is found above cwd.
- **`.github/workflows/tests.yml` step `Doc-constants drift check`** —
  fails the matrix on `docs/_generated/constants.json` drift.
- **EN/RU developer docs:** `dev-doc-checks.md` — how to run all of
  the above locally; documents negative behaviour.

### Added — Epic v14-skill-store (skill CLI UX & trust)

- **Skill CLI consistency** (`tausik skill ...`) — every subcommand has
  a noun-phrase help string and a "see: tausik skill list" hint on
  `name` args. Negative scenarios now surface a friendly
  `Error: ...` + exit 1 instead of a Python traceback;
  `SkillManagerError` is caught alongside `ServiceError` in `main()`.

### Refactored

- `scripts/project_parser.py` 465 → 372 lines: `add_skill` and
  `add_metrics` extracted into `scripts/project_parser_ops.py` to
  satisfy the 400-line filesize gate.

## [1.3.7] — 2026-04-29 — MCP clarity for Cursor/VSCode + docs consistency sweep

This patch hardens agent-facing MCP UX and aligns documentation with actual
multi-IDE validation status.

### Added
- **`tausik_task_done_v2` MCP tool** (Claude + Cursor server surfaces) with
  structured JSON output: stage flags, per-gate results, blocking failures,
  remediation hints, warnings, and cache status.
- **Gate progress events** in `gate_runner` and MCP stderr feedback:
  `[gate X/N] running ...`, `PASS/FAIL/SKIP`, duration per gate.
- **Cursor project MCP generation** in bootstrap:
  `.cursor/mcp.json` is now generated/merged alongside root `.mcp.json`.

### Changed
- `task_done` internals now reuse a shared structured report pipeline, while
  preserving backward-compatible plain-text behavior for legacy callers.
- README EN/RU now explicitly marks **officially tested** IDE combos:
  `VSCode + Claude Extension` and `Cursor`; other hosts are tagged as
  expected/partial.
- Quickstart EN/RU now documents dual MCP config locations:
  `.mcp.json` (Claude ecosystem) and `.cursor/mcp.json` (Cursor project).
- MCP docs EN/RU include `tausik_task_done_v2` and structured-response usage.

### Fixed
- Resolved docs drift in RU index and hooks docs:
  - RU docs index MCP count aligned to 96.
  - `brain_search_proactive.py` trigger description aligned with generated hook
    wiring (`WebSearch|WebFetch`, not generic user-prompt trigger).
- Synced stale dogfooding/test-count values in RU/agent onboarding docs.

### Tests
- Added/updated tests for:
  - `task_done_v2` MCP dispatch/shape.
  - Cursor MCP config generation and user-entry preservation.
  - MCP integration tool list including the new v2 endpoint.
- Target suite passed locally:
  `tests/test_project_mcp.py`,
  `tests/test_mcp_integration.py`,
  `tests/test_bootstrap_generate_mcp.py`.

### Versioning
- `__version__` bumped `1.3.6` → `1.3.7`.
- `pyproject.toml` version bumped `1.3.6` → `1.3.7`.

## [1.3.6] — 2026-04-29 — Dead code cleanup + framework integrity

Targets two CI workflow failures and a wider integrity audit. No behaviour
changes for end users; the framework surface is the same, just tidier.

### Removed
- `scripts/generate_cli_ref.py` — orphan (the CLI reference moved to
  `docs/{en,ru}/cli.md` in v1.3.0; the generator was never re-wired).
- `.github/workflows/docs-update.yml` — wrote to the deleted `references/`
  directory and was the source of the second CI red.
- `scripts/hooks/notify_on_done.py` + `scripts/notifier.py` +
  `tests/test_notifier.py` — the notification feature was implemented but
  never registered in any IDE settings template, so it was dead code.
  Parking-lot entry added to `TODO.md` if the feature needs to come back.

### Fixed
- **CI red — `ruff check scripts/` failure.** Removed 6 unused imports
  in `scripts/project_cli_doctor.py`, `scripts/service_task.py`, and
  `bootstrap/analyzer.py`.
- **Bootstrap drift.** `scripts/project_service.py` and
  `scripts/service_task_team.py` had been edited at the source without
  re-bootstrapping `.claude/`; `tausik doctor` now reports zero warnings.
- **Stale doc paths.** Six documents (`docs/{en,ru}/i18n-strategy.md`,
  `docs/en/environment.md`, `docs/en/troubleshooting.md`,
  `docs/en/skill-spec.md`, `docs/{en,ru}/architecture.md`) referenced the
  deleted root `references/` directory; updated to point at `docs/{en,ru}/cli.md`.
- **Hooks doc.** `docs/{en,ru}/hooks.md` no longer documents the deleted
  `notify_on_done.py` row in the PostToolUse table or the pipeline diagram.
- **Test counts.** Bumped 2270 → 2318 across `CLAUDE.md`, `README.md`,
  and `docs/{en,ru}/architecture.md` after the test_notifier removal.

### Changed
- **Ruff scope expanded in CI.** `ruff check` now runs on
  `scripts/ tests/ bootstrap/` (was `scripts/` only) so future drift in
  tests or bootstrap is caught at PR time.
- **`pyproject.toml`.** Added `[tool.ruff]` config with per-file `E402`
  ignores for the seven test/bootstrap modules that intentionally insert
  into `sys.path` before importing project modules. Project version field
  bumped from the stale `1.0.0` baseline to `1.3.6`.
- **Lint hygiene.** Cleaned 4× F541 (useless `f""` prefixes), 2× B007
  (unused loop control variables `dirpath`, `f`), 1× E741 (ambiguous
  `l` → `row`), 1× E401 (combined imports), and 7× F841 (unused locals
  in tests — including two test bugs where the assertion was missing
  entirely: `test_dotfile_not_ignored_by_default` and
  `test_case_insensitive_ext` in `tests/test_rag_edge.py`).
- **Mypy override.** Removed obsolete `module = "generate_cli_ref"`
  override pointing at the deleted file.

### Versioning
- `__version__` bumped `1.3.5` → `1.3.6`.
- `pyproject.toml` `version` synced from `1.0.0` (stale) to `1.3.6`.

## [1.3.5] — 2026-04-28 — Cursor session cost metrics (auto + CLI)

### Added
- `tausik metrics record-session` CLI subcommand to persist per-session
  token/cost/tool/model usage into project DB.
- New table `session_usage_metrics` (schema `v19`) with upsert by
  `session_id` and query/index support.
- `tausik metrics` output now includes `LLM Usage` summary and last
  recorded session details.

### Changed
- `session end` now attempts a best-effort call to
  `scripts/hooks/session_metrics.py --auto --record` (non-blocking).
- `scripts/hooks/session_metrics.py --auto` now searches both
  `~/.claude/projects` and `~/.cursor/projects` transcript roots.

### Tests
- Added `tests/test_metrics_session_usage.py`.
- Added `tests/test_session_end_metrics_hook.py`.

### Versioning
- `__version__` bumped `1.3.4` -> `1.3.5`.

## [1.3.4] — 2026-04-28 — Security & QG hardening + doc-truth

Closes the v1.3.1 blind-review HIGH/MED security and QG bypasses that
weren't bundled into the v1.3.0 release. Three commits:

### Doc-truth: test count drift (`fcbefb4`)
- README.md / README.ru.md badges + Stats tables, AGENTS.md,
  CONTRIBUTING.md, docs/{en,ru}/architecture.md — `2246` → `2270`
  (count after v1.3.3 added 24 tests). CHANGELOG entries kept
  historical.

### Verify cache cross-check vs git diff (`d8838f1`) — closes 1 HIGH (Sec)
- `scripts/verify_git_diff.py` (new): `changed_files_since(timestamp,
  root, runner)` shells out to `git log --since=<ts> --name-only` +
  `git diff --name-only HEAD`, unions, normalizes paths to forward
  slashes. Returns `None` on any failure (git missing, no `.git`,
  non-zero exit, OSError) so non-git users keep working.
- `is_declared_consistent_with_git_diff(declared, ts)` returns False
  iff declared_set is a strict subset of actually-changed-set
  (under-declaration). Over-declaration is fine.
- `service_verification.run_gates_with_cache`: new `task_created_at`
  param. When provided, gates cache lookup on git-diff consistency in
  addition to the existing security-bypass + files_hash checks. New
  status code `git-mismatch` joins `hit`/`miss`/`bypass`.
- `service_gates._run_quality_gates` and `project_cli_verify.cmd_verify`
  plumb `task["created_at"]` through.
- Closes the bypass: agent could declare `relevant_files=[docs/x.md]`
  while editing `scripts/auth.py` and the cache hashed only the declared
  files — next `task_done` saw a stale-green and skipped the security
  check.
- Refactor for filesize: extracted `qg0_dimensions_score` to
  `scripts/gate_qg0_score.py` (47 lines) so service_gates dropped from
  408 to 381.
- 16 new tests in `tests/test_service_verification.py`.

### Hook hardening batch (`b48d230`) — closes 5 MED (Sec) + 1 audit-clean
- **#1 bash_firewall regex.** WARN_PATTERNS now use word-boundary regex
  with the same shape as `git_push_gate.py` (command-start anchor +
  optional path + optional `git -c` flags). `echo 'git push --force is
  dangerous'` no longer false-positives. `gitfoo push --force` no longer
  matches. `/usr/bin/git push --force` still blocks. 11 new tests.
- **#2 skill_manager pip hardening.** `install_skill_deps` now passes
  `--no-config` to pip (disables every pip.conf scope) and strips
  `PIP_INDEX_URL`, `PIP_EXTRA_INDEX_URL`, `PIP_TRUSTED_HOST`,
  `PIP_FIND_LINKS`, `PIP_INDEX` from subprocess env. Combined with the
  existing `_SAFE_PKG` regex, closes the supply-chain redirect surface
  for third-party skills. 3 new tests.
- **#3 copytree symlinks=False.** 3 call sites — `skill_manager.copy_skill`,
  `service_skills.skill_install`, `bootstrap_copy.copy_dir` — now pass
  `symlinks=False` explicitly. New `tests/test_copy_symlinks_disabled.py`
  with hostile-repo fixture (skips on Windows non-admin where `os.symlink`
  fails); covers all 3 call sites.
- **#4 hooks detect TAUSIK by `.tausik/` dir, not `.db` file.** New
  helper `_common.is_tausik_project(project_dir)`. `task_gate.py` and
  `memory_pretool_block.py` migrated. Closes the
  bootstrap-but-not-init window where hooks silently skipped. 3 new tests.
- **#5 `last_user_prompt_text` bounded tail-read.** New
  `_read_transcript_tail()` seeks the last 50 KB of the JSONL transcript,
  drops the partial first line at the seek boundary. Long sessions no
  longer load the entire file into memory on every PreToolUse. 3 new tests.
- **#6 brain symlinks — AUDIT CLEAN.** `git grep` for
  `copytree|os\.symlink|os\.readlink|os\.lstat|shutil\.` across
  `scripts/brain_*.py` + `agents/claude/mcp/brain/` returned ZERO hits.
  No fix needed; the scan is the deliverable.

### QG hardening batch (this commit) — closes 5 MED (QG)
- **#1 Negative-scenario detection: regex with negation filter.** Old
  code did `kw in ac_text` substring match — "Works without errors"
  satisfied the gate because "error" substring was present. New
  `has_negative_scenario(ac_text)` splits AC into per-criterion lines
  (handles inline `1. ... 2. ...` numbering), redacts negation phrases
  ("no", "without", "never", "нет", "без", "не должно") plus their
  ~60-char span, then looks for surviving NEGATIVE_SCENARIO_KEYWORDS
  matches at word boundaries. 8 new tests.
- **#2 Checklist tier consults `relevant_files`.** New signature
  `_determine_checklist_tier(task, relevant_files=None)`: if
  `is_security_sensitive(relevant_files)` is True, tier promotes to
  `critical` regardless of title. Closes the case where "fix typo"
  (title=trivial) on `scripts/auth.py` got `lightweight` (4 items)
  instead of the critical-tier review. 3 new tests.
- **#3 `files_hash` includes 4 KiB content head.** New per-file tuple is
  `(path, mtime_ns, size, sha256(first_4KiB))`. Closes false cache hits
  on filesystems with coarse mtime resolution (FAT/HFS+/SMB) and on
  deliberate `touch -d` reverts. Hash format version bumped
  `verification_runs.v1` → `v2`. 3 new tests.
- **#4 `task_unblock` checks session_capacity.** Pre-v1.3.4 bypass:
  agent could `task_block` then `task_unblock` to dodge the 180-min
  ACTIVE-time check that fires on `task_start`. New `force=True` flag
  is the audit-logged escape hatch. 4 new tests.
- **#5 `--no-knowledge` refused for complex/defect.** SENAR Rule 8
  upgrades from warning to refusal when `complexity=complex` or
  `defect_of` is set. Complex tasks generate patterns worth recording;
  defect tasks generate root-cause/gotcha entries for future avoidance.
  Simple/medium non-defect tasks unaffected. 5 new tests.

### Tests
- 2332 passing, 1 skipped (vs 2270 in v1.3.3). +62 new across
  the four batches.

### Compatibility
- Verify cache: format version bumped (`verification_runs.v1` → `v2`).
  Old cache rows are silently invalidated by the new files_hash shape —
  they don't match new hashes. No DB migration needed.
- `task_unblock(slug)` still works as before for the common path; new
  `force=True` keyword is opt-in.
- `task_done(no_knowledge=True)` still works for simple/medium
  non-defect tasks. Refused for complex/defect — agent must drop the
  flag and let the warning fire (or capture knowledge first).

### Versioning
- `__version__` bumped 1.3.3 → 1.3.4.

## [1.3.3] — 2026-04-27 — Brain init anti-hallucination guards

Hardening release. `tausik brain init` now refuses to silently create a
duplicate set of 4 BRAIN databases when canonical-titled ones already exist
in the same Notion workspace. Triggered by a real incident where an agent
in a second project ran `brain init`, created a parallel set, and then
rationalized the duplicates as "per-project databases for privacy" — which
is the exact opposite of how Shared Brain is designed.

### Architectural rule (now enforced in code, docs, and the brain skill)

The Shared Brain has **ONE set of 4 Notion databases per workspace, shared
by ALL projects**. Per-project privacy is enforced via the
`Source Project Hash` column on every row, NOT by giving each project its
own copies of the four databases.

### Wizard changes

- **Pre-flight workspace search.** Before creating, the wizard calls
  `POST /v1/search` for canonical-titled BRAIN databases (`Brain · Decisions
  / Patterns / Gotchas / Web Cache`).
- **Refuses on full match.** All 4 found → wizard refuses with a clear
  error pointing at `--join-existing`.
- **Refuses on partial match.** 1-3 of 4 found → also refuses (ambiguous
  state); user must either restore the missing DBs or pass all 4 ids
  explicitly with `--decisions-id / --web-cache-id / --patterns-id /
  --gotchas-id`.
- **`--join-existing`** — new flag. Skips create entirely and writes
  `.tausik/config.json` to point at the existing 4 databases. Auto-discovers
  via search; explicit IDs override discovery and are also verified via
  `databases_query(page_size=1)` before save.
- **`--force-create`** — new escape hatch. Bypasses the duplicate guard for
  the rare case of an intentional brand-new workspace (different Notion
  account/integration). Logs an extra confirmation prompt.
- **Search failure tolerance.** If the workspace search itself fails
  (network, auth), the wizard logs a warning and proceeds with create
  rather than blocking — defensive default.

### Brain skill (`agents/skills/brain/SKILL.md`)

Added a top-of-file ARCHITECTURE block. Rewrote the "Brain disabled?"
section: agents must ASK the user before running any setup command, and
must use `--join-existing` when a workspace BRAIN already exists. Explicit
"NEVER guess" + "do not invent --force-create".

### Docs

`docs/en/shared-brain.md` and `docs/ru/shared-brain.md` — Setup section
restructured into "First project — create" / "Second / third project —
join existing" subsections, plus a new **Common mistakes** block listing
the duplicate-DB pitfall and the per-project-copies "privacy" anti-pattern.

### Tests

- `tests/test_brain_init.py` — 16 new tests covering
  `find_workspace_brain_databases`, `verify_brain_databases`, all four
  wizard branches (refuse-full-match, refuse-partial, force-create, join,
  join-with-explicit-ids, verify-failure), search-failure tolerance, and
  no-regression on the clean-workspace path.
- Existing interactive-wizard tests updated to match new prompt order
  (token first, parent-page-id second).

### Test isolation drive-bys

Two more svc fixtures (`tests/test_edge_cases.py`,
`tests/test_e2e_workflow.py`) needed the v1.3.2 `brain_config.load_brain`
stub — the same isolation gap fixed for `test_service_knowledge_decide.py`
in v1.3.2 was hiding in two more files. Tests passed locally only because
the live brain happened to write to Notion silently. Now stubbed.

`tests/test_skills_maturity.py::test_all_stack_guides_have_valid_stack`
fixed for the v1.3 stacks layout (`stacks/<name>/guide.md`, not
`agents/stacks/<name>.md`).

### Compatibility

Fully backward-compatible. Projects that already have brain configured are
unaffected — the guard only fires on `brain init` itself. Tokens, mirror
paths, database IDs, and existing data are untouched.

### Versioning

`__version__` bumped 1.3.2 → 1.3.3.

## [1.3.2] — 2026-04-28 — Brain token storage flexibility

Quality-of-life patch: the Notion integration token for Shared Brain can now be
stored in three places, in priority order:

1. **`os.environ[NOTION_TAUSIK_TOKEN]`** — highest priority. Best for CI/ops.
2. **`.tausik/.env`** — project-local KEY=VALUE file. Gitignored
   (`.tausik/` is fully ignored). Recommended for individual developers
   because it persists without shell-rc setup and survives reboot.
3. **`brain.notion_integration_token`** in `.tausik/config.json` — emits a
   stderr warning ("stored inline; prefer .tausik/.env"). Allowed for
   read-only setups but not encouraged.

### Why

Before 1.3.2 the token could only live in an environment variable. That
caused friction: users would `$env:NOTION_TAUSIK_TOKEN = "..."` in PowerShell,
the brain would work for that session, then break after reboot or window close.
The MCP server (subprocess of the IDE) didn't see env vars set after IDE start.
Several reports of "brain configured but says token missing".

### How

- New helper `brain_runtime.resolve_brain_token(cfg, project_dir=None)` —
  the cascade.
- New parser `brain_runtime._parse_dotenv(path)` — minimal KEY=VALUE reader
  (ignores blank lines, `#` comments, strips quotes; never raises).
- `brain_runtime._build_notion_client`, `try_brain_write_decision`, and
  `try_brain_write_web_cache` now use `resolve_brain_token` instead of
  reading `os.environ` directly.
- `brain_config.validate_brain` updated: doctor and `brain init` no longer
  report "env var not set" when the token is in `.tausik/.env` or
  config.json.
- 7 new tests in `tests/test_brain_token_resolve.py` cover env-wins,
  dotenv fallback, config-inline + warning, all-empty, dotenv parser
  edge cases (quotes, comments, whitespace), missing-file safety,
  and default `NOTION_TAUSIK_TOKEN` env-name fallback.

### Compatibility

Fully backward compatible. Projects that already set the env var continue
to work unchanged — env wins by priority. No config migration needed.

### Notion token UI path (for users)

To get the token: https://www.notion.so/profile/integrations → New
integration (or click an existing one) → Type: **Internal** → reveal
**Internal Integration Secret** (starts with `ntn_` or `secret_`). Then
share the BRAIN page tree with the integration via Notion → page → ⋯ →
Connections → Connect to.

---

## [1.3.0] — 2026-04-28 — Big release: MCP expansion + session discipline + plugin stacks

Single consolidated entry covering everything since v1.2.0 (40+ commits + an
independent 5-agent blind review hardening pass right before ship + a 4-agent
post-ship doc-truth audit that corrected propagated count errors).

### 📐 Post-ship 4-agent doc-truth audit

After v1.3.0 went out, a follow-up audit with 4 parallel agents (link
integrity / stale facts / README marketing / skills docs vs reality) caught
documentation that had not been kept in lock-step with the code:

**Count corrections (propagated across 12+ files):**

- **MCP tools: 100 → 96.** The "(90 project + 10 brain)" claim was wrong on
  the brain side — `agents/claude/mcp/brain/tools.py` ships **6** tools
  (`brain_search`, `brain_get`, `brain_store_decision`,
  `brain_store_pattern`, `brain_store_gotcha`, `brain_cache_web`), not 10.
  Fixed in README, README.ru, AGENTS, CLAUDE, docs/{en,ru}/{mcp,architecture,
  senar-compliance-matrix}.md.
- **Quality gates: "16 checks" → "25 checks".** `DEFAULT_GATES` resolves to
  5 universal + 20 stack-scoped = 25.
- **Skills marketing copy: "34 skills" → "13 core + 25 vendor (38 total)"**
  — README.md, README.ru.md, docs/en/adding-new-ide.md.
- **Dogfooding stats** in README.md / README.ru.md: 291 → 516 tasks, 22 →
  37 sessions, 918/1095 → 2246 tests, throughput ~13 → ~14 per session.
- **RU README badge mismatch fixed:** `[![2226 tests]` label vs
  `tests-2246%20passed` URL aligned.

**Broken internal links (9 of 12 reported, 3 false positives in
i18n-strategy code examples):**

- `CONTRIBUTING.md:87` →`docs/en/architecture.md` (was
  `references/architecture.md`)
- `CHANGELOG.md` three `references/*` links rewritten to
  `docs/research/anthropic-oss-applicability.md`,
  `docs/research/markitdown-integration.md`,
  `docs/en/brain-db-schema.md`.
- `docs/{en,ru}/shared-brain.md` two refs each → `brain-db-schema.md` as
  sibling.
- `docs/en/brain-db-schema.md`: relative-depth bug fixed
  (`../scripts/...` → `../../scripts/...`).
- `docs/ru/claude-md-guide.md`: `skill-spec.md` → `../en/skill-spec.md`
  (no RU translation).
- `scripts/README.md`: `references/project-cli.md` → `docs/en/cli.md`.

**Skill placement fix:** `docs/{en,ru}/skills.md` had `/docs`, `/excel`,
`/pdf` listed under "Integrations" — they're documentation/extraction
tools, not external-service integrations. Moved to a new "Documentation /
Extraction" subsection. "Integrations" now contains only MCP-backed
external services (jira, bitrix24, sentry, confluence).

**Bootstrap template:** `bootstrap/bootstrap_templates.py:build_skills_section`
rewritten for the v1.3 lean-core split. Generated CLAUDE.md / AGENTS.md /
.cursorrules / QWEN.md now explicitly list the 13 always-deployed core
skills and explain that 25+ official/vendor skills install on demand via
`tausik skill install <name>`.

**User-reported "two PDF links in main README":** investigated by the
link-integrity agent — exhaustive grep across `README.md` and
`README.ru.md` returned zero PDF references. The user may have been
looking at a different surface; no PDFs are broken.



### 🧠 Shared Brain — cross-project knowledge base (Notion-backed)
- 4 Notion DBs (decisions, patterns, gotchas, web_cache) + local SQLite mirror with FTS5 (Cyrillic-aware).
- Notion REST client, stdlib-only, with retry/backoff + 350ms write throttle.
- Pull-sync engine with delta-fetch (`last_edited_time` cursor), atomic single-tx, WAL mode.
- `tausik brain init` wizard creates 4 DBs + atomic config in one shot.
- MCP server `tausik-brain` (7 tools) + skill `/brain` (query/store/show/status/move).
- Auto-route `tausik decide` via rule-based local↔brain classifier.
- PostToolUse `WebFetch` auto-cache hook → next fetch of same URL is blocked by mirror.
- Proactive lookup before WebSearch/WebFetch — instant hit from mirror.
- Privacy: project names hashed (SHA256[:16]) — no plaintext in Notion.
- Stale-lock recovery for SIGKILL'd wizard. NFC normalization for unicode-equivalent names.
- Brain schema migration scaffold (forward-only, single-tx).
- Qwen Code: brain MCP registered via bootstrap.

### 🧩 Plugin stack architecture (single source of truth)
- `stacks/<name>/{stack.json, guide.md}` declarative format (was: 5 hardcoded modules).
- JSON Schema (Draft-07) + actionable validator.
- `StackRegistry` with layered deep-merge: built-in ← `.tausik/stacks/<name>/` user override.
- 25 built-in stacks migrated (incl. 5 IaC: ansible/terraform/helm/k8s/docker).
- 6 consumers refactored to use registry with hardcoded fallback for boot safety.
- CLI: `tausik stack {list,info,export,diff,reset,lint,scaffold}` for full lifecycle.
- 5 MCP tools: `tausik_stack_{list,show,lint,diff,scaffold}` for agent-driven use.
- Bootstrap NEVER writes to `.tausik/stacks/` (test-enforced invariant).

### 🎭 Roles — first-class CRUD with hybrid storage
- New SQLite `roles` table (migration v18) — slug PK + title + description.
- Auto-seed from `DISTINCT tasks.role` on migration (no orphan task references).
- Hybrid storage: metadata in DB, markdown profile in `.tausik/roles/<slug>.md` (user) or `agents/roles/<slug>.md` (built-in).
- Bootstrap NEVER overwrites `.tausik/roles/` — user profiles survive re-bootstrap.
- CLI: `tausik role {list,show,create,update,delete,seed}` with `--extends` profile cloning.
- 6 MCP tools: `tausik_role_{list,show,create,update,delete,seed}` for CRUD.
- Delete refuses if tasks reference role (force=true → cascade NULL the references).

### ⏱️ Session active-time (gap-based) replaces wall clock
- Sessions exceeding 180-min SENAR Rule 9.2 are now measured by ACTIVE minutes, not wall clock.
- Activity counted via `events` table; gaps ≥ idle threshold (default 10 min) excluded as AFK.
- New PostToolUse hook `activity_event.py` writes one row per tool call so the metric works for any agent activity (not just MCP/CLI).
- `tausik status` shows both numbers: "Session: #N (X min active / Y min wall, Z% idle)".
- New CLI `tausik session recompute` retro-analyses prior sessions (real numbers vs claimed wall clock).
- Threshold tunable via `.tausik/config.json` `session_idle_threshold_minutes`.
- session_extend now respects project's configured `session_max_minutes` (was: hardcoded 180).

### 🔬 SENAR verification — scoped + cached
- Pytest gate runs ONLY tests for `relevant_files` (was: full suite always).
- `verification_runs` cache reuses green runs within 10-min TTL on same `files_hash`.
- Cache key includes resolved gate command — config changes invalidate stale entries.
- Security-sensitive files (auth/payment/jwt/oauth/sso/etc + .env/.pem/.key) bypass cache, always re-verify.
- Tier mapping fixed: simple→lightweight, medium→standard, complex→high (was hardcoded `lightweight`).
- v1.3 fix: `relevant_files=None` SKIPS instead of falling back to full suite (burned MCP 10s budget).
- Scoped-skip results NOT cached as verified — prevents silent QG-2 weakening.
- `tausik verify --task <slug>` for ad-hoc verification.

### 🎯 Agent-native planning (tool calls, not hours)
- Tier scale: trivial(≤10) / light(≤25) / moderate(≤60) / substantial(≤150) / deep(≤400+).
- `--call-budget` auto-derives tier; warning at 1.5×budget for re-calibration.
- `task start <slug> --force` bypasses session capacity gate (audit-logged).
- Custom stacks via `.tausik/config.json` (`custom_stacks`) without code changes.

### 🛡️ Memory Discipline — auto-memory protection
- PreToolUse hook blocks Write/Edit to `~/.claude/projects/*/memory/` from TAUSIK projects.
- Bypass via explicit `confirm: cross-project` marker in last user prompt.
- PostToolUse audit catches project-specific content that bypassed via regex (paths, slugs, tausik commands).
- Memory-block guard widened to ALL `~/.claude/**/memory/` (was: only `projects/<slug>/memory/`).

### 📦 Bootstrap deploy fix (CRITICAL — caught in v1.3 dogfooding)
- Built-in skills under `agents/skills/` are NOW source-of-truth — force-included in deploy.
- Was: explicit allowlist via `core_skills`/`extension_skills`/`installed_skills`. Saved config froze old list.
- Result: 9 missing core skills restored (review, brain, commit, debug, interview, markitdown, ship, skill-test, test).
- Smoke-test in `tests/test_bootstrap_skills_coverage.py` guards against future drift (4 cases).

### 🪝 Hooks
- `activity_event.py` (PostToolUse, broad matcher) — feeds active-time metric.
- `brain_post_webfetch.py` (PostToolUse, WebFetch) — auto-cache web responses.
- `brain_search_proactive.py` (PreToolUse, WebSearch|WebFetch) — mirror lookup before fetch.
- `memory_pretool_block.py` + `memory_posttool_audit.py` (Write|Edit|MultiEdit).
- Shared helpers in `_common.py`.
- Strip invisible separators (U+2028/2029/0085/VT/FF) before marker anchor matching.

### 🧪 DX & Framework Polish
- `task_done` accepts inline `--evidence` arg → log+done in one CLI call (was: two).
- `_verify_ac` accepts ✓/verified markers + literal "AC verified" — broader format tolerance.
- Refactored 4 files to stay under 400-line filesize gate: split session/role/stack subparsers + service helpers.
- 3 rounds of post-merge review: 5 HIGH + 11 MED + 4 LOW findings closed.
- Quality reviews + SENAR audit + adversarial critic spawn via `/review`.

### 📚 Docs
- `docs/en/{stacks, customization, upgrade, shared-brain}.md`.
- `docs/ru/shared-brain.md`.
- README EN/RU with v1.3 features.
- `references/anthropic-oss-applicability.md` — patterns survey.
- `references/markitdown-integration.md` — opt-in DOCX/PPTX/XLSX/HTML/EPUB.

### 🛠️ Misc
- `markitdown` opt-in capability (lazy import, zero-deps invariant preserved) + `tausik doc extract`.
- `tausik brain status` snapshot CLI.
- `tausik brain move <id> --to-brain|--to-local` cross-project ownership transfer.
- 5 SENAR Compliance table rows updated with v1.3 semantics.

### ⚙️ Config knobs (hardcode → `.tausik/config.json`)

Documented in `references/configuration.md`. Project-level overrides without forking:

- `verify_cache_ttl_seconds` (default 600) — verify-run reuse window.
- `session_warn_threshold_minutes` (default 150) — stop-hook reminder threshold.
- `session_idle_threshold_minutes` (default 10) — gap above which pause = AFK.
- `session_max_minutes` (default 180) — hard SENAR Rule 9.2 limit.
- `session_capacity_calls` (default 200) — per-session tool-call budget.
- `custom_stacks`, `gates`, `brain.*` — already documented in earlier tiers.

### 🩺 `tausik doctor` — health diagnostic
Single-command sanity check: venv + DB + MCP servers + core skills + bootstrap drift + config knobs + gates registry + active session. Exits 1 on any FAIL so CI can gate on it.

### 🛡️ `/zero-defect` skill (Maestro-inspired)
Session-scoped precision mode: 8 rules (read-before-write, verify-before-claim, no API hallucination, etc) for high-stakes work. Inspired by [Maestro](https://github.com/sharpdeveye/maestro) `/zero-defect`.

### 🔒 Hardening Pass (post-cycle audits)

6 audit cycles, 35+ findings closed:

- **Newline injection** scrubbed across epic/story/task/role/memory write paths via shared `safe_single_line` helper.
- **role_create** writes profile FS-first via temp+rename, then DB INSERT — no orphan files on either failure path.
- **role_delete** uses begin_tx/commit_tx (not raw BEGIN) so audit `event_add` honors transaction; cascade-NULLs `tasks.role` on `force=true`.
- **Migration v18** auto-seeds `roles` from `DISTINCT tasks.role` with normalization (lowercase, strip, space→hyphen) and rewrites `tasks.role` in-place — no orphan rows. `v18_seeded` meta flag set in BEGIN IMMEDIATE tx WITH the seed (atomic, idempotent across concurrent inits).
- **Bootstrap rmtree** now uses `onexc=` on Python 3.12+, `onerror=` legacy fallback, with chmod-and-retry for Windows readonly files.
- **Stack scaffold** atomic write retries on Windows `PermissionError` (4×100ms); cleans up `.tmp` on any failure path.
- **Doctor** ASCII fallback (`OK`/`WARN`/`FAIL`) when stdout encoding lacks UTF-8 (Windows cp1251); CRLF normalization in drift compare; pre-svc DB existence captured to surface "never initialized" cases.
- **Activity hook** uses `PRAGMA journal_mode=WAL` + `synchronous=NORMAL` to reduce per-call fsync overhead.
- **session_warn_threshold** clamped to `max(1, …)`.
- **Quality-gate WARN** when scoped-skip fires with no `relevant_files` (visible to user, not silent).
- **MCP handlers** parity: claude+cursor byte-identical for `_handle_stack_scaffold` (catches `ValueError`/`KeyError`).

### 🔐 Independent 6-agent review pass — 31 findings closed

After cycle-6 SHIP verdict, ran a SEPARATE round of 6 parallel independent reviewers (architecture / public API / security / performance / docs / cross-platform). Closed 31 additional findings across waves:

**Security (Wave 1)**
- `git push` gate now uses regex matching `(?:^|[\s;&|()` + variant`])git push\b` — catches `cd && git push`, `(git push)`, `/usr/bin/git push`, `git -c x=y push`. Old token-split bypass eliminated.
- Memory pretool block resolves symlinks/junctions: `os.path.realpath(parent)` after the literal-path check — symlink-into-`~/.claude/**/memory/` is now blocked.
- `TAUSIK_SKIP_HOOKS` no longer disables security gates blanket. Per-hook scoped: `TAUSIK_SKIP_PUSH_HOOK=1` / `TAUSIK_SKIP_MEMORY_HOOK=1`.
- Vendor skill `requires` validated against PEP 508 simple-spec regex; rejects entries starting with `-`. `pip install --` separator added so positional args can't be re-interpreted as flags.

**Data integrity (Wave 2)**
- `brain_project_registry._normalize_path` adds `unicodedata.normalize('NFC', ...)` — fixes macOS HFS+ NFD double-registration.
- `bootstrap_config.save_tausik_config` writes to `*.tmp` then `os.replace` — atomic, SIGINT-safe.

**Truth (Wave 3)**
- README badges and stat lines updated: 35 → 38 skills, 82 → 100 MCP tools, 13 → 19 hooks, 1095 → 2246 tests.
- CLAUDE.md "Команды" section expanded with full top-level command list.

**Performance (Wave 4)**
- `compute_active_minutes` SQL drops `julianday()` from WHERE clause — events `created_at` index now used. ~50× speedup on 100k-row tables.
- `bootstrap copy_dir` byte-compares before write — no-op re-bootstrap is now near-instant on Windows+AV.

**API parity (Wave 5)**
- `--group` → `--story` rename for `task add` (with `--group` deprecated alias for back-compat).
- 4 new MCP tools: `tausik_doctor`, `tausik_verify`, `tausik_stack_reset`, `tausik_stack_export` — close CLI/MCP parity gap.

**Operations (Wave 6-7)**
- File logging: `RotatingFileHandler` at `.tausik/tausik.log` (5MB × 3 backups) for WARNING+. Errors no longer disappear in MCP context.
- CI matrix expanded to `[ubuntu, windows, macos]` × `[3.11, 3.12, 3.13]` — Windows-only bugs caught.
- CI now runs mypy + bandit (warning-only) alongside ruff.

### 🔬 Independent 5-agent blind review hardening pass (pre-ship)

Before tagging 1.3.0 we ran an independent blind review with five parallel
agents (architecture / security / agent UX / documentation truth / quality
gates). 50 findings: 16 HIGH / 21 MED / 13 LOW. The pre-ship pass closes
all HIGH and the most-impactful MED findings — the rest are tracked for
v1.3.x patch releases.

**QG-2 enforcement holes closed**

- **`tausik_task_update status=done` bypass** — the most serious finding.
  A single MCP call could close any task, skipping QG-2, AC verification,
  scoped pytest, cascade, and `call_actual` recording. Now refused with
  explicit `ServiceError` pointing at the lifecycle method (`task_done` /
  `task_start` / `task_block` / `task_review`). The "QG-2 cannot be
  bypassed (--force removed)" claim is now end-to-end true.
- **All-skipped scoped pytest passing as green** — when `relevant_files`
  was supplied but no `tests/test_<basename>.py` matched (source file
  with deleted or missing test), gates returned `passed=True` and QG-2
  closed silently. Now returns synthetic FAIL with
  `status="no-test-mapped"` and a notes line pointing at the missing
  tests.

**Security pattern gaps closed**

- **Brain plaintext leak via `tags`/`stack`/`domain`/`severity`** — only
  named text fields (name/context/decision/rationale) were scrubbed; tags
  arrays passed through verbatim, so `tags=["my-app", "example.com"]`
  would leak the project name into Notion despite the SHA256-hash privacy
  claim. Now ALL string-valued props per category join the scrub haystack.
- **`memory_pretool_block` Linux/macOS bypass via case** — the
  `"memory" in segments` check was case-folded only on Windows.
  `~/.claude/projects/foo/MEMORY/x.md` (uppercase) slipped through on
  every other platform. Now lowercase unconditionally.
- **Security-sensitive token list extended** — `_SECURITY_PATH_TOKENS` and
  `_SECURITY_BASENAMES` now cover `webhook`, `csrf`, `xsrf`, `mfa`, `2fa`,
  `totp`, `api_key`, `apikey`, `permissions`, `acl`, `iam`, `rbac`, `jwt`,
  `oauth`, `session`, `signup`, `login` as bare tokens (match files at
  any depth, not just inside same-named directories).

**Agent UX — RAG discoverability fully closed**

User report: *"Claude grepping over the codebase instead of using our RAG"*.
Root cause was structural — the framework wires `codebase-rag` MCP into
`.mcp.json` but never tells the agent it exists. Closed across four layers:

- **Tool routing rubric in templates** — `bootstrap_templates.py` adds a
  TOOL_ROUTING block with a Need / Primary / Fallback table directing
  agents to `mcp__codebase-rag__search_code` first, `Grep` only as
  fallback. Propagates to all four IDE configs (CLAUDE.md / AGENTS.md /
  .cursorrules / QWEN.md).
- **Skill word swaps** — `agents/skills/zero-defect/SKILL.md` rule 3 and
  `agents/skills/debug/SKILL.md` Phase 0 step 5 previously said "grep
  the codebase" — now point at `search_code` first, with Grep as fallback.
- **`session_start.py` injects RAG status** — agent sees
  `RAG: N chunks indexed` / `RAG: empty — full reindex spawned in
  background` / `RAG: not initialised — reindex spawned` at every new
  session.
- **Auto-incremental reindex** — every SessionStart spawns
  `index_incremental` in a detached background process (returns in
  ~3 ms, never blocks the agent); pre-commit hook runs incremental with
  5-second timeout so committed changes land in the index before the
  next session. First run on a fresh project triggers `index_full`
  automatically. The agent no longer needs to know about `reindex`
  at all.

**Architecture — drift hazard removed**

- **`_FALLBACK_STACK_GATES` (190 LOC) dropped** from `default_gates.py`.
  This was a hardcoded copy of every stack-scoped gate that silently
  activated when `stack_registry` import failed — any change to
  `stacks/<name>/stack.json` would not appear if the registry hiccupped.
  Now: failure logs WARNING and returns empty dict; universal gates
  (filesize, ruff, mypy, bandit, tdd_order) remain hardcoded since
  they're not stack-scoped. File shrinks 290→101 LOC.

**Documentation truth — counts reconciled**

- **MCP tool count** corrected from "106 (96 project + 10 brain)" to the
  actual **96 (90 project + 6 brain)**. The "96" was an aspirational
  number that matched no reality. Updated in 12+ files.
- **Test count** corrected from "2232" / "2226" / "2235" (mixed across
  files) to the empirical **2246** (`pytest --collect-only`).
- **`docs/en/doctor.md`** intro fixed to "eight checks" and the critical
  skills list synced to the actual `project_cli_doctor.py` set:
  `{start, end, task, plan, review, brain, ship, checkpoint}`.

**Filesize gate compliance**

Four modules compacted to stay under the 400-line limit while adding new
guards: `service_task.py` 419→400, `service_verification.py` 413→358,
`brain_mcp_write.py` 437→375, `default_gates.py` 290→101.

**Tests added**

- `tests/test_v131_blind_review.py` — 11 regression tests covering each
  closed finding.
- `tests/test_hud_cli.py` updated to use `be.task_update` for direct
  status manipulation (the QG-2 path the test exercises is meant to
  bypass — now explicit via the backend layer).

**Tracked for v1.3.x patch releases (still open from review):** verify-
cache cross-check against git diff, CLI-into-backend layer cleanup,
6-finding hook hardening batch, 5-finding QG-2 hardening batch, 13 LOW
polish items.

### 📊 Stats
- **2246 tests passing** (1183 → 2246 over the cycle, +11 new from blind-review hardening).
- **96 MCP tools** (90 project + 10 brain), up from 80 in v1.2.0.
- **13 core skills + 25+ official/vendor on demand** — v1.3 lean-core split: workflow primitives auto-deploy, niche/opt-in skills (`/zero-defect`, `/markitdown`, `/skill-test`, `/audit`, `/docs`, ...) install via `tausik skill install <name>`. Up from 29 unconditionally-deployed skills in v1.2.
- **19 hooks** (was 13 — added `activity_event`, `memory_pretool_block`, `memory_posttool_audit`, `brain_post_webfetch`, `brain_search_proactive`, `task_call_counter`).
- **25 stacks** (was 20 — added 5 IaC: ansible, terraform, helm, kubernetes, docker).
- Schema version: 17 → 18 (added `roles`, `session_activity`, `verification_runs` tables).
- 11 new modules (4 service helpers, 3 parser splits, 2 hooks, 1 CLI handler, 1 doctor).

### Compatibility
- No breaking changes. Existing `.tausik/config.json` merges cleanly.
- Re-bootstrap recommended to pull deployed scripts/MCP servers/skills up to date.
- Migration v18 auto-seeds `roles` table from `DISTINCT tasks.role` — no manual setup needed.
- After upgrade the first session sees `RAG: not initialised — full reindex spawned in background` and auto-builds the index.

---

## [1.3.0-detail-stacks] — historical detail (folded into 1.3.0 above)

> Per-story detail of plugin stack architecture work. Shipped as part of v1.3.0 — listed here for archive only.

### Added — Stack plugin foundation (Story 1, plugin-foundation)

- **`stacks/_schema.json`** — JSON Schema (Draft-07) for stack declarations. Fields: `name` (required), `version`, `extends` (`builtin:NAME`), `detect` (list of `{file,type,keyword}` with `type ∈ exact|glob|dir-marker`), `extensions`, `filenames`, `path_hints`, `gates` (with `null` to disable), `guide_path`, `extensions_extra` (additive merge).
- **`scripts/stack_schema.py`** — `validate_decl(decl, source) -> list[str]` returns actionable errors per offending field; never silently skips. 12 edge-cases covered via smoke harness.
- **`scripts/stack_registry.py`** — `StackRegistry` class with `load_builtin`/`load_user`/`reload`, layered deep-merge (extensions_extra additive, gates per-key override + null disable), and accessors `signatures_for`/`extensions_for`/`filenames_for`/`path_hints_for`/`gates_for`/`guide_path_for`. Source tracking: `source_for(name)` returns `'builtin'|'user'|'overridden'|None`; `is_user_overridden(name)` for user-override detection.
- **`tests/test_stack_registry.py`** — 27 tests across `TestLoadBuiltin`, `TestUserOverrides`, `TestReload`, `TestAccessors`, `TestSourceTracking`.

### Added — 25 built-in stacks migrated to plugin layout (Story 2, migrate-builtins)

Each stack is now `stacks/<name>/{stack.json, guide.md}`. Source of truth shifted from 5 hardcoded modules to a single declarative file.

- **Python family** ([stacks/python/](stacks/python/), fastapi, django, flask) — pytest gate owns stacks=[python,fastapi,django,flask].
- **Frontend** (react, next, vue, nuxt, svelte, typescript, javascript) — typescript owns `tsc`; javascript owns `eslint`+`js-test`. Both gates list all 6 frontend frameworks in `stacks` field.
- **Native** (go, rust, java, kotlin, swift, flutter) — go owns `go-vet`+`golangci-lint`+`go-test`; rust owns `cargo-check`+`clippy`+`cargo-test`; java owns `javac`; kotlin owns `ktlint`.
- **PHP family** (php, laravel, blade) — php owns `phpstan`+`phpcs`+`phpunit`; blade extension `.blade.php` is union'd with `.php` stacks via compound-extension logic in dispatch.
- **IaC** (ansible, terraform, helm, kubernetes, docker) — each stack owns its lint gate (ansible-lint / terraform-validate / helm-lint / kubeval / hadolint). All three detect forms exercised: `exact` (Dockerfile, Chart.yaml), `glob` (`*.tf`), `dir-marker` (playbooks/, roles/, k8s/, manifests/, .kube/).
- **`agents/stacks/*.md`** removed; legacy fallback in bootstrap still finds these for partial-migration repos.

### Changed — 6 consumers refactored to use the registry (Story 3, refactor-consumers)

Hardcoded data moved to defensive registry lookups with hardcoded fallbacks for boot safety.

- **[scripts/project_types.py](scripts/project_types.py)** — `DEFAULT_STACKS` now computed from `default_registry().all_stacks()`; `_FALLBACK_STACKS` retains the pre-plugin hardcoded set. `VALID_STACKS` remains an alias for back-compat.
- **[bootstrap/bootstrap_config.py](bootstrap/bootstrap_config.py)** — `STACK_SIGNATURES` built via `_load_stack_signatures()`. Each registry `{file, type, keyword}` entry is rendered to the `(filename, keyword)` tuple form `_signature_match()` understands; `dir-marker` types get the trailing `/` they need.
- **[scripts/gate_stack_dispatch.py](scripts/gate_stack_dispatch.py)** — `_EXT_TO_STACKS`, `_FILENAME_TO_STACKS`, `_PATH_HINTS` invert per-stack registry data via `_build_dispatch_tables()`. Compound `.blade.php` keeps its `.blade.php ∪ .php` semantics.
- **[scripts/default_gates.py](scripts/default_gates.py)** — split into `UNIVERSAL_GATES` (5 hardcoded: filesize, tdd_order, ruff, mypy, bandit) ∪ `_build_stack_scoped_gates()` (20 from registry). Gate ownership lives in each `stacks/<name>/stack.json`; first-stack-wins for duplicate names (alphabetical iteration). `DEFAULT_GATES` is the merged total — consumers untouched.
- **[scripts/project_config.py](scripts/project_config.py)** — `STACK_GATE_MAP` is registry-derived transitively via DEFAULT_GATES; no code change needed.
- **[agents/{claude,cursor}/mcp/project/tools.py](agents/claude/mcp/project/tools.py)** — 4 inline JSON-Schema stack enums replaced by `_STACKS_ENUM` constant under fenced `# === BEGIN/END STACKS_ENUM ===` markers. Bootstrap regenerates the constant from the registry via `bootstrap_stacks.regenerate_mcp_stack_enums()`. Also adds the 5 IaC stacks (ansible, terraform, helm, kubernetes, docker) which were missing from the legacy hardcoded list.

### Added — User customization layer (Story 4, user-customization)

- **`.tausik/stacks/<name>/`** is a first-class layered registry. `extends: "builtin:NAME"` deep-merges over a built-in entry; missing `extends` with a known name is full replace; new names are standalone stacks. `null` gate value disables an inherited gate. `extensions_extra` is additive.
- **`bootstrap/bootstrap_stacks.py`** — extracted `copy_stacks` and added `regenerate_mcp_stack_enums()`. Bootstrap NEVER writes inside `.tausik/`; **`tests/test_bootstrap_non_destructive.py`** asserts this with 5 cases (override-untouched, override-of-builtin-name-untouched, target-isolation, no-`.tausik`-paths-written, idempotent across runs).
- **CLI: `tausik stack {export,diff,reset,lint}`** ([scripts/project_cli_stack.py](scripts/project_cli_stack.py)) — `export` prints the resolved decl; `diff` shows unified diff between built-in and user override; `reset` removes `.tausik/stacks/<name>/` (with `--yes`); `lint` validates every user override against the schema. `info` and `list` retain previous behaviour.
- **Bootstrap printout** — surfaces `.tausik/stacks/` overrides on every run; first-time users see a guidance line directing customization to the safe path.

### Added — Documentation (Story 5, documentation-overhaul)

- **[docs/en/stacks.md](docs/en/stacks.md)** — plugin layout, schema reference, adding new stacks, registry consumer table.
- **[docs/en/customization.md](docs/en/customization.md)** — override rules, merge semantics, validation tools, do/don't list.
- **[docs/en/upgrade.md](docs/en/upgrade.md)** — bootstrap-owned vs user-owned tree, upgrade workflow, breakage scenarios + recovery.
- CLAUDE.md QG-2 description amended for scoped-skip behaviour and `.tausik/stacks/` invariant.

### Fixed — pytest gate scoped-skip (defect of stack-schema-design)

- **Scoped pytest gate must skip, not fall back to full suite** ([scripts/gate_runner.py](scripts/gate_runner.py)) — Previously, when `relevant_files` was non-empty but `resolve_test_files_for_relevant()` returned no matches (e.g. a brand-new module without `tests/test_<basename>.py` yet), the gate substituted `tests/` and ran the **entire** 900+ test suite as a "regression-safe fallback". This silently turned every `task_done` on a new module into a 60s+ wait and defeated the scoping promise in CLAUDE.md ("гонит только `tests/test_<basename>.py` для каждого relevant_files"). Fix: introduced `_SCOPED_SKIP_SENTINEL` returned by `run_command_gate` when scoped resolution fails; `run_gates` translates it to a `skipped=True` result with message `"No test file maps to relevant_files via tests/test_<basename>.py heuristic; gate skipped (scoped run)."`. Empty `relevant_files` (no scoping data at all) still falls back to the full suite — that path is regression-safe and unchanged. (`pytest-gate-must-skip-when-scoped-relevant-files-h`)

### Test Coverage — pytest gate scoped-skip

- **3 new + 1 rewritten** in [tests/test_gates.py](tests/test_gates.py) class `TestPytestGateScopeSubstitution`: `test_scoped_run_with_no_test_mapping_skips` asserts the sentinel is returned and `subprocess.run` is **not** invoked; `test_unscoped_call_falls_back_to_full_suite` covers the empty-relevant_files path; `test_run_gates_translates_scoped_skip_into_skipped_result` verifies end-to-end conversion to `skipped=True` result entries.

### Added — Backlog finish (4 final planning tasks)

Last 4 planning tasks shipped — backlog drained to **388/388 done** (100%):

- **Brain status CLI + skill** ([scripts/brain_status.py](scripts/brain_status.py), [agents/skills/brain/SKILL.md](agents/skills/brain/SKILL.md)) — `tausik brain status [--json]` снапшот состояния brain: enabled, mirror path/size/last-modified, per-category row counts + last_pull_at + last_error from `sync_state`, registered projects (name/canonical/hash), last web_cache write. `collect_status()` graceful: missing mirror / unreadable config / empty registry → consistent dict с `error` field, без crash. Skill SKILL.md документирует. (`brain-skill-status`)
- **Brain move CLI + skill** ([scripts/brain_move.py](scripts/brain_move.py)) — `tausik brain move <id> --to-brain --kind <decision|pattern|gotcha>` или `--to-local --category <decisions|patterns|gotchas>`. Cross-project ownership check (source_project_hash должен совпадать с current project's hash; `--force` override). Web_cache → refused (no local counterpart). На to-local после успеха: archive Notion page (`pages.update(archived=true)`) + delete from mirror, unless `--keep-source`. Story `brain-tausik-integration` + epic `shared-brain` auto-closed. (`brain-skill-move`)
- **Anthropic OSS research** ([docs/research/anthropic-oss-applicability.md](docs/research/anthropic-oss-applicability.md)) — Surveyed 7 наиболее релевантных Anthropic OSS репозиториев (knowledge-work-plugins, anthropic-cli, agent-sdk-workshop, original_performance_takehome, skills, claude-code-action, financial-services-plugins). Identified 9 applicable patterns (5 simple, 3 medium, 1 complex). Top 3 recommended next tasks: `tausik-skill-manifest` (skill.yaml registry), `tausik-metrics-tiers` (bronze/silver/gold/platinum), `tausik-brain-swappable-backend` (decouple from Notion). (`research-anthropic-repos`)
- **markitdown opt-in integration** ([scripts/doc_extract.py](scripts/doc_extract.py), [skills-official/markitdown/SKILL.md](skills-official/markitdown/SKILL.md), [docs/research/markitdown-integration.md](docs/research/markitdown-integration.md)) — Discovery: TAUSIK не имел "ручных парсеров документов" — pdf/excel skills делегируют Claude Code `Read` tool. markitdown добавлен как **opt-in** capability (convention #19 zero-deps сохранён): lazy import + graceful `None` если не установлен. CLI `tausik doc extract <file>` + Python API `extract_to_markdown(path)`. Когда использовать: DOCX/PPTX/XLSX/HTML/EPUB. PDF redirect → `/pdf` skill. Future hook: `brain_post_webfetch` мог бы использовать для HTML conversion (noted, not implemented). (`markitdown-integration`)

### Test Coverage — Backlog finish

- **+39 tests** — `test_brain_status.py` (9 tests: disabled, config_load_error, missing_mirror, enabled_empty/with_data, registered_projects, registry_missing, format_status×2), `test_brain_move.py` (19 tests: TestMoveToBrain×10 включая happy paths + scrub_blocked + notion_error + token_missing + brain_disabled + bad_input + not_found + keep_source; TestMoveToLocal×8 включая cross-project ownership × force, web_cache refused, mirror archive), `test_doc_extract.py` (11 tests + 1 skipif integration: is_available, happy path, format_hint, falls_back_to_markdown_attr, missing markitdown/path/empty/exception/unexpected shape).

### Fixed — Review findings MED/LOW (story review-findings-mlow-fix, 11 issues)

Follow-up to the 5 HIGH fixes — 11 MEDIUM/LOW findings from the same multi-agent review:

- **A7 MED** ([scripts/gate_runner.py](scripts/gate_runner.py) `resolve_test_files_for_relevant`) — Resolver теперь использует `os.walk(tests/)` вместо `os.listdir`. Tests в nested dirs (`tests/integration/`, `tests/unit/scoped/`) корректно матчатся вместо silent fallback на full suite. Single-pass index by basename, дедуп между путями. (`review-mlow-resolver-recursive`)
- **B6+B7 MED** ([scripts/brain_schema.py](scripts/brain_schema.py) `_migrate`) — Добавлен `PRAGMA foreign_keys=OFF/ON` envelope (insurance для будущих FK-touching migrations) + `PRAGMA foreign_key_check` после COMMIT (raise on violations). Docstring документирует irreversibility контракт ("failed batch only rolls back current; previously committed migrations stay applied"). (`review-mlow-brain-safety`)
- **B2 MED** ([scripts/brain_project_registry.py](scripts/brain_project_registry.py) `_acquire_lock`) — Docstring документирует "single reclaim per call (reclaimed flag)" контракт + acknowledge небольшой TOCTOU window между `_is_stale_lock` и `os.unlink`. (`review-mlow-brain-safety`)
- **A5 LOW** ([scripts/service_verification.py](scripts/service_verification.py) `run_gates_with_cache`) — `append_notes_fn` теперь типизирован `Callable[[str, str], None] | None` (был `Any`). (`review-mlow-polish-batch`)
- **A6 LOW** ([scripts/project_cli_verify.py](scripts/project_cli_verify.py) `cmd_verify`) — На cache HIT пишется `events` row `action='verify_cache_hit'` для telemetry. Best-effort try/except — никогда не блокирует verify. (`review-mlow-polish-batch`)
- **B4 LOW** ([scripts/brain_init.py](scripts/brain_init.py) `create_brain_databases`) — Per-category try/except. Новый `PartialCreateError(NotionError)` с `created_ids` attribute — partial-create surface'ит реально-созданные ids в orphan-cleanup guidance вместо `<missing>`. (`review-mlow-polish-batch`)
- **B5 LOW** ([scripts/brain_init.py](scripts/brain_init.py) `CliIO.prompt`) — EOF/KeyboardInterrupt branches: `KeyboardInterrupt` → "Aborted by user (Ctrl+C)", `EOFError` → "Aborted: no input available (stdin closed/piped)". Раньше — общее "Aborted by user" вне зависимости от типа. (`review-mlow-polish-batch`)
- **C-L3 LOW** ([tests/test_brain_notion_client.py](tests/test_brain_notion_client.py) `test_token_not_in_retry_log`) — Добавлен `assert len(caplog.records) >= 1` чтобы поймать silent-pass на пустом caplog (дрейф logger config). (`review-mlow-polish-batch`)
- **A2 docstring** ([scripts/service_verification.py](scripts/service_verification.py) `run_gates_with_cache`) — Concurrency note: "WAL safe but duplicate rows accepted; BEGIN IMMEDIATE worse" — accepted limitation. (`review-mlow-polish-batch`)
- **A3 docstring** ([scripts/service_verification.py](scripts/service_verification.py) `compute_files_hash`) — mtime resolution caveat: NTFS 100ns / ext4 1μs / HFS+ 1s / FAT 2s — false cache hits possible на быстрых правках на FAT/HFS+, recommendation для таких FS. (`review-mlow-polish-batch`)

### Test Coverage — Review fixes

- **+8 hardening tests** — `test_gates.py` (+4 TestResolveTestFilesForRelevant: glob_subdirectory_test_files, glob_subdirectory_with_suffix_variants, dedup_when_test_appears_in_multiple_dirs, missing_tests_dir_returns_empty), `test_brain_init.py` (+3 partial create + EOF distinct messages), `test_brain_notion_client.py` (+1 caplog non-empty assertion).

### Fixed — Review findings (story review-findings-fix, 5 HIGH issues)

Multi-agent review caught 5 HIGH-severity findings post-merge of the SENAR verify redesign + hooks widening; addressed in this batch:

- **C1** ([scripts/hooks/memory_pretool_block.py](scripts/hooks/memory_pretool_block.py)) — Memory guard regression: `~/.claude/projects/abc/memory` (directory-form path, no trailing file) больше НЕ блокировался. `os.path.normpath` срезает trailing slash, потом `[:-1]` slice исключает `'memory'` из проверки. Старый guard `rest[1] == 'memory'` это ловил. Fix: `'memory' in segments` без `[:-1]` — basename `memory.md` всё ещё False (segment exact compare), но bare `memory` ловится. (`review-fix-c1-memory-guard-dir`)
- **A9** ([scripts/service_gates.py](scripts/service_gates.py) `_run_quality_gates`) — Tier mapping регрессия: scope hardcoded в `'lightweight'` для ВСЕХ задач. Нарушал SENAR Rule 5 — auditor querying `verification_runs WHERE scope='critical'` получал 0 строк. Fix: scope резолвится через `_determine_checklist_tier(task)` (simple→lightweight, medium→standard, complex→high), `is_security_sensitive(relevant_files)` override → `'critical'`. (`review-fix-a9-tier-mapping`)
- **A4** ([scripts/service_verification.py](scripts/service_verification.py)) — Security bypass дыры: `auth.py`/`payment.py`/`billing.py` в корне НЕ матчатся (требовало `/auth/` со слэшами). Также не покрыты oauth/sso/saml/crypto/secrets/keys/admin/rbac/webhook/jwt/session/2fa/mfa/signup/login/password. `.env`/`.pem`/`.key`/`.p12`/`.pfx`/`.crt`/`.asc`/`.gpg` extensions тоже игнорировались. Fix: `_SECURITY_PATH_TOKENS` расширен +16 tokens; новые `_SECURITY_BASENAMES` frozenset для root-level `*.py/.ts/.go`; новый `_SECURITY_EXTENSIONS` frozenset; `is_security_sensitive` объединяет 3 проверки. (`review-fix-a4-security-bypass-tokens`)
- **A1** ([scripts/service_verification.py](scripts/service_verification.py), [scripts/project_cli_verify.py](scripts/project_cli_verify.py)) — Cache key не включал резолвенный gate command. Изменение `project_config.DEFAULT_GATES['pytest']['command']` оставляло старые зелёные runs валидными → стейл-кэш с НОВОЙ командой. Fix: новый `resolve_gate_signature(trigger)` — sha256 over sorted gate name+command+severity tuples, 16-char hex; `cache_command` теперь `f'trigger=task-done|sig={sig}|files=...'`. На load_config failure → fallback `'unavailable'` (не блокирует verification). (`review-fix-a1-cache-key-includes-cmd`)
- **H2** ([tests/test_service_verification.py](tests/test_service_verification.py)) — Integration test gap: `run_gates_with_cache` (главный orchestrator) тестировался только через примитивы. Регрессия в `cache_command` formatting прошла бы незаметно. Fix: новая `TestRunGatesWithCacheIntegration` с 6 end-to-end сценариями (miss-then-hit, security bypass, mtime invalidation, red run, append_notes на hit/miss). (`review-fix-h2-cache-integration-test`)

### Added — SENAR verify redesign (epic senar-verify-redesign)

- **Scoped per-task pytest gate** ([scripts/gate_runner.py](scripts/gate_runner.py), [scripts/project_config.py](scripts/project_config.py)) — новый `{test_files_for_files}` substitution + `resolve_test_files_for_relevant(relevant_files)` (basename heuristic + glob `tests/test_<stem>_*.py` варианты + test-file passthrough). Default pytest gate command изменён на `pytest -x -q {test_files_for_files}`. Без `relevant_files` substitution выдаёт `tests/` — fallback на полный suite (regression-safe). Раньше: full pytest на каждом `task done` (~3 мин), что нарушало SENAR Rule 5 tiering и делало Rule 9.5 audit redundant. Теперь: scoped по relevant_files задачи (`senar-verify-tiered`, Phase 1) — Pytest gate теперь scoped, не full suite
- **Verification cache (verification_runs table + lookup)** ([scripts/service_verification.py](scripts/service_verification.py), schema v16) — `compute_files_hash` (SHA256 over canonical path + mtime_ns + size, sorted), `record_run`, `lookup_recent_for_task` (misses on red/files_hash mismatch/command mismatch/stale ≥10 мин), `is_security_sensitive` (hooks/, /auth/, /payment/, /payments/, /billing/ → cache disabled). `service_gates._run_quality_gates` теперь делает lookup до запуска gates — cache hit пропускает их + лог в notes "Gates: cache hit (verify run #X)". Security-sensitive файлы всегда re-verify, не доверяем cache (`senar-verify-tiered`, Phase 2) — Cache reuse: повторный task done на тех же файлах в окне 10 мин — мгновенно
- **`tausik verify` CLI** ([scripts/project_parser.py](scripts/project_parser.py), [scripts/project_cli_extra.py](scripts/project_cli_extra.py)) — `tausik verify [--task slug] [--scope {lightweight,standard,high,critical,manual}]` запускает gates scoped к relevant_files задачи (или unscoped) и записывает результат в `verification_runs`. Полезно для ad-hoc проверки в середине работы (`senar-verify-tiered`, Phase 2) — Ad-hoc verify CLI с записью в кэш
- **CLAUDE.md QG-2/Rule 5 переписаны** — раздел "QG-2 Implementation Gate" (`Ограничения`) явно описывает scoped pytest + cache window + security bypass; раздел "Rule 5 Verification Checklist" в SENAR Compliance таблице обновлён с упоминанием scope-by-relevant_files; Архитектура секция добавляет `service_verification.py` к Gates слою (`senar-verify-tiered`, Phase 3) — Документация QG-2 отражает новый scoped + cache flow

### Test Coverage — SENAR verify

- **+30 unit tests** в `test_service_verification.py` — `compute_files_hash` (empty, none, mtime change, order-independent, missing sentinel, file appearance, skip non-string), `is_security_sensitive` (5 positive paths, 4 negative, empty/none, any-match), `record_run` + `lookup_recent_for_task` (hit, no-runs, files_hash mismatch, command mismatch, red run, stale, takes most recent, empty slug), `is_cache_allowed` (safe/security/empty)
- **+13 unit tests** в `test_gates.py` — `TestResolveTestFilesForRelevant` (empty, basename match, glob suffixes, no match, test-file passthrough, dedup, nonexistent paths, non-string entries, Windows backslash) + `TestPytestGateScopeSubstitution` (substitution uses mapped tests, falls back to full suite, default uses new substitution token)

## [1.3.0-detail-brain] — historical detail (folded into 1.3.0 above)

> Per-story detail of Shared Brain work. Shipped as part of v1.3.0 — listed here for archive only.

Cross-project knowledge layer backed by Notion, complementing the per-project `.tausik/tausik.db`. Only knowledge flagged as *generalizable* reaches the brain; project-specific traces stay local. Read-path fully implemented and offline-tested end-to-end; write-path and MCP tooling are the next story. 6 tasks done from epic `shared-brain` / 22 total. Кросс-проектный слой знаний на базе Notion.

### Added / Добавлено

- **Design doc** ([docs/en/brain-db-schema.md](docs/en/brain-db-schema.md)) — full spec of 4 Notion databases (`decisions`, `web_cache`, `patterns`, `gotchas`): property types + obligation, JSON `pages.create` payload for each, delta-pull mechanics (`last_edited_time` high-water mark), rate-limit handling, 7 trade-offs discussed, 8 negative-scenario fallbacks, privacy model (`SHA256(project_name_canonical)[:16]`) — Design-doc, без которого остальные задачи бы плавали
- **Local SQLite mirror** ([scripts/brain_schema.py](scripts/brain_schema.py)) — 4 tables mirroring Notion properties 1:1, FTS5 virtual tables with `unicode61 remove_diacritics 2` tokenizer (Cyrillic works), AI/AD/AU triggers per table, CHECK constraints for `generalizable` / `confidence` / `severity` / `sync_state.category`, 13 indexes covering delta-pull and dedup hot paths — Локальное FTS5-зеркало с поддержкой кириллицы
- **Brain config section** ([scripts/brain_config.py](scripts/brain_config.py)) — `DEFAULT_BRAIN` with safe defaults (enabled=false, mirror path, token env name, empty db-ids), `load_brain` / `is_brain_enabled` / `validate_brain` (returns error list, strict only when enabled=true) / `get_brain_mirror_path` (expands `~` and `$ENV`) / `compute_project_hash` (canonicalize then SHA256[:16]). Token is never stored in config — only the env-var name — Секция конфига с приватностью
- **Notion REST client** ([scripts/brain_notion_client.py](scripts/brain_notion_client.py)) — stdlib-only (urllib + http), zero external deps. Public API: `pages_create` / `pages_retrieve` / `pages_update` / `databases_query` / `iter_database_query` (auto-pagination iterator) / `search`. Write-side throttle 350 ms, 429/5xx retry with `Retry-After` and exponential backoff (2^n ± 20% jitter, cap 30 s), auth/not-found bypass retry, injected `urlopen`/`clock`/`sleep` for deterministic tests — REST-клиент без внешних зависимостей
- **Pull-sync engine** ([scripts/brain_sync.py](scripts/brain_sync.py)) — `open_brain_db` (creates parent dir, applies schema), per-category mapper (Notion `title`/`rich_text`/`multi_select`/`select`/`date`/`checkbox`/`url`/`number` → SQLite columns), `upsert_page` (INSERT OR REPLACE by `notion_page_id`), `sync_category` (delta filter by `last_pull_at`, ascending sort, advances high-water mark, records `last_error` on failure and re-raises), `sync_all` (continues after a single-category failure) — Делта-синк Notion → local
- **Local FTS5 search** ([scripts/brain_search.py](scripts/brain_search.py)) — `sanitize_fts_query` (neutralizes FTS5 operators via phrase-quoting; escapes inner `"` as `""`), `search_local` (bm25 ranking, global sort across 4 categories, `limit`/`offset`, category filter), `get_by_id` (exact lookup), SQL `snippet()` with `[...]` markers — Быстрый поиск по локальному зеркалу
- **Docs** — EN [docs/en/shared-brain.md](docs/en/shared-brain.md) and RU [docs/ru/shared-brain.md](docs/ru/shared-brain.md): philosophy (generalizable only), ASCII architecture diagram, manual setup steps (parent page → 4 databases → integration → token env → config → smoke-test), privacy contract, 7-row edge-cases table covering revoked token / rate-limit / offline / oversized content / scrubbing miss / schema drift / hash collision. README EN/RU have a short "Shared Brain" section linking to docs — Документация EN/RU + секции в README
- **PostToolUse WebFetch auto-cache hook** ([scripts/hooks/brain_post_webfetch.py](scripts/hooks/brain_post_webfetch.py)) — парный к PreToolUse `brain_search_proactive`: каждый успешный `WebFetch` автоматически уходит в `brain_web_cache` через `brain_mcp_write.store_record`, так что следующий fetch того же URL блокируется читающим хуком. Non-blocking (exit 0); пропускает приватные URL (`brain.private_url_patterns`), HTTP ≥ 400, пустые ответы, уже-свежие URL в зеркале, использует `response.url` вместо `input.url` после редиректа, обрезает content по 200 KB и stdin по 1 MiB. Scrubbing-блоки (private_urls / project_names_blocklist) тихо скипятся — это ожидаемое поведение, а не баг. Диагностика через `TAUSIK_BRAIN_HOOK_DEBUG=1`. `WebSearch` намеренно не кэшируется: в ответе несколько URL в одном блобе, нет канонического ключа; поисковые запросы обслуживаются FTS5 по контенту, записанному через `WebFetch` — PostToolUse хук для auto-cache web результатов
- **Brain runtime write helper** ([scripts/brain_runtime.py](scripts/brain_runtime.py)) — `try_brain_write_web_cache(url, content, cfg, *, query, title)` повторяет контракт `try_brain_write_decision`: `(True, page_id)` на `ok`/`ok_not_mirrored`, `(False, reason)` на token missing / scrub block / notion error / exception. Используется хуком и будущими callers (brain-skill-ui). Также выделен shared `_format_scrub_detectors` — surface только detector names, никогда raw `match` — Раннтайм-хелпер записи web_cache
- **Shared brain-hook utilities** ([scripts/brain_hook_utils.py](scripts/brain_hook_utils.py)) — `parse_iso_to_epoch`, `lookup_exact_url`, `is_fresh` вынесены из `brain_search_proactive.py`, чтобы пара Pre+Post хуков WebFetch делила одну реализацию mirror-lookup и TTL-семантики. `lookup_exact_url` корректно разбирает смешанные ISO-форматы (`Z` vs `.000Z`) — сортирует по parsed epoch, а не лексикографически по TEXT — Общие хелперы для brain-хуков
- **Hook registration** — `bootstrap_generate.py` регистрирует `brain_post_webfetch.py` на PostToolUse с matcher=`WebFetch`, timeout=10s. PreToolUse matcher `WebSearch|WebFetch` остался за `brain_search_proactive.py` — Регистрация в bootstrap
- **`/brain` skill** ([agents/skills/brain/SKILL.md](agents/skills/brain/SKILL.md)) — conversational UI над brain MCP tools: `/brain query <text>` → `brain_search`, `/brain store <type> <text>` → `tausik decide` или `brain_store_*`, `/brain show <id> <category>` → `brain_get`. Документирует bypass-маркеры (`refresh: web_cache`, `confirm: cross-project`), поведение при disabled brain, правила scrubbing. Не изобретает tool names — каждая подкоманда мапится на существующий MCP tool или CLI. `move` и `status` подкоманды вынесены в follow-up tasks `brain-skill-move` + `brain-skill-status` (нужны новые backend'ы) — `/brain` skill для query/store/show
- **`brain_runtime.open_brain_deps()`** ([scripts/brain_runtime.py](scripts/brain_runtime.py)) — shared `(conn, client, cfg)` primitive с None-семантикой: `(None, None, cfg)` если brain disabled, `(conn, None, cfg)` если token env unset, `(conn, client, cfg)` happy path. Fold: `_open_deps` + `_build_client` удалены из `agents/claude/mcp/brain/handlers.py` и `agents/cursor/mcp/brain/handlers.py` — оба импортируют из brain_runtime. Устраняет дубликат ~20 строк × 2 файла. Также добавлен `_FAST_FALLBACK_TIMEOUT = 5.0` как shared константа — Общий helper setup'а brain-зависимостей

### Fixed / Исправлено — Storage hardening batch

Пакет из 6 MED-исправлений в `brain_sync` + `brain_config` + `brain_runtime`, найденных при review2:

- **WAL mode** ([scripts/brain_sync.py](scripts/brain_sync.py) `open_brain_db`) — `PRAGMA journal_mode=WAL` сразу после connect, перед `apply_schema`. Устраняет SQLITE_BUSY между concurrent sync'ом и MCP read'ом на одном mirror'е. WAL — best-effort: `:memory:` / read-only FS / сетевые диски silently откатываются к default rollback journal, не raise (`brain-schema-wal-mode`) — WAL для параллельного чтения и записи
- **ISO timestamp compare** ([scripts/brain_sync.py](scripts/brain_sync.py) `sync_category`) — max_edited вычисляется через `_iso_epoch` (parsed UTC seconds), не лексикографически. Исправлен баг: `"...10:00:00Z"` > `"...10:00:00.000Z"` в ASCII-сравнении, но это ТОТ ЖЕ момент. Без фикса cursor мог регрессировать, если в батче смешаны форматы. Использует `brain_hook_utils.parse_iso_to_epoch` (shared с brain-search-proactive) (`brain-sync-iso-timestamp-compare`) — Корректный temporal compare смешанных ISO-форматов
- **Single-transaction atomicity** ([scripts/brain_sync.py](scripts/brain_sync.py) `sync_category`) — success path: один `conn.commit()` после всех upsert'ов и cursor-update'а. Error path: `conn.rollback()` снимает partial upsert'ы, затем отдельная best-effort tx пишет `last_error` в `sync_state`. Раньше было 2 commit'а в except-ветке — partial state при падении между ними (`brain-sync-transaction-atomicity`) — Атомарная single-tx sync-операция
- **Strict `after` cursor filter** ([scripts/brain_sync.py](scripts/brain_sync.py) `_make_filter`) — `{"last_edited_time": {"after": cursor}}` вместо `on_or_after`. Boundary-страница (edited == cursor) больше не re-fetches на каждом sync'е (`brain-sync-cursor-advance`) — Исключение boundary re-fetch
- **NFC normalization** ([scripts/brain_config.py](scripts/brain_config.py) `compute_project_hash`) — `unicodedata.normalize("NFC", name)` перед canonicalize/hash. Фикс: precomposed é (U+00E9) и decomposed e+U+0301 давали разные project_hash → двойная регистрация одного проекта (`brain-config-unicode-nfc`) — Единый hash для NFC и NFD имён
- **Mirror-path contract** ([scripts/brain_runtime.py](scripts/brain_runtime.py) `try_brain_write_*`) — оба wrapper'а теперь зовут `get_brain_mirror_path()` без аргумента. Раньше передавали уже-merged brain dict → `load_brain(merged).get("brain", {})` = `{}` → user's `local_mirror_path` silently отбрасывался, использовался DEFAULT. Regression-тесты с patched `load_config` + captured `open_brain_db` arg (`brain-config-mirror-path-contract`) — Пользовательский mirror path больше не теряется

### Changed / Изменено

- **brain_sync split** — Notion property readers + per-category mappers (`_concat_text`, `_read_prop`, `_prop_*`, `map_decision` / `map_web_cache` / `map_pattern` / `map_gotcha` + `MAPPERS_BY_CATEGORY`) вынесены в новый [scripts/brain_notion_props.py](scripts/brain_notion_props.py) (~142 lines). `brain_sync.py` сократился до 328 lines — под 400-line filesize gate. `map_page_to_row` остался в brain_sync как dispatcher — Выделение Notion parsers в отдельный модуль

### Fixed / Исправлено — review3 pass

4 findings from the third defensive review pass on commits af0a156 / 4a24c1a / 2e56a64:

- **[M1] `get_brain_mirror_path` shape detection** ([scripts/brain_config.py](scripts/brain_config.py)) — функция теперь принимает три формы: `None` (consults load_config), top-level `{"brain": {...}}`, и already-merged brain dict `{"enabled": ..., "local_mirror_path": ...}`. Детектит merged по отсутствию ключа `"brain"` + наличию любого из merged-shape маркеров (`enabled` / `local_mirror_path` / `database_ids`). Устраняет footgun: предыдущий фикс в `brain_runtime.try_brain_write_*` обходил баг через `get_brain_mirror_path()` без аргумента, но сама функция оставалась миной для будущих callers. Regression-тесты для обеих shapes — Контракт функции поддерживает обе shape
- **[M1 docs] docs/en|ru/shared-brain.md** — smoke-test snippet упрощён: `load_brain()` + `validate_brain()` + `get_brain_mirror_path()` все без аргументов, плюс параграф про три поддерживаемые формы входа — Документация смоук-теста без ambiguous cfg
- **[M2] Hoisted import** ([scripts/brain_sync.py](scripts/brain_sync.py)) — `from brain_hook_utils import parse_iso_to_epoch` на module scope. Раньше импорт был внутри `_iso_epoch` (вызывается per-page в sync loop) — per-call attribute lookup на холодном sync'е тысяч страниц — Импорт вынесен из hot loop
- **[L1] auto-BEGIN invariant comment** ([scripts/brain_sync.py](scripts/brain_sync.py) `sync_category`) — inline-комментарий фиксирует инвариант: `conn.rollback()` в except-ветке полагается на implicit BEGIN от первого `upsert_page`. Если рефакторинг добавит DML раньше в `_get_sync_state`, rollback boundary изменится — Комментарий защищает rollback-инвариант
- **[L2] Dead test удалён** ([tests/test_brain_storage_hardening.py](tests/test_brain_storage_hardening.py)) — `test_memory_db_falls_back_silently` не вызывал `open_brain_db`, тестировал поведение sqlite3 напрямую. `test_wal_failure_does_not_raise` покрывает настоящий контракт — Лишний тест сняли

### Added — MCP write/read hardening batch

- **Token-missing warning in MCP read handlers** ([agents/{claude,cursor}/mcp/brain/handlers.py](agents/claude/mcp/brain/handlers.py)) — `handle_brain_search` и `handle_brain_get` теперь явно сигналят пользователю когда `cfg.enabled=true` но `client=None` (token env unset): инжектят warning с именем env-переменной из `cfg.notion_integration_token_env` в первый слот `result.warnings`. Раньше handler молча пропускал Notion fallback — пользователь не отличал offline от no-token. Generic fallback текст когда `notion_integration_token_env` отсутствует/пуст. Disabled brain не получает warning (status quo) (`brain-mcp-token-missing-warning`) — Явный warning о ненастроенном токене вместо тихого пропуска

### Fixed — MCP write/read hardening batch

- **Dead category-fallback removed** ([scripts/brain_mcp_write.py](scripts/brain_mcp_write.py) `format_store_result`) — `cat = result.get("error_category") or result.get("category") or "unknown"` упрощено до `result.get("error_category") or "unknown"`. `store_record` пишет только `error_category` — мёртвая ветка скрывала бы будущие typos (`brain-mcp-write-dead-code-cleanup`) — Убрана defensive ветка, скрывавшая typos

### Changed — Hooks widening batch

- **Memory-block guard расширен на .claude/\*\*/memory/** ([scripts/hooks/memory_pretool_block.py](scripts/hooks/memory_pretool_block.py)) — `_is_in_claude_memory` теперь матчит любой `memory` сегмент под `~/.claude/`, а не только `projects/<slug>/memory/`. Silently-unguarded paths (`~/.claude/memory/`, `~/.claude/agents/<name>/memory/`, `~/.claude/plugins/.../memory/`) теперь блокируются. `memory_posttool_audit` расширяется автоматически (импортирует `is_in_claude_memory`). BLOCKED stderr обновлён. Файл с именем `memory.md` (не под директорией `memory/`) не блокируется. Substring `somememory/` / `memoryold/` тоже не ложноблокируются (`hooks-pretool-block-path-patterns`) — Гвард памяти теперь ловит все поддиректории memory под .claude/
- **Slug regex расширен с {2,} до {1,}** ([scripts/hooks/memory_markers.py](scripts/hooks/memory_markers.py)) — `_SLUG_RE` ловит 2-сегментные slug'и (`my-app`, `brain-init`, `acme-portal`), но `detect_markers` применяет precision guard: 2-seg slug попадает в результат только при корреляции с higher-precision детектором (`abs_path` / `src_file` / `tausik_cmd`) или 3+ seg slug'ом в том же тексте. Standalone 2-seg slug → empty (консервативно, английские kebab-compounds типа `kebab-case` / `ts-node` / `switch-case` / `double-quoted` / `single-quoted` не флагуются) (`hooks-markers-slug-regex-widen`) — Ловим короткие project slug'и при корреляции, не шумим на English kebab

### Added — Misc hardening batch (Batch 4)

- **Qwen Code brain MCP registration** ([bootstrap/bootstrap_qwen.py](bootstrap/bootstrap_qwen.py)) — `generate_settings_qwen` теперь регистрирует `tausik-brain` MCP server параллельно `tausik-project`/`codebase-rag` (тот же pattern что в `bootstrap_generate.py:241-246`). Раньше Qwen users молча оставались без brain. Silent skip когда `target_dir/mcp/brain/server.py` отсутствует — не ломает чистые qwen-only проекты (`bootstrap-qwen-brain-mcp`) — Qwen users теперь получают brain MCP при bootstrap
- **Brain schema migration path** ([scripts/brain_schema.py](scripts/brain_schema.py)) — `apply_schema` теперь читает `brain_meta.schema_version` после CREATE TABLE; если db_version > SCHEMA_VERSION → `RuntimeError("Brain DB schema vN newer than code v1; update tausik-lib")` (newer-code guard); если db_version < SCHEMA_VERSION → запускает новый `_migrate(conn, from_version)` helper. `BRAIN_MIGRATIONS = {}` placeholder dict с docstring контракта (sorted-by-key, single-tx, irreversible, bump после успешного COMMIT). Раньше `SCHEMA_VERSION=1` записывался но никогда не читался — нет ALTER strategy для будущих v2/v3 (`brain-schema-migration-path`) — Foundation для будущих brain schema bump'ов

### Added — Init/registry hardening batch

- **Orphan database cleanup guidance** ([scripts/brain_init.py](scripts/brain_init.py) `run_wizard`) — пост-create секция (register_project + all_project_names + config_ops.save) обёрнута в try/except. На любую ошибку после успешного `create_brain_databases` новый helper `_print_orphan_cleanup_guidance` печатает все 4 `category: db_id (title)` с инструкцией Archive via Notion UI, затем raise `WizardError("Post-create step failed ...")`. Раньше пользователь получал orphan Notion databases и не знал какие именно архивировать. Покрытие: registry RegistryLockError, config_ops.save OSError, happy path не регрессирует (`brain-init-orphan-cleanup`) — Видимая cleanup-инструкция вместо тихих orphan-ов
- **CliIO EOF/KeyboardInterrupt → WizardError** ([scripts/brain_init.py](scripts/brain_init.py)) — default `CliIO` поднята на module-level (раньше локальный `_CliIO` в `cmd_brain`); `prompt()` оборачивает `input()` в `try/except (EOFError, KeyboardInterrupt)` → raise `WizardError("Aborted by user.")` вместо raw traceback. project_cli_ops.cmd_brain использует `brain_init.CliIO`. Покрывает: piped stdin (EOFError) и Ctrl+C (KeyboardInterrupt) во время interactive wizard prompt'ов (`brain-init-input-error-handling`) — Чистый abort вместо traceback при piped stdin / Ctrl+C
- **Stale-lock recovery** ([scripts/brain_project_registry.py](scripts/brain_project_registry.py) `_acquire_lock`) — SIGKILL'нутый wizard оставлял `.lock` файл навсегда: новые `init`/`register_project` зависали до timeout. Новые `_pid_alive(pid)` (OS-агностичный через `os.kill(pid,0)`, корректно обрабатывает ProcessLookupError/PermissionError/Windows ERROR_INVALID_PARAMETER) + `_is_stale_lock(lock_path)` (stale если pid мёртв ИЛИ mtime > `_STALE_LOCK_AGE_S=30s`). На FileExistsError проверяем stale → unlink + log warning + retry (ровно 1 раз через `reclaimed` flag). Регрессия: live + fresh lock всё ещё блокирует. Boundary cases: malformed lock content fall-back на mtime, read OSError → not stale (conservative) (`brain-registry-stale-lock-recovery`) — Wizard recovery от orphan locks без manual cleanup

### Test Coverage / Тесты

- **+102 new tests** — `test_brain_schema.py` (17), `test_brain_config.py` (20), `test_brain_notion_client.py` (26), `test_brain_sync.py` (15), `test_brain_search.py` (24). Entire brain-suite green in 2 s; no network I/O (client tests inject `_Recorder`/`_ClockSleep`). Pre-existing 918 tests unaffected.
- **+19 hardening tests** — `test_brain_mcp_handlers.py` (+6 token-missing warning + boundary), `test_brain_mcp_write.py` (+3 NotionAuthError/RateLimitError(retry_after=42)/RateLimitError(retry_after=None default) + 2 ok_not_mirrored on upsert/map_page_to_row failure + 1 typo `category` → unknown), `test_brain_notion_client.py` (+7 secret-leak defense: `_LEAK_TOKEN` not in `repr(client)`, `NotionAuthError`/`NotionNotFoundError`/`NotionRateLimitError`/`NotionServerError`/`NotionNetworkError` strings + `caplog` retry log) (`brain-mcp-write-error-class-tests`, `brain-mcp-write-ok-not-mirrored-test`, `brain-notion-client-secret-leak-test`)
- **+9 hooks widening tests** — `test_memory_pretool_block_hook.py` (+3 new block paths: bare_claude_memory, agents_memory, deeply_nested_memory + 3 negatives: memory.md file, somememory/, memoryold/), `test_memory_markers.py` (+6 TestTwoSegmentSlugs: standalone 2-seg dropped, corroborated with abs_path/src_file/tausik_cmd/3seg-slug kept, 3-seg alone regression) (`hooks-pretool-block-path-patterns`, `hooks-markers-slug-regex-widen`)
- **+10 init/registry tests** — `test_brain_init.py` (+3: registry_failure_prints_orphan_guidance, config_save_failure_prints_orphan_guidance, happy_path_prints_no_orphan_guidance), `test_brain_project_registry.py` (+7: dead_pid_reclaimed, expired_mtime_reclaimed, live_fresh_not_reclaimed regression, malformed_reclaimed_after_ttl, malformed_fresh_blocks boundary, is_stale_lock_missing_returns_false, pid_alive_rejects_nonpositive) (`brain-init-orphan-cleanup`, `brain-registry-stale-lock-recovery`)
- **+3 CliIO tests** — `test_brain_init.py` (TestCliIOPrompt: returns_input_normally, eof_raises_wizard_error, keyboard_interrupt_raises_wizard_error) (`brain-init-input-error-handling`)
- **+3 qwen MCP tests** — `test_bootstrap_qwen.py` (qwen_registers_brain_when_server_present, qwen_skips_brain_when_server_missing, qwen_preserves_user_added_servers) (`bootstrap-qwen-brain-mcp`)
- **+5 brain schema migration tests** — `test_brain_schema.py` (BRAIN_MIGRATIONS dict exists, apply_schema idempotent when migrations empty, raises_when_db_newer guard, migrate_applies_pending_versions, migrate_skips_already_applied, migrate_rolls_back_on_failure) (`brain-schema-migration-path`)

### Knowledge Captured / Накоплено знаний

- **Decision #30** — 4 Notion databases, not one flat table (UX outweighs sync overhead)
- **Decision #31** — `SHA256(canonical)[:16]` privacy hash (64 bits, no plaintext project names)
- **Decision #32** — separate `Content Hash` column for `web_cache` dedup (URL changes over time)
- **Decision #33** — inject `urlopen` / `clock` / `sleep` via constructor instead of global monkeypatch
- **Gotcha #34** — FTS5 MATCH treats `-` as column-qualifier; wrap queries in `"..."` or avoid hyphens in markers
- **Convention #35** — `brain-*` modules are separate files (`brain_config.py`, `brain_schema.py`, ...), never folded into `project_config.py` — the 400-line file limit is real

## [1.3.0-pre] — 2026-04-23 — Memory Discipline (folded into 1.3.0 release above)

### Memory-Discipline Epic — auto-memory protection

Protects Claude's cross-project auto-memory (`~/.claude/projects/*/memory/`) from accidental project-specific writes. Project knowledge belongs in TAUSIK's per-project SQLite store (`tausik memory add`); the user's home memory is for cross-project preferences only. 8 tasks shipped across 3 stories. Защита Claude auto-memory от случайного проектного контекста.

### Added / Добавлено

- **PreToolUse memory block** (`scripts/hooks/memory_pretool_block.py`) — blocks Write/Edit/MultiEdit to `~/.claude/projects/*/memory/` from any TAUSIK project with a guidance message. Bypass via the `confirm: cross-project` marker in the user's latest prompt — hook parses the Claude Code transcript JSONL, honors both flat-string and list-of-content-blocks message shapes, and skips tool_result turns when finding the real user message — Блокирует записи в auto-memory с escape-маркером для кросс-проектных случаев
- **PostToolUse memory audit** (`scripts/hooks/memory_posttool_audit.py`) — safety-net that runs after every auto-memory write, scans the file with a regex marker set (absolute paths, kebab slugs ≥3 parts, `.tausik/tausik` commands, `scripts/*.py` file refs), emits a stderr warning listing up to 5 matches. Warning-only (exit 0) — catches content that bypassed the marker by accident — Аудит после записи с детектом проектных markers
- **Memory marker regex module** (`scripts/hooks/memory_markers.py`) — stdlib-only `detect_markers(text) -> list[Match]` with 4 precision-tuned pattern kinds (`abs_path`, `slug`, `tausik_cmd`, `src_file`); tuned against 14 cross-project preference strings ("user prefers Russian", "likes pytest", "uses VS Code", kebab-case lookalikes) to keep false positives at zero. Shared with upcoming brain-scrubbing pipeline — Отдельный модуль regex для переиспользования
- **Memory Policy rule in context injection** — `build_memory_block()` now begins with a ⚠ warning line explaining the TAUSIK-vs-auto-memory split, visible to the agent on every session start and `/checkpoint`. `session_start.py` Reminders gain a matching bullet so fresh projects (empty DB) still see the rule — Правило политики памяти в инжекте сессии
- **Hook registration** — `bootstrap_generate.py` + `bootstrap_qwen.py` wire both new hooks into PreToolUse / PostToolUse under matcher `Write|Edit|MultiEdit` for Claude Code and Qwen Code alike — Регистрация в bootstrap для обоих IDE

### Changed / Изменено

- **Hook count:** 11 → 13 (added `memory_pretool_block`, `memory_posttool_audit`) — 13 hook-ов в сумме
- **`is_in_claude_memory`** public alias added to `memory_pretool_block.py` so other hooks can import a stable name instead of the underscore-prefixed internal — Стабильный public API между hook-ами

### Fixed / Исправлено

- **Windows stderr encoding** — hook block messages used unicode arrows (`→`) that rendered as literal `→` on cp1251 consoles; replaced with ASCII `->` in user-facing warning text — Windows consoles больше не портят сообщения hook-ов

### Test Coverage / Тесты

- **+78 new tests** — 1105 → 1183 passing. `test_memory_pretool_block_hook.py` (30 cases: block/allow/bypass/tool_result/settings), `test_memory_markers.py` (29 cases: positive × kind, negatives × 14 preferences, dedup, edge, perf budget), `test_memory_posttool_audit_hook.py` (21+ cases: detection, silence on clean writes, non-audited paths, graceful, truncation `...and N more`, binary content, tool_input variants, settings registration)

## [1.2.0] — 2026-04-17

### Claude-Hardening Epic — anti-drift infrastructure

Inspired by [oh-my-claudecode](https://github.com/Yeachan-Heo/oh-my-claudecode) (staged pipelines, Ralph mode, keyword-detector), [prompt-master](https://github.com/nidhinjs/prompt-master) (load-bearing text, Memory Block, 9 dimensions of intent), and the leaked Claude Code architecture analysis on Habr (KAIROS always-on assistant, Dream System memory consolidation). Addresses the real-world problem that agents "drift" — ignore the framework, skip task creation, forget conventions between sessions. 18 tasks shipped across 4 stories (P0/P1/P2/P3).

### Added / Добавлено

- **Load-bearing CLAUDE.md / AGENTS.md / .cursorrules / QWEN.md templates** — generated IDE instructions went from ~30 lines to ~104 lines each, with 13 hard constraints, workflow graph, memory types table, SENAR rules reference, DYNAMIC block. All four IDE files share a single source of truth in `bootstrap/bootstrap_templates.py` (no more drift between IDEs) — Единый источник CLAUDE/AGENTS/cursorrules/QWEN
- **SessionStart hook** (`scripts/hooks/session_start.py`) — auto-injects TAUSIK state (status, active tasks, blocked tasks, Memory Block) into every new Claude Code / Qwen Code session; no manual `/start` needed — SessionStart хук с автоинъекцией состояния
- **UserPromptSubmit hook** (`scripts/hooks/user_prompt_submit.py`) — detects coding-intent keywords in user prompts (EN+RU) and nudges the agent to check for an active task before writing code — Детектор coding-intent с напоминанием
- **Stop hooks** — `scripts/hooks/keyword_detector.py` (drift-announcement detection in agent's last message — blocks stop if "I'll implement" without active task) and `scripts/hooks/session_cleanup_check.py` (warns about open exploration, review-tasks, session timeout) — Два Stop hook'а: keyword detector и session hygiene
- **PostToolUse verify-fix-loop hook** (`scripts/hooks/task_done_verify.py`) — after every successful `task_done`, 5 rule-based heuristics audit the AC evidence (file paths, ✓ markers, test counts, file refs, lint status); 2+ failures trigger a `/review` recommendation — Rule-based Ralph-mode-lite
- **Memory Block re-injection** — new `memory_block()` method + `tausik memory block` CLI + `tausik_memory_block` MCP tool returning compact markdown (recent decisions + conventions + dead ends, ≤50 lines) consumed by `/start`, `/checkpoint`, SessionStart hook — Повторная инъекция проектной памяти для anti-drift
- **`tausik memory compact`** CLI + `tausik_memory_compact` MCP — Dream-System-inspired aggregation of recent `task_logs` into phases / top opening words / top files mentioned — Консолидация логов в паттерны
- **QG-0 9-dimension intent completeness** — `qg0_dimensions_score()` in `service_gates.py` scores every task against {goal, acceptance_criteria, scope, scope_exclude, role, stack, complexity, story_link, evidence_plan}; <5 dims triggers a "CONTEXT" warning (prompt-master principle) — QG-0 расширен до 9 измерений
- **Adversarial critic in `/review`** — new sixth parallel review agent `agents/skills/review/agents/critic.md` hunting for exactly 3 weaknesses the other 5 agents miss (hidden failure modes, silent contract drift, assumption gaps); opt-in "deep mode" runs two critic passes — Adversarial критик в /review
- **`/interview` skill** — Socratic Q&A before complex tasks (max 3 clarifying questions, prompt-master principle) — Сократический Q&A скилл
- **`tausik hud`** CLI — one-screen live dashboard (session + active task + recent logs + gates) inspired by oh-my-claudecode HUD — Live HUD
- **`tausik suggest-model`** CLI + `scripts/model_routing.py` — model recommendation by complexity tier (simple→Haiku 4.5, medium→Sonnet 4.6, complex→Opus 4.7) for manual application via `/fast` — Cost-aware model routing
- **Webhook notifications** (`scripts/notifier.py` + `scripts/hooks/notify_on_done.py`) — Slack / Discord / Telegram webhooks fired on `task_done`; configured via `TAUSIK_SLACK_WEBHOOK` / `TAUSIK_DISCORD_WEBHOOK` / `TAUSIK_TELEGRAM_WEBHOOK` env vars — Webhook-уведомления в 3 канала
- **`CLAUDE_PLUGIN_DATA` env support** — `scripts/plugin_data.py` respects Claude Code's plugin-data convention for skill persistent state; falls back to `.tausik/plugin_data/` — Поддержка CLAUDE_PLUGIN_DATA
- **Mandatory Gotchas section lint** — `tests/test_skills_have_gotchas.py` enforces every SKILL.md has a "## Gotchas" section with real content (Habr recommendation) — Обязательная секция Gotchas
- **No-boilerplate lint** — `tests/test_skills_no_boilerplate.py` blocks re-introduction of "Always respond in user's language" in SKILLs (already covered by CLAUDE.md) — Лин для boilerplate

### Changed / Изменено

- **Bootstrap no longer copies `lib/AGENTS.md`** (which was dogfooding-specific, referenced `scripts/`/`agents/` structure); `generate_agents_md()` now produces a universal AGENTS.md with shared hard constraints — AGENTS.md теперь генерируется, не копируется из lib
- **Skills cleanup** — 12 SKILL.md files had "Always respond in the user's language" boilerplate removed (duplicate of CLAUDE.md Response Language section) — Чистка boilerplate в 12 skill-файлах
- **Shared hook helpers** — `scripts/hooks/_common.py` extracts `tausik_path()`, `has_active_task()`, `is_task_done_invocation()`, `extract_task_done_slug_from_bash()` previously duplicated across 5 hooks (convention #2: Mixin composition) — Рефакторинг общих helper-ов hooks
- **`bootstrap/bootstrap_venv.py`** gets `install_cli_wrapper()` helper (extracted from bootstrap.py to stay under 400-line gate) — CLI wrapper install вынесен
- **Skills count:** 34 → 35 (added `/interview`) — 35 скиллов
- **MCP tools:** 80 → 82 (added `tausik_memory_block`, `tausik_memory_compact`) — 82 MCP инструмента

### Fixed / Исправлено

- **H1 — Bash `"task done"` false-positive** — PostToolUse hooks (`notify_on_done`, `task_done_verify`) used substring match that triggered on `echo "task done today"`, `git log --grep="task done"`, etc. Replaced with a proper regex anchored to the actual `tausik[.cmd] task done <slug>` CLI shape in `_common.py`
- **H2 — `_check_ac_checkmarks` matched too loosely** — `"complete"` substring fired on `incomplete`/`completion`/`completeness`, and the heuristic ran on the full `task show` output (title + goal) rather than notes. Fixed with word-boundary regex `[✓✔]|\b(passed|verified|ok|complete[d]?)\b` plus `_extract_notes_section()`

### Test Coverage / Тесты

- **+177 new tests** — 918 → 1095 passing. Every new module (hooks, templates, routing, aggregates) ships with its own test file.

## [1.1.0] — 2026-04-12

### DX & Adoption Improvements

Inspired by ideas from [Molyanov AI Dev Framework](https://github.com/pavel-molyanov/molyanov-ai-dev) — two-phase planning, TDD enforcement, skill auto-testing. Community request for Qwen Code support ([#1](https://github.com/Kibertum/tausik-core/issues/1)).

### Added / Добавлено

- **Qwen Code (GigaCode) support** — full IDE integration: `.qwen/` directory, `QWEN.md` rules file, MCP config + SENAR hooks in `.qwen/settings.json`, 80 MCP tools + 4 enforcement hooks (task gate, bash firewall, push gate, auto-format) ([#1](https://github.com/Kibertum/tausik-core/issues/1)) — Полная поддержка Qwen Code CLI с хуками
- **TDD enforcement gate** — optional `tdd_order` quality gate verifies test files are modified alongside source code; disabled by default, enable via config — Опциональный gate для TDD-контроля
- **Two-phase planning** — `/plan` now starts with an interview phase (3+ clarifying questions) before decomposition; skip with `--skip-interview` — Двухфазное планирование с интервью
- **Auto-docs update on /ship** — after commit, `/ship` checks for structural changes and suggests updating `references/` documentation — Автообновление документации при /ship
- **`/skill-test` skill** — auto-generates 3-5 test scenarios for any skill and validates them through subagents — Автотестирование скиллов
- **IDE-aware skill catalog** — `skill-catalog.md` now uses correct IDE directory paths instead of hardcoded `.claude/` — Параметризованный каталог скиллов

### Changed / Изменено

- **`--smart` is now default** — stack detection and skill auto-enable run automatically; use `--no-detect` to skip — `--smart` теперь по умолчанию
- **`--init` no longer requires a name** — project name auto-derived from directory; `--init my-name` still works — `--init` без обязательного имени
- `bootstrap.py --ide` now accepts `qwen` and includes it in `all` — Qwen добавлен в выбор IDE
- Supported IDEs: Claude Code, Cursor, **Qwen Code**, Windsurf, Codex — 5 IDE
- Skills count: 33 → 34 (added `/skill-test`) — 34 скилла
- Filesize gate exempts `agents/qwen/mcp/` directory — Исключение для qwen mcp
## [1.1.1] — 2026-04-14

### Fixed

- **MCP tags coercion** — `tausik_dead_end` and `tausik_memory_add` now accept `tags` as both JSON array and string. MCP clients (Claude Code) may serialize array params as JSON strings; added `_coerce_tags()` helper to handle both formats gracefully.

## [1.0.0] — 2026-04-05

### Public Release / Публичный релиз

First public release of TAUSIK. Cross-IDE AI agent framework implementing [SENAR v1.3 Core](https://senar.tech).
Первый публичный релиз TAUSIK. Кросс-IDE фреймворк для AI-агентов, реализующий [SENAR v1.3 Core](https://senar.tech).

### Highlights / Основное

- **Cross-IDE support** — Claude Code, Cursor, Windsurf, Codex with unified skill/role/stack system — Поддержка Claude Code, Cursor, Windsurf, Codex с единой системой скиллов/ролей/стеков
- **31 skills** — from `/start` to `/ship`, covering the full development lifecycle — 31 скилл, покрывающих полный цикл разработки
- **SENAR v1.3 Core compliance (100%)** — Quality gates, metrics, dead ends, explorations, verification checklists — Полное соответствие SENAR v1.3 Core
- **Graph memory** — Project knowledge base with edges, soft-invalidation, FTS5 search — Графовая память проекта с рёбрами, soft-invalidation, FTS5 поиском
- **Autonomous batch mode** — `/run plan.md` executes multi-task plans with subagents — Автономный batch-режим для выполнения планов

### Added / Добавлено

- **Quality Gates** — QG-0 (context gate: goal + AC + negative scenario) and QG-2 (implementation gate: evidence + tests + ac-verified) — Quality gates с жёстким enforcement
- **Claude Code Hooks** — task gate, bash firewall, git push gate, auto-format — Хуки для контроля в реальном времени
- **SENAR Metrics** — Throughput, Lead Time, FPSR, DER, Dead End Rate, Cost per Task — Автоматические метрики
- **Multi-language gates** — pytest, ruff, go-vet, clippy, phpstan, eslint, tsc, and more — Gates для 10+ языков
- **5-agent review pipeline** — quality, implementation, testing, simplification, documentation agents with iterative cycle — 5 параллельных review-агентов с итеративным циклом
- **Dead ends & explorations** — `dead-end` for documenting failures, `explore` for time-bounded research — Документирование тупиков и исследования
- **Graph memory** — Polymorphic edges between memory/decision nodes, 4 relation types, recursive CTE traversal — Полиморфные рёбра, 4 типа связей, обход графа через CTE
- **Structured task logs** — `task_logs` table with phase tracking and FTS5 index — Структурированные логи задач
- **Vendor skills** — `skills.example.json` + `skill activate/deactivate` for third-party extensions — Поддержка сторонних скиллов
- **Bootstrap** — `bootstrap.py --smart --init` for one-command setup with stack detection — Настройка одной командой с детекцией стека
- **Apache 2.0 license** — Open source license — Лицензия Apache 2.0
- **Bilingual docs** — Full documentation in English and Russian — Полная документация на EN и RU
- **CONTRIBUTING.md** — Contributor guide — Гайд для контрибьюторов
- **837 tests** — Comprehensive test suite — Полный набор тестов
