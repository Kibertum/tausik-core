"""Tests for the caveman output-economy mode and its interop check.

The mode is TAUSIK's own OUTPUT compression (inspired by github.com/JuliusBrussee/caveman),
orthogonal to context_tier (which sizes the INPUT rules). It is opt-in, off by default, and
shipped as a directive baked into the generated rules — NOT via caveman's hook installer,
which would collide with TAUSIK's SessionStart hook and settings.json ownership.

Every guard here defends a token-economy or agent-first invariant:
- the injected directive is itself a per-session token line-item, so its length is capped;
- code/commands/errors must never be told to compress;
- verification records (AC evidence, decisions) must stay full-fidelity for future agents;
- a bad config value must never crash a bootstrap.
"""

from __future__ import annotations

import json
import os
import sys

import pytest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for _p in (os.path.join(_ROOT, "bootstrap"), os.path.join(_ROOT, "scripts")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from bootstrap_templates import (  # noqa: E402
    CAVEMAN_DIRECTIVE,
    CAVEMAN_DIRECTIVE_MAX_CHARS,
    build_full_body,
)
from bootstrap_config import DEFAULT_OUTPUT_MODE, resolve_output_mode  # noqa: E402


def _body(output_mode="off", context_tier="standard", ide="claude"):
    return build_full_body(
        "proj",
        ["python"],
        "an agent",
        ".claude",
        ide=ide,
        context_tier=context_tier,
        output_mode=output_mode,
    )


class TestDirectiveInjection:
    def test_off_by_default_no_directive(self):
        assert "caveman mode" not in _body(output_mode="off")

    def test_caveman_injects_directive(self):
        body = _body(output_mode="caveman")
        assert "Output economy (caveman mode)" in body
        assert "github.com/JuliusBrussee/caveman" in body, "attribution must be present"

    def test_directive_present_in_every_tier(self):
        """output_mode is orthogonal to tier — it must apply even in minimal."""
        for tier in ("minimal", "standard", "full"):
            assert "caveman mode" in _body(output_mode="caveman", context_tier=tier), tier

    def test_directive_reaches_every_ide_via_one_source(self):
        """All IDEs share build_full_body, so the directive lands uniformly — not via 5 copies."""
        for ide in ("claude", "cursor", "qwen", "opencode", None):
            assert "caveman mode" in _body(output_mode="caveman", ide=ide), ide


class TestDirectiveIsLean:
    def test_directive_under_length_ceiling(self):
        """The directive is injected EVERY session; a fat one would cost more input than the
        terse output saves. If this fails, the mode is defeating its own purpose."""
        assert len(CAVEMAN_DIRECTIVE) <= CAVEMAN_DIRECTIVE_MAX_CHARS, (
            f"directive is {len(CAVEMAN_DIRECTIVE)} chars, ceiling is {CAVEMAN_DIRECTIVE_MAX_CHARS}"
        )

    def test_ceiling_is_actually_enforced_not_vacuous(self):
        """Guard the guard: the ceiling must be a real bound, not set absurdly high."""
        assert CAVEMAN_DIRECTIVE_MAX_CHARS < 2000


class TestCarveOuts:
    def test_directive_protects_code_and_errors(self):
        d = CAVEMAN_DIRECTIVE.lower()
        for term in ("code", "command", "error", "path"):
            assert term in d, f"directive must carve out {term!r} from compression"

    def test_directive_protects_verification_records(self):
        d = CAVEMAN_DIRECTIVE.lower()
        assert "acceptance" in d or "evidence" in d
        assert "decision" in d
        assert "spec" in d or "adapt" in d


class TestResolveOutputMode:
    def test_default_is_off(self):
        assert DEFAULT_OUTPUT_MODE == "off"
        assert resolve_output_mode(None) == "off"
        assert resolve_output_mode({}) == "off"

    def test_valid_value(self):
        assert resolve_output_mode({"output_mode": "caveman"}) == "caveman"

    def test_normalization_accepts_case_and_whitespace(self):
        """'CAVEMAN' / ' caveman ' normalize to caveman rather than falling back — silently
        disabling a mode the user clearly asked for is the worse (surprising) outcome."""
        assert resolve_output_mode({"output_mode": "CAVEMAN"}) == "caveman"
        assert resolve_output_mode({"output_mode": "  caveman  "}) == "caveman"

    @pytest.mark.parametrize("bad", ["ultra", "wenyan", "caveman-lite", 42, 3.14, None, "", [], {}])
    def test_truly_invalid_falls_back_to_off_never_crashes(self, bad):
        """A typo in an output-economy knob must never break a bootstrap."""
        assert resolve_output_mode({"output_mode": bad}) == "off"

    def test_non_dict_config_is_safe(self):
        assert resolve_output_mode("not a dict") == "off"
        assert resolve_output_mode(42) == "off"


class TestModeDoesNotLeakIntoVerificationRecords:
    """AC evidence, decisions and SPEC/ADAPT are written by the service/DB layer, not by
    the rules templates. `output_mode` must never reach those writers: compressing a
    verification record would break the agent-first contract (future agents parse them).

    An earlier version of this test greped `bootstrap_generate` for `def record_evidence`
    / `def add_decision` — names that live in `scripts/project_cli_task.py` and were never
    going to appear there. It could not fail. This one reads the REAL writer modules.
    """

    def _writer_sources(self):
        import glob

        paths = [os.path.join(_ROOT, "scripts", "project_cli_task.py")]
        paths += glob.glob(os.path.join(_ROOT, "harness", "*", "mcp", "project", "handlers*.py"))
        found = {p: open(p, encoding="utf-8").read() for p in paths if os.path.isfile(p)}
        assert found, "no verification-record writer modules found — test would be vacuous"
        return found

    def test_writers_exist_where_this_test_looks(self):
        """Guard the guard: if the writers move, this test must fail loudly rather than
        keep passing against nothing."""
        srcs = self._writer_sources()
        joined = "\n".join(srcs.values())
        assert "def record_evidence" in joined or "evidence" in joined, (
            "the modules this test inspects no longer contain evidence-writing code — "
            "re-point the test instead of letting it pass vacuously"
        )

    def test_output_mode_never_reaches_a_verification_writer(self):
        leaked = [p for p, src in self._writer_sources().items() if "output_mode" in src]
        assert not leaked, (
            f"output_mode leaked into verification-record writers: {leaked}. The mode is a "
            "rules directive only — a compressed AC evidence string is unreadable to the "
            "next agent."
        )


# --- interop -----------------------------------------------------------------

from service_doctor_caveman import check_caveman_interop  # noqa: E402


class TestCavemanInterop:
    def test_silent_when_no_caveman(self, tmp_path):
        assert check_caveman_interop(str(tmp_path)) == []

    def test_detects_cursor_rule_file(self, tmp_path):
        rule = tmp_path / ".cursor" / "rules" / "caveman.mdc"
        rule.parent.mkdir(parents=True)
        rule.write_text("caveman rules\n", encoding="utf-8")
        findings = check_caveman_interop(str(tmp_path))
        assert findings
        assert any("external caveman detected" in d for _s, _l, d in findings)

    def test_detects_active_flag(self, tmp_path):
        (tmp_path / ".caveman-active").write_text("full\n", encoding="utf-8")
        assert check_caveman_interop(str(tmp_path))

    def test_warns_on_settings_json_overlap(self, tmp_path):
        claude = tmp_path / ".claude"
        claude.mkdir()
        (claude / "settings.json").write_text(
            '{"hooks":{"SessionStart":[{"command":"node caveman-activate.js"}]}}', encoding="utf-8"
        )
        findings = check_caveman_interop(str(tmp_path))
        assert any(s == "warn" for s, _l, _d in findings), "settings.json overlap must warn"
        assert any("settings.json" in d for _s, _l, d in findings)

    def test_no_false_positive_on_incidental_word(self, tmp_path):
        """A bare substring search cried wolf on any settings.json mentioning the word.
        A doctor that warns about nothing teaches people to ignore doctor."""
        claude = tmp_path / ".claude"
        claude.mkdir()
        (claude / "settings.json").write_text(
            json.dumps(
                {
                    "projectName": "caveman-widgets",
                    "hooks": {
                        "SessionStart": [
                            {"hooks": [{"type": "command", "command": "python scripts/lint.py"}]}
                        ]
                    },
                }
            ),
            encoding="utf-8",
        )
        findings = check_caveman_interop(str(tmp_path))
        assert not any(s == "warn" for s, _l, _d in findings), (
            "an incidental 'caveman' string produced a bogus collision warning"
        )

    def test_real_caveman_hook_still_warns(self, tmp_path):
        """The converse: the guard must still bite on a genuine caveman hook."""
        claude = tmp_path / ".claude"
        claude.mkdir()
        (claude / "settings.json").write_text(
            json.dumps(
                {
                    "hooks": {
                        "SessionStart": [
                            {"hooks": [{"type": "command", "command": "node caveman-activate.js"}]}
                        ]
                    }
                }
            ),
            encoding="utf-8",
        )
        assert any(s == "warn" for s, _l, _d in check_caveman_interop(str(tmp_path)))

    def test_never_a_fail_and_never_raises(self, tmp_path):
        """A co-installed caveman is not an error; a broken check must not crash doctor."""
        # malformed settings.json must not raise
        claude = tmp_path / ".claude"
        claude.mkdir()
        (claude / "settings.json").write_text("{ not json", encoding="utf-8")
        findings = check_caveman_interop(str(tmp_path))
        assert all(s in ("ok", "warn") for s, _l, _d in findings)
