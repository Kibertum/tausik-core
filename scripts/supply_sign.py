"""Supply-chain signing for skill/stack release artifacts (v15-supplychain-sign-release).

A release artifact is a directory (a skill, a stack). Signing builds a
deterministic integrity manifest — sorted relative paths with sha256 and
size — signs it with the project ed25519 key (same key as receipts,
story v15-crypto-foundation) and drops the tausik-signed/v1 envelope as
`.tausik-signature.json` INSIDE the directory, so it travels with the
artifact through git clones and copies.

Verification recomputes the manifest and compares it against the signed
one before checking the signature, so any added / removed / modified
file is named explicitly. Install-time enforcement lands in
v15-supplychain-verify-install.
"""

from __future__ import annotations

import hashlib
import json
import os
from typing import Any

MANIFEST_SCHEMA = "tausik-skill-sig/v1"
SIGNATURE_FILENAME = ".tausik-signature.json"
_EXCLUDED_DIRS = {".git", "__pycache__", ".mypy_cache", ".ruff_cache"}


class SupplySignError(Exception):
    """Signing/manifest construction failure (not a bad signature)."""


def _iter_files(artifact_dir: str) -> list[str]:
    """Sorted '/'-relative paths, excluding VCS noise and the signature itself."""
    out: list[str] = []
    for root, dirs, files in os.walk(artifact_dir):
        dirs[:] = [d for d in dirs if d not in _EXCLUDED_DIRS]
        for f in files:
            rel = os.path.relpath(os.path.join(root, f), artifact_dir).replace("\\", "/")
            if rel == SIGNATURE_FILENAME:
                continue
            out.append(rel)
    return sorted(out)


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def build_artifact_manifest(artifact_dir: str, *, name: str | None = None) -> dict[str, Any]:
    """Deterministic manifest of a release directory."""
    if not os.path.isdir(artifact_dir):
        raise SupplySignError(f"not a directory: {artifact_dir}")
    rels = _iter_files(artifact_dir)
    if not rels:
        raise SupplySignError(f"nothing to sign: {artifact_dir} has no files")
    files = [
        {
            "path": rel,
            "sha256": _sha256(os.path.join(artifact_dir, rel)),
            "size": os.path.getsize(os.path.join(artifact_dir, rel)),
        }
        for rel in rels
    ]
    return {
        "schema": MANIFEST_SCHEMA,
        "name": name or os.path.basename(os.path.normpath(artifact_dir)),
        "files": files,
    }


def sign_artifact(
    project_dir: str, artifact_dir: str, *, name: str | None = None
) -> dict[str, Any]:
    """Sign a release directory; writes SIGNATURE_FILENAME inside it.

    Returns {"path", "name", "files", "key_fingerprint"}. Raises
    SupplySignError (no key / empty dir / not canonicalizable).
    """
    import crypto_keys
    from crypto_receipt import ReceiptError
    from crypto_sign import SignError, sign_receipt

    manifest = build_artifact_manifest(artifact_dir, name=name)
    try:
        envelope = sign_receipt(project_dir, manifest)
    except (SignError, ReceiptError) as e:
        raise SupplySignError(str(e)) from e
    sig_path = os.path.join(artifact_dir, SIGNATURE_FILENAME)
    with open(sig_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(envelope, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")
    try:
        fp = crypto_keys.fingerprint(crypto_keys.load_public(project_dir))
    except crypto_keys.KeyError_:  # pragma: no cover — sign above already loaded it
        fp = "?"
    return {
        "path": sig_path,
        "name": manifest["name"],
        "files": len(manifest["files"]),
        "key_fingerprint": fp,
    }


def verify_signed_dir(artifact_dir: str, public: bytes) -> tuple[bool, str]:
    """(valid, detail) — recompute manifest, diff against signed, check ed25519.

    Never raises on artifact content; a missing/corrupt signature file or
    schema mismatch returns (False, reason).
    """
    import crypto_sign

    sig_path = os.path.join(artifact_dir, SIGNATURE_FILENAME)
    if not os.path.isfile(sig_path):
        return False, f"no {SIGNATURE_FILENAME} in {artifact_dir} (unsigned artifact)"
    try:
        with open(sig_path, encoding="utf-8") as f:
            envelope = json.load(f)
    except (OSError, ValueError) as e:
        return False, f"corrupt signature file: {e}"
    if not isinstance(envelope, dict):
        return False, "corrupt signature file: not a JSON object"

    signed = envelope.get("receipt")
    if not isinstance(signed, dict) or signed.get("schema") != MANIFEST_SCHEMA:
        return False, f"signature payload is not {MANIFEST_SCHEMA}"
    if not crypto_sign.verify_receipt(envelope, public=public):
        return False, "INVALID ed25519 signature — manifest was modified after signing"

    signed_files = {
        f["path"]: f["sha256"]
        for f in signed.get("files") or []
        if isinstance(f, dict) and isinstance(f.get("path"), str)
    }
    try:
        current = build_artifact_manifest(artifact_dir, name=str(signed.get("name") or ""))
    except SupplySignError as e:
        return False, str(e)
    current_files = {f["path"]: f["sha256"] for f in current["files"]}

    added = sorted(set(current_files) - set(signed_files))
    removed = sorted(set(signed_files) - set(current_files))
    changed = sorted(
        p for p in set(current_files) & set(signed_files) if current_files[p] != signed_files[p]
    )
    if added or removed or changed:
        parts = []
        if changed:
            parts.append(f"modified: {', '.join(changed[:5])}")
        if added:
            parts.append(f"added: {', '.join(added[:5])}")
        if removed:
            parts.append(f"removed: {', '.join(removed[:5])}")
        return False, "artifact differs from signed manifest — " + "; ".join(parts)
    fp = (envelope.get("signature") or {}).get("key_fingerprint", "?")
    return True, f"VALID — {len(current_files)} files match signed manifest (key {fp})"
