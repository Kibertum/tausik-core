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

from answer_shape import ANSWER_RULES  # noqa: E402
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


def test_this_repository_s_own_rules_file_carries_them():
    with open(os.path.join(_ROOT, "CLAUDE.md"), encoding="utf-8") as f:
        text = f.read()
    for line in ANSWER_RULES.splitlines():
        assert line in text, line
