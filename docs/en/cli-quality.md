**English** | [Русский](../ru/cli-quality.md)

# CLI: quality and checks

<!-- doc-map: reader=user; zone=core-surface -->

Verification, gates, reviews, audit. Part of the command reference. Start, and the working set, in [cli.md](cli.md).
## Verification

**v1.5 Verify-First Contract.** Heavy gates (pytest, tsc, cargo, phpstan, javac, js-test, terraform-validate, helm-lint, kubeconform, hadolint, ansible-lint) live on the `verify` trigger, not `task-done`. This decouples "task closure" (milliseconds) from "full verification" (potentially minutes on large projects). The `verify` result is cached in the `verification_runs` table for 10 minutes (TTL is configurable via `verify_cache_ttl_seconds` in config.json), and `task done` uses the cache for instant closure.

**Two phases inside a gate run (1.10).** Static gates go FIRST and report together; a test run starts only when none of them blocked. Measured: ruff plus the duplicate-test audit plus the prose-language audit answer in 3.5 seconds against about four minutes for the full lane, and fifteen times in one shift a static gate failed AFTER the lane had run — each costing the lane again plus two or three calls. Within a phase a failure does NOT stop the rest: three defects have to come back in one report, not in three rounds. A test gate that did not run reports `COULD_NOT_RUN` rather than a pass — it applies and produced no evidence (SENAR §8.6(e)).

```bash
verify [--task SLUG] [--relevant-files PATH ...]
       [--scope {lightweight,standard,high,critical,manual}]
       [--no-tests-expected]
                                # Run scoped verify-trigger gates ad-hoc; records into verify cache.
                                # With --task: gates scoped to the task's relevant_files.
                                # Without --task: gates with empty file scope (full suite for pytest).
                                # Cache hit (same files_hash, < 10 min) skips the run.
                                # Security-sensitive files (auth/payment/hooks) bypass the cache.
verify --tasks SLUG [SLUG ...]  # Pooled: ONE gate pass over the union of the
                                # members' relevant_files (>=2 members), one
                                # signed receipt for the whole cohort (1.11.3).
verify --story SLUG             # Resolve the story's non-done tasks as one
verify --epic SLUG              #   cohort and pool them; refuses pools of <2
                                #   and non-review-ready members. The receipt
                                #   redeems via story/epic done --verify-handle.
```

Pooled reuse is refused by a NAMED invalidator (membership drift, task edits,
member-status drift, gate-signature drift, security-sensitive scope, missing
evidence, uncertain dependency mapping) — and the refusal WIDENS: the full
lane executes, the prior cohort row is marked `invalidated`, and the output
names the refused reuse. Contract:
[`verification-cohort-contract.md`](verification-cohort-contract.md).

**`--relevant-files`.** Declares the task's scope AND verifies it in one step.
Requires `--task`: the scope is a property of a task, and there is nowhere else
to record it. The paths are PERSISTED to the task, so `task done` reads the same
scope and hits the cache — one source of truth, the task row.

Without a declared scope every scoped gate is `[SKIP]` and the receipt is still
signed: it certifies emptiness. Before this flag the only working move
(`task update <slug> --relevant-files ...`) was named in no message at all,
while the warning offered a flag `verify` did not have — which made ignoring the
warning the RATIONAL response rather than a careless one.

