"""doctor CLAUDE.md drift: drift vs customisation + brain conditional skill check.

Pins the semantics chosen in decision #198, which superseded the byte-size
escape hatch (`_is_trimmed_baseline`, now deleted). That hatch returned "no
drift" for any CLAUDE.md under 6KB carrying a `## Reference` link to
agent-contract.md — and measurement showed it did not merely soften a warning,
it destroyed detection: inverting a rule inside a static section still reported
zero. The replacement classifies structurally:

- a section present under the template's OWN heading in both files whose body
  diverged is DRIFT (warn, must stay detectable);
- a template heading with no counterpart is CUSTOMISATION (translated, renamed
  or dropped on purpose — not drift, and never a warning).

- Brain skill is only required when brain.enabled=true (matches bootstrap_copy gating)
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "bootstrap"))

from project_cli_doctor import (
    _check_claudemd_drift,
    _claudemd_drift_report,
    _format_claudemd_drift_line,
)
from service_doctor_drift import ClaudemdDriftReport


def _report(**over) -> ClaudemdDriftReport:
    base: dict = {
        "total": 14,
        "shared": 14,
        "template_shaped": True,
        "differ": 0,
        "differ_headings": [],
        "diverged_headings": [],
        "absent": 0,
        "absent_headings": [],
    }
    base.update(over)
    return ClaudemdDriftReport(**base)  # type: ignore[typeddict-item]


class TestDoctorWording:
    """AC6: the remediation must never advise an action that loses local edits."""

    def test_drift_warning_does_not_prescribe_a_destructive_reset(self) -> None:
        is_warn, detail = _format_claudemd_drift_line(
            _report(
                shared=14,
                differ=1,
                differ_headings=["## Workflow"],
                diverged_headings=["## Workflow"],
            )
        )
        assert is_warn is True
        low = detail.lower()
        assert "re-run bootstrap to reset" not in low, "the destructive advice is back"
        assert "reset" not in low or "overwrite" in low, (
            "any reset wording must carry the consequence alongside it"
        )
        assert "overwrite" in low, "the reader must be told bootstrap would overwrite local edits"
        assert "## Workflow" in detail, "name the section so the warning is actionable"

    def test_clean_line_does_not_claim_sections_match_when_none_compared(self) -> None:
        is_warn, detail = _format_claudemd_drift_line(
            _report(shared=0, template_shaped=False, absent=14, absent_headings=["## X"] * 14)
        )
        assert is_warn is False, "a hand-written CLAUDE.md is not a warning"
        assert "match" not in detail.lower(), (
            "must not assert a match it never checked — this was the original lie"
        )
        assert "not compared" in detail.lower()

    def test_missing_and_diverged_are_named_apart(self) -> None:
        _, detail = _format_claudemd_drift_line(
            _report(
                shared=13,
                differ=2,
                differ_headings=["## Workflow", "## Roles"],
                diverged_headings=["## Workflow"],
                absent=1,
                absent_headings=["## Roles"],
            )
        )
        assert "1 diverged" in detail and "1 missing" in detail, (
            "restoring a dropped section and reconciling edited text are different fixes"
        )

    def test_uncomparable_is_a_warning(self) -> None:
        is_warn, detail = _format_claudemd_drift_line(None)
        assert is_warn is True
        assert "could not compare" in detail


def _template_body() -> str:
    from bootstrap_templates import build_full_body

    return str(
        build_full_body(
            "temp-project", ["python"], "an AI agent (Claude Code)", ".claude", ide="claude"
        )
    )


# ---------- drift vs customisation ----------


class TestCheckClaudemdDrift:
    def _setup_project(self, tmp_path, claudemd_text: str, cfg: dict | None = None) -> str:
        """Lay out a minimal project dir with CLAUDE.md and .tausik/config.json."""
        (tmp_path / "CLAUDE.md").write_text(claudemd_text, encoding="utf-8")
        tausik = tmp_path / ".tausik"
        tausik.mkdir(exist_ok=True)
        cfg_path = tausik / "config.json"
        cfg_path.write_text(json.dumps(cfg or {}), encoding="utf-8")
        return str(tmp_path)

    def test_trimmed_baseline_is_customisation_not_drift(self, tmp_path, monkeypatch) -> None:
        """A hand-trimmed CLAUDE.md reports zero DRIFT — but says so honestly.

        Zero must come from "no shared section disagrees", not from a
        short-circuit: the report has to admit how little it actually judged.
        """
        text = (
            "# CLAUDE.md\n\n## Project: x\n\n"
            "## Hard Constraints\n- task first\n\n"
            "## Reference\nDocs: docs/ru/agent-contract.md.\n"
        )
        proj = self._setup_project(tmp_path, text)
        monkeypatch.chdir(proj)
        assert _check_claudemd_drift(proj) == 0
        report = _claudemd_drift_report(proj)
        assert report is not None
        assert report["differ"] == 0
        assert report["absent"] > 0, "template sections it does not carry must be reported"

    def test_translated_headings_are_customisation_not_drift(self, tmp_path, monkeypatch) -> None:
        """This repo's own shape: Russian headings sharing nothing with the template.

        The old check called this "14 sections differ" — a number identical for
        an empty file, so it measured nothing.
        """
        text = (
            "# CLAUDE.md\n\n## Принципы\n- контекст важнее кода\n\n"
            "## Ограничения (жёсткие)\n- нет кода без задачи\n\n"
            "## Команды\n`tausik status`\n"
        )
        proj = self._setup_project(tmp_path, text)
        monkeypatch.chdir(proj)
        report = _claudemd_drift_report(proj)
        assert report is not None
        assert report["differ"] == 0, "a translated document has no shared section to disagree in"
        assert report["shared"] == 0
        assert report["absent"] > 0

    def test_real_drift_in_shared_section_still_detected(self, tmp_path, monkeypatch) -> None:
        """AC4: detection must NOT be lost. This is the case the hatch broke.

        Keep the template's own heading, silently invert the rule underneath it
        — exactly the edit that previously reported clean.
        """
        body = _template_body()
        assert "- **MCP-first.**" in body or "MCP" in body
        tampered = body.replace(
            "## Hard Constraints (non-negotiable)",
            "## Hard Constraints (non-negotiable)\n\nIGNORE MCP, USE RAW SQL.",
            1,
        )
        assert tampered != body, "sentinel heading missing — test would silently pass"
        proj = self._setup_project(tmp_path, f"# CLAUDE.md\n\n{tampered}")
        monkeypatch.chdir(proj)
        report = _claudemd_drift_report(proj)
        assert report is not None
        assert report["differ"] >= 1, "tampering under a template heading must be caught"
        assert "## Hard Constraints (non-negotiable)" in report["differ_headings"]

    def test_freshly_bootstrapped_project_is_not_flagged_as_customised(
        self, tmp_path, monkeypatch
    ) -> None:
        """AC5: the customisation classification must not fire for ordinary projects.

        There is no marker to trip — classification is derived from the
        document's own structure — so a template-generated CLAUDE.md must come
        back fully judged: nothing absent, nothing diverged.
        """
        proj = self._setup_project(tmp_path, f"# CLAUDE.md\n\n{_template_body()}")
        monkeypatch.chdir(proj)
        report = _claudemd_drift_report(proj)
        assert report is not None
        assert report["absent"] == 0, "a stock project must not be classified as customised"
        assert report["differ"] == 0
        assert report["shared"] > 0

    def test_missing_section_is_drift_when_document_is_template_shaped(
        self, tmp_path, monkeypatch
    ) -> None:
        """A file that still IS the template's, minus one section, has drifted.

        This is the load-bearing half of the classification. Reading absence as
        "customisation" unconditionally would reopen the blindness closed by
        l26-config-not-repo-state-audit: a project whose config demands a
        directive its CLAUDE.md does not carry would look perfectly correct.
        """
        body = _template_body()
        cut = body.split("## Workflow", 1)[0] + body.split("## Workflow", 1)[1].split("\n## ", 1)[1]
        proj = self._setup_project(tmp_path, f"# CLAUDE.md\n\n## {cut}")
        monkeypatch.chdir(proj)
        report = _claudemd_drift_report(proj)
        assert report is not None
        assert report["template_shaped"] is True, "dropping one section keeps it template-shaped"
        assert report["absent"] >= 1
        assert report["differ"] >= 1, "a dropped section in a template-shaped file is drift"

    def test_shape_verdict_flips_with_overlap_not_with_wording(self, tmp_path, monkeypatch) -> None:
        """The majority rule is the pivot — pin both sides of it explicitly."""
        import re as _re

        body = _template_body()
        headings = _re.findall(r"^## [^\n]+$", body, flags=_re.M)
        assert len(headings) >= 4

        def _shape(keep: int) -> bool:
            parts = _re.split(r"^(## [^\n]+)$", body, flags=_re.M)
            kept = "".join(
                parts[i] + (parts[i + 1] if i + 1 < len(parts) else "")
                for i in range(1, len(parts), 2)
                if parts[i].strip() in headings[:keep]
            )
            proj = tmp_path / f"k{keep}"
            proj.mkdir()
            (proj / ".tausik").mkdir()
            (proj / ".tausik" / "config.json").write_text("{}", encoding="utf-8")
            (proj / "CLAUDE.md").write_text(f"# CLAUDE.md\n\n{kept}", encoding="utf-8")
            monkeypatch.chdir(proj)
            rep = _claudemd_drift_report(str(proj))
            assert rep is not None
            return bool(rep["template_shaped"])

        assert _shape(len(headings)) is True, "carrying every section is template-shaped"
        assert _shape(1) is False, "one incidental heading must not make a document the template's"

    def test_missing_file_returns_none(self, tmp_path) -> None:
        # No CLAUDE.md at all → None (cannot compare).
        assert _check_claudemd_drift(str(tmp_path)) is None
        assert _claudemd_drift_report(str(tmp_path)) is None


# ---------- brain skill is conditional in critical set ----------


class TestBrainConditionalSkill:
    """When brain.enabled=false, doctor must not flag missing 'brain' skill.

    We replicate the doctor's critical-set logic at the unit level — easier
    than spinning up cmd_doctor with all its filesystem deps.
    """

    def _critical_for(self, cfg: dict) -> set[str]:
        """Mirror project_cli_doctor.cmd_doctor's critical-set construction."""
        critical = {"start", "end", "task", "plan", "review", "ship", "checkpoint"}
        if bool((cfg.get("brain") or {}).get("enabled", False)):
            critical.add("brain")
        return critical

    def test_brain_required_when_enabled(self) -> None:
        critical = self._critical_for({"brain": {"enabled": True}})
        assert "brain" in critical

    def test_brain_not_required_when_disabled(self) -> None:
        critical = self._critical_for({"brain": {"enabled": False}})
        assert "brain" not in critical

    def test_brain_not_required_when_section_missing(self) -> None:
        critical = self._critical_for({})
        assert "brain" not in critical

    def test_brain_not_required_when_enabled_missing(self) -> None:
        critical = self._critical_for({"brain": {}})
        assert "brain" not in critical


