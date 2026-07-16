"""Guard tests: docs must not advertise packages or IDE support that do not exist.

Both failure modes below were live in the docs and cost a user a broken host.

  1. **Fake npm package.** `docs/*/model-providers.md` told the reader to run
     `npm i -g @anthropic-ai/opencode`. No such package exists — OpenCode is built
     by SST and ships as `opencode-ai`. Docs that name a nonexistent package teach
     agents to invent plausible-but-wrong module names by analogy; that is exactly
     how a downstream project ended up importing `@opencode-ai/plugin@local` and
     hitting ERR_MODULE_NOT_FOUND.

  2. **Unbacked IDE support.** The platform table listed OpenCode as supported (with
     a skills dir it never reads), while `bootstrap` had no generator branch for it.
     An agent reading "supported" but finding nothing configured closed the gap by
     hand — inventing a `tools.qg0` object in `opencode.json`, where `tools` accepts
     booleans only. The host died with ConfigInvalidError.

The "Scaffolded" column is therefore checked against `bootstrap_config.SCAFFOLD_IDES`,
the single source of truth. Add an IDE to SCAFFOLD_IDES and the table must follow —
and vice versa. Each guard is paired with a test proving it FAILS on planted bad
input, so the guard cannot rot into a no-op.

Run: pytest tests/test_docs_no_fake_npm_packages.py -v
"""

from __future__ import annotations

import glob
import os
import re
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_BOOTSTRAP = os.path.join(_ROOT, "bootstrap")
if _BOOTSTRAP not in sys.path:
    sys.path.insert(0, _BOOTSTRAP)

from bootstrap_config import SCAFFOLD_IDES  # noqa: E402

# Package names that do not exist on npm but are plausible enough that both humans
# and agents keep reinventing them. Key = bogus name, value = the real one.
FAKE_NPM_PACKAGES = {
    "@anthropic-ai/opencode": "opencode-ai",
}

# Table display name -> the `--ide` key used by bootstrap.
_DISPLAY_TO_IDE_KEY = {
    "Claude Code": "claude",
    "Cursor": "cursor",
    "Qwen Code": "qwen",
    "Kilo Code": "kilo",
    "OpenCode": "opencode",
    "Codex": "codex",
    "Windsurf": "windsurf",
}

# Affirmative cell values across the ru/en tables.
_YES = {"yes", "да"}
_NO = {"no", "нет"}

_MODEL_PROVIDER_DOCS = [
    os.path.join(_ROOT, "docs", "en", "model-providers.md"),
    os.path.join(_ROOT, "docs", "ru", "model-providers.md"),
]


# What makes a bogus name harmful is being *told to install it*. Naming it in prose to
# warn readers off ("there is no @anthropic-ai/opencode package") is the fix, not the
# bug — so the guard fires only when the name rides an install command.
_INSTALL_CMD = re.compile(r"\b(?:npm\s+i(?:nstall)?|yarn\s+add|pnpm\s+add|bun\s+add)\b")


def _find_fake_packages(text: str) -> list[str]:
    """Return every bogus npm package the text instructs the reader to install."""
    offenders = []
    for line in text.splitlines():
        if not _INSTALL_CMD.search(line):
            continue
        offenders.extend(fake for fake in FAKE_NPM_PACKAGES if fake in line)
    return offenders


def _parse_scaffolded_column(text: str) -> dict[str, bool]:
    """Extract {ide_key: is_scaffolded} from the platform table.

    Rows look like `| OpenCode | no | opencode.json | — | AGENTS.md |`. Rows whose
    first cell is not a known platform (header, separator, other tables) are ignored.
    """
    found: dict[str, bool] = {}
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2:
            continue
        ide_key = _DISPLAY_TO_IDE_KEY.get(cells[0])
        if ide_key is None:
            continue
        value = cells[1].lower()
        if value in _YES:
            found[ide_key] = True
        elif value in _NO:
            found[ide_key] = False
        else:
            raise AssertionError(
                f"platform table row {cells[0]!r} has an unreadable Scaffolded cell "
                f"{cells[1]!r}; expected one of {sorted(_YES | _NO)}"
            )
    return found


