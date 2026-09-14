**English** | [Русский](../ru/receipts.md)

# Signed verification receipts

When `tausik verify` finishes, it writes a small, **ed25519-signed** record of
what was checked — a *receipt*. The one-line value:

> you can prove a task was actually verified, not just claimed.

A receipt is bound to the gates that ran and to the current git `HEAD`. Because
it is signed with the project key, a passing ("green") verdict **cannot be
forged or replayed** by hand-editing a row or copying an old result onto a new
commit. `task done` (QG-2) reads the cached verify run before it lets a task
close, so the signature is the evidence behind the green.

Receipts are **portable** and **offline-verifiable**: export one to a JSON
file, attach it to a PR or CI artifact, and anyone can re-check the signature
with no database, no keystore, and no TAUSIK SDK.

## How a receipt is produced

```bash
tausik key init                  # once per project — generates the keypair
tausik verify --task my-feature  # runs the gates, then signs a receipt
```

`verify` records a `verification_run`, then emits a receipt for it. Emission is
best-effort: on a project **without** a key it degrades to "no key" and the
verify run still succeeds — you just get no signed evidence. The tail of a
`verify` run reports the outcome:

```
Recorded verification_run (task_slug=my-feature, exit=0).
Receipt: signed (run #412, key 9f3c1a2b4d5e6f70).
```

The receipt attests only the gates that **actually ran** — a skipped gate
proves nothing, so it is left out, even though it counts as "passed" for the
verdict.

## The envelope format (`tausik-signed/v1`)

A signed receipt is an *envelope* wrapping the canonical receipt plus its
signature. The signature is computed over the canonical bytes of the `receipt`
object only — never over the envelope.

```json
{
  "envelope": "tausik-signed/v1",
  "receipt": {
    "schema": "tausik-receipt/v2",
    "task_slug": "my-feature",
    "git_sha": "0123456789abcdef0123456789abcdef01234567",
    "scope": "standard",
    "gates": [
      {"name": "pytest", "passed": true, "severity": "block"},
      {"name": "ruff",   "passed": true, "severity": "warn"}
    ],
    "passed": true,
    "ran_at": "2026-06-13T10:42:07Z",
    "files_hash": "a1b2c3d4...",
    "key_fingerprint": "9f3c1a2b4d5e6f70",
    "declared_scope_status": "under-declared",
    "undeclared_files": ["CHANGELOG.md", "docs/en/receipts.md"],
    "undeclared_count": 2
  },
  "signature": {
    "algorithm": "ed25519",
    "key_fingerprint": "9f3c1a2b4d5e6f70",
    "value": "<128 hex chars — the 64-byte ed25519 signature>"
  }
}
```

Field notes:

- `git_sha` — the `HEAD` sha at verify time, or `null` outside a git repo. This
  is what binds a green to a specific commit and blocks replay onto new code.
- `gates[]` — reduced to the signable triple `{name, passed, severity}`. Bulky,
  non-deterministic gate output stays out of the receipt by design.
- `passed` — the overall verdict: every non-skipped `block` gate passed and at
  least one gate ran.
- `key_fingerprint` — first 16 hex of the SHA-256 of the public key; the same
  value appears in `tausik key show`.
- `value` — 128 hex chars (64-byte ed25519 signature).

### Scope honesty (schema v2)

A receipt claims that gates passed **over some set of files**. The three fields
below say whether that set was complete. Without them the receipt stayed silent
about the very thing that undermines it: an agent declaring
`relevant_files=[README.md]` during a broad edit still received a signed green
receipt for `README.md`.

- `declared_scope_status` — one of three values:
  - `complete` — the declared set covers everything git saw change since the
    task started;
  - `under-declared` — git saw changes outside the declared set;
  - `unknown` — the comparison **could not be made**: outside a git repo, with
    an empty `relevant_files`, without `task_created_at`, or when the git call
    failed.
- `undeclared_files` — sorted list of files git reports as changed that
  `relevant_files` does not name. Capped at 50 entries.
- `undeclared_count` — the full count, **never** truncated. When it exceeds the
  length of the list, the list is showing only part of the picture.

Three properties that matter when reading someone else's receipt:

1. **`unknown` is not `complete`.** A measurement that did not happen is never
   credited as confirmed coverage. Schema `v1` receipts issued before this
   change carry no such fields at all — treat their scope as **unverified**,
   not as complete.
2. **`under-declared` is not an accusation.** The divergence fires on nearly
   every honest closure: edits to CHANGELOG, docs, generated constants and
   badges routinely fall outside the declared set. It is therefore recorded but
   **does not block**. The one exception is an undeclared file matching the
   security predicate: gates scoped to the declared list would not have checked
   it at all, so that run fails with status `scope-security-mismatch` and asks
   for the file to be added to `relevant_files`.
