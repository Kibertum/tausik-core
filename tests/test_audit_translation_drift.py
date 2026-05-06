"""Tests for `scripts/audit_translation_drift.py` (v14b-junk-translation-drift-audit).

Covers:
  AC-1 — script runs in markdown / JSON / --check modes with sane exits.
  AC-2 — pairing: paired-with-drift, en-only, ru-only categorised correctly.
  AC-3 — drift detection: heading mismatch, code-block mismatch, table mismatch.
  AC-3 (negative) — perfect EN/RU match produces no drift.
  AC-6 (negative) — default mode always exits 0; --check exits 1 only on
    paired drift, never on unpaired files alone.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from audit_translation_drift import (  # noqa: E402
    audit_pairs,
    count_metrics,
    main,
    render_json,
    render_markdown,
)


@pytest.fixture
def fake_repo(tmp_path: Path) -> Path:
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "x"\n', encoding="utf-8")
    (tmp_path / "docs" / "en").mkdir(parents=True)
    (tmp_path / "docs" / "ru").mkdir(parents=True)
    return tmp_path


def _write(repo: Path, lang: str, name: str, body: str) -> None:
    (repo / "docs" / lang / name).write_text(body, encoding="utf-8")


def test_count_metrics_headings_code_tables() -> None:
    text = (
        "# H1\n"
        "## H2\n"
        "### H3\n"
        "Some text.\n"
        "```python\n"
        "x = 1\n"
        "```\n"
        "\n"
        "| col | col |\n"
        "|-----|-----|\n"
        "| a   | b   |\n"
    )
    m = count_metrics(text)
    assert m.headings == 3
    assert m.code_blocks == 2  # open + close fence
    assert m.tables == 1  # one separator row


def test_perfect_match_no_drift(fake_repo: Path) -> None:
    body = "# T\n## S\n```py\nx=1\n```\n"
    _write(fake_repo, "en", "matched.md", body)
    _write(fake_repo, "ru", "matched.md", body)
    drifts, en_only, ru_only = audit_pairs(fake_repo)
    assert drifts == []
    assert en_only == []
    assert ru_only == []


def test_heading_mismatch_flags_drift(fake_repo: Path) -> None:
    _write(fake_repo, "en", "h.md", "# A\n## B\n### C\n")
    _write(fake_repo, "ru", "h.md", "# A\n")
    drifts, _, _ = audit_pairs(fake_repo)
    assert len(drifts) == 1
    assert drifts[0].basename == "h.md"
    assert drifts[0].deltas()["headings"] == 2  # EN has 2 more


def test_code_block_mismatch_flags_drift(fake_repo: Path) -> None:
    en_body = "# T\n```py\nx=1\n```\n```js\ny=2\n```\n"
    ru_body = "# T\n```py\nx=1\n```\n"
    _write(fake_repo, "en", "c.md", en_body)
    _write(fake_repo, "ru", "c.md", ru_body)
    drifts, _, _ = audit_pairs(fake_repo)
    assert len(drifts) == 1
    assert drifts[0].deltas()["code_blocks"] == 1  # one extra logical block on EN


def test_table_mismatch_flags_drift(fake_repo: Path) -> None:
    en_body = "# T\n\n| a | b |\n|---|---|\n| 1 | 2 |\n\n| c | d |\n|---|---|\n| 3 | 4 |\n"
    ru_body = "# T\n\n| a | b |\n|---|---|\n| 1 | 2 |\n"
    _write(fake_repo, "en", "t.md", en_body)
    _write(fake_repo, "ru", "t.md", ru_body)
    drifts, _, _ = audit_pairs(fake_repo)
    assert len(drifts) == 1
    assert drifts[0].deltas()["tables"] == 1


def test_unpaired_categorisation(fake_repo: Path) -> None:
    _write(fake_repo, "en", "shared.md", "# T\n")
    _write(fake_repo, "ru", "shared.md", "# T\n")
    _write(fake_repo, "en", "en-only.md", "# T\n")
    _write(fake_repo, "ru", "ru-only.md", "# T\n")
    drifts, en_only, ru_only = audit_pairs(fake_repo)
    assert drifts == []
    assert en_only == ["en-only.md"]
    assert ru_only == ["ru-only.md"]


def test_render_markdown_no_drift_message(fake_repo: Path) -> None:
    out = render_markdown([], [], [])
    assert "No structural drift detected" in out


def test_render_markdown_drift_table(fake_repo: Path) -> None:
    _write(fake_repo, "en", "x.md", "# A\n## B\n")
    _write(fake_repo, "ru", "x.md", "# A\n")
    drifts, _, _ = audit_pairs(fake_repo)
    out = render_markdown(drifts, [], [])
    assert "structural drift" in out
    assert "`x.md`" in out
    assert "+1" in out  # +1 heading delta


def test_render_json_shape(fake_repo: Path) -> None:
    _write(fake_repo, "en", "x.md", "# A\n## B\n")
    _write(fake_repo, "ru", "x.md", "# A\n")
    drifts, en_only, ru_only = audit_pairs(fake_repo)
    out = render_json(drifts, en_only, ru_only)
    import json

    payload = json.loads(out)
    assert "drifts" in payload and len(payload["drifts"]) == 1
    assert payload["drifts"][0]["basename"] == "x.md"
    assert payload["drifts"][0]["deltas"]["headings"] == 1


def test_main_default_exit_zero_even_with_drift(
    fake_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write(fake_repo, "en", "x.md", "# A\n## B\n")
    _write(fake_repo, "ru", "x.md", "# A\n")
    rc = main(["--repo-root", str(fake_repo)])
    assert rc == 0  # advisory by default
    out = capsys.readouterr().out
    assert "structural drift" in out


def test_main_check_exits_one_on_drift(fake_repo: Path) -> None:
    _write(fake_repo, "en", "x.md", "# A\n## B\n")
    _write(fake_repo, "ru", "x.md", "# A\n")
    rc = main(["--check", "--repo-root", str(fake_repo)])
    assert rc == 1


def test_main_check_exits_zero_when_no_drift(fake_repo: Path) -> None:
    _write(fake_repo, "en", "x.md", "# A\n")
    _write(fake_repo, "ru", "x.md", "# A\n")
    rc = main(["--check", "--repo-root", str(fake_repo)])
    assert rc == 0


def test_main_check_does_not_flag_on_unpaired_only(fake_repo: Path) -> None:
    """Unpaired files alone are informational and must NOT trigger --check exit 1."""
    _write(fake_repo, "en", "en-only.md", "# A\n")
    _write(fake_repo, "ru", "ru-only.md", "# A\n")
    rc = main(["--check", "--repo-root", str(fake_repo)])
    assert rc == 0


def test_main_json_mode_emits_valid_json(
    fake_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write(fake_repo, "en", "x.md", "# A\n")
    _write(fake_repo, "ru", "x.md", "# A\n")
    rc = main(["--json", "--repo-root", str(fake_repo)])
    assert rc == 0
    out = capsys.readouterr().out
    import json

    json.loads(out)  # raises if invalid
