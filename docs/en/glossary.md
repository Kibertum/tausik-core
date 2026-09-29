[Русский](../ru/glossary.md) | **English**

# Glossary: what TAUSIK's words mean

<!-- doc-map: reader=user; zone=getting-started -->

This page exists because of a count: across the 88 pages marked for the user, `gate` appears
715 times, `slug` 467, `QG-2` 74 — and there was nowhere to look any of them up. The terms
below were gathered by counting those pages rather than by imagination: this is what a reader
actually trips over.

The order runs from what you meet in the first hour to what you need later.

## The work: what a task is made of

**Task** — a unit of work with a goal, acceptance criteria and a journal. Until a task is
started the agent may not write code. Everything else hangs off this.

**Slug** — a task's short hyphenated name, e.g. `no-glossary-so-the-vocabulary-is-a-wall`.
Every command addresses the task by it, and it does not change after creation, because
journals and commits already point at it.

**Acceptance criteria (AC)** — the list of what must be true before the task may close,
written BEFORE the work. At least one criterion says how the system must REFUSE; without that
only the happy path is ever checked.

**Task journal** — the record of how the work went and the evidence for closing it. Appended
to, never rewritten: evidence you can edit afterwards is not evidence.

**Story** and **epic** — two levels of grouping. The epic answers "which problem are we
solving", the story "which part of it is being taken now".

**Complexity**: `simple`, `medium`, `complex`. It decides which gates are hard and which model
the framework recommends.

**Tier** — how much evidence a closure owes, from `trivial` to `deep`. Complexity answers "how
much work", tier answers "how much proof".

## The checks: what refuses, and when

**Gate** — a check that can refuse. There are about fifty: linter, tests, file size, drift
between source and the deployed copies. A blocking gate stops the action; a warning one only
speaks.

**QG-0** — the gate at the START of a task. It refuses work without a goal and acceptance
criteria, because a task with no criteria is closed on a feeling.

**QG-2** — the gate at the CLOSE. It refuses a closure with no fresh green verification
belonging to that task.

**Verify-First** — the order in which heavy checks run once, ahead of time, via `verify` and
are cached, so the closure only presents the result. Otherwise every close would cost a full
test run.

**Receipt** — a signed record that a check happened: what ran, with what result, by whom. A
forged receipt does not pass verification.

**Ratchet** — a number allowed only to go down. It is how the framework holds a remainder that
cannot be cleared in one pass: rotted references, indistinguishable tests, answer length.
Growth goes red; shrinking passes.

**Dead end** — a recorded approach that did NOT work, and why. It exists so the next person
does not spend a day on the same thing.

## How it is put together

**Harness** — everything the framework deploys into a project around the agent: skills, hooks,
MCP servers, the rules file. It is what turns rules into mechanisms.

**Deployed profiles** — per-editor copies of the harness (`.claude/`, `.cursor/`, …). The copy
is what runs, so an edit to the source that has not reached it has not taken effect.

**Projection** — the Markdown tree under `tausik/` into which tasks, decisions and memory are
serialised. The database does not travel between machines; the tree does, which is how state
moves.

**Stack** — the project's language and tooling. It decides which gates apply.

**Handoff** — a session's note to the next one: what was done, what is left, what the owner
decides.

**Snapshot** — the public copy of the repository: the filtered tree of a tag, without the
internal projection or the working documents.

## Standards

**SENAR** — the external standard for AI-agent discipline that TAUSIK claims conformance to.
The rules about a task before code, about the journal, and about a check that did not run
certifying nothing come from there.

**RENAR** — the standard for describing requirements: specifications, traceability, acceptance
tests. TAUSIK declares itself NON-conformant to it, and the reason is named on the compliance
page.

## See also

- [Start here](start-here-user.md) — the reading order for your role
- [What is NOT guaranteed](known-limitations.md) — boundaries declared in advance
- [CLI reference](cli.md) — the commands in full
