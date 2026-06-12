"""Tests for scripts/receipt_export.py — portable receipt artifacts.

AC coverage (v15-receipt-export): self-contained build/write, offline
verify via embedded key (no DB), tamper -> invalid, garbage -> ExportError,
embedded fingerprint consistency.
"""

from __future__ import annotations

import json
import os
import sys

import pytest

_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

import crypto_keys  # noqa: E402
import crypto_sign  # noqa: E402
from crypto_receipt import build_receipt  # noqa: E402
from receipt_export import (  # noqa: E402
    EXPORT_SCHEMA,
    ExportError,
    build_export,
    default_export_path,
    verify_export,
    write_export,
)


@pytest.fixture
def keyed_project(tmp_path):
    crypto_keys.init_keys(str(tmp_path))
    return str(tmp_path)


def _envelope(project_dir, slug="task-a", git_sha="a" * 40):
    receipt = build_receipt(
        task_slug=slug,
        git_sha=git_sha,
        scope="standard",
        gates=[{"name": "pytest", "passed": True, "severity": "block"}],
        passed=True,
        ran_at="2026-06-12T00:00:00Z",
    )
    return crypto_sign.sign_receipt(project_dir, receipt)


class TestBuildAndWrite:
    def test_export_is_self_contained_and_valid(self, keyed_project):
        env = _envelope(keyed_project)
        public = crypto_keys.load_public(keyed_project)
        export = build_export(env, public)
        assert export["export"] == EXPORT_SCHEMA
        assert export["public_key"] == f"ed25519:{public.hex()}"
        assert export["key_fingerprint"] == env["signature"]["key_fingerprint"]
        valid, detail = verify_export(export)  # embedded key only — no keystore
        assert valid is True and "VALID" in detail

    def test_roundtrip_through_file(self, keyed_project, tmp_path):
        env = _envelope(keyed_project)
        export = build_export(env, crypto_keys.load_public(keyed_project))
        path = write_export(export, str(tmp_path / "out" / "r.json"))
        data = json.loads(open(path, encoding="utf-8").read())
        valid, _ = verify_export(data)
        assert valid is True

    def test_default_path_shape(self, keyed_project):
        env = _envelope(keyed_project, slug="task/a b", git_sha="f" * 40)
        p = default_export_path(keyed_project, env)
        assert p.endswith(os.path.join(".tausik", "receipts", "task-a-b-ffffffff.json"))

    def test_default_path_without_git_sha(self, keyed_project):
        env = _envelope(keyed_project, git_sha=None)
        assert default_export_path(keyed_project, env).endswith("task-a-nogit.json")

    def test_build_rejects_non_envelope(self, keyed_project):
        with pytest.raises(ExportError, match="envelope"):
            build_export({"foo": 1}, crypto_keys.load_public(keyed_project))


class TestVerify:
    def test_tampered_receipt_invalid_exit1_path(self, keyed_project):
        env = _envelope(keyed_project)
        export = build_export(env, crypto_keys.load_public(keyed_project))
        export["envelope"]["receipt"]["passed"] = False
        valid, detail = verify_export(export)
        assert valid is False and "INVALID" in detail

    def test_swapped_embedded_key_invalid(self, keyed_project, tmp_path_factory):
        # Attacker re-embeds their own key but keeps the original signature
        other = str(tmp_path_factory.mktemp("other"))
        crypto_keys.init_keys(other)
        env = _envelope(keyed_project)
        export = build_export(env, crypto_keys.load_public(other))
        valid, _ = verify_export(export)
        assert valid is False

    def test_explicit_pub_overrides_embedded(self, keyed_project, tmp_path_factory):
        # Verifier's out-of-band key catches the swapped-envelope trick
        other = str(tmp_path_factory.mktemp("other"))
        crypto_keys.init_keys(other)
        env_other = _envelope(other)
        export = build_export(env_other, crypto_keys.load_public(other))
        valid, _ = verify_export(export)  # self-consistent forge: valid
        assert valid is True
        valid, _ = verify_export(export, public=crypto_keys.load_public(keyed_project))
        assert valid is False  # but not against OUR out-of-band key

    @pytest.mark.parametrize(
        "garbage",
        [
            {"export": "wrong/v9"},
            {"export": EXPORT_SCHEMA},  # no envelope
            {"export": EXPORT_SCHEMA, "envelope": {"receipt": {}}},  # no key
            {"export": EXPORT_SCHEMA, "envelope": {}, "public_key": "ed25519:zz"},
            {"export": EXPORT_SCHEMA, "envelope": {}, "public_key": "ed25519:aabb"},
            "not a dict",
        ],
    )
    def test_garbage_raises_export_error(self, garbage):
        with pytest.raises(ExportError):
            verify_export(garbage)