3. **The task's own bookkeeping does not count against it.** Two files are
   written by the framework rather than by the agent, and both are subtracted
   before the comparison:
   - `tausik/tasks/<slug>.md`, the task's own export — rewritten between
     `task start` and the verify by `started_at`, every `task log`, the declared
     scope and the receipt itself;
   - `tausik/stories/<parent>.md`, the projection of the task's parent story —
     `task start` flips its `status: open -> active`.

   Only the CURRENT task's two files. Somebody else's export, and any other
   story, is a real product of the task that edits it and stays listed. The
   parent EPIC is not subtracted: a task's lifecycle was measured not to touch
   it. When the subtraction is the only reason nothing is left, the reason names
   the files instead of claiming the tree never moved.
4. **A committed sibling is excluded only with commit-local proof.** An active
   task can overlap a release-accumulation commit, but its timestamp does not
   make every path in that commit its work. For every commit since `started_at`
   `verify` reads three tiers of evidence and resolves each changed path on the
   strongest tier that names anyone — one name owns the path, two or more keep
   it ambiguous, and a weaker tier is never consulted once a stronger one has
   spoken:
   - *same commit* — another task's export committed alongside the path
     declares it in `relevant_files`, or the export is `active`/`blocked`/`done`
     and its `scope_paths` ACL matches it;
   - *parent tree* — an `active`/`blocked`/`done` export already committed
     before this commit declared the path in `relevant_files` (a task may
     declare first and commit its implementation later);
   - *projection* — the path IS another task's export, its parent story, or a
     DYNAMIC-block-only refresh of `AGENTS.md`/`CLAUDE.md`.

   A task never holds a work claim on its own export, whichever field spells it.
   Uncommitted paths, malformed exports, `planning` exports and paths with two
   claimants on the deciding tier remain in the comparison.

The receipt is **canonical** (JCS / RFC 8785 spirit): keys sorted at every
level, no whitespace, ASCII-only, floats rejected. The same logical receipt
always serializes to the same bytes, so signatures verify identically across
machines and platforms.

### What the receipt says about itself (schema v3)

Schema `v2` named `files_hash` — an opaque digest you can **compare** but not
**read**. Such a receipt could not answer the two questions without which it
cannot be presented as proof: "over which files?" and "with which gate set?".
Schema `v3` adds three fields, and they are what turn the receipt from a stamp
over a row into a document.

- `files` — the sorted list of declared paths. The security predicate applies to
  THIS list, not to the argument of the `task done` call: otherwise a closer
  could declare a harmless scope while presenting a receipt that covered `auth/`.
- `gate_signature` — the same 16 hex that go into `verification_runs.command`.
  It is **not** recomputed: the gate-set signature is taken from one source, or
  the receipt could agree with itself and disagree with the row that produced it.
- `expires_at` — the shelf life **inside the signature**. A policy that sits
  beside the document gets edited along with it; a policy inside the signature
  does not.

Receipts of schema `v1` and `v2` remain cryptographically valid, and the old
closing path (looking up a fresh run) still accepts them. But such a receipt
cannot be **presented** by handle: it reads as **partial**, and the refusal
names the missing fields outright. The unknown is reported as unknown — never
rounded down to "complete" nor up to "tampered".

## The run handle — presenting instead of searching

Decision #218, adopting SEP-2567's "explicit state handles".

