"""Security-sensitive path classifier — directory-anchored, no bare substrings.

Extracted from service_verification.py for filesize compliance
(v14b-filesize-debt-paydown). Public surface:

    _SECURITY_PATH_TOKENS  — directory-anchored auth surface tokens
    _SECURITY_BASENAMES    — exact filename auth-surface matches
    _SECURITY_EXTENSIONS   — credential-bearing extensions
    is_security_sensitive(file_paths) -> bool

Behaviour follows the v14b-defect-qg2-security-substring-too-broad contract:
no bare substrings, only directory-anchored path tokens (must start AND end
with `/`), exact basename match, or extension match. Hooks dir, hook tests,
SKILL.md / README.md / CHANGELOG.md are explicitly NOT security-sensitive.
"""

from __future__ import annotations

import os


# Directory-anchored security path tokens. Each MUST start AND end with `/` —
# bare substrings false-positive on TAUSIK infra (scripts/hooks/session_start.py,
# tests/test_session_start_hook.py) and force is_cache_allowed=False, which
# blocks the verify-first cache for non-auth code (the v14b-defect-qg2 incident).
_SECURITY_PATH_TOKENS = tuple(
    f"/{seg}/"
    for seg in (
        "auth payment payments billing oauth sso saml crypto secrets keys admin "
        "iam permissions webhook webhooks csrf xsrf rbac acl jwt mfa totp 2fa "
        "login signup session sessions password passwords"
    ).split()
)
_SEC_BASE = (
    "auth payment billing secret secrets credentials jwt session login signup "
    "login_handler session_handler session_manager session_store session_token "
    "signup_handler password webhook webhooks csrf xsrf totp permissions acl rbac iam "
    "api_key apikey oauth_callback oauth_handler"
).split()
_SEC_EXT = (".py", ".ts", ".tsx", ".js", ".go", ".rs", ".php")
_SECURITY_BASENAMES = frozenset(
    {f"{b}{e}" for b in _SEC_BASE for e in _SEC_EXT}
    | {"secrets.json", "credentials.json", ".npmrc", "id_rsa", "id_ed25519"}
)

_SECURITY_EXTENSIONS = frozenset({".env", ".pem", ".key", ".p12", ".pfx", ".crt", ".asc", ".gpg"})


def is_security_sensitive(file_paths: list[str]) -> bool:
    """True iff any path matches a security-sensitive segment, basename, or ext.

    Three orthogonal signals (any one triggers True):
    1. Path tokens — directory-anchored only (must start AND end with `/`),
       e.g. `/auth/`, `/oauth/`, `/payment/`. Bare substrings ("session",
       "login", "scripts/hooks/") are NOT used — they previously matched
       hook tests and TAUSIK harness infra (see
       v14b-defect-qg2-security-substring-too-broad). Hooks/tests/docs are
       explicitly NOT security-sensitive.
    2. Basenames — exact filename matches (`auth.py`, `secrets.json`).
    3. Extensions — credential-bearing suffixes (`.env`, `.pem`, `.key`).

    Stale greens for security paths are more expensive than redundant gates,
    so verify cache refuses to satisfy task_done for them.
    """
    for raw in file_paths or []:
        if not raw or not isinstance(raw, str):
            continue
        # Case-insensitive: PascalCase dirs (OAuth/, Payments/, Auth.py) and
        # uppercase credential extensions (keys.PEM, id_rsa.KEY) must match.
        # On Windows/macOS the filesystem is case-insensitive anyway.
        norm = "/" + raw.replace("\\", "/").lstrip("/").lower()
        if any(tok in norm for tok in _SECURITY_PATH_TOKENS):
            return True
        basename = os.path.basename(norm)
        if basename in _SECURITY_BASENAMES:
            return True
        for ext in _SECURITY_EXTENSIONS:
            if basename.endswith(ext):
                return True
    return False
