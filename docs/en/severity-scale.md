**English** | [Русский](../ru/severity-scale.md)

# Severity scale of review findings

<!-- doc-map: reader=user; zone=reference -->

SENAR 1.5 §10.15(f) requires this page. Without it, two things cannot be decided: a CRITICAL finding blocks a commit under §10.15(d), and CRITICAL findings are the numerator of the Adversarial Detection Rate in §9.2. `tausik review metrics` prints that rate.

## Which scale this is

Three scales in SENAR share their words. This page defines **only the severity of a finding**.

| Scale | What it classifies | What it selects | Where in TAUSIK |
|-------|--------------------|-----------------|-----------------|
| **Finding severity** (this page) | One defect found by a review | Whether the commit is blocked, and the ADR numerator | `/review`, `tausik-reviewer`, `tausik-external-reviewer`, `tausik review record` |
| Change risk level (§8.7) | A change before review | How deep the review goes | Task risk score in `tausik metrics` |
| Checklist tier (SENAR Core) | A task at closure | How much of the verification checklist runs | Task `tier`: trivial … deep |

"High" appears in all three scales. A HIGH finding does not make a change high-risk, and a deep-tier task does not make its findings CRITICAL.

## The levels

| Level | Covers in this project | Consequence |
|-------|------------------------|-------------|
| **CRITICAL** | Wrong data written or lost; a gate that passes work it should refuse (silent fail-open); injection or command execution from input; an auth or scope bypass; a secret leaked into a file, log or event; a crash on a supported path (CLI, MCP, hook) | Blocks the commit until resolved (§10.15(d)). Counted in ADR. Its reason is recorded. |
| **HIGH** | Missing input validation on a boundary; a swallowed exception that hides a failure; a broken compatibility promise (schema upgrade, CLI flag, MCP contract); a test that asserts a number instead of a behaviour | Fixed before the task closes, or filed as a defect task with the reason it waits |
| **MEDIUM** | Duplication of three or more copies; a plausible edge case left unhandled; a file over the size cap; docs that disagree with the code | Fixed in the task or filed; never silently dropped |
| **LOW** | Naming, dead code, comment drift, formatting | Advisory |

The standard names CRITICAL, HIGH and MEDIUM. LOW is this project's addition for advisories. It never blocks and is not counted.

## Who assigns it

- **The review agent proposes.** `/review`, `tausik-reviewer` and `tausik-external-reviewer` classify each finding by this table.
- **The supervisor decides.** The owner, or whoever accepts the finding, is accountable for its classification. For an L3 review that is the supervisor §10.15(a) permits, not the party that directed the work under review.
- **CRITICAL is recorded with its reason.** `tausik review record --critical N` with N above zero is refused without `--reason`. The reason is stored with the record and shown by `tausik review list`.

```bash
tausik review record --task <slug> --type L3 --critical 1 --warnings 2 \
  --reason "hook fails open on a locked DB: the write goes through unchecked"
```