**How it was.** `task done` searched `verification_runs` for a row: green, same
`files_hash`, same gate signature, younger than 600 seconds. The link between "I
verified" and "I am closing" was a *search*, not a presentation. Three
consequences, all of them defects: a substantive refusal ("the declared scope is
already behind the git changes") reached the agent as a **cache miss**; the
freshness window belonged to the server and was invisible to the model; and two
processes with different in-memory module state judged "freshness" differently.

**How it is now.** `tausik verify --task <slug>` prints a handle:

```
Verify handle: 4821.9f3c1a2b4d5e6f7089abcdef01234567
  valid until 2026-06-13T11:42:07Z (single use). Present it:
  tausik task done my-feature --ac-verified --verify-handle 4821.9f3c...
```

The handle is `<run_id>.<nonce>`, where the nonce is 128 bits from `secrets` (a
SEP-2567 requirement). The server does a **point** lookup by `run_id` rather
than a search by freshness.

**The shelf life is 3600 seconds (one hour)**, against 600 for the previous
cache. That is not a loosening but a consequence of the clock no longer being
the main criterion: on redemption `files_hash` is recomputed over the **live**
files and the gate signature over the **live** config. A tree that has moved is
caught by what actually changed, not by a timer. The clock remains only as the
bound on how long an unredeemed handle may hang about. Overridden by the config
key `verify_handle_ttl_seconds`.

The shelf life is named in the `tausik_verify` tool description, in the CLI
output, and in the receipt's own `expires_at` field — on SEP-2567's explicit
requirement: "A policy only in server documentation is not visible to the model".

### Verification on presentation — fail-closed

Every clause refuses; none passes silently:

| Condition | What the refusal says |
|---|---|
| handle of the wrong shape | `<run_id>.<32-hex>` was expected |
| no such run in this DB | the handle was issued by another project |
| nonce mismatch (constant-time compare) | handles are single-use and replaced by every verify |
| the run was red | a red run confers no right to close a task |
| the run verified a different task | a handle is valid for the task it was issued under |
| the run is marked `noncacheable\|` | recorded for audit, not as a certificate |
| the handle is already redeemed | single use (replay, SEP-2322) |
| expired / unreadable expiry | an unreadable expiry is **not** read as "no expiry" |
| the project has no usable public key | the handle path is CLOSED; this is a **named mode**, not a failed check — either `tausik key init`, or close without `--verify-handle` |
| no receipt / broken JSON / bad signature | there is nothing to present |
| the receipt is signed for a different task than the run row | a substituted receipt |
| the receipt's `ran_at` disagrees with the run row | a substituted receipt |
| a v1/v2 receipt | the missing v3 fields are listed |
| `files` cover a security path | such scopes are re-checked on every close |
| `files_hash` over the live files diverged | a **substantive** refusal, not a cache miss |
| the receipt's `files_hash` diverged from the run row | document and record describe different file sets |
| the gate signature diverged from the row or from the live config | the receipt certifies a gate set that is no longer the one |
| git sees a security file changed that the receipt does NOT name | gates scoped by the receipt's list never looked at that file |

**And `verify` never hands out what this table would refuse.** A handle is
minted only when the receipt it stands for was SIGNED (GitLab #15). Two distinct
lines replace the ready-to-copy `--verify-handle` command that `task done` was
bound to refuse: in a keyless project, "Verify handle: none — no project key,
so no signed receipt (tausik key init enables them)"; when a key is present
but signing failed, "Verify handle: none — the receipt could not be signed (see
.tausik/tausik.log, tausik key show)". Both end with the close command that
works — `task done <slug> --ac-verified`, the freshness lookup. The same
renderer serves the CLI and `tausik_verify`.

One divergence deliberately does NOT block: if git sees changes outside the
receipt's scope but none of them is security-sensitive, the handle is honoured
and the divergence goes into the verdict text (decision #138 — it fires on
almost every honest close: CHANGELOG, docs, generated constants). A divergence
nobody sees equals an unmeasured one, so it is stated rather than swallowed.

**Compatibility.** `task done` **without** `--verify-handle` works as before,
through the fresh-run lookup. A silent tightening is not allowed: the handle
changes how a green is **presented**, not which greens count.

**What the handle does NOT give you.** It is not authorisation. The private seed
lives in the working tree (see "What the signature does NOT prove" below), so an
agent is capable of producing a signature the key will accept. The handle's job
is to make the link "verified -> closing" explicit and checkable, and replay
countable; not to restrain a determined agent. That is precisely why everything
the old search checked is **recomputed here against live state** rather than
taken on trust from the presented document (SEP-2322: "servers MUST always
validate that state, as the client is an untrusted intermediary").

Auditing unredeemed handles:

```sql
SELECT id, task_slug, handle_expires_at FROM verification_runs
WHERE handle_nonce IS NOT NULL AND handle_redeemed_at IS NULL;
```

## Key management

```bash
tausik key init    # generate the project ed25519 keypair (refuses to overwrite)
tausik key show    # print the public key + fingerprint (never the seed)
```

Keys live under `.tausik/keys/`:

| File | Contents | Shareable? |
|---|---|---|
| `project.key` | private 32-byte seed (`ed25519:<64 hex>`) | **No** — never leaves the machine; `.tausik/` is gitignored |
| `project.pub` | public key (`ed25519:<64 hex>`) | Yes — distribute out-of-band for verification |

To rotate, run `tausik key init --force`. Be aware: **existing signatures will
no longer verify** against the new key.

## Working with receipts

### `tausik receipt show`

Print the latest stored envelope for a task (or a specific run) and re-verify
its signature against the project key.

```bash
tausik receipt show --task my-feature      # or: --run 412
tausik receipt show --task my-feature --json   # raw envelope JSON
```

Exit codes: `0` valid, `1` signature **invalid** (payload or signature was
modified), `2` not found / no key.

### `tausik receipt export`

Produce a self-contained, portable artifact — the envelope plus the embedded
public key — for a PR or external audit. Export refuses to run if the stored
signature does not verify against the current key (tampered row or rotated
key).

```bash
tausik receipt export --task my-feature           # writes to .tausik/receipts/
tausik receipt export --task my-feature --out receipt.json
tausik receipt export --task my-feature --stdout  # print, don't write
```

The export wraps the envelope in a `tausik-receipt-export/v1` artifact that
embeds the public key, so it can be verified anywhere:

```json
{
  "export": "tausik-receipt-export/v1",
  "envelope": { "...tausik-signed/v1, untouched..." },
  "public_key": "ed25519:<64 hex>",
  "key_fingerprint": "9f3c1a2b4d5e6f70"
}
```

### `tausik receipt verify <file>`

Offline integrity check of an exported artifact — **no database, no keystore,
no SDK** required. By default it uses the public key embedded in the file. To
distrust that key, pin your own out-of-band:

```bash
tausik receipt verify receipt.json
tausik receipt verify receipt.json --pub ed25519:7c2f...e0
```

Exit codes: `0` valid, `1` real artifact with a bad signature, `2` the file is
not a valid export artifact.

## Trust model

The signature proves **integrity** — the receipt was not modified after it was
signed. It does **not**, on its own, prove **origin**: an embedded fingerprint
is only as trustworthy as the file it travels in. To anchor origin, compare the
`key_fingerprint` against an out-of-band channel — `tausik key show` output, a
pinned CI variable, or the PR description — and never trust a fingerprint
embedded in the very artifact you are verifying.

### What the signature does NOT prove — the key boundary

Be precise about the claim, because the wording is legally load-bearing under
the EU AI Act (logging obligations for high-risk systems apply from August
2026). The private seed lives at `.tausik/keys/project.key` **inside the
working tree** — the same tree the agent whose work the key signs can read
(`mode 0600` is best-effort on POSIX and a no-op on Windows). Therefore:

- A valid signature is **tamper-evidence against EXTERNAL edits** to
  `tausik.db`: nobody rewrote the "green" verdict or replayed an old result
  onto a new commit *without access to the key*. The same holds for the
  `events_anchor` signature over the event chain.
- It is **NOT attestation against the agent**. An agent (or anything else) with
  read access to the working tree can read the seed and produce a signature the
  key would accept. The receipt proves "someone with filesystem access produced
  this", not "an independent party attests the agent behaved".

To obtain attestation the agent cannot forge, the signing key must live
**outside the agent's write (and read) zone** — a managed path, an OS keychain,
or a separate signer process. That relocation is deliberately deferred (see the
`tausik decide` record for `l26-signing-key-boundary`): it is a cross-platform
key-custody design of its own, and the immediate integrity win is stating this
boundary honestly rather than implying an attestation the current storage
cannot deliver.

## Offline / no-SDK verification over HTTP

For agents and CI that cannot use the CLI or MCP, `tausik serve` exposes the
same signing and verification over a stateless HTTP endpoint — submit gate
results and get back the same `tausik-signed/v1` receipt. See
[no-sdk-verify.md](no-sdk-verify.md) for the endpoints, a stdlib client, and a
GitHub Actions snippet.

## See also

- [cli.md](cli.md) — full CLI reference (`key`, `verify`, `receipt`).
- [mcp.md](mcp.md) — the equivalent MCP tools.
- [no-sdk-verify.md](no-sdk-verify.md) — HTTP verify endpoint (`tausik serve`).
- [senar.md](senar.md) — the SENAR verify-first principle behind QG-2.


## Who did the work (`actor`, v4)

A receipt is signed with the **project** key and answers which gates passed on
which state of the code. Until v4 it did not answer WHO ran them — while the
whole quality story rests on separation of duties: an external reviewer on a
different model, and with P8 also "the test author is not the implementer". All
of it asserted, none of it attestable.

The measurement behind the field: 1,686 receipts, not one carrying an actor;
`claimed_by` NULL across all 1,574 tasks; of the 29 tasks recording both a
starting and a closing model, **none differ**. On the verify path separation of
duties does not merely lack attestation — it does not happen.

`actor` is **content** of the project-signed receipt, not a second signer. A
second key would mean per-agent key material and an identity registry; neither is
created, and keys stay local. The field is inside the canonical bytes, so an
actor edited after the fact breaks the signature.

**Comparing two receipts yields THREE outcomes, not two:** `same`, `different`
and `unknown`. A receipt with no `actor` is not a receipt by a different actor,
and a check of the form `!= same` would count every one of the 1,686 legacy
receipts as separated. Require `different` explicitly.

**The boundary.** The receipt records the actor OF THE VERIFICATION RUN. It does
not say who wrote the test and who wrote the code — that is P8's subject, and
offering this field as evidence for that claim is not allowed.

v1–v3 receipts stay valid: the field is added, not required. `actor` is
deliberately absent from `V3_REQUIRED_FIELDS`, or 1,686 closures would stop
reading at once.
