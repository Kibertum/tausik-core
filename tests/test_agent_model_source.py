"""Which model is running this session, and what happens when nobody knows.

session-model-recorded-on-non-claude-hosts. The task was raised as "the model is
not recorded on NON-Claude hosts". Measured on this project's own database in
session #231 before anything was designed, the truth was worse and simpler:

    sessions:  231 rows, model_id set on 0
    tasks:    1560 rows, started_model_id on 0, done_model_id on 0,
              model_mismatch raised 0 times

Model pinning (RENAR Rule 10.13) had never fired anywhere, on any host, in the
project's entire history. `session_start` read only environment variables, Claude
Code exports none of them, and one missing link killed the whole chain: the
session pinned NULL, so every task pinned NULL.

The seam existed the whole time. `providers.get('claude').get_active_model()`
returns the id, read from the transcript. Nothing consulted it.

THE ASSERTION THAT MATTERS MOST HERE IS THE NEGATIVE ONE: the model is never
inferred from the host's NAME. Claude Code pointed at z.ai through
`ANTHROPIC_BASE_URL` is running GLM, and a chain that answers "claude, probably"
would be confidently wrong in exactly the case this exists to catch.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO / "scripts") not in sys.path:
    sys.path.insert(0, str(_REPO / "scripts"))

import agent_model_source as ams  # noqa: E402

CROSSCUTTING_SCOPE = ["scripts/agent_model_source.py", "scripts/providers/"]


class TestTheChainRunsInTheDeclaredOrder:
    def test_the_explicit_override_outranks_every_host_variable(self):
        env = {"TAUSIK_AGENT_MODEL": "glm-4.6", "CLAUDE_MODEL": "claude-opus-5"}
        assert ams.from_env(env) == ("glm-4.6", "TAUSIK_AGENT_MODEL")

    @pytest.mark.parametrize("name", ams.ENV_SOURCES)
    def test_every_declared_variable_is_actually_read(self, name):
        """A name in the tuple that nothing reads is a promise to a user who set
        it and got nothing."""
        assert ams.from_env({name: "some-model"}) == ("some-model", name)

    def test_the_source_is_named_so_a_wrong_id_can_be_traced(self):
        resolved = ams.resolve({"OPENAI_MODEL": "gpt-5"}, ide=None)
        assert resolved["model_id"] == "gpt-5"
        assert resolved["source"] == "OPENAI_MODEL"

    def test_the_provider_answers_when_the_environment_does_not(self, monkeypatch):
        class _Fake:
            def get_active_model(self):
                return "glm-4.6"

        monkeypatch.setitem(sys.modules, "providers", type("M", (), {"get": lambda _n: _Fake()}))
        assert ams.from_provider("kilo") == ("glm-4.6", "provider:kilo")

    def test_nothing_answering_is_absence_and_says_so(self):
        resolved = ams.resolve({}, ide=None)
        assert resolved["model_id"] is None
        assert resolved["source"] is None


class TestTheModelIsNeverInferredFromTheHost:
    """The task's own negative requirement, and the reason it was written."""

    def test_a_silent_claude_provider_yields_absence_not_a_claude_id(self, monkeypatch):
        class _Silent:
            def get_active_model(self):
                return None

        monkeypatch.setitem(sys.modules, "providers", type("M", (), {"get": lambda _n: _Silent()}))
        model, source = ams.from_provider("claude")
        assert model is None and source is None, (
            "the host is called 'claude', which is not evidence about the model "
            "serving it — Claude Code on another endpoint runs that endpoint's model"
        )

    def test_the_host_name_appears_nowhere_in_the_resolved_id(self, monkeypatch):
        class _Glm:
            def get_active_model(self):
                return "glm-4.6"

        monkeypatch.setitem(sys.modules, "providers", type("M", (), {"get": lambda _n: _Glm()}))
        assert ams.resolve({}, ide="claude")["model_id"] == "glm-4.6"


class TestAFailingSourceNeverStopsASession:
    def test_a_provider_that_raises_yields_absence(self, monkeypatch):
        class _Boom:
            def get_active_model(self):
                raise RuntimeError("transcript unreadable")

        monkeypatch.setitem(sys.modules, "providers", type("M", (), {"get": lambda _n: _Boom()}))
        assert ams.from_provider("claude") == (None, None)

    def test_a_providers_package_that_will_not_import_yields_absence(self, monkeypatch):
        def _explode(*_a, **_k):
            raise ImportError("no providers here")

        monkeypatch.setattr(ams, "from_provider", lambda ide: (None, None))
        monkeypatch.setitem(sys.modules, "providers", None)
        assert ams.resolve({}, ide="claude")["model_id"] is None

    def test_a_host_with_no_provider_yields_absence(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "providers", type("M", (), {"get": lambda _n: None}))
        assert ams.from_provider("opencode") == (None, None)

    def test_no_host_at_all_yields_absence(self):
        assert ams.from_provider(None) == (None, None)


