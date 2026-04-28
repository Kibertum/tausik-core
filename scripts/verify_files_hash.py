"""Files-hash for verify cache (v1.3.4 med-batch-2-qg #3).

Lives separately from `service_verification.py` for filesize-gate
compliance. Public API is just `compute_files_hash` plus the
`_FILES_HASH_CONTENT_SAMPLE_BYTES` constant; both are re-exported by
service_verification so existing imports keep working.
"""

from __future__ import annotations

import hashlib
import os


# v1.3.4 (med-batch-2-qg #3): per-file content sample size for files_hash.
# 4 KiB is enough to catch most edits (function bodies, header changes,
# imports) without dragging large binaries through the hash on every
# task_done.
_FILES_HASH_CONTENT_SAMPLE_BYTES = 4096


def compute_files_hash(file_paths: list[str], *, root: str | None = None) -> str:
    """SHA256 over (canonical_path, mtime_ns, size, content_head_sha256) tuples.

    Order-independent (sorted before hashing). Missing files contribute their
    canonical path with mtime/size/content sentinel `0` so the hash detects
    "file appeared / disappeared" changes.

    Empty list → stable empty-marker hash (so cache-by-hash still works for
    full-suite verifies that have no scoped files).

    v1.3.4 (med-batch-2-qg #3): hash now also incorporates SHA-256 of the
    first 4 KiB of each file's content. mtime alone could miss edits on
    filesystems with coarse mtime resolution (FAT/HFS+/SMB) AND on
    deliberate `touch -d` reverts; size alone misses content swaps with
    same length. The content head changes detect both cases. Reading a
    bounded prefix (4 KiB) is fast even for large files.

    Files unreadable due to permission/race (FileNotFoundError,
    PermissionError, IsADirectoryError) contribute the all-zeros sentinel
    so the hash flips when the file's accessibility changes.

    Caveat — mtime resolution AS A SECONDARY SIGNAL: NTFS gives 100ns
    precision; ext4 1μs; HFS+ 1s; FAT32/exFAT 2s. Even on coarse-mtime
    filesystems the content-head check catches edits the mtime missed.
    """
    base = root or os.getcwd()
    canon: list[tuple[str, int, int, str]] = []
    for raw in file_paths or []:
        if not raw or not isinstance(raw, str):
            continue
        rel = raw.replace("\\", "/")
        abs_p = rel if os.path.isabs(rel) else os.path.join(base, rel)
        try:
            st = os.stat(abs_p)
        except OSError:
            canon.append((rel, 0, 0, "0" * 64))
            continue
        head_hex = "0" * 64
        try:
            with open(abs_p, "rb") as f:
                head = f.read(_FILES_HASH_CONTENT_SAMPLE_BYTES)
            head_hex = hashlib.sha256(head).hexdigest()
        except OSError:
            pass
        canon.append((rel, st.st_mtime_ns, st.st_size, head_hex))
    canon.sort()
    h = hashlib.sha256()
    h.update(b"verification_runs.v2\n")
    for path, mtime_ns, size, head_hex in canon:
        h.update(f"{path}|{mtime_ns}|{size}|{head_hex}\n".encode())
    return h.hexdigest()
