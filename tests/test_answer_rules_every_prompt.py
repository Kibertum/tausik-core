"""The answer rules are in front of the agent before every answer, in every project.

Owner, session #279: the rules shipped only into generated consumer CLAUDE.md, this
repository's own CLAUDE.md carried one line, and the prompt hook spoke only AFTER an
over-budget answer. Now the hook injects the rules on every human prompt.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _p in ("scripts", "bootstrap"):
    sys.path.insert(0, os.path.join(_ROOT, _p))

from answer_shape import (  # noqa: E402
    ANSWER_RULES,
    FORMAT_RULE,
    Report,
    explanation_format_rule,
    measure_transcript,
)
from bootstrap_templates import ANSWER_SHAPE, ANSWER_SHAPE_MARKER  # noqa: E402

_HOOK = os.path.join(_ROOT, "scripts", "hooks", "user_prompt_submit.py")


def test_the_injected_rules_are_the_shipped_rules_byte_for_byte():
    assert ANSWER_SHAPE == f"{ANSWER_SHAPE_MARKER}\n\n{ANSWER_RULES}"


def test_the_hook_injects_the_rules_on_a_prompt_with_no_prior_answer(tmp_path):
    """No transcript, so no budget line: the rules still arrive, before the first answer."""
    (tmp_path / ".tausik").mkdir()
    (tmp_path / ".tausik" / "tausik.db").write_bytes(b"")
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(tmp_path)}
    env.pop("TAUSIK_SKIP_HOOKS", None)
    out = subprocess.run(
        [sys.executable, _HOOK],
        input=json.dumps({"prompt": "what is left before the release?"}),
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        timeout=30,
    )
    context = json.loads(out.stdout)["hookSpecificOutput"]["additionalContext"]
    assert "[TAUSIK answer rules]" in context
    assert ANSWER_RULES in context
    assert "[TAUSIK explanation format]" not in context


def test_explanation_format_matrix_covers_routes_and_hook_delivery(tmp_path):
    triggers = (
        "Compare these four exact mappings",
        "Draw an architecture diagram",
        "Create an interactive HTML explanation",
        "Объясни последовательность",
        "Make an explainer video",
    )
    assert all(explanation_format_rule(prompt) == FORMAT_RULE for prompt in triggers)
    assert explanation_format_rule("Fix the parser") is None
    for term in (
        "prose by default",
        "a table for 3+",
        "Mermaid",
        "HTML only",
        "video only on request",
    ):
        assert term in FORMAT_RULE

    (tmp_path / ".tausik").mkdir()
    (tmp_path / ".tausik" / "tausik.db").write_bytes(b"")
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(tmp_path)}
    env.pop("TAUSIK_SKIP_HOOKS", None)
    out = subprocess.run(
        [sys.executable, _HOOK],
        input=json.dumps({"prompt": triggers[0]}),
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        timeout=30,
    )
    context = json.loads(out.stdout)["hookSpecificOutput"]["additionalContext"]
    assert FORMAT_RULE in context


def test_this_repository_s_own_rules_files_carry_them():
    for name in ("CLAUDE.md", "AGENTS.md"):
        with open(os.path.join(_ROOT, name), encoding="utf-8") as f:
            text = f.read()
        for line in ANSWER_RULES.splitlines():
            assert line in text, f"{name}: {line}"


def test_native_codex_answers_use_only_owner_messages_and_turn_boundaries(tmp_path):
    """Codex messages have a different envelope; collaborator output is not the owner's answer."""
    records = [
        {
            "type": "response_item",
            "payload": {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": "first"}],
            },
        },
        {
            "type": "response_item",
            "payload": {
                "type": "message",
                "role": "assistant",
                "content": [{"type": "output_text", "text": "Working details."}],
            },
        },
        {
            "type": "response_item",
            "payload": {
                "type": "agent_message",
                "content": [{"type": "input_text", "text": "not owner-visible"}],
            },
        },
        {
            "type": "response_item",
            "payload": {
                "type": "message",
                "role": "assistant",
                "content": [{"type": "output_text", "text": "Done: first."}],
            },
        },
        {
            "type": "response_item",
            "payload": {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": "second"}],
            },
        },
        {
            "type": "response_item",
            "payload": {
                "type": "message",
                "role": "assistant",
                "content": [{"type": "output_text", "text": "Done: second."}],
            },
        },
    ]
    path = tmp_path / "native.jsonl"
    path.write_text("\n".join(json.dumps(record) for record in records), encoding="utf-8")
    report = Report()
    measure_transcript(str(path), report)
    assert [score.words for score in report.finals] == [2, 2]
    assert report.interim_words == [2, 0]
