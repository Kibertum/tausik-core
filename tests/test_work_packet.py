"""Behavioral proof for one bounded retrieval work packet."""

from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

import pytest

from project_backend import SQLiteBackend
from project_cli_task import cmd_task
from project_parser import build_parser
from project_service import ProjectService
from task_context_package import build_task_context_package
from work_packet import build_work_packet


FROZEN_REPLAY = {
    "topology_evidence": "tests/fixtures/work_packet_replay.json",
    "selected_target": ["retrieval", "retrieval"],
    "query": "bounded packet",
    "sources": ["scripts/a.py"],
    "original_returns": ["task_context", "search", "memory", "source"],
    "packet_returns": ["work_packet"],
    "required_addresses": ["task:work", "memory:", "file:scripts/a.py#L1-L2"],
}


@pytest.fixture
def svc(tmp_path):
    tausik_dir = tmp_path / ".tausik"
    tausik_dir.mkdir()
    service = ProjectService(SQLiteBackend(str(tausik_dir / "t.db")))
    service.epic_add("e", "E")
    service.story_add("e", "s", "S")
    service.task_add("s", "work", "Bounded packet work", complexity="medium")
    service.task_update(
        "work",
        goal="compose bounded packet",
        acceptance_criteria="AC-1 packet contains retrieval evidence",
        scope="scripts/a.py and tests",
        scope_exclude="scripts/secret.txt",
        scope_paths=["scripts/a.py", "scripts/secret.txt"],
        relevant_files=json.dumps(["tests/test_a.py"]),
    )
    service.memory_add(
        "context",
        "Bounded packet memory",
        "The bounded packet keeps source addresses.",
        task_slug="work",
    )
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "a.py").write_text("first\nsecond\n", encoding="utf-8")
    (scripts / "secret.txt").write_text("excluded", encoding="utf-8")
    (tmp_path / "outside.txt").write_text("outside task scope", encoding="utf-8")
    yield service
    service.be.close()


