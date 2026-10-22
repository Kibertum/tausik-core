"""Cursor economy baseline doc: method present, honesty intact, unknown named."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_en_and_ru_name_unknown_and_forbid_codex_relabel():
    en = (ROOT / "docs/en/cursor-economy-baseline.md").read_text(encoding="utf-8")
    ru = (ROOT / "docs/ru/cursor-economy-baseline.md").read_text(encoding="utf-8")
    for text in (en, ru):
        assert "unknown" in text.lower()
        assert "tausik_memory_brief" in text
        assert "session_start" in text and "verify" in text
        assert "codex" in text.lower()
        assert "usd" in text.lower() or "API-USD" in text or "API-USD" in en
    assert "relabel" in en.lower() or "must not" in en.lower()
    assert "переклеивать" in ru or "нельзя" in ru
