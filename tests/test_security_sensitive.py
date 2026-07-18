"""Tests for is_security_sensitive — guards QG-2 verify-first cache integrity.

Background: v14b-defect-qg2-security-substring-too-broad. The earlier
implementation matched bare substrings ("session", "login", "scripts/hooks/")
which false-positive on TAUSIK's own infra files (hook scripts, hook tests).
That made `is_cache_allowed` return False for non-auth changes, so every fresh
`tausik verify` run for hook-touching tasks was rejected by `task_done` with
"no fresh verify run". This module pins the contract: only true auth surface
triggers, hooks/docs/test infra do not.
"""

from __future__ import annotations

import os
import sqlite3
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from service_verification import (  # noqa: E402
    _build_cache_command,
    has_fresh_verify_run,
    is_cache_allowed,
    is_security_sensitive,
    record_run,
)
from verify_files_hash import compute_files_hash  # noqa: E402


class TestPositiveCases:
    """Real auth surface — must keep returning True after the fix."""

    @pytest.mark.parametrize(
        "path",
        [
            "scripts/auth/login.py",
            "src/payment/billing.py",
            "src/oauth/callback.py",
            "backend/sso/handler.go",
            "app/iam/role.ts",
            "services/admin/dashboard.tsx",
            "src/secrets/loader.py",
            "lib/keys/store.rs",
            "infra/saml/parser.py",
            "src/billing/invoice.php",
            "src/permissions/check.js",
            "src/webhook/receiver.py",
            "src/webhooks/queue.py",
            "src/csrf/middleware.py",
            "src/xsrf/token.py",
            "src/rbac/role.py",
            "src/acl/check.py",
            "src/jwt/validator.py",
            "src/mfa/challenge.py",
            "src/totp/generator.py",
        ],
    )
    def test_path_token_match(self, path):
        assert is_security_sensitive([path]) is True

    @pytest.mark.parametrize(
        "path",
        [
            "auth.py",
            "login_handler.ts",
            "session_token.py",
            "session_handler.go",
            "session_manager.py",
            "session_store.rs",
            "secrets.json",
            "credentials.json",
            ".npmrc",
            "id_rsa",
            "id_ed25519",
            "billing.py",
            "webhook.py",
            "deeply/nested/path/payment.py",
        ],
    )
    def test_basename_match(self, path):
        assert is_security_sensitive([path]) is True

    @pytest.mark.parametrize(
        "path",
        [
            ".env",
            "production.env",
            "deploy.pem",
            "private.key",
            "client.p12",
            "cert.pfx",
            "ca.crt",
            "release.asc",
            "signature.gpg",
        ],
    )
    def test_extension_match(self, path):
        assert is_security_sensitive([path]) is True


class TestFalsePositiveElimination:
    """The defect — these MUST stop returning True after the fix.

    Each case below was true-by-mistake under the old substring matcher,
    causing v14b-rag-first-nudges close to fail with "no fresh verify run".
    """

    @pytest.mark.parametrize(
        "path",
        [
            "scripts/hooks/session_start.py",
            "scripts/hooks/keyword_detector.py",
            "scripts/hooks/posttool_usage.py",
            "scripts/hooks/auto_format.py",
            "scripts/hooks/memory_markers.py",
            "scripts/hooks/_common.py",
            ".claude/hooks/session_start.py",
        ],
    )
    def test_tausik_hooks_are_infra_not_auth(self, path):
        assert is_security_sensitive([path]) is False

    @pytest.mark.parametrize(
        "path",
        [
            "tests/test_session_start_hook.py",
            "tests/test_session_metrics.py",
            "tests/test_keyword_detector_hook.py",
            "tests/test_user_prompt_submit_hook.py",
        ],
    )
    def test_hook_tests_are_not_auth_surface(self, path):
        assert is_security_sensitive([path]) is False

    @pytest.mark.parametrize(
        "path",
        [
            "harness/skills/start/SKILL.md",
            "README.md",
            "CHANGELOG.md",
            "docs/en/architecture.md",
            "docs/ru/quickstart.md",
        ],
    )
    def test_docs_not_security_sensitive(self, path):
        assert is_security_sensitive([path]) is False

    @pytest.mark.parametrize(
        "path",
        [
            "src/utils/login_form_label.ts",
            "src/components/UserSignupBanner.tsx",
            "session_id_test_data.txt",
        ],
    )
    def test_bare_substrings_no_longer_trigger(self, path):
        """These contain auth-adjacent words but live outside auth surface."""
        assert is_security_sensitive([path]) is False


