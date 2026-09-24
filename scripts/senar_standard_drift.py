"""Did SENAR move under us? Read the corpus, not our idea of it (1.10, story F).

`renar_standard_drift` has done this for RENAR since 1.9. Nothing did it for
SENAR, and TAUSIK learned that 1.4 (2026-09-04) and 1.5 (2026-09-07) were out
from its owner on 2026-09-23 — the "learned by reading, weeks later" class the
RENAR detector was written against.

WHAT IS PARSED, FROM THE TEXT (never copied here — a copy would be the thing
this module watches for): the top RELEASED version in the corpus CHANGELOG
(a heading marked "unreleased" is skipped), the Core and Standard version
banners, the Core rule count (`### Rule N.`), the Core gate names
(`### … Gate`), and the gate-property letters of Standard §8.6.

WHAT IT IS COMPARED WITH: the edition TAUSIK claims (read from README.md,
"claims SENAR vX.Y Core") and the Core shape TAUSIK's compliance matrix is
built on (`EXPECTED_*` below — the matrix's own assumptions, named so a change
of the standard is a finding, not a silent mismatch).

THREE STATES, as in the RENAR detector: NOT CHECKED (no corpus configured or
the path is missing), UNREADABLE (the path lacks what is parsed — named), and
findings. "No findings" is never printed for a corpus that was not read.
"""

from __future__ import annotations

import os
import re
from typing import Any

Finding = dict[str, str]
DETECTOR = "senar"
CORPUS_CONFIG_KEY = "senar_standard_corpus"

# The Core shape the compliance matrix assumes (SENAR Core 1.5).
EXPECTED_CORE_RULES = 8
EXPECTED_CORE_GATES = ("Start Gate", "Done Gate")
EXPECTED_GATE_PROPERTIES = "abcde"

_CORE = os.path.join("core", "en", "senar-core.md")
_GATES = os.path.join("standard", "08-quality-gates.md")
_CHANGELOG = "CHANGELOG.md"

_RELEASE = re.compile(r"^## v(\d+\.\d+)\b(.*)$", re.M)
_RULE = re.compile(r"^### Rule (\d+)\.", re.M)
_GATE = re.compile(r"^### (\w+ Gate)\s*$", re.M)
_PROPERTY = re.compile(r"^([a-z])\) \*\*", re.M)
_CLAIM = re.compile(r"claims SENAR v(\d+\.\d+) Core")


def _read(root: str, rel: str) -> str | None:
    path = os.path.join(root, rel)
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return None


def corpus_root(cfg: dict[str, Any] | None = None) -> str | None:
    """The configured corpus directory, or None when unset or missing."""
    if cfg is None:
        from project_config import load_config

        cfg = load_config()
    raw = str((cfg or {}).get(CORPUS_CONFIG_KEY) or "").strip()
    if not raw:
        return None
    path = os.path.expanduser(raw)
    return path if os.path.isdir(path) else None


def released_versions(root: str) -> list[str]:
    """Released versions in the corpus CHANGELOG, newest first ('unreleased' skipped)."""
    text = _read(root, _CHANGELOG) or ""
    return [m.group(1) for m in _RELEASE.finditer(text) if "unreleased" not in m.group(2).lower()]


def core_shape(root: str) -> dict[str, Any] | None:
    core = _read(root, _CORE)
    if core is None:
        return None
    return {
        "rules": len({int(n) for n in _RULE.findall(core)}),
        "gates": tuple(_GATE.findall(core)),
    }


def gate_properties(root: str) -> str | None:
    text = _read(root, _GATES)
    if text is None or "## 8.6" not in text:
        return None
    section = text.split("## 8.6", 1)[1].split("\n## ", 1)[0]
    return "".join(_PROPERTY.findall(section))


def claimed_version(repo_root: str) -> str | None:
    """The edition TAUSIK claims, read from its README."""
    text = _read(repo_root, "README.md") or ""
    m = _CLAIM.search(text)
    return m.group(1) if m else None


def corpus_status(root: str | None) -> str:
    """One line saying WHETHER SENAR was checked."""
    if root is None:
        return f"senar corpus: NOT CHECKED — no local checkout configured ({CORPUS_CONFIG_KEY})"
    rel = released_versions(root)
    return f"senar corpus: checked against {root} (released {rel[0] if rel else 'unknown'})"


def detect_senar_drift(root: str, repo_root: str) -> list[Finding]:
    """Findings between the corpus and what TAUSIK claims and assumes."""
    out: list[Finding] = []

    def add(kind: str, ref: str, message: str, severity: str = "warn") -> None:
        out.append(
            {
                "detector": DETECTOR,
                "kind": kind,
                "severity": severity,
                "ref": ref,
                "message": message,
            }
        )

    missing = [rel for rel in (_CORE, _GATES, _CHANGELOG) if _read(root, rel) is None]
    for rel in missing:
        add(
            "corpus-unreadable",
            rel,
            f"{rel} is not in the corpus — the part it parses was not read",
        )
    released = released_versions(root)
    claim = claimed_version(repo_root)
    if released and claim and released[0] != claim:
        newer = released[: released.index(claim)] if claim in released else released[:1]
        add(
            "edition-drift",
            _CHANGELOG,
            f"TAUSIK claims SENAR v{claim} Core; the corpus has released "
            f"{', '.join('v' + v for v in newer)} since",
        )
    shape = core_shape(root)
    if shape is not None:
        if shape["rules"] != EXPECTED_CORE_RULES:
            add(
                "core-rules-drift",
                _CORE,
                f"SENAR Core has {shape['rules']} rules; the compliance matrix assumes {EXPECTED_CORE_RULES}",
            )
        if tuple(shape["gates"]) != EXPECTED_CORE_GATES:
            add(
                "core-gates-drift",
                _CORE,
                f"SENAR Core gates are {list(shape['gates'])}; the matrix assumes {list(EXPECTED_CORE_GATES)}",
            )
    props = gate_properties(root)
    if props is not None and props != EXPECTED_GATE_PROPERTIES:
        add(
            "gate-properties-drift",
            _GATES,
            f"§8.6 lists properties {props!r}; the matrix assumes {EXPECTED_GATE_PROPERTIES!r}",
        )
    return out


def corpus_health(cfg: dict[str, Any] | None = None) -> tuple[str, str]:
    """`(level, text)` for one doctor line about the SENAR corpus."""
    if cfg is None:
        from project_config import load_config

        cfg = load_config()
    raw = str((cfg or {}).get(CORPUS_CONFIG_KEY) or "").strip()
    if not raw:
        return "ok", f"not configured ({CORPUS_CONFIG_KEY}) — SENAR drift detector dormant"
    path = os.path.expanduser(raw)
    if not os.path.isdir(path):
        return "warn", f"{path} does not exist — fix {CORPUS_CONFIG_KEY}"
    if _read(path, _CORE) is None:
        return "warn", f"{path} has no {_CORE} — not the SENAR standard's source"
    rel = released_versions(path)
    return "ok", f"{path} — released v{rel[0] if rel else '?'}"
