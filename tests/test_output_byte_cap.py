"""A line limit cannot see one enormous line — so there is a byte limit too.

The truncation nudge counted LINES with a threshold of 250. A minified file, a
JSON document on one line, a log without newlines: all of them enter the context
in full while the line counter reads "1". That blindness is the whole subject of
this file, and the test that matters is the third one below — one line, fifty
thousand bytes, and advice that names the cure.

MEASURED, NOT ASSUMED — AND THEN RE-READ. Session #229 measured the delta from
one call to the next inside one session: over 9,844 Bash calls, median 848, p90
2,514, p99 6,386, max 18,900. The byte default sits near that p99 so the nudge
speaks about calls that cost something.

The delta contains the tool's result AND the model's own output on that turn.
The first version of this note called all 66.4% of it "Bash", which credited the
command with what the model wrote. Split on the same 14,048 pairs: model output
is 71.6% of growth, tool results plus framing 28.4%; within Bash, 60.4% model and
39.6% result, so Bash RESULTS are 26.3% of all growth. The threshold stands (p99
is a property of the delta), the claim shrinks.

THE MEASUREMENT ALSO CORRECTED ITS OWN PREMISE, which is why the numbers are
here rather than in prose: the growth is BROAD, not tail-heavy — the top 1% of
Bash calls is only 6.8% of Bash's growth and 4.5% of everything. No catastrophic
single result appears in the corpus, because the Claude Code harness truncates
tool output itself. On a host that does not, it would. The byte threshold is
therefore worth most exactly where this framework promises the most and delivers
the least today: on hosts other than this one.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_HOOKS = _REPO / "scripts" / "hooks"
sys.path.insert(0, str(_HOOKS))
sys.path.insert(0, str(_REPO / "scripts"))

from tool_output_truncation_nudge import (  # noqa: E402
    DEFAULT_BYTE_THRESHOLD,
    DEFAULT_THRESHOLD,
    build_nudge,
    count_bytes,
    count_lines,
)

CROSSCUTTING_SCOPE = ["scripts/hooks/tool_output_truncation_nudge.py"]


class TestTheTwoThresholdsSeeDifferentDefects:
    def test_output_under_either_threshold_says_nothing(self):
        """Silence is the common case; a nudge that always fires is not read.

        Both quiet cases live here rather than in two tests of identical shape:
        comfortably small, and large-but-just-under the byte line. The second is
        the one that matters — an off-by-one there would make the byte rule
        swallow the silence the line rule is entitled to.
        """
        assert build_nudge("Bash", 5, 100, 250, 24000) == ""
        assert build_nudge("Bash", 1, 23_999, 250, 24_000) == ""
        assert build_nudge("Bash", 250, 24_000, 250, 24_000) == ""

    def test_many_short_lines_trips_the_line_threshold_only(self):
        msg = build_nudge("Bash", 900, 1000, 250, 24000)
        assert "900 lines" in msg
        assert "bytes" not in msg.split("Configure")[0].replace("24,000", "")

    def test_one_enormous_line_trips_the_byte_threshold(self):
        """THE defect. The line counter reads 1 and sees nothing wrong."""
        msg = build_nudge("Bash", 1, 50_000, 250, 24_000)
        assert msg, "a 50 KB single line produced no nudge at all"
        assert "50,000 bytes" in msg
        assert "1 lines" not in msg
        assert "a line limit cannot see this" in msg

    def test_the_byte_only_case_names_the_cure_a_line_limit_cannot_give(self):
        msg = build_nudge("Bash", 1, 50_000, 250, 24_000)
        assert "head -c" in msg, "advice that does not say what to do is noise"

    def test_both_over_names_both_and_still_offers_the_cap(self):
        msg = build_nudge("Bash", 900, 50_000, 250, 24_000)
        assert "900 lines" in msg and "50,000 bytes" in msg
        assert "head -c" in msg


class TestTheThresholdsAreMeasuredNotGuessed:
    def test_the_byte_default_sits_above_the_measured_p99(self):
        """p99 of Bash per-call growth was 6,386 tokens ~= 25 KB of text.

        A default below that would fire on ordinary work and be learned into
        invisibility — the failure mode of every warning nobody can act on.
        """
        assert DEFAULT_BYTE_THRESHOLD >= 20_000
        assert DEFAULT_BYTE_THRESHOLD <= 40_000

    def test_the_line_default_is_unchanged(self):
        """This task added a threshold; it did not retune the existing one."""
        assert DEFAULT_THRESHOLD == 250


class TestCountingIsInBytesNotCharacters:
    def test_cyrillic_costs_two_bytes_per_letter(self):
        """A character count would be twice as loose on Russian output, which is
        most of this project's own text."""
        assert count_bytes("привет") == 12
        assert len("привет") == 6

    def test_empty_and_newline_counting(self):
        assert count_bytes("") == 0
        assert count_lines("") == 0
        assert count_lines("a\nb") == 2
        assert count_lines("a\nb\n") == 2


