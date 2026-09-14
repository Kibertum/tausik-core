"""§8.4.1 coverage completeness — does a SPEC's body describe its subject exhaustively?

WHY THIS EXISTS. ADR-023 (`spec-coverage-completeness`) is the ONE of the four
unassessed accepted ADRs that actually BINDS us: its §5 puts into §8.4.1 the
provision *"the mandatory body describes the subject of the specification
exhaustively; limiting coverage to a subset of elements by a subjective
selection criterion is forbidden, in all eleven types and regardless of
vocabulary"*. Unlike ADR-020 it carries no RENAR-level caveat, so our RENAR-1
does not cut it off.

WHAT WAS MISSING, NAMED EXACTLY. The live `gates status` shows SPEC artifacts
touched by exactly two gates, both `warn`: `renar_drift_schema` (SCHEMA
validation) and `renar_drift_provenance` (FRESHNESS of task↔SPEC links).
Neither asks about the body. `renar_drift.py:91` compares
`s["type"] not in SPEC_TYPES` — the TYPE, not the exhaustiveness of the
description. No control in the registry answered §8.4.1 at all, blocking or
warning.

THE CHECK IS BY SUBJECT, NOT BY VOCABULARY, AND THAT IS THE WHOLE DESIGN.
ADR-023 §4 takes apart why a ban on words ("key", "critical", "core") is wrong
in BOTH directions: the same adjectives are legitimate when they name a property
OF the subject, and illegitimate when they narrow what is to be described. A
blacklist of adjectives would fail the criterion even if it caught every case we
have today. So nothing here inspects vocabulary.

Instead: a SPEC declares, in the committed `tausik/spec_coverage.json`, the
ENUMERABLE SET that constitutes its subject and how to enumerate it. The control
enumerates that set from the live code and asks whether the body names every
member. A body may call one of them "the critical one" and stay green — the
adjective removes no member. A body that describes four of seven guarded keys is
red no matter how neutrally it is phrased. Vocabulary is not evidence in either
direction; the enumeration is.

WHAT IT REPORTS. The concrete SPEC and the concrete omission, by name — never a
coverage percentage. "83% covered" tells a reader nothing they can act on, and
the criterion asks for the missing element, not its cardinality.

REACH IS STATED AS A NUMBER, AND THE NUMBER IS DERIVED. `reach()` reports both
cardinalities from `len()` and names, by type, everything the standard closes
over that our own list omits. Since v49 that omission is empty: ADR-013 admitted
SPEC-TEST and SPEC-DOC, and `service_specs.SPEC_TYPES` now carries §8.3 in full.
The mechanism stays precisely BECAUSE the shortfall is gone — a control that
hard-coded "all types covered" would commit the very narrowing §8.4.1 forbids,
selecting the convenient subset and calling it the whole, on the day the
standard is next amended. Arithmetic reports what prose used to assert.

A SPEC WITH NO ENTRY IS UNCHECKED, NOT PASSING. The absence of a negative
finding is not a positive verdict (SENAR 1.4 §8.6(e)), so a SPEC this registry
does not describe is reported by name as UNCHECKED. Same for a body the control
cannot read — `renar-adoption` points at `decisions#109`, which is a record, not
a file. Saying so beats scoring it green.
"""

from __future__ import annotations

import io
import json
import os
import re
from dataclasses import dataclass, field
from typing import Callable

# The standard's eleven, transcribed from §8.3 — NOT derived from our own
# SPEC_TYPES. Ours matches it in full (v49 / ADR-013), and that agreement is
# exactly why the literal stays: a denominator computed from the numerator can
# never report a shortfall, so the next amendment of the standard would move
# both sides together and go unnoticed. Their agreement is a FACT this module
# lets a test check, not an identity it assumes.
STANDARD_SPEC_TYPES: tuple[str, ...] = (
    "ARCH",
    "API",
    "DATA",
    "INT",
    "PROC",
    "UI",
    "AI",
    "SEC",
    "OPS",
    "TEST",
    "DOC",
)

REGISTRY_NAME = "spec_coverage.json"


@dataclass(frozen=True)
class Finding:
    """One SPEC and one concrete thing wrong with its body."""

    spec: str
    kind: str  # OMISSION | UNCHECKED | UNREADABLE_BODY | STALE_ENTRY | NO_ENUMERATOR
    detail: str

    def describe(self) -> str:
        return f"{self.kind} {self.spec}: {self.detail}"


@dataclass
class Report:
    findings: list[Finding] = field(default_factory=list)
    complete: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.findings

    def render(self) -> str:
        if self.ok:
            return f"{len(self.complete)} SPEC body(ies) describe their subject exhaustively"
        return "\n".join(f.describe() for f in self.findings)


# --- Enumerators: what constitutes a subject --------------------------------
#
# Each returns the members a body must name. They read the LIVE code, so a
# member added to the product widens what the body owes without anybody
# remembering to update a list here.


def config_trust_guarded_keys() -> list[str]:
    """The guarded keys of the config trust tiers, from `config_trust.GUARDS`."""
    from config_trust import GUARDS

    return [".".join(g.path) for g in GUARDS]


def state_projection_kinds() -> list[str]:
    """The entity kinds the git-native projection writes, from the exporter's
    own registry (`state_serialize.ENTITY_DIRS`)."""
    from state_serialize import ENTITY_DIRS

    return list(ENTITY_DIRS)


ENUMERATORS: dict[str, Callable[[], list[str]]] = {
    "config_trust_guarded_keys": config_trust_guarded_keys,
    "state_projection_kinds": state_projection_kinds,
}


# --- Registry ---------------------------------------------------------------


