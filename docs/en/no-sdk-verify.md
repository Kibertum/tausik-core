# No-SDK verification: HTTP endpoint for any agent or CI

TAUSIK attestation without MCP, hooks, or any SDK. `tausik serve` starts a
stateless HTTP endpoint; anything that can speak JSON over HTTP — a GPT-based
agent, a Jenkins job, a bash script — can submit gate results and get back a
**signed, portable receipt** (`tausik-signed/v1`, ed25519).

## Quickstart

```bash
tausik key init          # once per project: ed25519 keypair in .tausik/keys/
tausik serve --port 8765 # binds 127.0.0.1 (no auth layer — localhost only)
```

Non-localhost binds require an explicit `--yes-expose` and are NOT
recommended: the endpoint has no authentication. Put a reverse proxy with
auth in front if you must expose it.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/verify` | gate results → verdict + signed receipt |
| POST | `/receipt/verify` | re-check an envelope or export artifact |
| GET | `/key` | public key + fingerprint (never the seed) |
| GET | `/healthz` | liveness |

### POST /verify

```bash
curl -s http://127.0.0.1:8765/verify -d '{
  "task_slug": "ci-build-42",
  "scope": "standard",
  "git_sha": "0123456789abcdef0123456789abcdef01234567",
  "gates": [
    {"name": "pytest",  "passed": true,  "severity": "block"},
    {"name": "eslint",  "passed": true,  "severity": "warn"},
    {"name": "hadolint","passed": true,  "severity": "warn", "skipped": true}
  ]
}'
```

Response: `{"passed": true, "blocking_failed": [], "all_skipped": false,
"envelope": {...}}`.

Verdict semantics mirror the local pipeline: every non-skipped gate with
`severity: "block"` must pass, **and** at least one gate must have actually
run — an all-skipped submission is `passed: false`. The receipt inside
`envelope` attests only the gates that ran.

Errors: `400` invalid input (message says which field), `503` no project key
(run `tausik key init`), `404` unknown path.

### POST /receipt/verify

Accepts either a `tausik-signed/v1` envelope or a `tausik-receipt-export/v1`
artifact (from `tausik receipt export`):

```bash
curl -s http://127.0.0.1:8765/receipt/verify -d @receipt.json
# {"valid": true, "detail": "..."}
```

## Trust model

The signature proves **integrity** (the receipt was not modified after
signing). Origin requires comparing the key fingerprint against an
out-of-band channel — `tausik key show` output, a pinned CI variable, a PR
description. Never trust a fingerprint embedded in the same artifact you are
verifying.

## Working client example

The runnable, CI-tested reference client lives at
[`tests/test_no_sdk_example.py`](https://github.com/Kibertum/tausik-core/blob/main/tests/test_no_sdk_example.py) — pure
`http.client` stdlib, no dependencies. Core of it:

```python
import http.client, json, sys

def submit_gates(host, port, task_slug, gates):
    conn = http.client.HTTPConnection(host, port, timeout=30)
    conn.request("POST", "/verify",
                 body=json.dumps({"task_slug": task_slug, "gates": gates}),
                 headers={"Content-Type": "application/json"})
    resp = conn.getresponse()
    data = json.loads(resp.read())
    if resp.status == 503:
        sys.exit(f"endpoint has no signing key: {data['error']}")
    if resp.status != 200:
        sys.exit(f"verify request rejected ({resp.status}): {data['error']}")
    return data

result = submit_gates("127.0.0.1", 8765, "ci-build-42",
                      [{"name": "pytest", "passed": True, "severity": "block"}])
json.dump(result["envelope"], open("receipt.json", "w"))
sys.exit(0 if result["passed"] else 1)   # fail the CI job on a red verdict
```

## GitHub Actions snippet

```yaml
- name: Attest test results with TAUSIK
  run: |
    tausik serve --port 8765 &
    sleep 1
    python ci_verify.py            # the client above; exits 1 on red verdict
    curl -s http://127.0.0.1:8765/receipt/verify -d @receipt.json
- name: Upload signed receipt
  uses: actions/upload-artifact@v4
  with: { name: tausik-receipt, path: receipt.json }
```