def test_packet_composes_existing_readers_with_addresses(svc):
    packet = build_work_packet(svc, "work", "bounded packet", ["scripts/a.py"])

    assert packet["context"]["required"]["slug"] == "work"
    assert any(hit["address"] == "task:work" for hit in packet["search"])
    assert any(hit["address"].startswith("memory:") for hit in packet["memory"])
    assert packet["sources"][0]["address"] == "file:scripts/a.py#L1-L2"
    assert packet["sources"][0]["path"] == "scripts/a.py"
    assert packet["sources"][0]["content"].splitlines() == ["first", "second"]
    assert packet["sources"][0]["content_bytes"] == len(packet["sources"][0]["content"].encode())
    assert packet["bytes"] <= packet["max_bytes"]
    encoded = json.dumps(packet, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    assert packet["bytes"] == len(encoded.encode())


def test_utf8_ceiling_omits_whole_units_without_truncation(svc):
    for index in range(8):
        svc.memory_add(
            "context",
            f"bounded packet память {index}",
            "я" * 400,
            task_slug="work",
        )

    packet = build_work_packet(svc, "work", "bounded packet", max_bytes=4_096)

    assert packet["bytes"] <= 4_096
    assert packet["overflow"] is True
    assert packet["omitted"]
    assert all("reason" in item and "address" in item for item in packet["omitted"])
    assert all(not str(hit.get("content", "")).endswith("…") for hit in packet["memory"])


@pytest.mark.parametrize(
    ("source", "reason"),
    [
        ("outside.txt", "out_of_task_scope"),
        ("scripts/secret.txt", "scope_excluded"),
        ("missing.txt", "unreadable_or_outside_project"),
    ],
)
def test_source_refusals_are_addressed(svc, source, reason):
    packet = build_work_packet(svc, "work", "bounded packet", [source])

    assert packet["sources"] == []
    assert packet["omitted"][-1]["reason"] == reason
    assert packet["omitted"][-1]["address"].startswith("file:")


def test_binary_and_oversized_sources_are_refused(svc):
    root = Path(svc.tausik_dir()).parent
    binary = root / "scripts" / "binary.py"
    binary.write_bytes(b"\xff\xfe")
    large = root / "scripts" / "large.py"
    large.write_text("x" * 9_000, encoding="utf-8")
    svc.task_update("work", scope_paths=["scripts/*.py"])

    packet = build_work_packet(
        svc,
        "work",
        "bounded packet",
        ["scripts/binary.py", "scripts/large.py"],
        max_bytes=8_192,
    )

    reasons = {item["reason"] for item in packet["omitted"]}
    assert {"unreadable_utf8", "source_exceeds_packet_ceiling"} <= reasons
    assert packet["bytes"] <= packet["max_bytes"]


def test_resolved_symlink_cannot_escape_project(svc, tmp_path):
    link = Path(svc.tausik_dir()).parent / "scripts" / "escape.py"
    external = tmp_path.parent / "work-packet-external.py"
    external.write_text("external", encoding="utf-8")
    try:
        link.symlink_to(external)
    except OSError:
        pytest.skip("symlinks unavailable on this host")
    svc.task_update("work", scope_paths=["scripts/*.py"])

    packet = build_work_packet(svc, "work", "bounded packet", ["scripts/escape.py"])

    assert packet["sources"] == []
    assert packet["omitted"][-1]["reason"] == "unreadable_or_outside_project"


@pytest.mark.parametrize(
    ("query", "sources", "max_bytes", "match"),
    [
        ("", [], 8_192, "query"),
        ("bounded", ["scripts/a.py"] * 2, 8_192, "unique"),
        ("bounded", [f"scripts/{i}.py" for i in range(17)], 8_192, "at most 16"),
        ("bounded", [], 512, "required task context"),
    ],
)
def test_invalid_or_unrepresentable_request_is_refused(svc, query, sources, max_bytes, match):
    with pytest.raises(ValueError, match=match):
        build_work_packet(svc, "work", query, sources, max_bytes=max_bytes)


def test_cli_and_mcp_are_thin_transports_over_same_packet(svc, capsys, monkeypatch):
    args = Namespace(
        task_cmd="show",
        slug="work",
        work_packet=True,
        package=False,
        query="bounded packet",
        sources=["scripts/a.py"],
        max_bytes=8_192,
    )
    cmd_task(svc, args)
    cli = json.loads(capsys.readouterr().out)

    monkeypatch.syspath_prepend(str(Path(__file__).parents[1] / "harness/claude/mcp/project"))
    from handlers_task import _handle_task_show

    mcp = json.loads(
        _handle_task_show(
            svc,
            {
                "slug": "work",
                "packet": json.dumps(
                    {
                        "query": "bounded packet",
                        "sources": ["scripts/a.py"],
                        "max_bytes": 8_192,
                    }
                ),
            },
        )
    )
    assert cli == mcp


def test_cli_and_mcp_share_packet_default_ceiling(svc, capsys, monkeypatch):
    args = build_parser().parse_args(
        ["task", "show", "work", "--work-packet", "--query", "bounded packet"]
    )
    cmd_task(svc, args)
    cli = json.loads(capsys.readouterr().out)

    monkeypatch.syspath_prepend(str(Path(__file__).parents[1] / "harness/claude/mcp/project"))
    from handlers_task import _handle_task_show

    mcp = json.loads(
        _handle_task_show(
            svc,
            {"slug": "work", "packet": json.dumps({"query": "bounded packet"})},
        )
    )
    assert cli == mcp
    assert cli["max_bytes"] == 16_384


def test_frozen_replay_preserves_original_information_and_removes_three_boundaries(svc):
    root = Path(svc.tausik_dir()).parent
    original_returns = [
        build_task_context_package(svc, "work"),
        svc.search(FROZEN_REPLAY["query"], "all", 6),
        svc.memory_search(FROZEN_REPLAY["query"]),
        (root / FROZEN_REPLAY["sources"][0]).read_bytes().decode("utf-8"),
    ]
    packet = build_work_packet(
        svc,
        "work",
        FROZEN_REPLAY["query"],
        FROZEN_REPLAY["sources"],
    )
    packet_returns = [packet]
    addresses = [
        f"task:{packet['context']['required']['slug']}",
        *(hit["address"] for hit in packet["search"]),
        *(hit["address"] for hit in packet["memory"]),
        *(source["address"] for source in packet["sources"]),
    ]

    for required in FROZEN_REPLAY["required_addresses"]:
        assert any(address.startswith(required) for address in addresses)

    original_context, original_search, original_memory, original_source = original_returns
    assert packet["context"]["required"]["goal"] == original_context["required"]["goal"]
    assert (
        packet["context"]["required"]["acceptance_criteria"]
        == original_context["required"]["acceptance_criteria"]
    )
    original_task = next(row for row in original_search["tasks"] if row["slug"] == "work")
    packet_task = next(hit for hit in packet["search"] if hit["address"] == "task:work")
    assert packet_task["label"] == original_task["title"]
    original_memory_hit = next(row for row in original_memory if row.get("id") == 1)
    packet_memory_hit = next(hit for hit in packet["memory"] if hit["address"] == "memory:1")
    assert (packet_memory_hit["title"], packet_memory_hit["content"]) == (
        original_memory_hit["title"],
        original_memory_hit["content"],
    )
    assert packet["sources"][0]["content"] == original_source

    topology = json.loads(
        (Path(__file__).parents[1] / FROZEN_REPLAY["topology_evidence"]).read_text(encoding="utf-8")
    )
    target = next(
        row for row in topology["transitions"] if row["sequence"] == ["retrieval", "retrieval"]
    )
    assert target["occurrences"] >= 2
    removed = len(original_returns) - len(packet_returns)
    assert FROZEN_REPLAY["selected_target"] == ["retrieval", "retrieval"]
    assert removed == 3
