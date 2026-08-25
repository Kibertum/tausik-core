---
slug: r14-senar-context-hygiene
title: "SENAR Rule 10.12: PII/secrets detection in task notes (not only brain scrubbing)"
status: done
epic: rel-14-readiness
story: rel-14-audit-fixes
complexity: null
role: null
stack: null
tier: moderate
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-01T01:02:26Z"
---

## Goal

Release 1.4 readiness: r14-senar-context-hygiene

## Acceptance Criteria

1. New PreToolUse hook scripts/hooks/secret_scan.py scans Write/Edit/MultiEdit tool_input for AWS/GitHub/Slack/Stripe/OpenAI/Anthropic tokens, JWT, private-key blocks. 2. Warning by default, TAUSIK_SECRET_SCAN_STRICT=1 blocks (exit 2). 3. Wired into bootstrap_generate.py and bootstrap_qwen.py PreToolUse Write/Edit/MultiEdit. 4. docs/{en,ru}/hooks.md document the new hook and bumped count 17->18. 5. Negative scenario: legitimate code without secrets passes silently (no false positive); skipped via TAUSIK_SKIP_HOOKS=1; non-Write tools (Read/Bash) are ignored.

## Plan

## Rollback

## Journal

- 2026-05-01T01:02:26Z [implementation] — AC verified: 1. secret_scan.py exists ✓. 2. Warn by default, strict via env var ✓ (test_strict_mode_blocks). 3. Bootstrap configs include the hook in claude+qwen ✓ (parity test). 4. Docs mention v1.4 row + count 18 ✓. 5. Negative - clean payload silent ✓ (test_clean_payload_passes), skip-hooks short-circuit ✓, non-Write ignored ✓.
- 2026-05-01T01:02:26Z [implementation] — Created scripts/hooks/secret_scan.py with 11 regex patterns covering AWS access/secret keys, GitHub PAT/OAuth, Slack tokens, Stripe live/test keys, OpenAI/Anthropic keys, Notion secrets, generic private-key blocks, JWT tokens, and broad password/api_key/token literal assignments. Walks dict/list/string fields up to 50 KB.
- 2026-05-01T01:02:26Z [implementation] — Tests: tests/test_secret_scan_hook.py (6 cases) covers clean payload, AWS warn, OpenAI strict block, TAUSIK_SKIP_HOOKS, non-Write tool ignored, RSA private-key block. 9/9 pass with parity test. Hook count updated in docs/{en,ru}/hooks.md mirror to .claude.
- 2026-05-01T01:02:26Z [implementation] — Wired into both Claude (bootstrap_generate.py) and Qwen (bootstrap_qwen.py) PreToolUse with matcher Write|Edit|MultiEdit, timeout 5s. Updated test_bootstrap_hooks_parity required-set so future regressions on either side are caught.
