"""Regression: CLAUDE.md static portion must stay <= 4096B (v14b-claudemd-trim).

Why: CLAUDE.md is loaded into agent context every turn. Each KB above
the cap multiplies into ~250 tokens per turn -> ~25K extra tokens per
100-turn session. Heavy reference belongs in docs/ru/agent-contract.md
(loaded on demand via Read), not in CLAUDE.md.

Cap is enforced on the STATIC portion only (everything outside the
``<!-- DYNAMIC:START --> ... <!-- DYNAMIC:END -->`` block). The dynamic
block is rewritten by ``tausik update-claudemd`` and grows naturally
with task counts; capping it would punish having more tasks tracked.
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
