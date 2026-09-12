"""The generated block of the rules file: cost per part and two usage proxies.

Every proxy has a positive (the block was the only possible source) and a
negative (a tool result or the human said it first, or the id was never in
the tail), so the figures the audit prints cannot be inflated by the tail's
own numbering or by a compaction summary that quotes the ids.
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import context_block_audit as cba  # noqa: E402

CROSSCUTTING_SCOPE: list[str] = []  # reads a rules file and transcripts, never the tree

RULES = (
    "# CLAUDE.md\n\n## Принципы\n- rule one\n\n"
    "<!-- DYNAMIC:START -->\n## Current State\nSession: #249 (active)\nActive: x\n\n"
    "### Memory tail\nContext (2):\n- #684 first\n- #425 second\nDecisions (1):\n- #361 third\n\n"
    "**Shared knowledge — from other projects (1):**\n- [gotcha] foreign\n<!-- DYNAMIC:END -->\n"
)


# --- the split ------------------------------------------------------------------------


def test_parts_are_cut_at_the_generators_markers():
    parts = cba.split_parts(RULES)
    assert parts["handwritten"].startswith("# CLAUDE.md") and "DYNAMIC" not in parts["handwritten"]
    assert parts["state"].startswith("<!-- DYNAMIC:START -->\n## Current State")
    assert parts["tail"].startswith("### Memory tail") and "#361" in parts["tail"]
    assert parts["shared"].startswith("**Shared knowledge") and "foreign" in parts["shared"]
    assert "".join(parts.values()) == RULES, "the split loses nothing"


def test_a_file_without_a_block_is_all_handwritten_and_costs_nothing_generated():
    parts = cba.split_parts("# CLAUDE.md\n\nrules only\n")
    assert parts == {
        "handwritten": "# CLAUDE.md\n\nrules only\n",
        "state": "",
        "tail": "",
        "shared": "",
    }
    cost = cba.cost_of("# CLAUDE.md\n\nrules only\n")
    assert cost["tail"]["bytes"] == 0 and cost["handwritten"]["context_share_pct"] > 0


def test_a_pre_marker_file_splits_at_the_state_heading():
    parts = cba.split_parts("rules\n\n## Current State\nSession: #1\n\n### Memory tail\n- #7 x\n")
    assert (
        parts["handwritten"] == "rules\n\n" and parts["tail"] == "- #7 x\n" or "#7" in parts["tail"]
    )


def test_cost_share_is_against_the_measured_median_context():
    cost = cba.cost_of(RULES)
    tail = cost["tail"]
    assert tail["tokens"] == round(tail["bytes"] / cba.CHARS_PER_TOKEN)
    assert tail["context_share_pct"] == round(100 * tail["tokens"] / cba.MEDIAN_CONTEXT_TOKENS, 3)
    assert cba.MEDIAN_CONTEXT_TOKENS == 276_702, "the #230 measurement, not a guess"


# --- what counts as a memory citation ----------------------------------------------------


def test_the_tail_ids_are_read_by_construction_and_prose_ids_need_a_reason():
    assert cba.tail_ids(RULES) == {684, 425, 361}
    assert cba.cited_ids("memory #425 says so; decision #361; норма #628") == {425, 361, 628}
    assert cba.cited_ids("#684 retired the rule") == {684}, (
        "above the session ceiling: credited bare"
    )
    assert cba.cited_ids("session #249 opened; смена #232 записала; verify run #2523") == set()
    assert cba.cited_ids("Передача #226 прочитана. #228 открыта.") == set(), (
        "session-sized bare numbers"
    )
    assert cba.cited_ids("see #226", tail=True) == {226}, "inside the tail every #N is an id"


# --- proxies over a transcript -----------------------------------------------------------


def _rec(kind, blocks):
    return {"type": kind, "message": {"content": blocks}}


def _text(kind, text):
    return _rec(kind, [{"type": "text", "text": text}])


def _tool(name, **inp):
    return _rec("assistant", [{"type": "tool_use", "name": name, "input": inp}])


def _result(text):
    return _rec("user", [{"type": "tool_result", "content": text}])


def _write(path, records):
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n", "utf-8")


def test_proxy_a_counts_a_status_refetch_only_within_the_first_calls(tmp_path):
    early = tmp_path / "early.jsonl"
    _write(early, [_text("user", "go"), _tool("Bash", command=".tausik/tausik status")])
    assert cba.session_use(early, set()).refetch_in_first_calls

    mcp = tmp_path / "mcp.jsonl"
    _write(mcp, [_text("user", "go"), _tool("mcp__tausik-project__tausik_session_current")])
    assert cba.session_use(mcp, set()).refetch_in_first_calls

    late = tmp_path / "late.jsonl"
    _write(
        late,
        [_text("user", "go")]
        + [_tool("Bash", command="ls") for _ in range(cba.FIRST_CALLS)]
        + [_tool("Bash", command=".tausik/tausik status")],
    )
    assert not cba.session_use(late, set()).refetch_in_first_calls
    assert not cba.session_use(late, set()).tail_sourced_ids


def test_proxy_b_credits_the_tail_only_when_nothing_earlier_carried_the_id(tmp_path):
    history = {425, 684}
    fresh = tmp_path / "fresh.jsonl"
    _write(
        fresh, [_text("user", "fix it"), _text("assistant", "Per memory #425 the rule is retired.")]
    )
    assert cba.session_use(fresh, history).tail_sourced_ids == {425}

    fetched = tmp_path / "fetched.jsonl"
    _write(
        fetched,
        [
            _text("user", "fix it"),
            _tool("mcp__tausik-project__tausik_memory_show", id=425),
            _result("#425 [convention] the rule is retired"),
            _text("assistant", "Per memory #425 the rule is retired."),
        ],
    )
    assert cba.session_use(fetched, history).tail_sourced_ids == set(), (
        "a tool result said it first"
    )

    quoted = tmp_path / "quoted.jsonl"
    _write(
        quoted,
        [_text("user", "summary: memory #425 matters"), _text("assistant", "memory #425, yes")],
    )
    assert cba.session_use(quoted, history).tail_sourced_ids == set(), "the human said it first"

    invented = tmp_path / "invented.jsonl"
    _write(invented, [_text("user", "go"), _text("assistant", "memory #999 says so")])
    use = cba.session_use(invented, history)
    assert use.tail_sourced_ids == set() and use.unverified_ids == {999}, (
        "never in the tail: uncredited"
    )


def test_a_second_mention_is_not_a_second_sourcing(tmp_path):
    p = tmp_path / "twice.jsonl"
    _write(
        p,
        [
            _text("user", "go"),
            _text("assistant", "memory #425"),
            _text("assistant", "memory #425 again"),
        ],
    )
    assert cba.session_use(p, {425}).tail_sourced_ids == {425}


# --- the report -------------------------------------------------------------------------------


def test_an_empty_set_is_named_not_reported_as_zero_usage(tmp_path):
    usage = cba.usage_report([str(tmp_path)], {425})
    assert usage["sessions"] == 0 and usage["tail_sourced_pct"] is None
    assert "NO agent sessions" in cba.render(cba.cost_of(RULES), usage)
    chat_only = tmp_path / "chat.jsonl"
    _write(chat_only, [_text("user", "hi"), _text("assistant", "hello")])
    assert cba.usage_report([str(tmp_path)], {425})["sessions"] == 0, (
        "no tool call: not an agent session"
    )


def test_report_percentages_are_over_agent_sessions(tmp_path):
    _write(
        tmp_path / "a.jsonl", [_text("user", "go"), _tool("Bash", command=".tausik/tausik status")]
    )
    _write(
        tmp_path / "b.jsonl",
        [_text("user", "go"), _tool("Bash", command="ls"), _text("assistant", "memory #425")],
    )
    usage = cba.usage_report([str(tmp_path)], {425})
    assert usage["sessions"] == 2
    assert usage["state_refetch_pct"] == 50.0 and usage["tail_sourced_pct"] == 50.0
    assert usage["tail_sourced_ids"] == 1 and usage["tail_history_ids"] == 1


def test_history_outside_a_repo_is_empty_not_an_error(tmp_path):
    assert cba.tail_ids_in_history(str(tmp_path)) == set()
