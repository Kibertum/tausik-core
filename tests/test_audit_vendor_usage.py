"""Tests for scripts/audit_vendor_usage.py — static vendor cleanup audit."""

from __future__ import annotations

import json
import os
import sys

_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

import audit_vendor_usage as av  # noqa: E402


def _make_vendor(root, name, skills):
    path = root / name
    path.mkdir(parents=True)
    for s in skills:
        sd = path / s
        sd.mkdir()
        (sd / "SKILL.md").write_text(f"# {s}\n", encoding="utf-8")
    return path


def _make_config(root, installed):
    cfg = root / "config.json"
    cfg.write_text(json.dumps({"installed_skills": installed}), encoding="utf-8")
    return str(cfg)


def test_empty_vendor_dir_returns_empty(tmp_path):
    cfg = _make_config(tmp_path, [])
    result = av.audit_vendor_usage(str(tmp_path / "missing-vendor"), cfg)
    assert result == {"installed": [], "vendored_unused": [], "unknown": []}


def test_single_installed_vendor(tmp_path):
    vendor_dir = tmp_path / "vendor"
    _make_vendor(vendor_dir, "tausik-skills", ["plan", "task"])
    cfg = _make_config(tmp_path, ["plan"])
    result = av.audit_vendor_usage(str(vendor_dir), cfg)
    assert len(result["installed"]) == 1
    assert result["installed"][0]["name"] == "tausik-skills"
    assert sorted(result["installed"][0]["skills"]) == ["plan", "task"]
    assert result["vendored_unused"] == []


def test_single_unused_vendor(tmp_path):
    vendor_dir = tmp_path / "vendor"
    _make_vendor(vendor_dir, "stale-repo", ["foo"])
    cfg = _make_config(tmp_path, [])
    result = av.audit_vendor_usage(str(vendor_dir), cfg)
    assert result["installed"] == []
    assert len(result["vendored_unused"]) == 1
    assert result["vendored_unused"][0]["name"] == "stale-repo"


def test_mixed_vendors(tmp_path):
    vendor_dir = tmp_path / "vendor"
    _make_vendor(vendor_dir, "active", ["good"])
    _make_vendor(vendor_dir, "stale", ["bad"])
    cfg = _make_config(tmp_path, ["good"])
    result = av.audit_vendor_usage(str(vendor_dir), cfg)
    names_installed = [v["name"] for v in result["installed"]]
    names_unused = [v["name"] for v in result["vendored_unused"]]
    assert names_installed == ["active"]
    assert names_unused == ["stale"]


def test_missing_config_treats_all_as_unused(tmp_path):
    vendor_dir = tmp_path / "vendor"
    _make_vendor(vendor_dir, "any", ["x"])
    result = av.audit_vendor_usage(str(vendor_dir), str(tmp_path / "no-such-config.json"))
    assert len(result["vendored_unused"]) == 1


def test_malformed_config_treats_all_as_unused(tmp_path):
    vendor_dir = tmp_path / "vendor"
    _make_vendor(vendor_dir, "any", ["x"])
    bad = tmp_path / "config.json"
    bad.write_text("{not valid json", encoding="utf-8")
    result = av.audit_vendor_usage(str(vendor_dir), str(bad))
    assert len(result["vendored_unused"]) == 1


def test_vendor_without_skills_still_classified(tmp_path):
    vendor_dir = tmp_path / "vendor"
    (vendor_dir / "empty-vendor").mkdir(parents=True)
    cfg = _make_config(tmp_path, [])
    result = av.audit_vendor_usage(str(vendor_dir), cfg)
    assert len(result["vendored_unused"]) == 1
    assert result["vendored_unused"][0]["skills"] == []


def test_audit_never_deletes(tmp_path):
    """Read-only invariant: audit never modifies vendor or config."""
    vendor_dir = tmp_path / "vendor"
    _make_vendor(vendor_dir, "v1", ["s1"])
    cfg = _make_config(tmp_path, [])
    before_files = sorted(os.listdir(vendor_dir))
    av.audit_vendor_usage(str(vendor_dir), cfg)
    after_files = sorted(os.listdir(vendor_dir))
    assert before_files == after_files
    assert os.path.isfile(cfg)


def test_last_modified_iso_present_for_real_files(tmp_path):
    vendor_dir = tmp_path / "vendor"
    _make_vendor(vendor_dir, "v1", ["s1"])
    cfg = _make_config(tmp_path, ["s1"])
    result = av.audit_vendor_usage(str(vendor_dir), cfg)
    assert result["installed"][0]["last_modified_iso"] is not None
    assert result["installed"][0]["last_modified_iso"].endswith("Z")
