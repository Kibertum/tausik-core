"""Fail-closed Git object resolution for release qualification."""

from __future__ import annotations

import hashlib
from pathlib import Path
import re
import subprocess
from typing import cast


OBJECT_ID = re.compile(r"^[0-9a-f]{40}$")


class QualificationError(ValueError):
    """The candidate or attestation does not satisfy the protected contract."""


def git(root: Path, *args: str, text: bool = True) -> str | bytes:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=str(root),
            capture_output=True,
            text=text,
            encoding="utf-8" if text else None,
            timeout=120,
            stdin=subprocess.DEVNULL,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise QualificationError("git object resolution timed out") from exc
    except OSError as exc:
        raise QualificationError("git object resolution could not start") from exc
    if result.returncode != 0:
        error = result.stderr if text else result.stderr.decode("utf-8", errors="replace")
        raise QualificationError(f"git object resolution failed: {error.strip()}")
    return cast(str | bytes, result.stdout)


def object_id(root: Path, ref: str, kind: str) -> str:
    value = str(git(root, "rev-parse", "--verify", f"{ref}^{{{kind}}}")).strip()
    if not OBJECT_ID.fullmatch(value):
        raise QualificationError(f"{kind} is not an exact object ID")
    return value


def projection_hashes(root: Path, commit: str, paths: tuple[str, ...]) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for path in paths:
        payload = git(root, "show", f"{commit}:{path}", text=False)
        assert isinstance(payload, bytes)
        hashes[path] = hashlib.sha256(payload).hexdigest()
    return hashes


def version_at(root: Path, commit: str, path: str, pattern: bytes) -> str:
    payload = git(root, "show", f"{commit}:{path}", text=False)
    assert isinstance(payload, bytes)
    match = re.search(pattern, payload)
    if match is None:
        raise QualificationError(f"release version is missing from {path}")
    try:
        return match.group(1).decode("ascii")
    except UnicodeDecodeError as exc:
        raise QualificationError(f"release version in {path} is not canonical ASCII") from exc
