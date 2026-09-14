"""Keep the public Codex hard-guarantee claim tied to a generated profile.

The failure mode is documentation widening after the generator changed: a row can
say ``hard`` while no installed Codex hook can intercept the host action.  This
test reads the EN/RU matrix, builds the profile a user receives, and checks the
same rule-coverage classifier used by the generated host notice.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
for _path in (str(_ROOT / "scripts"), str(_ROOT / "bootstrap")):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from bootstrap_codex import generate_codex_hooks  # noqa: E402
import rule_coverage as coverage  # noqa: E402


MATRIX_HEADING = "### Codex enforcement matrix"
RU_MATRIX_HEADING = "### Матрица принуждения Codex"
PROMISED_RULES = (
    "QG-0 Context Gate",
    "QG-2 Implementation Gate / Verify-First",
    "Rule 9.2 Session limit",
    "Rule 1 Task before code",
    "Rule 2 Scope Boundaries",
)
RULE_COVERAGE_NAMES = {
    "QG-0 Context Gate": "QG-0 Context Gate",
    "QG-2 Implementation Gate / Verify-First": "QG-2 Implementation Gate",
    "Rule 9.2 Session limit": "Rule 9.2 Session limit",
    "Rule 1 Task before code": "Rule 1 Task before code",
    "Rule 2 Scope Boundaries": "Rule 2 Scope Boundaries",
}


def _matrix_rows(path: Path, heading: str) -> dict[str, list[str]]:
    text = path.read_text(encoding="utf-8")
    section = text.split(heading, 1)[1].split("\n## ", 1)[0]
    rows = {}
    for line in section.splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) == 3 and cells[1] in {"hard", "instruction"}:
            rows[cells[0]] = cells
    return rows


def _generated_codex_profile(tmp_path: Path) -> Path:
    profile = tmp_path / ".codex"
    generate_codex_hooks(str(tmp_path), str(profile))
    return profile


def test_codex_matrix_is_complete_and_language_paired():
    en_rows = _matrix_rows(_ROOT / "docs" / "en" / "model-providers.md", MATRIX_HEADING)
    ru_rows = _matrix_rows(_ROOT / "docs" / "ru" / "model-providers.md", RU_MATRIX_HEADING)
    assert tuple(en_rows) == PROMISED_RULES
    assert tuple(ru_rows) == PROMISED_RULES
    assert all(row[1] == "hard" for row in en_rows.values())
    assert all(row[1] == "hard" for row in ru_rows.values())


def test_every_hard_codex_row_has_a_mechanism_in_the_generated_profile(tmp_path):
    profile = _generated_codex_profile(tmp_path)
    held = {rule.rule: mode for rule, mode in coverage.coverage_for_host(str(profile))}

    for promised, coverage_name in RULE_COVERAGE_NAMES.items():
        assert held[coverage_name] in {coverage.SURFACE, "realtime"}, (
            f"{promised} is documented hard but generated Codex has no mechanism: "
            f"{held[coverage_name]}"
        )


# The two rows whose mechanism is the HOST intercepting its own action. A hook
# file on disk is only half of that mechanism: Codex runs a project's hooks
# only after the user has trusted them, and the live acceptance run measured
# the other half — an untrusted generated profile let the forbidden write
# through (session #251). The profile scan above cannot see trust, so the
# precondition must be stated on the row itself, in both languages.
HOST_INTERCEPTION_RULES = ("Rule 1 Task before code", "Rule 2 Scope Boundaries")
TRUST_MARKERS = {"en": ("trusted",), "ru": ("довери",)}


@pytest.mark.parametrize(("lang", "heading"), [("en", MATRIX_HEADING), ("ru", RU_MATRIX_HEADING)])
def test_host_interception_rows_state_the_trust_precondition(lang, heading):
    rows = _matrix_rows(_ROOT / "docs" / lang / "model-providers.md", heading)
    for rule in HOST_INTERCEPTION_RULES:
        mechanism = rows[rule][2].lower()
        assert any(marker in mechanism for marker in TRUST_MARKERS[lang]), (
            f"{lang}: {rule} is documented hard without naming the trusted-hooks "
            "precondition — an untrusted Codex profile enforces nothing (measured live)"
        )


@pytest.mark.parametrize("lang", ["en", "ru"])
def test_no_page_claims_codex_enforcement_without_the_precondition(lang):
    """The prose above the matrix made the same claim in one sentence; that
    sentence must carry the condition too, in the same paragraph."""
    text = (_ROOT / "docs" / lang / "model-providers.md").read_text(encoding="utf-8")
    key = "not merely instructed" if lang == "en" else "не просто предписываются"
    para = next(p for p in text.split("\n>\n") if key in p)
    assert any(m in para.lower() for m in TRUST_MARKERS[lang]), (
        f"{lang}: the enforcement sentence stands without the trust precondition"
    )


def test_removing_the_generated_hooks_rejects_host_operation_hard_claims(tmp_path):
    profile = _generated_codex_profile(tmp_path)
    (profile / "hooks.json").unlink()
    held = {rule.rule: mode for rule, mode in coverage.coverage_for_host(str(profile))}

    assert held["Rule 1 Task before code"] == coverage.NEEDS_INTERCEPTION
    assert held["Rule 2 Scope Boundaries"] == coverage.NEEDS_INTERCEPTION
