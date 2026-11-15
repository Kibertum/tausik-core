"""Atomic single-use nonce markers for release qualification."""

from __future__ import annotations

import os
from pathlib import Path
import re


_NONCE = re.compile(r"^[0-9a-f]{64}$")


class LedgerError(ValueError):
    """The replay ledger cannot safely consume the nonce."""


def consume(directory: str | Path, nonce: str) -> None:
    """Create one durable marker; an existing marker is a replay."""

    if not _NONCE.fullmatch(nonce):
        raise LedgerError("attestation nonce is invalid")
    target = Path(directory)
    try:
        target.mkdir(parents=True, exist_ok=True)
        fd = os.open(target / nonce, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise LedgerError("attestation was replayed") from exc
    except OSError as exc:
        raise LedgerError("attestation replay marker cannot be created") from exc
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(b"consumed\n")
            handle.flush()
            os.fsync(handle.fileno())
    except OSError as exc:
        # The marker remains present, so an uncertain write fails closed.
        raise LedgerError("attestation replay marker cannot be persisted") from exc
    if os.name != "nt":
        try:
            directory_fd = os.open(target, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        except OSError as exc:
            raise LedgerError("attestation replay directory cannot be persisted") from exc
