"""The changing part of a rules file comes last, so a change there costs only itself.

The host caches the longest unchanged prefix. The session state and the memory tail
change every session; kept at the very end (the DYNAMIC block), they invalidate nothing
that follows them. Declared in docs/{en,ru}/known-limitations.md.
"""

from __future__ import annotations

import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _p in ("bootstrap", "scripts"):
    sys.path.insert(0, os.path.join(_ROOT, _p))

from bootstrap_templates import build_full_body  # noqa: E402

START, END = "<!-- DYNAMIC:START -->", "<!-- DYNAMIC:END -->"


def static_after_dynamic(text: str) -> str:
    """Whatever non-blank text follows the dynamic block; empty when the order holds."""
    assert START in text and END in text, "no dynamic block to order"
    assert text.index(START) < text.index(END)
    return text.split(END, 1)[1].strip()


def test_the_generated_rules_file_ends_with_the_dynamic_block():
    body = build_full_body("proj", ["python"], "Claude Code", ".claude", ide="claude")
    assert static_after_dynamic(body) == ""


def test_this_repository_s_claude_md_ends_with_the_dynamic_block():
    with open(os.path.join(_ROOT, "CLAUDE.md"), encoding="utf-8") as f:
        assert static_after_dynamic(f.read()) == ""


def test_a_static_section_after_the_block_is_caught():
    """NEGATIVE: the check is not hollow."""
    body = f"# Rules\n\n{START}\nstate\n{END}\n\n## Late rule\n"
    assert static_after_dynamic(body) == "## Late rule"
