"""The shipped agent workflow must preserve the bounded-L3 policy."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

CROSSCUTTING_SCOPE = [
    "harness/skills/ship/SKILL.md",
    "harness/claude/subagents/tausik-external-reviewer.md",
    "docs/en/workflow.md",
    "docs/en/assurance.md",
    "docs/ru/workflow.md",
    "docs/ru/assurance.md",
]


def _text(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_ship_and_external_reviewer_use_cohort_commands_and_two_round_cap():
    ship = _text("harness/skills/ship/SKILL.md")
    reviewer = _text("harness/claude/subagents/tausik-external-reviewer.md")

    assert "review cohort-open" in ship
    assert "review cohort-record" in ship
    assert "There is no automatic round 3" in ship
    assert "cohort-decide" in ship and "--owner {id}" in ship
    assert "/review --deep" in ship
    assert "do not inspect tasks carried green" in reviewer
    assert "Never request or perform an automatic round 3" in reviewer
    assert '"critical":0,"high":0,"warnings":1' in reviewer
    assert '"dependency_map_complete":true' in reviewer
    assert "--results-json @results.json" in reviewer
    assert "--packet-digest" in reviewer
    assert "tools: Read, Grep\n" in reviewer
    assert "Bash" not in reviewer.split("---", 2)[1]
    assert "Send the complete packet, its own" in ship
    assert "`packet_digest`, and `cohort_id`" in ship
    assert "Send only `packet.tasks`" not in ship

    order = [
        "Open the cohort",
        "Send that packet",
        "Record round 1 immediately",
        "repair only red or affected tasks",
        "Request `cohort-status",
        "Record round 2",
        "request the owner disposition",
    ]
    positions = [ship.index(item) for item in order]
    assert positions == sorted(positions)


def test_agent_contracts_use_the_persisted_cohort_verdict_vocabulary():
    for path in ("docs/en/agent-contract.md", "docs/ru/agent-contract.md"):
        text = _text(path)
        assert "approved | changes_requested | blocked" not in text
        for term in ("critical", "high", "warnings", "accepted_risk", "blocked"):
            assert term in text


def test_en_and_ru_user_docs_state_delta_only_round_two_and_no_round_three():
    english = _text("docs/en/workflow.md") + _text("docs/en/assurance.md")
    russian = _text("docs/ru/workflow.md") + _text("docs/ru/assurance.md")

    assert "only prior-red or affected tasks" in english
    assert "no automatic round 3" in english
    assert "только красные или затронутые" in russian
    assert "Автоматического round 3" in russian


def test_mcp_docs_publish_all_cohort_actions_and_required_record_fields():
    for path in ("docs/en/mcp.md", "docs/ru/mcp.md"):
        text = _text(path)
        for action in ("open", "status", "record", "decide"):
            assert f'"action":"{action}"' in text
        for field in (
            "cohort_id",
            "round",
            "results",
            "packet_digest",
            "dependency_map_complete",
            "author_model",
            "reviewer_model",
        ):
            assert f'"{field}"' in text


def test_release_body_links_are_bound_to_the_release_tag():
    body = _text("release-body-1.11.6.md")
    links = [part.split(")", 1)[0] for part in body.split("](")[1:]]
    assert links
    assert all("/blob/v1.11.6/" in link for link in links)