**The paths are SPACE-separated** — `--relevant-files a.py b.py`, on `verify`,
`task update` and `task done` alike; the list is stored as JSON, which is the
storage shape, not the input format. A value like `"a.py,b.py"` is ONE argument
to argparse and used to be stored as one path, so scoped gates ran over nothing
and the refusal came from `verify` worded as "no tests mapped" (GitLab #13).
Since 1.9 an element that carries a comma and resolves to no file is refused at
the write, naming the right form; a path with a comma in its name that exists
is accepted as it is, and a declared path that does not exist yet is accepted
with a note — the task may be about to create it.

**`--no-tests-expected`.** A run in which no gate actually executed (everything
`[SKIP]`) blocks: it proves nothing, and a green recorded against it would stay
valid for the whole TTL across arbitrary tree changes. For documentation,
config and migrations that is a dead end — no test maps to those files and none
ever will. The flag declares this EXPLICITLY: the run is recorded green under
`no_tests_declared = 1`.

The same holds when the only gates that ran are PROJECT-WIDE — a gate with no
`file_extensions`, no `file_patterns` and no `{files}` in its command, such as a
custom `make check`. Its PASS is the same whether the declared files changed or
not, so while every file-scoped gate skipped, the run is treated as all-skipped
and the refusal names the project-wide gates. A config made only of project-wide
gates is not affected. The test and build gates of the shipped stacks declare
their language's extensions for this reason.

The flag buys visibility, not permission. The closure still happens with no gate
executed; what changes is that such closures are now countable with one query
instead of being indistinguishable from verified ones:

```sql
SELECT task_slug, ran_at FROM verification_runs WHERE no_tests_declared = 1;
```

It applies only to SKIPPED gates. A failing gate stays red and `verify` still
exits 1.

**Verify-first workflow:**

```bash
.tausik/tausik task start my-task                    # QG-0
# … work on code …
.tausik/tausik verify --task my-task                 # heavy: pytest etc.
.tausik/tausik task done my-task --ac-verified       # lightweight: cache lookup
```

**Legacy opt-out (CI/inline behavior):** add to `.tausik/config.json`:

```json
{ "task_done": { "auto_verify": true } }
```

Now `task done` runs the verify gates inline within its transaction — the v1.3 behavior. Useful for CI where a single long step is preferable to two.

**Pytest fast lane (v1.5.x).** The default pytest configuration (`pyproject.toml` → `[tool.pytest.ini_options]` → `addopts = "-m 'not slow'"`) skips tests marked `@pytest.mark.slow` (subprocess-heavy bootstrap, MCP integration, e2e, stress). This drops a clean `tausik verify` run from ~12 minutes to ~1.5 minutes on the TAUSIK repo. Three escape hatches when you need the full battery:

```bash
# 1. Direct pytest, override the addopts
pytest --override-ini='addopts=' tests/

# 2. Marker-only filter (overrides the inherited -m 'not slow')
pytest -m '' tests/                        # all tests
pytest -m 'slow' tests/                    # only slow tests (CI nightly)

# 3. Through the verify gate — set the env var before invoking tausik
TAUSIK_VERIFY_FULL=1 .tausik/tausik verify --task my-task
```

To mark a new test slow: file-level `pytestmark = pytest.mark.slow` (preferred for whole files) or per-test `@pytest.mark.slow`. Reach for it when a test spawns subprocesses, hits the network/MCP, or sleeps > 200 ms — anything that breaks the < 60 s interactive verify budget.

**Terminology:** [Verify / QG glossary](verify-glossary.md) — opt-out vs bypass vs test shim.

## Quality Gates

```bash
gates status                    # Show all quality gates and their configuration
gates list                      # List gates with enabled/disabled status
gates enable <name>             # Enable gate
gates disable <name>            # Disable gate
```

The `path_artifact` gate (block, on commit) binds PATHS to ARTIFACTS: with
`gates.path_artifact.map = [{"paths": ["scripts/**"], "artifacts": ["CHANGELOG.md"]}]`
a staged change under `scripts/` needs a substantive staged change to
`CHANGELOG.md` (whitespace-only does not count). The default map is empty, so it
guards nothing and says so; an unreadable staged set blocks.

The `ruff_format` gate (block, on verify and commit) runs `ruff format --check` over the
task's Python files. Files that diverged when it landed are frozen in `tausik/gates.json`
→ `ruff_format.legacy_unformatted` and skipped; the list only shrinks — format a listed file
and remove it from the list in the same change.

The `test_dedupe` gate (block, on task-done and commit) reddens on GROWTH in COPIES
— tests that are the same code once formatting, comments and the function's own name
are set aside. The baseline is a ratchet in the committed `tausik/gates.json`
(`groups`/`tests`/`copies`), so existing debt blocks nobody. The subject is
DISTINGUISHABILITY, not count: the gate never measures how many tests exist, so
deleting tests can never satisfy it.

The `groups`/`tests` numbers are a DECLARED REMAINDER about similarity, not
copy-paste debt. Measured: of 286 groups, 284 (99.3%) differ in exactly the parts the
signature erases — names, strings, numbers — which is one contract exercised on
different inputs. So `copies` is what reddens, not shape. A baseline without the
`copies` key reads as zero: a project that adopted the ratchet earlier gains the
check rather than losing one.

The report prints a verdict beside EVERY group (`COPY` or `PARALLEL`) — the verdict
is written down, not left to the reader. Full per-group report:

```bash
python scripts/audit_pytest_dedupe.py            # markdown report by group
python scripts/audit_pytest_dedupe.py --json     # the same, machine-readable
```

## RENAR drift detectors (§4.11)

RENAR §4.11 defines 8 drift classes. 2 are implemented (audit recommendation R4),
both in **warning mode** — findings never block; the agent reads the listing and
reacts.

```bash
drift                          # Run every implemented detector
drift --detector schema        # drift-1 only (artifact schema)
drift --detector provenance    # drift-7 only (TC↔requirement provenance)
drift --detector supersession  # ADR-007: a delta-ADAPT on a superseded parent
drift --detector standard      # THE RENAR STANDARD moving (corpus vs our declarations)
drift --detector senar         # SENAR moving: claimed edition vs released, Core shape (key senar_standard_corpus)
```

- **drift-1 (schema)** — re-validates SPEC/ADAPT against the closed lists +
  cross-field invariants a DB CHECK cannot express: `delta_n ↔ parent_adapt`
  (delta_n>0 without a parent_adapt / delta_n=0 with a parent_adapt),
  `approved ↔ architect signature` (§7.5 — the client signature was withdrawn
  by ADR-011; surviving records are NAMED as `signature-role-withdrawn`, never
  erased),
  blank version. Catches direct-DB tampering and migration gaps.
- **drift-7 (TC↔requirement provenance)** — TAUSIK has no first-class TC; the
  verification unit is a task (its acceptance_criteria == the "TC") linked to a
  SPEC (the requirement) via `task_specs`. Two signals: `stale-verification`
  (done task whose SPEC was edited after the link → verification predates the
  current requirement version) and `deprecated-requirement` (in-flight task
  linked to a deprecated SPEC).

- **standard (the corpus moved)** — the only detector that compares OUR
  DECLARATIONS WITH THE STANDARD ITSELF rather than the database with our
  declarations: the closed lists (SPEC types §8.3, finding categories §7.4.4,
  ADAPT statuses §7.8.1), the corpus edition, and accepted ADRs this repository
  never mentions. The source is a local checkout named by
  `renar_standard_corpus` in `.tausik/config.json`; without it the command
  prints "standard corpus: NOT CHECKED" and does NOT report "no drift".
  Proposed ADRs are never findings.

Also wired as gates `renar_drift_schema` / `renar_drift_provenance`
(severity=warn, trigger=task-done). `standard` is not wired as a gate: not every
machine carries the corpus. The other 5 classes are out of scope.

## RENAR conformance (§13.4)

```bash
renar conformance              # Generate RENAR-CONFORMANCE.yaml (to stdout)
renar conformance --write      # Write RENAR-CONFORMANCE.yaml at the project root
renar conformance --assessor <id>
renar export [--out DIR] [--check]  # Serialize specs+adapts+conformance to a derived renar/ tree; --check is a CI drift gate (exit 1 if stale)
```

A self-assessment manifest with every §13.4.2 mandatory field. The RENAR-1..5
level is **computed honestly from live DB state** (§13.4.3), never declared: any
unmet mandatory clause → `pre_adoption: true` + `level: null` (the kai pattern,
the adoption audit). The `assessment-evidence` section reports raw counts + per-signal
met/unmet and exactly where the level is blocked, so an agent sees what is missing
to reach the next level. Machinery clauses (closed lists, V1–V6, QG-0/QG-2,
schema-validation hook = our drift-1) are confirmed by capability; data clauses
(`adapt-per-tz`) only when artifacts exist.

## Periodic Audit (SENAR Rule 9.5)

```bash
audit check                     # Is the audit overdue: closures since the last mark >= audit_every_closures (17)
audit mark                      # Mark the audit done now (no session needed)
audit vendors [--json]          # Audit cloned vendor skill repos (read-only): classifies each as
                                # 'installed' (in installed_skills config) or 'vendored_unused'
                                # (candidate for `skill repo remove`). Never deletes.
audit research [--min-age-days N] [--json]
                                # Audit docs/{en,ru}/research/ for stale unreferenced files
                                # (default >30 days, no refs in tests/scripts/CHANGELOG/README).
                                # Read-only — surfaces candidates for docs/_archive/research/.
audit evidence [--json] [--no-git]
                                # Do the test citations in closed tasks still resolve?
                                # Read-only and NEVER blocking: renaming a test is legitimate,
                                # the point is that the decay becomes VISIBLE.
```

`audit evidence` has four buckets, deliberately not merged into one "broken" number:

| bucket | meaning |
|---|---|
| `ROTTED` | the target WAS in git history and is gone — renamed or deleted after closure. The reference decayed; the coverage may be intact. |
| `NEVER_EXISTED` | the target was never in history — a citation invented at closure time. |
| `ILLUSTRATIVE` | an EXAMPLE, not a citation: `tests/foo.py`, `tests/test_does_not_exist.py`, `tests/../scripts/prod.py`. Such names are quoted by tasks whose SUBJECT is the citation format itself. |
| `UNKNOWN_HISTORY` | git refused to answer — the verdict is withheld, not guessed. Appears under `--no-git`. |

`ILLUSTRATIVE` was split off on a measurement: of the 25 refs then in `NEVER_EXISTED`, 13 were examples and 3 were genuine, so the headline over-reported real rot by a factor of two beside 22 `ROTTED` entries a reader was being taught to skim. Examples are **counted separately, not dropped**: a number that silently loses entries is the next version of the same problem, and the rule that fired is printed next to each entry. The notion of an example path is shared with the `stale_file` detector of `memory lint` (`scripts/illustrative_paths.py`) — a second copy of the placeholder list is exactly how the two detectors drifted apart.

## Reviews (SENAR Rule 10.15) — v1.5

Track L1/L2/L3 review runs and surface the **ADR** (Adversarial Defect Rate) metric.

```bash
review record --task <slug> --type {L1|L2|L3} \
              [--critical N] [--high N] [--warnings N] [--reason "..."] [--notes "..."]
              # --critical > 0 without --reason is refused: CRITICAL is recorded
              # with its reason (SENAR 1.5 §10.15(f); scale: severity-scale.md)
              [--reviewer-model M] [--author-model M]
              # L3 only: both models are stored in notes; a same-family pair,
              # a missing reviewer or an unknown author is refused (SENAR Rule 4).
              # --author-model defaults to the model of the running session.
review list   [--task <slug>] [--type {L1|L2|L3}] [--limit N] [--json]
review metrics                  # ADR = critical_findings / L3_reviewed_tasks * 100
```

The `/review` skill records L3 only when at least one adversarial reviewer runs on a different model family from the author; fresh same-family contexts qualify as L2. `tausik metrics` includes an `Adversarial Review` block once any valid L3 reviews exist.

## A bypassed gate leaves a record (SENAR 1.5 §8.6(j))

Editing a task's artifact by a route no gate stands in front of — INCLUDING a
direct edit by the supervisor — admits the effect QG-0 declared without a
positive verdict; §8.6(h) counts that as a bypass regardless of intent. This is
NOT a prohibition but a regulated exception, and it stays available. What is
required is a RECORD, in every case.

The one recognized case is an environment in which no agent can be run and there is nothing to switch to (SENAR 1.5 §4.1, revision of 2026-09-07; re-read under §10.13 when the model generation changes).

SENAR 1.4 §4.1 listed five cases. The other four — an agent stuck, an agent most of
the way there, a fix cheaper than preparing context, a deadline hotfix — are
addressable by agent means where an agent environment exists. They are still
recorded if they happen. The senior who approves the bypass decides whether a
case is the recognized one.

```bash
events emit-supervision --vector direct_edit --task <slug> \
    --rationale "no agent environment on this host, nothing to switch to" \
    --risk-accepted "the fix ships without a scoped verify" \
    --remediation "re-run verify and re-close the task" \
    --approved-by "owner"
```

A record with no `--rationale` is REFUSED (exit 2): a bypass without a reason is
the form filled in without looking. What is refused is the RECORD, never the
edit — the edit has already happened.

WHY THE METRIC IS COMPUTED FROM RECORDS AND NOT FROM SELF-REPORT (§9.2, §9.3): a
self-reported figure is a CLAIM, not a measurement; it satisfies neither §8.6(c)
nor §8.6(d), and the standard cannot demand of gates what it does not demand of
its own measure of compliance.

THE TWO FREQUENCIES ARE NESTED AND SHALL NOT BE ADDED (§8.6(i)): manual
interventions are a SUBSET of bypasses, so `metrics` prints them as "of which"
rather than as a second total. Summed, they double-count, and the threshold
fires on a team doing nothing wrong.