def registry_path(start: str | None = None) -> str | None:
    """`tausik/spec_coverage.json`, found beside the committed `gates.json`.

    The locator is reused rather than rewritten (convention #266); this file
    lives in the same non-dotted projection for the same reason — a fresh clone
    has to carry it.
    """
    from gate_filesize import _committed_gates_config_path

    gates = _committed_gates_config_path(start)
    if not gates:
        return None
    return os.path.join(os.path.dirname(gates), REGISTRY_NAME)


def load_registry(start: str | None = None) -> dict[str, dict]:
    """Read the committed registry. Missing or broken → `{}`.

    Degrading to `{}` makes every SPEC UNCHECKED, which is loud. A measure of
    this kind must never degrade toward "everything is fine".
    """
    path = registry_path(start)
    if not path or not os.path.isfile(path):
        return {}
    try:
        with io.open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {k: v for k, v in data.items() if not k.startswith("_") and isinstance(v, dict)}


def reach(known_types: tuple[str, ...] | None = None) -> dict:
    """How much of the standard this control can possibly cover, as a number."""
    if known_types is None:
        from service_specs import SPEC_TYPES

        known_types = SPEC_TYPES
    absent = [t for t in STANDARD_SPEC_TYPES if t not in known_types]
    return {
        "types_known": len(known_types),
        "types_in_standard": len(STANDARD_SPEC_TYPES),
        "absent": absent,
        "note": (
            f"covers {len(known_types)} of {len(STANDARD_SPEC_TYPES)} SPEC types; "
            + (
                f"{', '.join('SPEC-' + t for t in absent)} absent from our closed list "
                "(service_specs.SPEC_TYPES must be widened to match §8.3)"
                if absent
                else "none absent"
            )
        ),
    }


# --- The check --------------------------------------------------------------


def _read_body(ref: str, repo_root: str) -> tuple[str | None, str]:
    """The body text behind a `content_ref`, or (None, why-not)."""
    if not ref:
        return None, "the SPEC declares no content_ref, so it has no body to describe anything"
    if "#" in ref and not ref.endswith(".md"):
        return None, f"content_ref {ref!r} points at a record, not a readable body file"
    path = os.path.join(repo_root, ref.replace("/", os.sep))
    if not os.path.isfile(path):
        return None, f"content_ref {ref!r} names no file in the tree"
    try:
        return io.open(path, encoding="utf-8").read(), ""
    except (OSError, UnicodeDecodeError) as e:
        return None, f"content_ref {ref!r} is unreadable: {e}"


def _member_pattern(member: str) -> "re.Pattern[str]":
    """A member name as a matcher, with `*` standing for one path segment.

    Some members are FAMILIES rather than single keys: `gates.*.enabled` is one
    guard covering every gate. Prose spells that placeholder however the prose
    likes — `gates.<имя>.enabled` in the Russian body, `gates.mypy.enabled` in
    a worked example — and demanding the literal asterisk would have failed four
    keys this body describes perfectly well. That would be a check about
    typography, and the criterion is about the subject.

    The segment deliberately excludes whitespace, dots and backticks, so the
    wildcard cannot swallow its way across a sentence and score an unrelated
    mention as coverage.
    """
    parts = [re.escape(p) for p in member.split("*")]
    return re.compile(r"[^\s`.]+".join(parts))


def check_body(members: list[str], body: str) -> list[str]:
    """Members of the subject the body never names. Order preserved.

    Membership is tested by NAME because a name is what the enumerator produces
    and what a reader looks for. No judgement is made about the sentence a name
    appears in: the criterion is coverage of the subject, and a member that is
    named is covered whatever adjectives surround it — which is exactly why a
    body may call one element "the critical one" and stay green.
    """
    return [m for m in members if not _member_pattern(m).search(body)]


def audit(
    specs: list[dict] | None = None,
    registry: dict[str, dict] | None = None,
    repo_root: str | None = None,
    enumerators: dict[str, Callable[[], list[str]]] | None = None,
) -> Report:
    """Judge every SPEC in the project. Arguments are injectable so the negative
    scenarios can narrow ONE body and watch this name it."""
    if repo_root is None:
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if registry is None:
        registry = load_registry()
    if enumerators is None:
        enumerators = ENUMERATORS
    if specs is None:
        from service_factory import get_service

        specs = list(get_service().spec_list())

    report = Report()
    by_slug = {s["slug"]: s for s in specs}

    for slug in sorted(by_slug):
        entry = registry.get(slug)
        if not entry:
            report.findings.append(
                Finding(
                    slug,
                    "UNCHECKED",
                    "no spec_coverage entry names the enumerable subject this body owes a "
                    "description of — the absence of a finding is not a verdict",
                )
            )
            continue
        name = str(entry.get("enumerator") or "")
        enumerate_ = enumerators.get(name)
        if enumerate_ is None:
            report.findings.append(
                Finding(slug, "NO_ENUMERATOR", f"enumerator {name!r} is not implemented")
            )
            continue
        body, why = _read_body(
            str(entry.get("body") or by_slug[slug].get("content_ref") or ""), repo_root
        )
        if body is None:
            report.findings.append(Finding(slug, "UNREADABLE_BODY", why))
            continue
        missing = check_body(enumerate_(), body)
        if missing:
            subject = str(entry.get("subject") or name)
            for m in missing:
                report.findings.append(
                    Finding(
                        slug,
                        "OMISSION",
                        f"the body never names {m!r}, an element of its subject "
                        f"({subject}) — coverage limited to a subset",
                    )
                )
            continue
        report.complete.append(slug)

    for slug in sorted(set(registry) - set(by_slug)):
        report.findings.append(
            Finding(slug, "STALE_ENTRY", "spec_coverage names a SPEC the project does not have")
        )

    return report
