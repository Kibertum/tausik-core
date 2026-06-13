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
    "schema": "tausik-receipt/v1",
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
    "key_fingerprint": "9f3c1a2b4d5e6f70"
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

The receipt is **canonical** (JCS / RFC 8785 spirit): keys sorted at every
level, no whitespace, ASCII-only, floats rejected. The same logical receipt
always serializes to the same bytes, so signatures verify identically across
machines and platforms.

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
