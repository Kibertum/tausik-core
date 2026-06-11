"""Pure-python ed25519 (RFC 8032) — stdlib only.

Decision #90 (v15-crypto-keymgmt): TAUSIK stays dependency-free, so the
evidence-attestation primitives use the RFC 8032 reference construction on
top of hashlib.sha512 and python big ints. Sign/verify cost ~30-60 ms —
fine for low-frequency receipt signing.

NOT constant-time. Threat model is local file-based signing: an attacker
able to measure timing on this machine can already read the key file.
Do NOT reuse for network-facing or high-frequency signing.

Public surface (bytes in, bytes out):
    generate_seed() -> 32-byte seed
    public_from_seed(seed) -> 32-byte public key
    sign(seed, message) -> 64-byte signature
    verify(public, message, signature) -> bool
"""

from __future__ import annotations

import hashlib
import os

_P = 2**255 - 19
_Q = 2**252 + 27742317777372353535851937790883648493


def _inv(x: int) -> int:
    return pow(x, _P - 2, _P)


_D = -121665 * _inv(121666) % _P
_I = pow(2, (_P - 1) // 4, _P)


def _xrecover(y: int) -> int:
    xx = (y * y - 1) * _inv(_D * y * y + 1)
    x = pow(xx, (_P + 3) // 8, _P)
    if (x * x - xx) % _P != 0:
        x = x * _I % _P
    if x % 2 != 0:
        x = _P - x
    return x


_BY = 4 * _inv(5) % _P
_BX = _xrecover(_BY)
_B = (_BX, _BY)


def _edwards_add(pt1: tuple[int, int], pt2: tuple[int, int]) -> tuple[int, int]:
    x1, y1 = pt1
    x2, y2 = pt2
    denom = _D * x1 * x2 * y1 * y2
    x3 = (x1 * y2 + x2 * y1) * _inv(1 + denom)
    y3 = (y1 * y2 + x1 * x2) * _inv(1 - denom)
    return (x3 % _P, y3 % _P)


def _scalarmult(pt: tuple[int, int], e: int) -> tuple[int, int]:
    result = (0, 1)
    addend = pt
    while e:
        if e & 1:
            result = _edwards_add(result, addend)
        addend = _edwards_add(addend, addend)
        e >>= 1
    return result


def _encodepoint(pt: tuple[int, int]) -> bytes:
    x, y = pt
    return int.to_bytes(y | ((x & 1) << 255), 32, "little")


def _isoncurve(pt: tuple[int, int]) -> bool:
    x, y = pt
    return (-x * x + y * y - 1 - _D * x * x * y * y) % _P == 0


def _decodepoint(s: bytes) -> tuple[int, int]:
    y = int.from_bytes(s, "little") & ((1 << 255) - 1)
    x = _xrecover(y)
    if x & 1 != (s[31] >> 7):
        x = _P - x
    pt = (x, y)
    if not _isoncurve(pt):
        raise ValueError("point not on curve")
    return pt


def _secret_expand(seed: bytes) -> tuple[int, bytes]:
    if len(seed) != 32:
        raise ValueError("seed must be 32 bytes")
    h = hashlib.sha512(seed).digest()
    a = int.from_bytes(h[:32], "little")
    a &= (1 << 254) - 8
    a |= 1 << 254
    return a, h[32:]


def generate_seed() -> bytes:
    """Fresh 32-byte private seed from the OS CSPRNG."""
    return os.urandom(32)


def public_from_seed(seed: bytes) -> bytes:
    a, _ = _secret_expand(seed)
    return _encodepoint(_scalarmult(_B, a))


def sign(seed: bytes, message: bytes) -> bytes:
    a, prefix = _secret_expand(seed)
    public = _encodepoint(_scalarmult(_B, a))
    r = int.from_bytes(hashlib.sha512(prefix + message).digest(), "little") % _Q
    r_enc = _encodepoint(_scalarmult(_B, r))
    k = int.from_bytes(hashlib.sha512(r_enc + public + message).digest(), "little") % _Q
    s = (r + k * a) % _Q
    return r_enc + int.to_bytes(s, 32, "little")


def verify(public: bytes, message: bytes, signature: bytes) -> bool:
    """True iff signature is a valid ed25519 signature of message by public."""
    if len(public) != 32 or len(signature) != 64:
        return False
    try:
        pt_a = _decodepoint(public)
        pt_r = _decodepoint(signature[:32])
    except ValueError:
        return False
    s = int.from_bytes(signature[32:], "little")
    if s >= _Q:
        return False
    k = int.from_bytes(hashlib.sha512(signature[:32] + public + message).digest(), "little") % _Q
    return _scalarmult(_B, s) == _edwards_add(pt_r, _scalarmult(pt_a, k))
