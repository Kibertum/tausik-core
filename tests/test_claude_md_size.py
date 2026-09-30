"""Regression: CLAUDE.md static portion must stay <= 4096B (v14b-claudemd-trim).

Why: CLAUDE.md is loaded into agent context every turn. Each KB above
the cap multiplies into ~250 tokens per turn -> ~25K extra tokens per
100-turn session. Heavy reference belongs in docs/ru/agent-contract.md
(loaded on demand via Read), not in CLAUDE.md.

Cap is enforced on the STATIC portion only (everything outside the
``<!-- DYNAMIC:START --> ... <!-- DYNAMIC:END -->`` block). The dynamic
block is rewritten by ``tausik update-claudemd`` and grows naturally
with task counts; capping it would punish having more tasks tracked.

A CAP WITH NO ROOM LEFT IS A BAN, and nothing said so. Measured in session #277: 13 bytes
free, which is less than one pointer line. The file had stopped accepting additions while
still passing, and the next author would have learned that from a failing test rather than
from the file. The headroom check below states the room as a number, and the admission rule
it enforces -- a line earns its place only if the agent would do the wrong thing without it,
plus a declaration a standard requires -- is written in the file it governs, because a rule
kept away from its subject is an excuse nobody re-reads.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CLAUDE_MD = REPO_ROOT / "CLAUDE.md"
AGENT_CONTRACT = REPO_ROOT / "docs" / "ru" / "agent-contract.md"
MAX_STATIC_BYTES = 4096

DYNAMIC_BLOCK = re.compile(
    r"<!-- DYNAMIC:START -->.*?<!-- DYNAMIC:END -->",
    re.DOTALL,
)


def _static_size(text: str) -> int:
    """Return CLAUDE.md size with the dynamic block stripped out."""
    return len(DYNAMIC_BLOCK.sub("", text).encode("utf-8"))


def test_claude_md_static_under_size_cap() -> None:
    assert CLAUDE_MD.exists(), "CLAUDE.md missing at repo root"
    text = CLAUDE_MD.read_text(encoding="utf-8")
    static = _static_size(text)
    assert static <= MAX_STATIC_BYTES, (
        f"CLAUDE.md static portion is {static}B, exceeds cap "
        f"{MAX_STATIC_BYTES}B. Move heavy reference content to "
        "docs/ru/agent-contract.md (or docs/ru/architecture.md / "
        "docs/ru/cli.md) to keep per-turn context tax bounded."
    )


def test_claude_md_references_agent_contract() -> None:
    content = CLAUDE_MD.read_text(encoding="utf-8")
    assert "agent-contract.md" in content, (
        "CLAUDE.md must point agents at docs/ru/agent-contract.md "
        "for the extended ruleset (estimation, SENAR matrix, roles)."
    )


def test_agent_contract_exists_and_nonempty() -> None:
    assert AGENT_CONTRACT.exists(), (
        "docs/ru/agent-contract.md must exist as the extended TAUSIK "
        "contract (heavy reference extracted from CLAUDE.md)."
    )
    assert AGENT_CONTRACT.stat().st_size > 1024, (
        "docs/ru/agent-contract.md is suspiciously small (<1KB); "
        "extraction from CLAUDE.md likely incomplete."
    )


def test_claude_md_keeps_dynamic_block() -> None:
    """update-claudemd writes between DYNAMIC markers; lose them and CLI breaks."""
    content = CLAUDE_MD.read_text(encoding="utf-8")
    assert "<!-- DYNAMIC:START -->" in content
    assert "<!-- DYNAMIC:END -->" in content


#: One pointer line in this project's CLAUDE.md is about 45 bytes ("Что НЕ гарантировано:
#: `docs/ru/known-limitations.md`."). Room for four of them is the smallest headroom that
#: makes the cap a budget instead of a wall, and it is deliberately not a second cap: the
#: number exists so a trim happens BEFORE an addition, not after a red test.
MIN_HEADROOM_BYTES = 180


def test_the_cap_leaves_room_for_the_next_pointer() -> None:
    """THE FAILURE THIS FILE MISSED: 4088 of 4096 used, and every test green."""
    static = _static_size(CLAUDE_MD.read_text(encoding="utf-8"))
    free = MAX_STATIC_BYTES - static
    assert free >= MIN_HEADROOM_BYTES, (
        f"CLAUDE.md static portion is {static}B, leaving {free}B free — under the "
        f"{MIN_HEADROOM_BYTES}B a next pointer needs. Trim reference prose rather than "
        f"raising the cap: a line belongs here only if the agent would do the wrong thing "
        f"without it. Guide: docs/ru/claude-md-guide.md"
    )


def test_the_admission_rule_is_stated_in_the_file_it_governs() -> None:
    """A rule kept only in the guide is a rule the next author edits the file without."""
    content = CLAUDE_MD.read_text(encoding="utf-8")
    assert "Что имеет право стоять здесь" in content
    assert "claude-md-guide.md" in content, "and it names where the reasoning lives"


def test_no_documentation_address_is_named_twice() -> None:
    """One address, named once. A second mention is a second thing to keep in step, and
    the bytes it costs are bytes the next pointer does not have."""
    import collections
    import re

    static = DYNAMIC_BLOCK.sub("", CLAUDE_MD.read_text(encoding="utf-8"))
    counts = collections.Counter(re.findall(r"docs/(?:ru|en)/[a-z0-9-]+\.md", static))
    twice = {a: n for a, n in counts.items() if n > 1}
    assert not twice, f"named more than once in CLAUDE.md: {twice}"


def test_the_guide_carries_the_measurement_that_set_the_rule() -> None:
    """Both languages, because an agent reading either must get the same rule."""
    for rel in ("docs/ru/claude-md-guide.md", "docs/en/claude-md-guide.md"):
        text = (REPO_ROOT / rel).read_text(encoding="utf-8")
        assert "4096" in text and "13" in text, rel