class TestTheHookStaysAdviceAndLeaksNothing:
    """It must not censor, must not crash, and must not copy the output."""

    def _run(self, payload: dict, env: dict | None = None) -> subprocess.CompletedProcess:
        environ = dict(os.environ)
        environ.pop("TAUSIK_SKIP_HOOKS", None)
        environ.update(env or {})
        return subprocess.run(
            [sys.executable, str(_HOOKS / "tool_output_truncation_nudge.py")],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(_REPO),
            env=environ,
            timeout=60,
        )

    def test_the_output_itself_never_reaches_stderr(self):
        secret = "sk-ant-SUPERSECRET-do-not-leak"
        payload = {
            "tool_name": "Bash",
            "tool_response": {"output": secret + ("x" * 60_000)},
        }
        proc = self._run(payload)
        assert proc.returncode == 0
        assert secret not in proc.stderr
        assert "bytes" in proc.stderr  # it DID notice, it just did not quote

    def test_it_never_blocks_and_never_rewrites_the_result(self):
        proc = self._run({"tool_name": "Bash", "tool_response": {"output": "y" * 60_000}})
        assert proc.returncode == 0
        assert proc.stdout.strip() == "", "a coaching hook must not emit a decision on stdout"

    def test_malformed_input_is_survived_in_silence(self):
        for payload in ("", "not json", "[]", '{"tool_name": 7}'):
            proc = subprocess.run(
                [sys.executable, str(_HOOKS / "tool_output_truncation_nudge.py")],
                input=payload,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                cwd=str(_REPO),
                timeout=60,
            )
            assert proc.returncode == 0, f"hook died on {payload!r}: {proc.stderr[-200:]}"

    def test_an_unwatched_tool_is_ignored(self):
        proc = self._run({"tool_name": "WebFetch", "tool_response": {"output": "z" * 60_000}})
        assert proc.stderr.strip() == ""

    def test_a_non_numeric_env_threshold_falls_back_instead_of_crashing(self):
        proc = self._run(
            {"tool_name": "Bash", "tool_response": {"output": "z" * 60_000}},
            env={"TAUSIK_OUTPUT_TRUNCATION_BYTES": "not-a-number"},
        )
        assert proc.returncode == 0
        assert "bytes" in proc.stderr  # the default still applied

    def test_the_env_threshold_is_honoured_when_it_is_a_number(self):
        small = self._run(
            {"tool_name": "Bash", "tool_response": {"output": "z" * 5_000}},
            env={"TAUSIK_OUTPUT_TRUNCATION_BYTES": "1000"},
        )
        assert "5,000 bytes" in small.stderr
        quiet = self._run(
            {"tool_name": "Bash", "tool_response": {"output": "z" * 5_000}},
            env={"TAUSIK_OUTPUT_TRUNCATION_BYTES": "100000"},
        )
        assert quiet.stderr.strip() == ""