class TestBoundaryInputs:
    """No crashes on degenerate input."""

    def test_empty_list(self):
        assert is_security_sensitive([]) is False

    def test_none_argument(self):
        assert is_security_sensitive(None) is False  # type: ignore[arg-type]

    def test_list_with_empty_strings(self):
        assert is_security_sensitive(["", "  "]) is False

    def test_list_with_none_entry(self):
        assert is_security_sensitive([None, "scripts/hooks/foo.py"]) is False  # type: ignore[list-item]

    def test_unknown_extension_not_classified(self):
        assert is_security_sensitive(["data.unknownext"]) is False

    def test_mixed_separators(self):
        assert is_security_sensitive(["scripts\\auth\\login.py"]) is True
        assert is_security_sensitive(["scripts\\hooks\\session_start.py"]) is False


class TestCaseInsensitivity:
    """v14b-defect-security-pattern-case-insensitive — PascalCase auth dirs and
    uppercase credential extensions must match. Filesystem on Windows/macOS is
    case-insensitive, so `keys.PEM` and `keys.pem` are the same file.
    """

    @pytest.mark.parametrize(
        "path",
        [
            "src/OAuth/handler.py",
            "src/Payments/api.py",
            "src/Auth/middleware.ts",
            "backend/SSO/handler.go",
            "app/IAM/role.ts",
            "src/RBAC/role.py",
            "src/JWT/validator.py",
            "src/Webhook/receiver.py",
            "src/Sessions/store.py",
        ],
    )
    def test_pascalcase_path_tokens_match(self, path):
        assert is_security_sensitive([path]) is True

    @pytest.mark.parametrize(
        "path",
        [
            "Auth.py",
            "Login_Handler.ts",
            "Session_Token.py",
            "Secrets.json",
            "Credentials.json",
        ],
    )
    def test_uppercase_basenames_match(self, path):
        assert is_security_sensitive([path]) is True

    @pytest.mark.parametrize(
        "path",
        [
            "keys.PEM",
            "id_rsa.KEY",
            "client.P12",
            "cert.PFX",
            "ca.CRT",
            "production.ENV",
        ],
    )
    def test_uppercase_extensions_match(self, path):
        assert is_security_sensitive([path]) is True

    @pytest.mark.parametrize(
        "path",
        [
            "src/Components/Button.tsx",
            "src/Pages/Home.tsx",
            "lib/Utils/Helpers.ts",
            "components/Header.tsx",
        ],
    )
    def test_pascalcase_non_security_paths_not_misclassified(self, path):
        """Negative: lowercasing must not turn unrelated PascalCase paths
        into auth surface."""
        assert is_security_sensitive([path]) is False


class TestVerifyFirstRegression:
    """The exact failure mode that blocked v14b-rag-first-nudges close.

    With the fix in place: a fresh green verify run scoped to a hook file
    must be visible to has_fresh_verify_run (cache_allowed=True now).
    """

    @pytest.fixture
    def conn(self, tmp_path):
        db = tmp_path / "verify.db"
        c = sqlite3.connect(str(db))
        c.row_factory = sqlite3.Row
        c.execute(
            """
            CREATE TABLE verification_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_slug TEXT,
                scope TEXT NOT NULL,
                command TEXT NOT NULL,
                exit_code INTEGER NOT NULL,
                summary TEXT,
                files_hash TEXT NOT NULL,
                ran_at TEXT NOT NULL,
                duration_ms INTEGER,
                declared_scope_status TEXT, undeclared_files TEXT
            )
            """
        )
        return c

    def test_hook_file_cache_now_lookups(self, conn, tmp_path):
        """Reproduces v14b-rag-first-nudges close failure — must now pass."""
        hook_file = tmp_path / "posttool_usage.py"
        hook_file.write_text("# hook\n", encoding="utf-8")
        relevant_files = [str(hook_file)]
        assert is_cache_allowed(relevant_files), (
            "hook files must be cache-allowed after fix; "
            "before fix is_cache_allowed=False blocked task_done"
        )
        record_run(
            conn,
            task_slug="t-defect-regression",
            scope="manual",
            command=_build_cache_command("verify", relevant_files),
            exit_code=0,
            summary="pytest pass",
            files_hash=compute_files_hash(relevant_files),
            duration_ms=100,
        )
        fresh, hit = has_fresh_verify_run(conn, "t-defect-regression", relevant_files)
        assert fresh is True, "fresh verify run on hook file must satisfy verify-first"
        assert hit is not None
        assert hit["files_hash"] == compute_files_hash(relevant_files)
