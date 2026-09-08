# What changed in 1.9

A page for whoever is upgrading. Before reading what breaks, it is worth knowing
what it was for.

## What 1.9 is, in three points

**📏 A release that stopped taking its own word for things.** 1.8 answered the
question "does the framework enforce discipline". 1.9 asks no question — it makes
two statements about the product and requires each to be measured: a substantial
token saving, and higher development quality on any model.

**🔢 Zero stopped passing itself off as a measurement.** A quantity that cannot
be obtained is now ABSENT, not nought. That sounds like a nicety until you look
at the numbers: the telemetry asserted 55,471 times that work had cost $0.00,
and model pinning had NEVER fired in 231 sessions. Both defects looked exactly
like "a feature nobody needed".

**🖧 Guarantees are stated by rule, not by host.** Five environments were handed
the same rules text promising automatic enforcement; on two of the five that was
untrue. Each host now reads what is actually deployed for it — and by rule,
because "everything here is instructions" is untrue too on a host without hooks:
closing a task IS refused there.

Full list of changes: [CHANGELOG.md](../../CHANGELOG.md). This page is not a
retelling: the Unreleased section holds 163 entries, and what is selected here is
what changes the experience of UPGRADING.

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

---

## What else changes on upgrade

### Database schema: 44 → 58

Fourteen migrations apply automatically on first access. Each is preceded by a
backup at `.tausik/tausik.db.bak.v<old>`; spares are cleared with
`tausik db prune --keep N`.

The most visible is v58: the token and cost columns in `usage_events` became
nullable. **NULL means "not measured", and that is not the same as 0.** The
migration turned 55,307 rows — provably never measured — into NULL and touched
no row carrying a real number.

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

### Output economy: two levers, both off on purpose

`read_ledger` (do not pay twice for an unchanged file) and a byte cap on command
output both ship, both are **off by default**, and each has a decision with a
number behind it. Turning them on is your choice, not our default.

---

## See also

- [publishing.md](publishing.md) — the two repository lines, and why a published tag never moves
- [enforcement-coverage.md](enforcement-coverage.md) — what is enforced on your host, and by what
- [cost-telemetry.md](cost-telemetry.md) — how to read cost after v58
