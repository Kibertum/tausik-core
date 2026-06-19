"""v15-crypto-canonical-receipt: determinism of the signing payload."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from crypto_receipt import (  # noqa: E402
    RECEIPT_SCHEMA,
    ReceiptError,
    build_receipt,
    canonical_bytes,
)


def _sample(**overrides):
    kwargs = dict(
        task_slug="my-task",
        git_sha="831f03e0000000000000000000000000000000aa",
        scope="standard",
        gates=[
            {"name": "pytest", "passed": True, "severity": "block"},
            {"name": "hadolint", "passed": False, "severity": "warn"},
        ],
        passed=True,
        ran_at="2026-06-12T00:00:00Z",
        files_hash="abc123",
        key_fingerprint="103a83a212851018",
    )
    kwargs.update(overrides)
    return build_receipt(**kwargs)


class TestBuildReceipt:
    def test_schema_and_fields(self):
        r = _sample()
        assert r["schema"] == RECEIPT_SCHEMA
        assert r["task_slug"] == "my-task"
        assert {g["name"] for g in r["gates"]} == {"pytest", "hadolint"}

    def test_gates_sorted_and_slimmed(self):
        r = _sample(
            gates=[
                {"name": "z", "passed": True, "severity": "warn", "output": "x" * 9000},
                {"name": "a", "passed": False, "severity": "block"},
            ]
        )
        assert [g["name"] for g in r["gates"]] == ["a", "z"]
        assert "output" not in r["gates"][0]

    def test_requires_slug_and_ran_at(self):
        with pytest.raises(ReceiptError):
            _sample(task_slug="")
        with pytest.raises(ReceiptError):
            _sample(ran_at="")


class TestCanonicalBytes:
    def test_key_order_irrelevant(self):
        r = _sample()
        shuffled = dict(reversed(list(r.items())))
        shuffled["gates"] = [dict(reversed(list(g.items()))) for g in r["gates"]]
        assert canonical_bytes(r) == canonical_bytes(shuffled)

    def test_same_input_same_bytes(self):
        assert canonical_bytes(_sample()) == canonical_bytes(_sample())

    def test_roundtrip_stable(self):
        b = canonical_bytes(_sample())
        assert canonical_bytes(json.loads(b)) == b

    def test_no_whitespace_ascii_only(self):
        b = canonical_bytes(_sample())
        assert b" " not in b
        b.decode("ascii")

    def test_gate_list_order_change_changes_bytes_pre_build(self):
        """Sorting happens in build_receipt; canonical_bytes preserves list
        order (lists are semantically ordered in JSON)."""
        r1 = _sample()
        r2 = _sample()
        r2["gates"] = list(reversed(r2["gates"]))
        assert canonical_bytes(r1) != canonical_bytes(r2)

    def test_float_rejected(self):
        r = _sample()
        r["duration"] = 1.5
        with pytest.raises(ReceiptError, match="float"):
            canonical_bytes(r)

    def test_nan_rejected(self):
        r = _sample()
        r["x"] = float("nan")
        with pytest.raises(ReceiptError):
            canonical_bytes(r)

    def test_non_json_type_rejected(self):
        import datetime

        r = _sample()
        r["when"] = datetime.datetime(2026, 6, 12)
        with pytest.raises(ReceiptError, match="canonicalizable"):
            canonical_bytes(r)

    def test_non_string_key_rejected(self):
        r = _sample()
        r["bad"] = {1: "x"}
        with pytest.raises(ReceiptError, match="non-string"):
            canonical_bytes(r)

    def test_unicode_escaped_to_ascii(self):
        r = _sample(task_slug="задача")
        b = canonical_bytes(r)
        b.decode("ascii")
        assert json.loads(b)["task_slug"] == "задача"