class TestTheIdIsUntrustedInput:
    """It arrives from the environment and from a file, and lands in reports."""

    @pytest.mark.parametrize(
        "raw",
        [
            pytest.param("", id="empty"),
            pytest.param("   ", id="whitespace"),
            pytest.param("x" * 121, id="oversized"),
            pytest.param("claude\x1b[31m-opus", id="escape_sequence"),
            pytest.param("model with spaces", id="spaces"),
            pytest.param("claude\nopus", id="newline"),
            pytest.param(None, id="not_a_string"),
            pytest.param(5, id="an_int"),
        ],
    )
    def test_a_value_that_is_not_a_model_token_is_absence(self, raw):
        assert ams.sanitise(raw) is None

    @pytest.mark.parametrize(
        "raw",
        [
            pytest.param("claude-opus-5", id="claude"),
            pytest.param("glm-4.6", id="glm"),
            pytest.param("gpt-5", id="gpt"),
            pytest.param("a/b:c@d+e", id="every_allowed_separator"),
            # Trimmed, not rejected: surrounding space is formatting, not
            # part of the name, and refusing it would send a real id to
            # absence.
            pytest.param("  claude-opus-5  ", id="padded"),
        ],
    )
    def test_real_model_ids_survive(self, raw):
        assert ams.sanitise(raw) == raw.strip()

    def test_a_blank_variable_does_not_shadow_the_next_source(self):
        """`TAUSIK_AGENT_MODEL=""` says nothing. Treating it as an answer would
        let an empty export silence the whole chain below it."""
        assert ams.from_env({"TAUSIK_AGENT_MODEL": "", "CLAUDE_MODEL": "claude-opus-5"}) == (
            "claude-opus-5",
            "CLAUDE_MODEL",
        )


class TestTheTranscriptReadIsBounded:
    def _read(self, path):
        from model_routing import read_active_model_from_transcript

        return read_active_model_from_transcript(str(path))

    @pytest.mark.parametrize(
        "body,expected",
        [
            pytest.param(
                '{"type":"assistant","message":{"model":"glm-4.6"}}\n',
                "glm-4.6",
                id="nested_under_message",
            ),
            pytest.param('{"model":"glm-4.6"}\n', "glm-4.6", id="top_level"),
            pytest.param(
                '{"model":"claude-opus-4-8"}\n{"model":"claude-opus-5"}\n',
                "claude-opus-5",
                id="most_recent_wins",
            ),
            pytest.param('{"type":"user","content":"hi"}\n', None, id="no_model_anywhere"),
        ],
    )
    def test_the_model_is_read_from_a_small_file(self, tmp_path, body, expected):
        """One file, one expected answer — including the case where the file
        names no model at all, which must be absence rather than a guess."""
        p = tmp_path / "t.jsonl"
        p.write_text(body, encoding="utf-8")
        assert self._read(p) == expected

    def test_only_the_tail_is_read_and_the_answer_is_still_right(self, tmp_path):
        """A transcript is an append-only log with no ceiling. Reading all of it
        to look at the last few lines cost 70 ms on this project's live file and
        was bounded by nothing at all."""
        from model_routing import _TAIL_BYTES

        p = tmp_path / "big.jsonl"
        filler = '{"type":"user","content":"%s"}\n' % ("x" * 900)
        with open(p, "w", encoding="utf-8") as fh:
            while fh.tell() < _TAIL_BYTES * 2:
                fh.write(filler)
            fh.write('{"type":"assistant","message":{"model":"glm-4.6"}}\n')
        assert p.stat().st_size > _TAIL_BYTES
        assert self._read(p) == "glm-4.6"

    def test_a_model_older_than_the_window_is_absent_not_guessed(self, tmp_path):
        """The declared limit, stated rather than hidden: a model id further back
        than the window is not found. Absence is the honest answer — the window
        is chosen so the CURRENT model is always inside it."""
        from model_routing import _TAIL_BYTES

        p = tmp_path / "old.jsonl"
        with open(p, "w", encoding="utf-8") as fh:
            fh.write('{"model":"claude-opus-5"}\n')
            filler = '{"type":"user","content":"%s"}\n' % ("x" * 900)
            while fh.tell() < _TAIL_BYTES * 2:
                fh.write(filler)
        assert self._read(p) is None

    def test_a_split_line_at_the_window_edge_is_dropped_not_misparsed(self, tmp_path):
        """The first line of the window is a fragment. Half a JSON object parses
        as nothing at best and as the wrong thing at worst."""
        from model_routing import _tail_lines

        p = tmp_path / "split.jsonl"
        p.write_text("A" * 300000 + "\n" + '{"model":"x"}\n', encoding="utf-8")
        lines = _tail_lines(str(p))
        assert lines and lines[-1] == '{"model":"x"}'
        assert not any(line.startswith("A") for line in lines)

    def test_a_missing_file_is_absence_not_an_exception(self, tmp_path):
        assert self._read(tmp_path / "nope.jsonl") is None