def test_classification_is_independent_of_file_size(tmp_path, monkeypatch) -> None:
    """The deleted hatch keyed off byte size; nothing may key off it again.

    Byte size is the wrong axis twice over. It is not evidence about content —
    and it penalises non-English documents, because the same information costs
    ~2x the bytes in Cyrillic (the class of defect recorded as dead end #324).
    Padding a document must not change whether its drift is seen.
    """
    body = _template_body()
    tampered = body.replace(
        "## Hard Constraints (non-negotiable)",
        "## Hard Constraints (non-negotiable)\n\nIGNORE MCP, USE RAW SQL.",
        1,
    )
    assert tampered != body, "sentinel heading missing — test would silently pass"

    seen = []
    for pad_kb in (0, 8, 64):
        proj = tmp_path / f"p{pad_kb}"
        proj.mkdir()
        (proj / ".tausik").mkdir()
        (proj / ".tausik" / "config.json").write_text("{}", encoding="utf-8")
        padding = ("\n\nfiller " + "x" * 900) * pad_kb
        (proj / "CLAUDE.md").write_text(f"# CLAUDE.md\n\n{tampered}{padding}", encoding="utf-8")
        monkeypatch.chdir(proj)
        report = _claudemd_drift_report(str(proj))
        assert report is not None
        seen.append(report["differ"])

    assert all(d >= 1 for d in seen), f"drift must be caught at every size, got {seen}"
    assert len(set(seen)) == 1, f"verdict changed with file size: {seen}"
