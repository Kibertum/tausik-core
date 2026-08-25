---
slug: extend-security-token-list
title: "Add webhook/oauth/csrf/mfa/api_key etc to security tokens"
status: done
epic: v131-blind-review-fixes
story: security-high
complexity: simple
role: developer
stack: python
tier: trivial
call_budget: 10
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/service_verification.py"
  - "tests/test_v131_blind_review.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-27T12:04:15Z"
---

## Goal

_SECURITY_PATH_TOKENS misses common security file basenames. Add: webhook, oauth, csrf, xsrf, mfa, 2fa, totp, api_key, apikey, permissions, acl, rbac, iam. Closes HIGH (QG).

## Acceptance Criteria

1. _SECURITY_PATH_TOKENS extended with: webhook, oauth, csrf, xsrf, mfa, 2fa, totp, api_key, apikey, permissions, acl, rbac, iam; 2. Tests cover: webhook.py, oauth_callback.py, csrf.py recognized as security-sensitive; 3. Negative: editing webhook.py no longer hits cache, always re-verifies.

## Plan

## Rollback

## Journal

- 2026-04-27T12:02:59Z [implementation] — AC: 1.✓ _SECURITY_PATH_TOKENS extended with bare tokens (webhook, csrf, xsrf, mfa, 2fa, totp, api_key, apikey, acl, jwt, oauth) + new path tokens (/iam/, /permissions/); 2.✓ _SECURITY_BASENAMES extended with webhook.py, csrf.py, totp.py, permissions.py, etc; 3.✓ test asserts 8 paths recognised (webhook/csrf/totp/api_key/permissions/iam/oauth_callback/xsrf); 4.✓ Negative — webhook.py at any depth (scripts/webhook.py, lib/xsrf.py) hits cache bypass.
- 2026-04-27T12:04:14Z [implementation] — AC: 1.✓ _SECURITY_PATH_TOKENS extended (csrf/xsrf/totp/api_key/apikey/acl/iam/permissions); 2.✓ _SECURITY_BASENAMES generated cross-product, covers webhook.py, csrf.py, totp.py, etc; 3.✓ test asserts 8 paths recognised; 4.✓ filesize gate now passes (358 lines &lt; 400); 5.✓ Negative — webhook.py at root no longer hits cache.
