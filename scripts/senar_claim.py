"""The SENAR claim: one sentence, its disclosures, and whether the edition is public.

THE SENTENCE. SENAR 1.5 §13.1 gives the form "[Organization] conforms to SENAR
v[version] [Configuration] configuration, [self-declared | ...], as of [date]".
TAUSIK claims SENAR Core, which is not one of the §11 configurations: Core says
of itself that no formal declaration is required and conformance is
self-assessed. We still state it in the §13.1 form, with "Core" where the
configuration goes, so a reader gets edition, scope, mode and date in one line.
`claim_sentence()` builds it from `DECLARED_SENAR_VERSION`; README (EN/RU),
CLAUDE.md's pointer and agent-contract carry it verbatim, and a test holds them.

THE DISCLOSURES (§13.1(c), (e)). A claim publishes, wherever it is published,
the SHALL requirements handled under §13.5 and the SHOULD requirements not
implemented. `NONCONFORMITIES` and `UNIMPLEMENTED_SHOULD` are those registers.
Both are empty, and emptiness is DECLARED with its basis (`EMPTY_BECAUSE`):
"nothing to disclose" and "nobody looked" read the same otherwise. A record
added here that README does not carry is a red test.

THE EDITION MUST BE PUBLIC. The owner claimed 1.5 before publishing it (decision
#376). A release that points readers at an edition they cannot read would claim
against a text nobody can check, so `published()` asks GitHub Kibertum/SENAR for
the tag, and `tausik publish senar-check` refuses a TAUSIK release tag until it
is there. No network is NOT VERIFIED, never "published" (§8.6(e)). Development
and CI are not touched by this check — only the release procedure runs it.
"""

from __future__ import annotations

import re
import subprocess
from typing import Callable

from senar_version_claim import DECLARED_SENAR_VERSION

ORGANIZATION = "TAUSIK"
MODE = "self-declared"
#: Date of the claim: the owner's decision #376 (session #266).
CLAIM_DATE = "2026-09-23"
SENAR_REPO = "https://github.com/Kibertum/SENAR.git"
SENAR_RELEASES = "https://github.com/Kibertum/SENAR/releases"

#: §13.5 records disclosed with the claim (§13.1(e)).
NONCONFORMITIES: list[dict[str, str]] = []
#: SHOULD requirements of the claimed scope not implemented (§13.1(c)).
UNIMPLEMENTED_SHOULD: list[dict[str, str]] = []
EMPTY_BECAUSE = (
    "assessed on 2026-09-23 against core/en/senar-core.md of the claimed edition: its "
    "8 rules and 2 gates carry no SHOULD, and no rule is handled under §13.5. Rules "
    "enforced by warning rather than refusal are named in the compliance matrix's "
    "Enforcement column."
)


def claim_sentence(version: str = DECLARED_SENAR_VERSION) -> str:
    return f"{ORGANIZATION} conforms to SENAR v{version} Core, {MODE}, as of {CLAIM_DATE}"


def _git_tags(url: str) -> list[str]:
    out = subprocess.run(
        ["git", "ls-remote", "--tags", url],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=20,
        check=True,
    ).stdout
    return [ln.split("refs/tags/", 1)[1] for ln in out.splitlines() if "refs/tags/" in ln]


def published(
    version: str = DECLARED_SENAR_VERSION, lister: Callable[[str], list[str]] = _git_tags
) -> tuple[str, str]:
    """("published" | "not-published" | "not-verified", detail)."""
    try:
        tags = lister(SENAR_REPO)
    except Exception as e:  # noqa: BLE001 — any failure is NOT VERIFIED, never a pass
        return "not-verified", f"{type(e).__name__}: {e}"[:200]
    want = re.compile(rf"^v?{re.escape(version)}(\.\d+)*$")
    names = sorted({t.removesuffix("^{}") for t in tags})
    if any(want.match(t) for t in names):
        return "published", f"tag for {version} found"
    newest = names[-1] if names else "none"
    return "not-published", f"tags on GitHub: {', '.join(names) or 'none'} (newest {newest})"


def check_message(status: str, detail: str, version: str = DECLARED_SENAR_VERSION) -> str:
    if status == "published":
        return f"OK: SENAR v{version}, the edition TAUSIK claims, is published ({detail})."
    head = (
        "NOT VERIFIED: could not read the SENAR tags"
        if status == "not-verified"
        else "REFUSED: the claimed SENAR edition is not published"
    )
    return (
        f"{head}. Claimed: v{version}. Published: {detail}. Releases: {SENAR_RELEASES}. "
        "Do not tag a TAUSIK release until the claimed edition is public."
    )


#: What a README must carry next to the claim when both registers are empty.
EMPTY_MARKERS = {
    "en": "No SHALL is handled under §13.5, and no SHOULD of the claimed scope is unimplemented",
    "ru": "Ни одно SHALL не обрабатывается по §13.5, и ни одно SHOULD заявленного объёма не оставлено",
}


def missing_disclosures(text: str, lang: str) -> list[str]:
    """What the published claim in `text` fails to disclose (§13.1(c), (e))."""
    missing = [] if claim_sentence() in text else ["the claim sentence"]
    records = NONCONFORMITIES + UNIMPLEMENTED_SHOULD
    if not records:
        return missing + ([] if EMPTY_MARKERS[lang] in text else ["the empty-register statement"])
    return missing + [r["clause"] for r in records if r["clause"] not in text]
