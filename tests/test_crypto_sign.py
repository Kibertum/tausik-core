"""v15-crypto-sign-verify-lib: envelope sign/verify over canonical bytes."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import crypto_keys  # noqa: E402
from crypto_receipt import build_receipt  # noqa: E402
from crypto_sign import (  # noqa: E402
    ENVELOPE_SCHEMA,
    SignError,
    sign_receipt,
    verify_receipt,
)


@pytest.fixture()
def project(tmp_path):
    crypto_keys.init_keys(str(tmp_path))
    return str(tmp_path)


def _receipt(slug="my-task"):
    return build_receipt(
        task_slug=slug,
        git_sha="a" * 40,
        scope="standard",
        gates=[{"name": "pytest", "passed": True, "severity": "block"}],
        passed=True,
        ran_at="2026-06-12T00:00:00Z",
    )


def test_sign_then_verify_roundtrip(project):
    env = sign_receipt(project, _receipt())
    assert env["envelope"] == ENVELOPE_SCHEMA
    assert env["signature"]["algorithm"] == "ed25519"
    assert verify_receipt(env, project_dir=project)


def test_verify_with_explicit_public(project):
    env = sign_receipt(project, _receipt())
    public = crypto_keys.load_public(project)
    assert verify_receipt(env, public=public)


def test_fingerprint_matches_keystore(project):
    env = sign_receipt(project, _receipt())
    info = crypto_keys.key_info(project)
    assert env["signature"]["key_fingerprint"] == info["fingerprint"]


def test_tampered_receipt_fails(project):
    env = sign_receipt(project, _receipt())
    env["receipt"]["passed"] = False
    assert not verify_receipt(env, project_dir=project)


def test_tampered_nested_gate_fails(project):
    env = sign_receipt(project, _receipt())
    env["receipt"]["gates"][0]["passed"] = False
    assert not verify_receipt(env, project_dir=project)


def test_corrupt_signature_fails(project):
    env = sign_receipt(project, _receipt())
    sig = env["signature"]["value"]
    env["signature"]["value"] = ("0" if sig[0] != "0" else "1") + sig[1:]
    assert not verify_receipt(env, project_dir=project)


def test_foreign_key_fails(project, tmp_path_factory):
    other = tmp_path_factory.mktemp("other-project")
    crypto_keys.init_keys(str(other))
    env = sign_receipt(project, _receipt())
    assert not verify_receipt(env, project_dir=str(other))


def test_sign_without_key_raises(tmp_path):
    with pytest.raises(SignError, match="key init"):
        sign_receipt(str(tmp_path), _receipt())


def test_verify_without_key_source_raises(project):
    env = sign_receipt(project, _receipt())
    with pytest.raises(SignError, match="public=|project_dir"):
        verify_receipt(env)


def test_malformed_envelopes_return_false(project):
    public = crypto_keys.load_public(project)
    good = sign_receipt(project, _receipt())
    assert not verify_receipt({}, public=public)
    assert not verify_receipt({"envelope": "junk"}, public=public)
    assert not verify_receipt(
        {**good, "signature": {"algorithm": "rsa", "value": "00"}}, public=public
    )
    assert not verify_receipt(
        {**good, "signature": {**good["signature"], "value": "not-hex"}},
        public=public,
    )
    assert not verify_receipt({**good, "receipt": "not-a-dict"}, public=public)


def test_uncanonicalizable_receipt_raises_on_sign(project):
    bad = _receipt()
    bad["duration"] = 1.5
    with pytest.raises(SignError, match="canonicalizable"):
        sign_receipt(project, bad)