def test_no_fake_npm_package_anywhere_in_docs():
    """No doc may name an npm package that does not exist."""
    offenders = []
    for path in glob.glob(os.path.join(_ROOT, "docs", "**", "*.md"), recursive=True):
        for fake in _find_fake_packages(open(path, encoding="utf-8").read()):
            rel = os.path.relpath(path, _ROOT)
            offenders.append(f"{rel}: {fake!r} does not exist — use {FAKE_NPM_PACKAGES[fake]!r}")
    assert not offenders, "docs advertise nonexistent npm packages:\n  " + "\n  ".join(offenders)


def test_fake_package_guard_actually_bites():
    """Negative scenario: the guard must flag a planted install line, not silently pass."""
    planted = "2. Install OpenCode: `npm i -g @anthropic-ai/opencode` (or via brew)\n"
    assert _find_fake_packages(planted) == ["@anthropic-ai/opencode"]
    assert _find_fake_packages("2. Install OpenCode: `npm i -g opencode-ai`\n") == []


def test_warning_prose_may_name_the_fake_package():
    """Naming the bogus package to warn readers off it must stay legal.

    Otherwise the guard would forbid the very sentence that prevents the mistake.
    """
    warning = "OpenCode is built by SST; there is no `@anthropic-ai/opencode` package.\n"
    assert _find_fake_packages(warning) == []


def test_platform_table_matches_scaffold_ides():
    """The Scaffolded column must agree with SCAFFOLD_IDES in every language."""
    mismatches = []
    for path in _MODEL_PROVIDER_DOCS:
        table = _parse_scaffolded_column(open(path, encoding="utf-8").read())
        rel = os.path.relpath(path, _ROOT)
        assert table, f"{rel}: platform table not found or unparseable"
        for ide_key, claimed in table.items():
            actual = ide_key in SCAFFOLD_IDES
            if claimed != actual:
                mismatches.append(
                    f"{rel}: {ide_key!r} claims scaffolded={claimed} "
                    f"but SCAFFOLD_IDES says {actual}"
                )
        for ide_key in SCAFFOLD_IDES:
            if ide_key not in table:
                mismatches.append(f"{rel}: scaffolded IDE {ide_key!r} is missing from the table")
    assert not mismatches, "platform table drifted from SCAFFOLD_IDES:\n  " + "\n  ".join(
        mismatches
    )


def test_scaffolded_column_guard_actually_bites():
    """Negative scenario: a row claiming scaffolded=yes must be READ as True, so that
    the real test above can catch it when SCAFFOLD_IDES disagrees.

    (An earlier version of this test ended in `assert table["opencode"] != (...) or
    (...)` — a tautology: `(True != B) or B` holds for every B, so it could not fail
    for any input. A guard's negative test must be able to go red.)
    """
    planted = "| OpenCode | yes | `opencode.json` | `.claude/skills/` | `AGENTS.md` |"
    assert _parse_scaffolded_column(planted) == {"opencode": True}

    denied = "| OpenCode | no | `opencode.json` | — | `AGENTS.md` |"
    assert _parse_scaffolded_column(denied) == {"opencode": False}

    # The parser feeds test_platform_table_matches_scaffold_ides, which compares these
    # values against the code. Since v1.7.0 OpenCode is really scaffolded, so a doc
    # row saying "no" is now the lie — and that is what must be caught.
    assert "opencode" in SCAFFOLD_IDES


def test_unreadable_scaffolded_cell_is_rejected():
    """Negative scenario: a vague cell ('partial', 'wip') must fail loudly, not be guessed."""
    import pytest

    with pytest.raises(AssertionError, match="unreadable Scaffolded cell"):
        _parse_scaffolded_column("| OpenCode | partial | `opencode.json` | — | `AGENTS.md` |")


def test_tools_key_boolean_only_warning_is_documented():
    """The ConfigInvalidError trap must stay documented in both languages.

    A reader who knows `tools` takes booleans will not hand-write a `tools.qg0`
    object. This is the cheapest possible fix for the class of bug that broke the
    user's host, so it must not silently disappear from the docs.
    """
    missing = []
    for path in _MODEL_PROVIDER_DOCS:
        text = open(path, encoding="utf-8").read()
        if "tools.qg0" not in text or "ConfigInvalidError" not in text:
            missing.append(os.path.relpath(path, _ROOT))
    assert not missing, "the tools-accepts-booleans-only warning was dropped from: " + ", ".join(
        missing
    )
