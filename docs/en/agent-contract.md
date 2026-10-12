**English** | [Русский](../ru/agent-contract.md)

# TAUSIK agent contract — extended reference

<!-- doc-map: reader=agent; zone=core-surface -->

This document continues `CLAUDE.md`. CLAUDE.md is loaded into the agent's context **on
every turn**, so it holds only enforceable rules and a quick reference. Everything needed
less often was moved here: the estimation table, the SENAR compliance matrix, the QG-2
mechanics, roles, external skills, custom stacks.

Load this file through Read when you need it — not on every turn.

---

## QG-2 Implementation Gate — mechanics

`task done --ac-verified` requires evidence in the notes plus passing **scoped** quality
gates. The pytest gate uses the `{test_files_for_files}` substitution — it runs only
`tests/test_<basename>.py` for each entry of `relevant_files` (basename heuristic plus the
`_*.py` glob variants).

- If `relevant_files` is non-empty but nothing maps to a test → the **gate is SKIPPED**
  (it used to fall back to the full suite — that defect is fixed).
- A narrowed run prefixes its output with `SCOPE: scoped run over N of M test file(s) …
  NOT the full suite: …` — identically on pass, on fail and on timeout. It is printed for
  a PASSING gate too (the other gates show nothing on success). The denominator is
  mandatory: `[PASS] pytest` over two files out of 318 reads as a statement about the
  project, and in session #134 it was read exactly that way — a task closed with a green
  signed receipt while the full suite was red. Before writing "the full pytest is green"
  into evidence, run it separately: it takes ~9–10 minutes and does finish (memory #304),
  and the gate's numbers are not its numbers.
- Without `relevant_files` (None/empty) `task done` **BLOCKS**: an undeclared scope is
  "unknown", not "verified empty" (verify-cache-empty-scope-hit, session #118). The
  full-suite fallback was retired. Declare the files and run verify.
- A task that **legitimately touches no files** (pure planning, `tausik decide`) closes
  with `task done --no-file-changes` — the third state of a scope. Allowed ONLY when git
  confirms the declared scope (`--relevant-files` as a pathspec; the whole tree when the
  list is empty) has no uncommitted edits; otherwise fail-closed. Countable:
  `SELECT * FROM tasks WHERE no_file_changes_declared = 1`
  (qg2-cannot-close-fileless-task).
- The state projection — `tausik/{epics,stories,tasks,decisions,memory}/` — is **EXCLUDED**
  from that check. `task log` is a hard rule of this project, it automatically exports the
  journal into `tausik/tasks/<slug>.md`, and following the rule dirtied the very tree the
  check reads: the flag was unreachable. **A commit for the sake of closing is NO LONGER
  NEEDED** — the old workaround is retired, do not repeat it out of habit
  (no-file-changes-unreachable-journaling-dirties-the-tree).
  The boundary of the exclusion is stated out loud: an edit INSIDE those five directories
  made by hand is byte-for-byte indistinguishable from the auto-export — an uncommitted
  edit has no author — and therefore gets through. Everything else under `tausik/`
  (`tausik/gates.json`, for example) is NOT in the exclusion and blocks as before.
- **A task's own export is subtracted from the receipt's COVERAGE**
  (verify-handle-dies-on-a-tasks-own-export-file). A task may declare its own
  `tausik/tasks/<slug>.md` in `--relevant-files` — for a task whose product is records (an
  analysis, verdicts, decisions, planning) that is its natural scope. Such a declaration
  used to make closing impossible IN PRINCIPLE: the `verify` run itself writes into the
  task (the declared scope, the run number, the receipt), the export changes because of
  that, and the handle was rejected with the precise but useless wording "the files this
  receipt covers have changed". Retrying never converged — each run moved the hash further
  (observed: `870e9d910c7c -> edd0acd46e7b -> e8d9e08ecc20`). **If you ended up in a
  verify/done loop, this was it, and the cache had nothing to do with it.** Now exactly
  THAT ONE file is subtracted from coverage (convention #409: a check must subtract the
  framework's own bookkeeping), on both sides — when recording the run and when presenting
  the handle.
  - ONLY a task's own export is subtracted. Someone else's
    (`tausik/tasks/<another-slug>.md`, `tausik/decisions/*.md`) stays a legitimate subject
    of coverage: the current run does not touch it, and its hash means exactly what it says.
  - The boundary is stated out loud: a hand edit of your own export between `verify` and
    the close is NO LONGER noticed — the same honest limit as the projection exclusion above.
  - An edit of a SOURCE file between `verify` and the close is rejected as before; the
    refusal now says explicitly that the task's export is not part of coverage and is not
    what moved.
  - A scope consisting of ONLY your own export covers zero files after the subtraction and
    therefore does NOT certify: the refusal names the cause and both exits — declare the
    real files, or close through `--no-file-changes`.
- Verify cache (the `verification_runs` table): a green run within the last 10 minutes with
  the same `files_hash` → cache hit, gate skipped.
- Security-sensitive files (`scripts/hooks/`, `/auth/`, `/payment/`, `/billing/`) bypass the
  cache — always re-verify.
- **The boundary of the receipt's signature** (l26-signing-key-boundary): signing a
  receipt/anchor is tamper-evidence against EXTERNAL edits of `tausik.db`, but NOT an
  attestation against the agent: the seed sits in the working tree, readable by the agent.
  More on it, and on why moving the key out was deferred, in `docs/en/receipts.md` (section
  on the key boundary). A signing failure is now visible (`Receipt: WARNING` plus a
  `receipt_sign_failed` event) rather than degrading silently to an unsigned run.
- **The continuous-CHANGELOG gate** (changelog-continuous-gate, convention #275): when
  enabled in the config, `task done` blocks the close if git does NOT show an added
  NON-EMPTY line in EVERY configured changelog file. This makes the continuous-changelog
  discipline mechanical instead of a line in the acceptance criteria. The mechanism is
  general, the policy is in the config (TAUSIK is a framework; another project may keep no
  changelog):

  ```json
  "task_done": {
    "changelog_gate": {
      "enabled": true,
      "files": ["CHANGELOG.md", "CHANGELOG.ru.md"]
    }
  }
  ```

  It is **off** by default (opt-in) — the absence of a `changelog_gate` block is a
  deliberate decline rather than an error, and it makes no noise. But a block that EXISTS
  and is broken (`enabled` not a boolean, `files` not a list, the config unreadable) BLOCKS
  the close: a policy that cannot be read cannot be treated as switched off — it is unknown
  (decision #157). A typo in the config must not silently cancel a discipline the project
  believes is on.

  What counts as an entry:
  - **a non-empty added line** — "the bytes in the file changed" does not pass: one blank
    line makes the file dirty while adding nothing;
  - changes in the working tree (staged and unstaged) **and commits made during the task**
    (the window from `started_at`). The second is mandatory: `/ship` commits at step 7 and
    closes the task at step 8 — a requirement of "uncommitted only" would block the
    canonical path to a close and leave `--no-changelog` as the single way through. A rule
    whose only way through is its own bypass teaches the bypass;
  - a new (untracked) changelog file with text in it is an entry too.

  Fail-closed: if git is unavailable or the service does not know its own project directory
  — block, not skip (following the whole-tree proof, decision #157). The gate's config is
  read for the SERVICE's project (`tausik_dir`), not from the process's current directory.
  A task that legitimately requires no changelog entry (docs, cleanup, a measurement) closes
  with `task done --no-changelog` — it skips the gate and writes an explicit bypass event
  (`supervision` / `bypass_changelog_gate`); there is no silent bypass. Fileless tasks
  (`--no-file-changes`) never reach this gate — their path returns earlier.

Log the AC verification through `task log` before closing.

### Structured evidence (`--evidence-json`, v1.4 polish)

An alternative to the prose form is a JSON argument, converted into the canonical prose
form inside the service:

```bash
.tausik/tausik task done my-task --ac-verified --evidence-json '{
  "ac_evidence": [
    {"n": 1, "status": "pass", "evidence": "tests/test_foo.py::test_bar"},
    {"n": 2, "status": "pass", "evidence": "smoke run", "manual": true},
    {"n": 3, "status": "pass", "evidence": "401 on bad creds", "negative": true},
    {"n": 4, "status": "pass", "evidence": "the order total is non-negative for real inputs", "domain": true}
  ]
}'
```

The optional per-item flags `manual` / `negative` / `domain` are passed through as markers
in the prose, so that the `service_ac_evidence` parser sets
`has_manual` / `has_negative_evidence` / `has_domain_evidence` in the report. `--evidence`
and `--evidence-json` are mutually exclusive (argparse plus the service). The MCP tool
`tausik_task_done` has the same semantics through its `evidence_json` argument.

**SENAR Rule 4 — the domain challenge (v15s-rule4-domain-challenge).** The QG-2 checklist
for every tier except the planning tier `trivial` requires an answer to a domain question:
*does the result make sense OUTSIDE the tests?* (arXiv 2605.30353 — an agent passes tests
with physically meaningless output). A `Domain:` line in the notes/evidence is enough, for
example `Domain: the output is semantically valid for real inputs`. The parser recognises
`domain` / `sanity` / `makes sense` / `имеет смысл` / `доменн` / `real-world`. It is skipped
only for `trivial`.

---

## File a finding freely, start by the plan (measured in session #277)

THE MEASUREMENT THAT PRODUCED THIS RULE. In one session 22 tasks were closed: 4 from the
plan that existed before the session, the other 18 (82%) were filed AND closed inside that
same session. Some of them on the owner's direct instruction, which is legitimate; the rest
were findings the agent picked up because the context was warm. Four of those the owner
later called work that is not needed before the release.

THE MECHANISM IS IN THE LOOP, NOT IN THE DISCIPLINE, which is why trying harder cannot fix
it:

1. `task done` prints findings — closure notes, ratchets that fired, tracker reminders,
   gate output.
2. The first principle requires filing every one of them. **That step is right and stays
   free:** forbidding the filing of findings would bring back the silent errors this project
   exists against.
3. The agent then immediately STARTS it, because starting is cheap right now.

The third step is the defect. "Cheap now" is not "next by the plan", and repeating it walks
the defect tree depth-first without ever returning to the release composition. Across that
session `task next` — which chooses correctly: release first, then the declared order — was
never called once.

**The rule.** After every close, ask the plan first, then decide. Filing a finding — yes;
starting it — only if it IS the composition's choice. Otherwise defer it.

From 1.10 the tool says so itself, at two points:

- `task done` names, at the end of its output, the task the composition suggests — so that
  the finding and the plan stand side by side and the choice is made between them rather
  than in favour of whatever is freshest. On a BLOCKED close there is no such line: there
  the next action is to clear the block.
- `task start` prints when the task being started displaces the composition's choice, names
  what was displaced, and gives the command to go back.

Both lines are signals, not gates (decision #376): they refuse nothing and stay silent when
the composition suggests nothing.

## Agent-native estimation

Tasks are measured in **tool calls**, not in hours.

| Tier | call_budget | When it fits |
|------|-------------|--------------|
| `trivial` | ≤10 | a small fix, a single flag, a doc edit |
| `light` | ≤25 | a migration plus helpers plus tests on one surface |
| `moderate` | ≤60 | hook plus service plus tests, a multi-file feature |
| `substantial` | ≤150 | CLI plus service plus MCP plus mirror plus tests at once |
| `deep` | ≤400 | a full vertical (a new stack, an end-to-end feature) |

Budgets **>400** are allowed — `call_budget` is kept as given while the tier label is capped
at `deep`. The warning at 1.5× budget works for any N. Regularly exceeding 400 is a signal
to split the task (through a subagent or a sequential session).

When creating a task through `task add`/`task update`, pass `--call-budget` (the tier is
auto-derived) or `--tier` directly. Omitting it is allowed but justify it **explicitly** —
budget calibration breaks without it. On task_done `call_actual` is recorded automatically
(events plus the PostToolUse hook); if actual > 1.5× budget, TAUSIK logs a warning for
re-calibration.

`tausik task start <slug> --force` was withdrawn in 1.10: session capacity is no longer a
gate but a signal in the output of `task start`; the flag answers with a refusal that states
the reason (decision #376).

---

## SENAR Compliance

The claim (SENAR 1.5 §13.1 form): "TAUSIK conforms to SENAR v1.5 Core, self-declared, as of
2026-09-23". The disclosures beside it and the check that the edition is published live in
the README and in `scripts/senar_claim.py`.

There is one compliance matrix, in [senar-compliance-matrix.md](senar-compliance-matrix.md):
gates, rules, metrics, every row naming the code. It is no longer duplicated here: two copies
of one table drift, and this copy assigned Standard rules 9.x to "Core", where SENAR Core has
none. What matters to an agent out of it: QG-0 and QG-2 are hard (CLI plus MCP); Rule 1 and
Rule 2 are held by PreToolUse hooks; session time and call capacity are signals, not gates
(decision #376, 1.10); Rule 4 is an external review on a different model when the evidence is
thin.

## How rules reach the agent (measured in session #230)

**THE CLAIM "A DIRECTIVE IS DELIVERED ONCE" WAS REFUTED BY MEASUREMENT.** Checked by calling,
not by reading:

| question | answer | how it was obtained |
|---|---|---|
| Does the SessionStart hook carry the directive? | **No.** 7263 bytes of context (~1815 tokens), no "Output economy" marker in them | a run of `session_start.py` |
| Then where is it? | In the RULES FILE, which the harness supplies as the project's instructions **in every request** | the contents of CLAUDE.md are observed in the system prompt hours into a session |
| Does it survive compaction? | **Yes**, by construction: the rules sit in the request PREFIX, and compaction shortens the conversation history | same |
| What does the injection cost per turn? | ≤888 characters ≈ 222 tokens against a median context of 276,702 — **0.08%** (before the response contract in 1.9 it was 700 / 0.06%) | `CAVEMAN_DIRECTIVE_MAX_CHARS`, guarded by a test |
| Does it pay for itself? | A savings ceiling of ~2% against a cost of 0.08% — roughly **twenty-five-fold** | the measurement of the economy-mode task |

What happens once is NOT the delivery but **the writing of the file**: every rules generator
is preserve-if-exists, so if the file already existed the directive will not land in it. That
is exactly what `warn_output_mode_not_applied` warns about, and since 1.9 the parity of that
warning across all generators is held by `tests/test_rules_generator_warning_parity.py`: a
host whose generator stayed silent would leave the user believing the mode was applied.

## Does the generated half of CLAUDE.md pay for itself (measured in session #249)

arXiv 2602.11988 (ETH Zurich, 438 tasks, 4 agents): context files GENERATED by a model cost
+20–23% and take away 0.5–2% of success; human-written ones give +4%. Our rules file is a
hybrid: hand-written rules plus a DYNAMIC section (`## Current State`, the memory tail, the
shared-knowledge block) that `update-claudemd` regenerates every session and the harness
supplies with EVERY request. The instrument: `scripts/context_block_audit.py`. The thresholds
were declared before the measurement (in the task journal): the memory tail stays if ≥25% of
sessions contain a citation whose only possible source was the tail; the state block stays if
<75% of sessions have the agent re-requesting it within the first 8 calls.

**Cost per request** (CLAUDE.md as of the measurement): hand-written 4067 B ≈ 1017 tokens —
0.37% of the median 276,702 context; `Current State` 246 B ≈ 62 — 0.02%; the memory tail
2750 B ≈ 688 — 0.25%; shared knowledge 1518 B ≈ 380 — 0.14%. The generated half is 4514 B,
0.41% of context per turn, not +20%: the scale of the paper's verdict does not transfer to us,
but it does not remove the question of whether the agent reads it.

**Usage**, across 94 transcripts of this project from this machine (42 top-level sessions and
52 subagent transcripts, which carry the same rules file):

| proxy | what counts | result | threshold | verdict |
|---|---|---|---|---|
| A, the state block | `status` / `session current` / `session open` within the first 8 calls — a re-request of what the block already carries | 41 of 94 — **43.6%** | < 75% | stays |
| B, the memory tail | the agent cites a memory/decision id that had not appeared in any tool result or any human message of the transcript, and that the tail carried at least once in CLAUDE.md's history (338 ids across 198 commits) | 35 of 94 — **37.2%**, 58 distinct ids | ≥ 25% | stays |

What was NOT counted: 68 cited ids the tail never carried (their source is the relevance block
at `task start`, tool output, shared memory, or invention — the instrument does not
distinguish and does not count them); session, verify-run, receipt and attempt numbers
(`session #232`, `Handoff #226`) — the first version of the instrument credited those to the
tail, a sampled check caught it, and a number below 300 without the word "memory/decision/
norm" in front of it is no longer counted as an id. The shared-knowledge block (0.14%) has no
ids and its reading is NOT MEASURED. What is NOT measured is the main thing — task success,
the paper's metric: that needs a paired A/B on one task set with and without the block, which
is separate runs and the owner's decision. By the declared rules both measured parts stay;
nothing will be cut out of habit — and nothing will be kept out of habit either: repeat with
the same instrument, `python scripts/context_block_audit.py <transcripts>`.

## Compliance with the response contract: the baseline (measured in session #249)

A rule with no measurement of obedience is the same as a check that never existed. The
instrument: `scripts/response_contract_audit.py` — it reads the answers TO THE USER (the last
text block from the agent before the next human message; an answer to a harness notification
is not an answer) out of this project's Claude Code transcripts, out of Codex rollouts whose
cwd is this project, and out of an arbitrary JSONL of `{"text"}`. It counts four markers —
exactly the four deletions the contract asks you to make before sending — over prose with the
protected parts cut out (code, quoted output, paths, AC/decision/root-cause lines, harness
tags):

| marker | what it catches | RU/EN |
|---|---|---|
| `intent_opener` | the first line announces an intention ("I'll start with…", "Let me look…", "Начинаю с…") | yes |
| `closing_recap` | a paragraph in the last third is a summary or a courtesy ("In summary", "Итого:", "Let me know") | yes |
| `side_branch` | a paragraph opens a side branch ("By the way", "Попутно:", "Заодно") | yes |
| `empty_hedge` | a word of uncertainty with no named uncertainty ("probably", "скорее всего", "вроде") | yes |

The rubric is lexical and says so plainly: it does not distinguish an empty hedge from a named
one (the test `test_a_hedge_that_names_its_uncertainty_is_still_counted` pins that), and "By
the way: …" with a substantive finding counts as a branch.

**THE THRESHOLD WAS DECLARED BEFORE THE MEASUREMENT** (in the task journal): if the share of
answers with at least one marker is < 10%, no obedience lever gets built and the task is
withdrawn.

**THE MEASUREMENT, SESSION #249**, on this machine, with nothing from the corpus entering the
repository: 451 answers to the user across 151 files (Claude 317, Codex 134; median 2175
characters). `intent_opener` 1.1%, `closing_recap` 0.2%, `side_branch` 2.4%, `empty_hedge`
3.3%; **with at least one marker — 7.1%**. Below the threshold: the lever is NOT built. What
this measurement does NOT claim: it measures four deletions, not the shape
"done → verified by → left → your call" — compliance with the shape stays unmeasured, and
"the contract is being followed" is not credited here. A sensitivity check before the final
figure: a sample of the first and last two words of every answer — the most frequent openings
are state-first ("The task is closed", "State:", "The tree is clean"), not announcements; the
forms "Starting with", "Opening", "Taking" were added to the rubric because of that sample.
To repeat with the same instrument:
`python scripts/response_contract_audit.py <transcripts> --project <root> --threshold 7.1`
— exit 1 means "no better than the baseline".

## A cap on the output of a command of unknown size

**MEASURED ON OUR OWN CORPUS, SESSION #229**, with this release's instrument: context growth
is attributed to the tool whose result caused it (the delta up to the next call
within one session and one transcript).

| tool | calls | median growth | p90 | growth on pairs | share |
|---|---:|---:|---:|---:|---:|
| Bash | 9844 | 848 | 2,514 | 11,883,280 | 66.4% |
| Write | 640 | 2,092 | 4,717 | 1,591,159 | 8.9% |
| Edit | 1500 | 662 | 1,682 | 1,319,862 | 7.4% |
| Read | 285 | 748 | 2,685 | 370,213 | 2.1% |

**THIS TABLE HAS TO BE READ PRECISELY.** The growth from one call to the next contains TWO
things: the tool's result AND the model's own output on that same turn (reasoning, text, the
call block). The share in the last column is the TOTAL delta on pairs involving that tool, not
the cost of the tool itself.

Split over the same 14,048 pairs, with a total growth of 18,009,761:

| what exactly | tokens | share of growth |
|---|---:|---:|
| the model's own OUTPUT, all tools | 12,895,606 | **71.6%** |
| tool results and their framing | 5,114,155 | 28.4% |
| of those, results of **Bash commands** | 4,740,033 | **26.3%** |

So the main lever of economy is THE SHAPE OF THE MODEL'S OWN ANSWER, and capping command
output is worth 26.3%, not two thirds. That does not retire the cap rule and does not move its
threshold: p99 was computed over the delta, and the delta was not revised.

The growth is **broad rather than tail-heavy**: the top 1% of Bash calls give only 6.8% of its
growth. There is no catastrophic single output in the corpus because the Claude Code harness
truncates tool output itself; **on a host without such truncation there would be one**.

**THE RULE.** A command whose output size is not known IN ADVANCE gets its output limited. A
line limit is not enough: one long line (a minified file, JSON on a single line, a log with no
newlines) overflows the context while the line counter shows one.

An unlimited call is forbidden for:

| call | how to limit it |
|---|---|
| `cat <file>` with no range | `Read` with `offset`/`limit`, or `sed -n 'A,Bp'` |
| a wide `rg` / `grep -r` | `Grep` with `glob`/`path`, or `\| head -c 24000` |
| `find` over the tree | narrow `-maxdepth`/`-name`, or `\| head -50` |
| `ls -R` | `Glob` with a pattern |
| a whole `git diff` | `--stat`, then a range by files |
| `git log` without `-n` | `-n <N>` and `--format` |

**CHECKED BY FIRING, NOT BY BEING WRITTEN DOWN.** The PostToolUse hook
`tool_output_truncation_nudge` counts both lines (threshold 250) and bytes (threshold 24,000,
set from the measured p99 = 6,386 tokens). It ADVISES rather than blocks: the tool's result is
unchanged, the call is not cancelled. The thresholds are configurable through
`tool_output_truncation_threshold` and `tool_output_truncation_bytes` in `.tausik/config.json`.
The mutation checks are in `tests/test_output_byte_cap.py`, including the "one line, 50 KB"
case that a line threshold cannot see.

**WE DO NOT REPEAT SOMEONE ELSE'S NUMBER.** An external source
(github.com/Austin1serb/agents-md) calls a byte cap its main win and claims around −50% of
tokens. That figure is **someone else's, unverified here, and is not claimed as ours** — the
same caveat was already made about the "~65%" of caveman mode. Our measured claim here is
exactly one: the results of Bash commands account for 26.3% of context growth, and for some of
those calls the output size is not known in advance.

## The boundary of hook enforcement: what is covered and what is not

Moved into its own document: [`../en/enforcement-coverage.md`](enforcement-coverage.md)
(RU: [`../ru/enforcement-coverage.md`](../ru/enforcement-coverage.md)).

It holds: what `bash_write_gate` catches and what it does NOT, wrappers and transparent
prefixes, the behaviour on an unparseable command, the **channel coverage matrix**
(Write/Edit × Bash × PowerShell) and mixed scope (Rule 2, AC3).

---

## Rule 4 — External Validation (separation of duties)

Closing a task with **measured-high** risk requires an independent adversarial review by a
DIFFERENT model — a model cannot validate its own code. The implementation:

- **The subagent** `tausik-external-reviewer` (`harness/claude/subagents/`) — read-only tools
  (`Read, Grep, Bash`, no `Write`/`Edit`: SENAR "Reviewer SHALL NOT have write access"),
  `model: opus`. It returns a structured verdict
  (`approved | changes_requested | blocked`) and the exact `tausik review record` command.
- **Different model.** `scripts/external_reviewer.py::recommend_reviewer_model(author)` picks a
  family different from the author's (order: opus → fable → sonnet → haiku);
  `is_separate_duty()` rejects a family match and an unknown reviewer. If the author is already
  on opus, the reviewer falls back to fable.
- **The trigger.** `risk_l3_trigger.check_l3_required` blocks `task done` on a measured-high
  closure (the selection describes how thin the evidence is, it does not predict an escape —
  decision #212) and names `@tausik-external-reviewer` in the remediation together with the
  recommended model and the author's exact model id. A recorded
  `tausik review record --type L3 --author-model … --reviewer-model …` clears the block; a
  record with models from one family, or with none, is refused (github#157). Opt-out:
  `config risk.l3_block_on_high=false` (→ warning).
- **Evidence.** The reviewer's verdict is stored in the `reviews` table (run_type=L3) and
  reaches the ADR metrics (`tausik review metrics`).

---

## Rule 7 — Structured Root Cause (defect tasks)

Two levels (decision #96):

- **Keyword floor (Hard).** `task done` for a defect task (`defect_of` set) is blocked if the
  notes mention no cause (`root cause` / `причина` / `caused by` / `из-за` / …). Opt-out:
  `config task_done.root_cause_hard=false` → warning.
- **Structured layer (Advisory).** On top of the floor: if a cause is present but not in the
  canonical form — an escalating nudge (silent→hint→warning→strong), which does NOT block.
  Compliance resets the counter.

**The canonical format** (one `task log` line):

```
Root cause (<category>): <description>. Prevention: <how to avoid it>.
```

Bilingual: `Причина (<category>): <описание>. Профилактика: <…>.`

**The closed list of categories** (`scripts/root_cause.py::ROOT_CAUSE_CATEGORIES`):
`logic-error`, `missing-validation`, `race-condition`, `config-error`,
`integration-mismatch`, `regression`, `edge-case`, `performance`,
`dependency`, `documentation`, `other`.

An unknown category, or a missing `Prevention:`, means the form is not structured (no
exceptions). Coverage (the share of done defect tasks with the structure) is printed by
`tausik metrics` (the *Root Cause Coverage* section).

An example:

```
.tausik/tausik task log fix-pager "Root cause (logic-error): off-by-one in the paginator on an empty page. Prevention: add a bounds test for the last page."
```

---

## Searching across word forms

`tausik search` and the memory search understand case and number: a Cyrillic word of five
letters or more is searched together with its stem (`калибровкой` finds both «калибровка» and
«калибровки»). A short word is searched as given — if you need the stem, add an asterisk:
`гейт*`. The asterisk works only at the end of a word; in the middle, and on its own, it is
stripped. If an exact query returned nothing, shorten the word to its stem with an asterisk
rather than rewording at random.

## Workflow and commands (the full list)

**The workflow graph:** `start → plan → task → [review, test] → commit → end`
**Batch workflow:** `run plan.md → [task start → subagent → validate → commit] × N → summary`

**The full CLI:** `epic | story | task | session | gates | skill | stack | role | memory | doctor | hud | metrics | roadmap | events | search | decide | dead-end | explore | audit | run | doc | verify | suggest-model | team | update-claudemd | fts | init`. Details in `docs/en/cli.md`.

**Knowledge:** a decision → `decide`. A dead end → `dead-end`. A pattern → `memory add`. The
end of a session → `session handoff`.

---

## Roles

Free text (any string). Common ones: `developer`, `architect`, `qa`, `tech-writer`. The
profiles live in `harness/roles/{role}.md`.

---

## External skills

Repositories: `.tausik/tausik skill repo add <url>`. Installation:
`.tausik/tausik skill install <name>`. Activation: `.tausik/tausik skill activate {name}`.
Deactivation: `.tausik/tausik skill deactivate {name}`. The format is `tausik-skills.json` at
the root of a compatible repository. Legacy: `skills.json` plus bootstrap, for backward
compatibility.

---

## Stacks

**DEFAULT_STACKS** (25): python, fastapi, django, flask, react, next, vue, nuxt, svelte,
typescript, javascript, go, rust, java, kotlin, swift, flutter, laravel, php, blade, ansible,
terraform, helm, kubernetes, docker.

**Custom stacks.** The list is open for extension — add your stack to `.tausik/config.json`:

```json
{ "custom_stacks": ["ruby", "elixir", "scala", "csharp"] }
```

After that `task add --stack ruby` is accepted. Stack-scoped gates (pytest, go-test and so on)
are deliberately NOT applied to custom stacks — for those you register a custom gate in the
`gates` section of `config.json`. Universal gates (filesize, class_surface, tdd_order) work for
every stack. `tausik stack list` shows custom stacks marked `(custom)`.

The guides live in `harness/stacks/{stack}.md`.

---

## Why this was split off (history)

`CLAUDE.md` is loaded into the agent's context **on every turn** — even when the agent is only
writing "ok". Before the v1.4 trim the file was ~15.5KB ≈ 4000 tokens; over a 100-turn session
that is 400K tokens of tax from CLAUDE.md alone.

Trimming it to ≤4KB takes the non-enforceable reference (this file) out of the hot path. The
regression test `tests/test_claude_md_size.py` pins the boundary — the current limit is a
constant in that test and stands at ~4500 bytes after the v1.4 edits to CLAUDE.md; if the file
grows past it, CI blocks.
