---
slug: review-fix-a4-security-bypass-tokens
title: "[A4 HIGH] Расширить _SECURITY_PATH_TOKENS + basename matching"
status: done
epic: senar-verify-redesign
story: review-findings-fix
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/service_verification.py, tests/test_service_verification.py"
scope_exclude: "scripts/service_gates.py"
relevant_files:
  - "scripts/service_verification.py"
  - "tests/test_service_verification.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-25T10:16:45Z"
---

## Goal

Multi-agent review: is_security_sensitive в service_verification.py:25-31 имеет дыры. Текущий список: scripts/hooks/, /auth/, /payment/, /payments/, /billing/. Не покрывает: auth.py/payment.py/billing.py в корне (нет окружающих /), /oauth/, /sso/, /saml/, /crypto/, /secrets/, /keys/, /admin/, /rbac/, /webhook/, /jwt/, /token/, /session/, /password/, /2fa/, /mfa/, .env, *.pem, *.key, credentials*. Нужно: расширить tokens + добавить basename allowlist для root-level *.py с security-семантикой.

## Acceptance Criteria

1. _SECURITY_PATH_TOKENS расширен: добавлены /oauth/, /sso/, /saml/, /crypto/, /secrets/, /keys/, /admin/, /rbac/, /webhook/, /jwt/, /session/, /password (без /), /2fa/, /mfa/, /signup/, /login/
2. Новый _SECURITY_BASENAME_PATTERNS — regex или set для root-level basename detection: auth.py, payment.py, billing.py, secret.py, secrets.py, credentials.py, jwt.py, session.py, login.py, signup.py, password.py
3. Новый _SECURITY_FILE_EXTENSIONS — {.env, .pem, .key, .p12, .pfx} → security-sensitive
4. is_security_sensitive объединяет path-token + basename + extension checks
5. Регрессия: existing positive cases (scripts/hooks/*, /auth/*, /payment/*, /payments/*, /billing/*) всё ещё True
6. Регрессия: existing negative cases (scripts/brain_init.py, src/profile/page.tsx, scripts/hooksomething.py) всё ещё False
7. Новые positive: auth.py, payment.py, .env, foo.pem, oauth/handler.py, secrets/key.txt
8. Ошибка/граничный случай: пустой path/None safe (False)
9. Ошибка/граничный случай: пустые file_paths list → False
10. is_cache_allowed автоматически расширяется (использует is_security_sensitive)
11. pytest зелёный, ruff clean

## Plan

## Rollback

## Journal

- 2026-04-25T10:16:38Z [implementation] — AC verified: ✓1 _SECURITY_PATH_TOKENS расширен +16: oauth/sso/saml/crypto/secrets/keys/admin/rbac/webhook/jwt/session/2fa/mfa/signup/login/password ✓2 _SECURITY_BASENAMES frozenset для root-level *.py/.ts/.go (auth/payment/billing/secret/secrets/credentials/jwt/session/login/signup/password) ✓3 _SECURITY_EXTENSIONS frozenset (.env/.pem/.key/.p12/.pfx/.crt/.asc/.gpg) ✓4 is_security_sensitive объединяет 3 проверки в одном loop: token + basename + extension ✓5 регрессия: 5 existing positive cases (hooks/auth/payment/payments/billing) PASS ✓6 регрессия: 4 existing negative cases PASS ✓7 16 новых positive path-tokens + 9 новых basenames + 10 extensions ✓8 empty/None safe ✓9 empty list False ✓10 is_cache_allowed автомат через is_security_sensitive ✓11 pytest 71/71, ruff clean
