"""`replaces` names the manifest that actually preceded this one (§13.4.2).

It used to be composed from TODAY's date and the previous version number —
`CFM-<today>-tausik@v<n-1>` — which names a real manifest only when the
predecessor was written on the same calendar day. Seven regenerations in a
row happened to be; the first cross-day one (session #208) published
`replaces: CFM-2026-09-04-tausik@v13` for a predecessor whose id was
`CFM-2026-09-03-tausik`, and an auditor following the chain would have hit a
manifest that never existed. Found by the fix review, record #24.
"""

from __future__ import annotations

import os
import sys

_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

import pytest  # noqa: E402

yaml = pytest.importorskip("yaml")

from project_cli_renar import _existing_manifest, _existing_version, previous_link  # noqa: E402


def _manifest(tmp_path, *, version: int, manifest_id: str) -> str:
    p = tmp_path / "RENAR-CONFORMANCE.yaml"
    p.write_text(
        f"manifest-version: {version}\nmanifest-id: {manifest_id}\n"
        f"assessment-date: '{manifest_id[4:14]}'\n",
        encoding="utf-8",
    )
    return str(p)


def test_the_link_names_the_predecessor_not_today():
    """A predecessor written yesterday is still the predecessor today."""
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as d:
        p = _manifest(Path(d), version=13, manifest_id="CFM-2026-09-03-tausik")
        assert previous_link(p) == "CFM-2026-09-03-tausik@v13"
        assert _existing_manifest(p) == (13, "CFM-2026-09-03-tausik")
        assert _existing_version(p) == 13


def test_no_predecessor_means_no_link(tmp_path):
    assert previous_link(str(tmp_path / "missing.yaml")) is None
    assert _existing_version(str(tmp_path / "missing.yaml")) == 0


def test_a_manifest_without_an_id_yields_no_link(tmp_path):
    p = tmp_path / "RENAR-CONFORMANCE.yaml"
    p.write_text("manifest-version: 2\n", encoding="utf-8")
    assert previous_link(str(p)) is None
    assert _existing_version(str(p)) == 2


def test_the_committed_manifest_chain_resolves():
    """The live artifact: `replaces` must name the id git holds one version back.

    Read-only; skipped when the file or git history is unavailable (a fresh
    clone without the artifact, a shallow CI checkout).
    """
    import subprocess

    root = os.path.abspath(os.path.join(_SCRIPTS, ".."))
    path = os.path.join(root, "RENAR-CONFORMANCE.yaml")
    if not os.path.isfile(path):
        pytest.skip("no manifest in this tree")
    with open(path, encoding="utf-8") as f:
        cur = yaml.safe_load(f) or {}
    link = cur.get("replaces")
    if not link or int(cur.get("manifest-version", 0)) <= 1:
        pytest.skip("first manifest of the chain")
    prev_id, _, prev_v = str(link).rpartition("@v")
    r = subprocess.run(
        ["git", "log", "--format=%H", "-n", "40", "--", "RENAR-CONFORMANCE.yaml"],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if r.returncode != 0 or not r.stdout.strip():
        pytest.skip("git history unavailable")
    seen: set[tuple[int, str]] = set()
    for sha in r.stdout.split():
        show = subprocess.run(
            ["git", "show", f"{sha}:RENAR-CONFORMANCE.yaml"],
            cwd=root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if show.returncode != 0:
            continue
        old = yaml.safe_load(show.stdout) or {}
        seen.add((int(old.get("manifest-version", 0)), str(old.get("manifest-id"))))
    assert (int(prev_v), prev_id) in seen, (
        f"replaces names {link}, but git holds no manifest with that id and version; "
        f"known: {sorted(seen)}"
    )
