---
slug: verify-signer-failure-used-to-be-a-warning-on-a-green-run
title: "verify: signer failure used to be a WARNING on a green run"
type: gotcha
tags: []
task: null
edges: []
---

When a project key exists but emit_signed_receipt returns status error, verify printed a WARNING and the run stayed green and closable. Since 1.10 verify_cached_run turns it red with INFRASTRUCTURE: SIGNER_UNAVAILABLE (scripts/infra_refusal.py). receipt_status travels from verify_run_record handle_out into details; verify_cached_run needs a local details sink or the check is skipped when the caller passes none.
