"""Did the STANDARD move under us? Read the corpus, not our idea of it.

Every other RENAR check in this project compares the live database against our
own declarations. That is the right question for "do we obey what we think the
standard says" and the wrong one for "is what we think still true". Both gaps
this epic exists for were found the second way: ADR-011 withdrew the ADAPT
client signature and ADR-013 widened the SPEC type list, and we learned of it
by reading in session #178 — months after the fact, while the CLI help went on
publishing a withdrawn edition to users. RENAR is on a wave branch with more
ADRs proposed, so the next move is a schedule, not a hypothesis.

WHAT IS CHECKED, named in advance and by substance: the closed lists the
standard fixes (SPEC types §8.3, backward-finding categories §7.4.4, ADAPT
lifecycle statuses §7.8.1), and the corpus version against the one our manifest
publishes. Values are PARSED OUT OF THE TEXT — copying them here would make
this module the thing it is watching for.

ACCEPTED IS NOT PROPOSED, and this is the constraint the task states as a
negative: a detector that demands implementation of every proposed ADR reddens
permanently and gets switched off. So an ADR is a finding only when its status
begins with `accepted` AND our repository never mentions its id. Proposed,
draft and superseded ones are never findings — the test plants one and requires
silence.

THREE STATES, as everywhere a reader can fail here: NO CORPUS (the path is
unset or absent) is "not checked" and is NOT the same as "no drift"; a corpus
present but a chapter that will not parse is a FINDING of its own, because a
detector that silently reads nothing is the degeneracy ADR-021 names; a parsed
corpus yields a verdict on the substance.

NOT BUILT HERE, and stated rather than left to be assumed: divergence between
the LOCAL corpus and the one published at renar.tech is a real finding of a
DIFFERENT kind — it needs the network inside a gate, which nothing in this
project does today, and it answers "is our copy current" rather than "have we
kept up with our copy". It belongs to its own task, with its own decision about
where a gate is allowed to make an outbound request.

Read-only in both directions: the corpus is never written, and neither is the
database (this detector does not use one).
"""

from __future__ import annotations

import os
import re
from typing import Any

from service_adapts import ADAPT_STATUSES, FINDING_CATEGORIES
from service_specs import SPEC_TYPES

Finding = dict[str, str]

DETECTOR = "standard"

# Config key holding the corpus path. Declared, never hardcoded: the corpus is
# a sibling repository whose location is a property of the machine, and owner
# decision #255 puts the local checkout in charge.
CORPUS_CONFIG_KEY = "renar_standard_corpus"

# Chapters the parsers below read, by the standard's own file names.
CH_ADAPT = "07-adapt.md"
CH_SPEC = "08-specifications.md"
CH_CONFORMANCE = "13-conformance.md"

# Bound for the one git call here. Same reasoning as every other git call in
# this project: an unbounded one is itself a hang risk (see git_exec).
_GREP_TIMEOUT = 20

# `**Часть RENAR Standard v1.0**` — the banner every chapter carries.
_VERSION_RE = re.compile(r"RENAR\s+Standard\s+v(\d+\.\d+)", re.IGNORECASE)

# THE CORPUS WRITES ITS CLOSED LISTS IN TWO SHAPES, and reading only one was
# the first thing this module got wrong. §8.3 and §7.4.4 enumerate in prose with
# backticks — "`SPEC-ARCH`, `API`, …", "`contradiction`, `gap`, …" — while
# §7.8.1 shows the ADAPT statuses as a frontmatter example, pipe-separated and
# unquoted: "status: draft | review | asked | …". Each list below names the
# shape it is written in; guessing one shape for all of them would have read an
# absent list as an agreeing one.
_MEMBER_RE = re.compile(r"`([A-Za-z][A-Za-z\-]*)`")
_NAME_RE = re.compile(r"[A-Za-z][A-Za-z\-]*")

# ADR frontmatter: the id and the status that decides whether it binds us.
_ADR_ID_RE = re.compile(r"^adr:\s*(\d+)\s*$", re.MULTILINE)
_ADR_STATUS_RE = re.compile(r"^status:\s*(.+?)\s*$", re.MULTILINE)


def _finding(kind: str, ref: str, message: str) -> Finding:
    return {
        "detector": DETECTOR,
        "kind": kind,
        "severity": "warn",
        "ref": ref,
        "message": message,
    }


