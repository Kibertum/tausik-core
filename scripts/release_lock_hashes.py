"""Expand a compiled requirements lock to every wheel published for each pin."""

from __future__ import annotations

import argparse
import json
import os
import re
import urllib.parse
import urllib.request
from collections.abc import Callable, Iterable
from pathlib import Path

_PIN = re.compile(r"^([A-Za-z0-9_.-]+)==([^ ;]+)(?:\s*;.*)?$")
_HASH = re.compile(r"^    --hash=sha256:([0-9a-f]{64})$")
_MAX_PYPI_RESPONSE_BYTES = 8 * 1024 * 1024


def _without_continuation(line: str) -> str:
    return line[:-2] if line.endswith(" \\") else line


def render_all_artifact_hashes(
    lock: str,
    lookup: Callable[[str, str], Iterable[str]],
) -> str:
    """Replace each pin's platform-selected hash with the full wheel hash set."""
    lines = lock.splitlines()
    rendered: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        candidate = _without_continuation(line)
        match = _PIN.fullmatch(candidate)
        index += 1
        if match is None:
            rendered.append(line)
            continue

        rendered.append(candidate + " \\")
        while index < len(lines) and _HASH.fullmatch(_without_continuation(lines[index])):
            index += 1
        if index < len(lines) and lines[index].lstrip().startswith("--hash="):
            raise ValueError(f"malformed hash line after {match.group(1)}=={match.group(2)}")
        hashes = sorted(set(lookup(match.group(1), match.group(2))))
        if not hashes or any(re.fullmatch(r"[0-9a-f]{64}", value) is None for value in hashes):
            raise ValueError(
                f"invalid or empty artifact hash set for {match.group(1)}=={match.group(2)}"
            )
        for offset, digest in enumerate(hashes):
            continuation = " \\" if offset < len(hashes) - 1 else ""
            rendered.append(f"    --hash=sha256:{digest}{continuation}")
    if not any(_PIN.fullmatch(_without_continuation(line)) for line in lines):
        raise ValueError("lock contains no exact package pins")
    return "\n".join(rendered) + "\n"


def wheel_hashes_from_pypi_payload(payload: object, name: str, version: str) -> list[str]:
    """Validate a PyPI response and return only binary-wheel SHA-256 identities."""
    if not isinstance(payload, dict):
        raise ValueError(f"PyPI returned invalid metadata for {name}=={version}")
    info = payload.get("info")
    if not isinstance(info, dict) or info.get("version") != version:
        raise ValueError(f"PyPI returned the wrong release for {name}=={version}")
    urls = payload.get("urls", [])
    if not isinstance(urls, list):
        raise ValueError(f"PyPI returned invalid artifacts for {name}=={version}")
    hashes: list[str] = []
    for item in urls:
        if not isinstance(item, dict) or item.get("packagetype") != "bdist_wheel":
            continue
        if not str(item.get("filename", "")).endswith(".whl"):
            raise ValueError(f"PyPI returned an invalid wheel for {name}=={version}")
        digests = item.get("digests")
        if not isinstance(digests, dict) or not isinstance(digests.get("sha256"), str):
            raise ValueError(f"PyPI returned an invalid wheel digest for {name}=={version}")
        hashes.append(digests["sha256"])
    return hashes


def pypi_release_hashes(name: str, version: str) -> list[str]:
    """Return SHA-256 identities for all wheels in one immutable PyPI release."""
    quoted_name = urllib.parse.quote(name, safe="")
    quoted_version = urllib.parse.quote(version, safe="")
    url = f"https://pypi.org/pypi/{quoted_name}/{quoted_version}/json"
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=30) as response:  # nosec B310 -- fixed HTTPS origin
        raw = response.read(_MAX_PYPI_RESPONSE_BYTES + 1)
    if len(raw) > _MAX_PYPI_RESPONSE_BYTES:
        raise ValueError(f"PyPI response is too large for {name}=={version}")
    return wheel_hashes_from_pypi_payload(json.loads(raw), name, version)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("lock", type=Path)
    args = parser.parse_args(argv)
    lock = args.lock.resolve()
    rendered = render_all_artifact_hashes(lock.read_text(encoding="utf-8"), pypi_release_hashes)
    temporary = lock.with_suffix(lock.suffix + ".tmp")
    temporary.write_text(rendered, encoding="utf-8", newline="\n")
    os.replace(temporary, lock)
    print(f"expanded release hashes in {lock}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
