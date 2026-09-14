# AT Generation Procedure (RENAR §8A)

*Agent-facing specification — consumed by AI assistants, not end users. No RU
mirror is produced (see docs/README.md § Internal agent specs).*

RENAR §8A (ADR-012) closes the one class of defect traceability (TC → SR →
ADAPT → ТЗ) cannot catch: a wrong interpretation makes every TC pass because
the system perfectly matches the wrong reading, and fails acceptance at the
client. An AT (Acceptance Test) is the check that can still catch it — but
only if it is produced the way the standard requires. `tausik at create`
**records** an AT; it does not generate one. Generation is this procedure,
followed by whichever agent is orchestrating the work.

## The three properties that make an AT valid

1. **Derived by an isolated agent from the final TZ alone.** No ADAPT, BR, SR,
   SPEC, TC or code in its input. An agent that has seen the interpretation
   reproduces its mistake — isolation here is a generation mechanism, not a
   courtesy.
2. **Regenerated before every trial from the current edition.** A system
   tested against a year-old contract at the end of a long engagement is not
   tested against the contract. `tausik at check-freshness` names any AT whose
   `source_as_of` no longer matches the live `final_tz_snapshot` for its
   `tz_ref`.
3. **`tz_text` is a verbatim quote**, not a paraphrase — the field that ties
   an AT back to what the client actually signed, independent of whatever the
   `scenario` prose says about it.

## Procedure

1. **Pull the current reference, nothing else.**
   ```
   tausik actz final-tz
   ```
   or `tausik_actz_final_tz` over MCP. For the `tz_ref` you are generating an
   AT for, take exactly two fields: `governing_text` (becomes `tz_text`,
   verbatim) and `completed_at` (becomes `source_as_of`).

2. **Spawn a genuinely isolated agent.** Use the Agent tool with a
   general-purpose subagent and a **self-contained prompt containing only**:
   - the `tz_ref` and the verbatim `governing_text` from step 1;
   - a generic instruction to write one or more acceptance scenarios that
     verify a system satisfies that clause, in plain language a client could
     read.

   Do **not** paste ADAPT interpretations, SPEC content, existing TC, or code
   into the prompt. Do not summarize "what we built" first — the isolated
   agent must not know. If the orchestrating session has already discussed
   the implementation of this clause in the current conversation, that
   context must not reach the subagent's prompt.

3. **Transcribe, don't edit.** The orchestrating agent records the isolated
   agent's output as-is:
   ```
   tausik at create <slug> <tz_ref> "<verbatim tz_text>" "<scenario>" \
     --as-of <completed_at from step 1> --by <this session's identity>
   ```
   Editing the scenario for style is fine; changing what it checks is not —
   that reintroduces exactly the contamination isolation exists to prevent.
   `generated_by` names the **orchestrator** (this session), not the isolated
   subagent — the isolated agent has no access to `at create` by design, and
   the field records who is vouching that the procedure was followed, not who
   wrote the words.

4. **Regenerate before trial, not once.** Run `tausik at check-freshness`
   before any acceptance run. A stale AT (its `tz_ref`'s governing point
   changed since generation) must be regenerated via steps 1–3 before the
   trial counts as evidence. The `at_freshness` gate (warn) surfaces this at
   `task-done` automatically; it cannot regenerate anything itself.

## What this procedure is not

It is not a way to generate AT content for this project's own SPECs as part
of routine development — that is a separate, larger effort building on this
mechanism, not a step of it. This document describes the mechanism only.