def corpus_root(cfg: dict[str, Any] | None = None) -> str | None:
    """The corpus checkout to read, or ``None`` when this machine has none.

    ``None`` is a first-class answer, not a failure: a consumer project has no
    business carrying the standard's repository, and a detector that treated
    its absence as "no drift" would publish a silence as a verdict.
    """
    if cfg is None:
        from project_config import load_config

        cfg = load_config()
    raw = str((cfg or {}).get(CORPUS_CONFIG_KEY) or "").strip()
    if not raw:
        return None
    path = os.path.expanduser(raw)
    return path if os.path.isdir(path) else None


def _chapter(root: str, name: str) -> str | None:
    path = os.path.join(root, "standard", name)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return None


def backticked(line: str) -> tuple[str, ...]:
    """Members written in prose with backticks (§8.3, §7.4.4)."""
    return tuple(m.group(1) for m in _MEMBER_RE.finditer(line))


def pipe_separated(line: str) -> tuple[str, ...]:
    """Members written as a frontmatter example, `key: a | b | c` (§7.8.1).

    Split rather than matched with one pattern: the first attempt was a single
    regex and it silently returned nothing, because the corpus puts a space on
    both sides of the bar and the pattern only allowed one. A partial parse is
    the failure mode this whole module exists to avoid, so a part that is not a
    plain name makes the WHOLE line unreadable — never a shorter list quietly
    reported as the standard's.
    """
    _, sep, rest = line.partition(":")
    if not sep or "|" not in rest:
        return ()
    parts = [p.strip() for p in rest.split("|")]
    if not all(p and _NAME_RE.fullmatch(p) for p in parts):
        return ()
    return tuple(parts)


def closed_list_from(text: str, cue: str, shape: Any = backticked) -> tuple[str, ...] | None:
    """Members of a closed list introduced by *cue*, in the corpus's own words.

    The cue is the phrase that identifies the line; *shape* is how that line
    writes its members. Returns ``None`` when the cue is absent — the chapter
    is there but does not say what we came to read, which is a finding and not
    an emptiness.
    """
    for line in text.splitlines():
        if cue in line:
            return shape(line) or None
    return None


def _normalise_spec_types(members: tuple[str, ...]) -> tuple[str, ...]:
    """`SPEC-ARCH`, `API`, … → ARCH, API, …

    The corpus prefixes only the first member; ours are bare. Comparing the
    written forms rather than the identities would report a drift on every run.
    """
    return tuple(m[5:] if m.upper().startswith("SPEC-") else m for m in members)


def corpus_version(root: str) -> str | None:
    """The standard's version, from the banner its chapters carry."""
    text = _chapter(root, CH_CONFORMANCE) or _chapter(root, CH_SPEC)
    if not text:
        return None
    m = _VERSION_RE.search(text)
    return m.group(1) if m else None


def accepted_adrs(root: str) -> list[tuple[str, str]]:
    """`(ADR-NNN, status)` for every ADR whose status begins with "accepted".

    Read from the frontmatter, because that is where the standard records the
    difference between a proposal and a decision. `accepted-pending-adr-012`
    counts: it is an accepted decision waiting on a sibling, and ADR-011 — one
    of the two we missed — carries exactly that status.
    """
    out: list[tuple[str, str]] = []
    decisions = os.path.join(root, "research", "decisions")
    if not os.path.isdir(decisions):
        return out
    for name in sorted(os.listdir(decisions)):
        if not name.endswith(".md"):
            continue
        try:
            with open(os.path.join(decisions, name), encoding="utf-8") as fh:
                head = fh.read(2000)
        except OSError:
            continue
        id_m, status_m = _ADR_ID_RE.search(head), _ADR_STATUS_RE.search(head)
        if not id_m or not status_m:
            continue
        status = status_m.group(1).strip()
        if status.lower().startswith("accepted"):
            out.append((f"ADR-{int(id_m.group(1)):03d}", status))
    return out


def adrs_mentioned_in(repo_root: str) -> set[str] | None:
    """Every `ADR-NNN` this repository mentions anywhere it tracks; None if unasked.

    One `git grep` over tracked files rather than reading four thousand of
    them, and ``None`` rather than an empty set when git cannot answer —
    "nobody mentions any ADR" and "we could not look" are different facts, and
    only the first is a finding.
    """
    import subprocess

    import git_exec

    try:
        res = git_exec.run(["grep", "-hoIE", r"ADR-[0-9]{3}"], cwd=repo_root, timeout=_GREP_TIMEOUT)
    except (OSError, subprocess.SubprocessError):
        return None
    # git grep exits 1 when nothing matched — a fact, not a failure.
    if res.returncode not in (0, 1):
        return None
    return {line.strip() for line in (res.stdout or "").splitlines() if line.strip()}


