# Codex L3 read-only path (TB-009)

**English** | [Russian](../ru/codex-l3-readonly.md)

<!-- doc-map: reader=agent; zone=quality -->

Bounded L3 review on a Codex host needs a **mechanically** read-only reviewer
that can still **read** the repository. A product `red`/`green` must not be
recorded when the host cannot do that — that burned both defect-repair rounds
in dogfood (`bugs.txt` TB-009).

## Supported Codex invocation

```text
codex exec --sandbox read-only --ephemeral
```

Use the same-family model as the author (one family per environment). Carry
`Author model: <id>` from the cohort packet / `delegation` field into
`review cohort-record --author-model`.

## Capability preflight

Declare the reviewer surface in `.tausik/config.json`:

```json
{
  "review": {
    "l3_host": {
      "tools": ["Read", "Grep", "Bash"],
      "read_probe_results": {
        "Get-Content": true,
        "rg": true,
        "cmd /c type": true,
        "Set-Content": false,
        "Out-File": false,
        "Remove-Item": false,
        "New-Item": false
      }
    }
  }
}
```

- Write-capable editor tools (`Write`, `Edit`, …) → `L3_HOST_WRITE_CAPABLE`.
- Read probes blocked under a “read-only” sandbox → `L3_READONLY_POLICY_BLOCKS_READS`.
- When `review.l3_host` is set and assessment fails, `cohort-record` refuses
  with `review_infrastructure_blocked` and does **not** advance `current_round`.

## Infrastructure receipt (budget preserved)

```text
.tausik/tausik review cohort-infrastructure-blocked <id> \
  --round 1 \
  --packet-digest <digest> \
  --code L3_READONLY_POLICY_BLOCKS_READS \
  --reason "Codex read-only policy blocked Get-Content/rg" \
  --detail "Windows PowerShell"
```

`rounds` stays `0/2` (or `1/2` before round 2). Re-open or fix the host, then
run a real file review.

## Negative

A write-capable host must never be recorded as an L3 PASS. Prefer the
infrastructure receipt over fabricating findings.
