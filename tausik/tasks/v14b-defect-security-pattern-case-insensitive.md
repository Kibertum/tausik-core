---
slug: v14b-defect-security-pattern-case-insensitive
title: "C1: is_security_sensitive case-sensitive — bypassed by PascalCase auth dirs and uppercase credential extensions"
status: done
epic: v14-polish-quality
story: v14-polish-b-quality
complexity: simple
role: developer
stack: python
tier: light
call_budget: 15
defect_of: null
scope: "scripts/security_pattern.py, tests/test_security_sensitive.py"
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-03T21:44:37Z"
---

## Goal

Lowercase-normalize all three signals in is_security_sensitive (path tokens, basenames, extensions) so that PascalCase dirs (OAuth/, Payments/, Auth.py) and uppercase credential extensions (keys.PEM, id_rsa.KEY) are correctly classified as security-sensitive, restoring the verify_cache stale-green protection contract.

## Acceptance Criteria

1. is_security_sensitive(["src/OAuth/handler.py"]) returns True. 2. is_security_sensitive(["src/Payments/api.py"]) returns True. 3. is_security_sensitive(["Auth.py"]) returns True. 4. is_security_sensitive(["keys.PEM"]) returns True. 5. is_security_sensitive(["id_rsa.KEY"]) returns True. 6. NEGATIVE: is_security_sensitive(["src/Components/Button.tsx"]) returns False (PascalCase non-security paths are NOT misclassified). 7. NEGATIVE: is_security_sensitive([]) returns False (empty input handled). 8. NEGATIVE: is_security_sensitive(["scripts/hooks/session_start.py"]) returns False (TAUSIK harness regression guard from v14b-defect-qg2 still holds). 9. Existing lowercase tests still pass. 10. New PascalCase + uppercase-extension cases added to tests/test_security_sensitive.py. 11. pytest tests/test_security_sensitive.py PASS. 12. tausik verify --task &lt;slug&gt; PASS.

## Plan

## Rollback

## Journal

- 2026-05-03T21:43:41Z [implementation] — Fix applied: norm = "/" + raw.replace("\\", "/").lstrip("/").lower(). All three signals (path tokens, basenames, extensions) now match against the lowercased path. Token/basename/ext sets are already lowercase. Case-insensitive on Windows/macOS aligns with FS semantics.
- 2026-05-03T21:44:16Z [implementation] — AC verified: 1.✓ OAuth/handler.py → True. 2.✓ Payments/api.py → True. 3.✓ Auth.py → True. 4.✓ keys.PEM → True. 5.✓ id_rsa.KEY → True. 6.✓ Components/Button.tsx → False (negative). 7.✓ empty list → False. 8.✓ scripts/hooks/session_start.py → False (regression guard). 9.✓ all existing lowercase tests pass. 10.✓ TestCaseInsensitivity class added (4 parametrized groups). 11.✓ pytest 93/93 PASS in 0.27s. 12.✓ tausik verify passed=True (gate=pytest, scope=task-files).</evidence> <parameter name="relevant_files">["scripts/security_pattern.py", "tests/test_security_sensitive.py"]