def detect_standard_drift(
    root: str | None = None,
    *,
    our_version: str | None = None,
    repo_mentions: set[str] | None = None,
    check_adrs: bool = True,
) -> list[Finding]:
    """Findings against the corpus, or [] when there is no corpus to read.

    ``repo_mentions`` is the set of ADR ids this project says anything about,
    used only to ask whether an accepted decision has been RECKONED WITH at
    all. Injected rather than gathered here so the check has an expressible
    green branch on a synthetic input; ``check_adrs=False`` turns that half off
    for callers that only want the closed lists.
    """
    if root is None:
        root = corpus_root()
    if root is None:
        return []  # no corpus on this machine — see `corpus_status`
    findings: list[Finding] = []

    if our_version is None:
        from renar_conformance import RENAR_VERSION

        our_version = RENAR_VERSION
    found_version = corpus_version(root)
    if found_version is None:
        findings.append(
            _finding(
                "corpus-unreadable",
                CH_CONFORMANCE,
                "no `RENAR Standard vX.Y` banner found — the corpus is present but "
                "does not say which edition it is",
            )
        )
    elif found_version != our_version:
        findings.append(
            _finding(
                "version-behind",
                f"corpus v{found_version}",
                f"the corpus is edition v{found_version} while we publish "
                f"renar-version {our_version} — re-assessment is due (§13.4.3)",
            )
        )

    findings.extend(
        _list_findings(
            root,
            CH_SPEC,
            "Типов спецификаций ровно",
            SPEC_TYPES,
            "spec-types",
            "§8.3",
            normalise=_normalise_spec_types,
        )
    )
    findings.extend(
        _list_findings(
            root,
            CH_ADAPT,
            "категорий §7.4.4",
            FINDING_CATEGORIES,
            "finding-categories",
            "§7.4.4",
        )
    )
    findings.extend(
        _list_findings(
            root,
            CH_ADAPT,
            "status: draft",
            ADAPT_STATUSES,
            "adapt-statuses",
            "§7.8.1",
            shape=pipe_separated,
        )
    )

    if check_adrs:
        if repo_mentions is None:
            findings.append(
                _finding(
                    "repo-unreadable",
                    "git grep",
                    "could not ask which ADRs this repository mentions, so the "
                    "accepted-ADR half of this detector did not run — that is not "
                    "the same as finding nothing",
                )
            )
        else:
            for adr, status in accepted_adrs(root):
                if adr not in repo_mentions:
                    findings.append(
                        _finding(
                            "accepted-adr-unreckoned",
                            adr,
                            f"{adr} is {status} in the corpus and this repository never "
                            "mentions it — an accepted decision nobody has read",
                        )
                    )
    return findings


def _list_findings(
    root: str,
    chapter: str,
    cue: str,
    ours: tuple[str, ...],
    kind: str,
    section: str,
    normalise: Any = None,
    shape: Any = backticked,
) -> list[Finding]:
    """One closed list: unreadable, or the difference between corpus and ours."""
    text = _chapter(root, chapter)
    if text is None:
        return [_finding("corpus-unreadable", chapter, f"chapter {chapter} is not in the corpus")]
    members = closed_list_from(text, cue, shape)
    if members is None:
        return [
            _finding(
                "corpus-unreadable",
                f"{chapter} {section}",
                f"the sentence declaring the {kind} list closed was not found — "
                "the chapter may have been reworded, and an unread list is not an "
                "agreeing one",
            )
        ]
    if normalise is not None:
        members = normalise(members)
    missing = [m for m in members if m not in ours]
    extra = [m for m in ours if m not in members]
    if not missing and not extra:
        return []
    return [
        _finding(
            f"{kind}-drift",
            f"{chapter} {section}",
            f"the corpus closes the list at {len(members)}; ours has {len(ours)}. "
            f"In the standard and not in ours: {missing or 'nothing'}; "
            f"in ours and not in the standard: {extra or 'nothing'}",
        )
    ]


def corpus_status(root: str | None = None) -> str:
    """One line saying WHETHER the standard was checked, for a caller to print.

    Separate from the findings on purpose: "no findings" and "not checked"
    render identically otherwise, and this whole epic exists because a silence
    was read as an agreement for months.
    """
    if root is None:
        root = corpus_root()
    if root is None:
        return (
            "standard corpus: NOT CHECKED — no local checkout configured "
            f"({CORPUS_CONFIG_KEY} in .tausik/config.json)"
        )
    version = corpus_version(root) or "unknown edition"
    return f"standard corpus: checked against {root} ({version})"
