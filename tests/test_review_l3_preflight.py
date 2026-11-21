"""TB-009: L3 host capability classification."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from review_l3_preflight import (
    RECEIPT_KIND,
    assess_declared_tools,
    assess_l3_host,
    assess_read_probe_results,
    preflight_from_config,
)


def test_write_capable_host_is_blocked():
    cap = assess_declared_tools(["Read", "Write", "Grep"])
    assert not cap.ok
    assert cap.code == "L3_HOST_WRITE_CAPABLE"
    assert "write" in cap.detail.lower()


def test_read_only_tools_pass():
    cap = assess_declared_tools(["Read", "Grep"])
    assert cap.ok
    assert cap.code == "L3_HOST_MECHANICAL_READONLY"


def test_codex_policy_blocking_reads_is_infrastructure():
    cap = assess_read_probe_results(
        {
            "Get-Content": False,
            "rg": False,
            "cmd /c type": False,
            "Set-Content": False,
        }
    )
    assert not cap.ok
    assert cap.code == "L3_READONLY_POLICY_BLOCKS_READS"
    assert "Get-Content" in cap.detail


def test_write_probe_allowed_under_readonly_is_blocked():
    cap = assess_read_probe_results(
        {
            "Get-Content": True,
            "rg": True,
            "cmd /c type": True,
            "Set-Content": True,
        }
    )
    assert not cap.ok
    assert cap.code == "L3_READONLY_POLICY_ALLOWS_WRITES"


def test_combined_host_assessment_prefers_tool_failure():
    cap = assess_l3_host(
        tools=["Read", "Edit"],
        read_probe_results={"Get-Content": True, "rg": True, "cmd /c type": True},
    )
    assert not cap.ok
    assert cap.code == "L3_HOST_WRITE_CAPABLE"


def test_missing_config_is_advisory_not_enforced():
    cap = preflight_from_config({})
    assert cap.ok
    assert not cap.enforced
    assert cap.as_dict()["receipt_kind"] is None


def test_configured_blocked_host_is_enforced_receipt():
    cap = preflight_from_config({"review": {"l3_host": {"tools": ["Read", "Write"]}}})
    assert cap.enforced and not cap.ok
    assert cap.as_dict()["receipt_kind"] == RECEIPT_KIND
