"""Keep implicit agent rules bounded without testing each sentence separately."""

from __future__ import annotations

import collections
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CLAUDE_MD = REPO_ROOT / "CLAUDE.md"
AGENTS_MD = REPO_ROOT / "AGENTS.md"
AGENT_CONTRACT = REPO_ROOT / "docs" / "ru" / "agent-contract.md"
MAX_STATIC_BYTES = 4096
MIN_HEADROOM_BYTES = 180

DYNAMIC_BLOCK = re.compile(
    r"<!-- DYNAMIC:START -->.*?<!-- DYNAMIC:END -->",
    re.DOTALL,
)


def _static_size(text: str) -> int:
    return len(DYNAMIC_BLOCK.sub("", text).encode("utf-8"))


def test_implicit_rule_files_keep_their_context_budgets() -> None:
    """Both implicit files must leave room instead of merely fitting today."""
    assert CLAUDE_MD.exists(), "CLAUDE.md missing at repo root"
    claude_static = _static_size(CLAUDE_MD.read_text(encoding="utf-8"))
    free = MAX_STATIC_BYTES - claude_static
    assert claude_static <= MAX_STATIC_BYTES
    assert free >= MIN_HEADROOM_BYTES, (
        f"CLAUDE.md leaves {free}B free; keep at least {MIN_HEADROOM_BYTES}B "
        "for the next necessary pointer"
    )

    agents_static = _static_size(AGENTS_MD.read_text(encoding="utf-8"))
    assert agents_static <= 6_144 - 256, (
        f"AGENTS.md static portion is {agents_static}B; keep 256B free below 6144B"
    )


def test_claude_md_keeps_its_navigation_and_update_contract() -> None:
    """The small file stays writable and sends detail to the canonical document."""
    content = CLAUDE_MD.read_text(encoding="utf-8")
    assert "agent-contract.md" in content
    assert "<!-- DYNAMIC:START -->" in content
    assert "<!-- DYNAMIC:END -->" in content
    assert "What belongs here" in content or "Что имеет право стоять здесь" in content
    assert "claude-md-guide.md" in content

    static = DYNAMIC_BLOCK.sub("", content)
    counts = collections.Counter(re.findall(r"docs/(?:ru|en)/[a-z0-9-]+\.md", static))
    assert not {address: count for address, count in counts.items() if count > 1}
    assert AGENT_CONTRACT.exists()
    assert AGENT_CONTRACT.stat().st_size > 1024


def test_the_guide_carries_the_measurement_that_set_the_rule() -> None:
    for rel in ("docs/ru/claude-md-guide.md", "docs/en/claude-md-guide.md"):
        text = (REPO_ROOT / rel).read_text(encoding="utf-8")
        assert "4096" in text and "13" in text, rel
