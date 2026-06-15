"""Project key management — ed25519 keypair under .tausik/keys/.

v15-crypto-keymgmt: foundation for signed receipts / scope / releases.
Private seed never leaves .tausik/ (the directory is gitignored by design);
the public key is exported via `tausik key show` for out-of-band
verification.

File format (algorithm-agility prefix):
    .tausik/keys/project.key  ->  "ed25519:<64 hex chars>"  (32-byte seed)
    .tausik/keys/project.pub  ->  "ed25519:<64 hex chars>"  (32-byte public)
"""

from __future__ import annotations

import hashlib
import os
import stat

import crypto_ed25519 as ed25519

_ALGO = "ed25519"
KEY_FILENAME = "project.key"
PUB_FILENAME = "project.pub"


class KeyError_(Exception):
    """Key management failure (init conflict, missing/corrupt key files)."""


def keys_dir(project_dir: str) -> str:
    return os.path.join(project_dir, ".tausik", "keys")


def _key_path(project_dir: str) -> str:
    return os.path.join(keys_dir(project_dir), KEY_FILENAME)


def _pub_path(project_dir: str) -> str:
    return os.path.join(keys_dir(project_dir), PUB_FILENAME)


def _encode(raw: bytes) -> str:
    return f"{_ALGO}:{raw.hex()}"


def _decode(text: str, *, expect_len: int) -> bytes:
    text = text.strip()
    if ":" not in text:
        raise KeyError_("key file is missing the algorithm prefix")
    algo, hexpart = text.split(":", 1)
    if algo != _ALGO:
        raise KeyError_(f"unsupported key algorithm {algo!r} (expected {_ALGO})")
    try:
        raw = bytes.fromhex(hexpart)
    except ValueError as e:
        raise KeyError_(f"corrupt key file: {e}") from e
    if len(raw) != expect_len:
        raise KeyError_(f"corrupt key file: expected {expect_len} bytes, got {len(raw)}")
    return raw


def fingerprint(public: bytes) -> str:
    """Short stable id of the public key: first 16 hex of sha256."""
    return hashlib.sha256(public).hexdigest()[:16]


def init_keys(project_dir: str, *, force: bool = False) -> dict[str, str]:
    """Generate the project ed25519 keypair. Refuses to overwrite sans force."""
    key_path = _key_path(project_dir)
    if os.path.exists(key_path) and not force:
        raise KeyError_(
            f"project key already exists at {key_path} — rerun with --force to "
            "replace it (existing signatures will no longer verify)"
        )
    os.makedirs(keys_dir(project_dir), exist_ok=True)
    seed = ed25519.generate_seed()
    public = ed25519.public_from_seed(seed)

    with open(key_path, "w", encoding="ascii") as f:
        f.write(_encode(seed) + "\n")
    try:  # best-effort owner-only on POSIX; no-op semantics on Windows
        os.chmod(key_path, stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass
    with open(_pub_path(project_dir), "w", encoding="ascii") as f:
        f.write(_encode(public) + "\n")

    return {
        "algorithm": _ALGO,
        "public": _encode(public),
        "fingerprint": fingerprint(public),
        "key_path": key_path,
        "pub_path": _pub_path(project_dir),
    }


def load_seed(project_dir: str) -> bytes:
    """Read the private seed. Raises KeyError_ when absent/corrupt."""
    path = _key_path(project_dir)
    if not os.path.isfile(path):
        raise KeyError_(f"no project key at {path} — run `tausik key init` first")
    with open(path, encoding="ascii") as f:
        return _decode(f.read(), expect_len=32)


def load_public(project_dir: str) -> bytes:
    """Read the public key; falls back to deriving it from the seed."""
    path = _pub_path(project_dir)
    if os.path.isfile(path):
        with open(path, encoding="ascii") as f:
            return _decode(f.read(), expect_len=32)
    return ed25519.public_from_seed(load_seed(project_dir))


def key_info(project_dir: str) -> dict[str, str]:
    """Public-only view for `tausik key show` (never exposes the seed)."""
    public = load_public(project_dir)
    return {
        "algorithm": _ALGO,
        "public": _encode(public),
        "fingerprint": fingerprint(public),
        "pub_path": _pub_path(project_dir),
    }
