"""v15-crypto-keymgmt: ed25519 core (RFC 8032) + project key storage."""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import crypto_ed25519 as ed  # noqa: E402
import crypto_keys  # noqa: E402

# RFC 8032 §7.1 test vector 1 (empty message)
V1_SEED = bytes.fromhex("9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60")
V1_PUB = bytes.fromhex("d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a")
V1_SIG = bytes.fromhex(
    "e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e06522490155"
    "5fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b"
)

# RFC 8032 §7.1 test vector 2 (one-byte message 0x72)
V2_SEED = bytes.fromhex("4ccd089b28ff96da9db6c346ec114e0f5b8a319f35aba624da8cf6ed4fb8a6fb")
V2_PUB = bytes.fromhex("3d4017c3e843895a92b70aa74d1b7ebc9c982ccf2ec4968cc0cd55f12af4660c")
V2_MSG = bytes.fromhex("72")
V2_SIG = bytes.fromhex(
    "92a009a9f0d4cab8720e820b5f642540a2b27b5416503f8fb3762223ebdb69da"
    "085ac1e43e15996e458f3613d0f11d8c387b2eaeb4302aeeb00d291612bb0c00"
)


class TestEd25519Core:
    def test_rfc8032_vector1(self):
        assert ed.public_from_seed(V1_SEED) == V1_PUB
        assert ed.sign(V1_SEED, b"") == V1_SIG
        assert ed.verify(V1_PUB, b"", V1_SIG)

    def test_rfc8032_vector2(self):
        assert ed.public_from_seed(V2_SEED) == V2_PUB
        assert ed.sign(V2_SEED, V2_MSG) == V2_SIG
        assert ed.verify(V2_PUB, V2_MSG, V2_SIG)

    def test_tampered_message_rejected(self):
        assert not ed.verify(V1_PUB, b"tampered", V1_SIG)

    def test_tampered_signature_rejected(self):
        bad = bytearray(V1_SIG)
        bad[0] ^= 1
        assert not ed.verify(V1_PUB, b"", bytes(bad))

    def test_wrong_key_rejected(self):
        assert not ed.verify(V2_PUB, b"", V1_SIG)

    def test_malformed_inputs_return_false(self):
        assert not ed.verify(b"short", b"", V1_SIG)
        assert not ed.verify(V1_PUB, b"", b"short")
        assert not ed.verify(b"\xff" * 32, b"", V1_SIG)

    def test_fresh_keypair_roundtrip(self):
        seed = ed.generate_seed()
        pub = ed.public_from_seed(seed)
        msg = b"tausik receipt payload"
        assert ed.verify(pub, msg, ed.sign(seed, msg))

    def test_sign_performance_budget(self):
        t0 = time.monotonic()
        ed.sign(V1_SEED, b"x")
        assert time.monotonic() - t0 < 5  # low-frequency local signing


class TestKeyStorage:
    def test_init_creates_files_and_roundtrips(self, tmp_path):
        info = crypto_keys.init_keys(str(tmp_path))
        assert info["algorithm"] == "ed25519"
        assert info["public"].startswith("ed25519:")
        assert len(info["fingerprint"]) == 16
        seed = crypto_keys.load_seed(str(tmp_path))
        pub = crypto_keys.load_public(str(tmp_path))
        assert ed.public_from_seed(seed) == pub
        assert (tmp_path / ".tausik" / "keys" / "project.key").is_file()
        assert (tmp_path / ".tausik" / "keys" / "project.pub").is_file()

    def test_second_init_refuses_without_force(self, tmp_path):
        crypto_keys.init_keys(str(tmp_path))
        with pytest.raises(crypto_keys.KeyError_, match="--force"):
            crypto_keys.init_keys(str(tmp_path))

    def test_force_replaces_key(self, tmp_path):
        first = crypto_keys.init_keys(str(tmp_path))
        second = crypto_keys.init_keys(str(tmp_path), force=True)
        assert first["public"] != second["public"]

    def test_private_key_inside_gitignored_tausik_dir(self, tmp_path):
        info = crypto_keys.init_keys(str(tmp_path))
        rel = Path(info["key_path"]).relative_to(tmp_path)
        assert rel.parts[0] == ".tausik"

    def test_key_info_never_exposes_seed(self, tmp_path):
        crypto_keys.init_keys(str(tmp_path))
        info = crypto_keys.key_info(str(tmp_path))
        seed_hex = crypto_keys.load_seed(str(tmp_path)).hex()
        assert seed_hex not in str(info)

    def test_load_seed_missing_raises_with_hint(self, tmp_path):
        with pytest.raises(crypto_keys.KeyError_, match="key init"):
            crypto_keys.load_seed(str(tmp_path))

    def test_corrupt_key_file_raises(self, tmp_path):
        crypto_keys.init_keys(str(tmp_path))
        (tmp_path / ".tausik" / "keys" / "project.key").write_text("garbage")
        with pytest.raises(crypto_keys.KeyError_):
            crypto_keys.load_seed(str(tmp_path))

    def test_pub_derivable_when_pub_file_deleted(self, tmp_path):
        info = crypto_keys.init_keys(str(tmp_path))
        (tmp_path / ".tausik" / "keys" / "project.pub").unlink()
        pub = crypto_keys.load_public(str(tmp_path))
        assert crypto_keys._encode(pub) == info["public"]
