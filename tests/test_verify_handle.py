"""Explicit state handle for verify runs — mint, present, refuse, spend.

v2-verify-receipt-as-argument (decision #218, SEP-2567 / SEP-2322). The AC this
file discharges, one class per item:

  AC1  a v2 receipt is PARTIAL, and the refusal NAMES the missing fields
  AC2  verify mints <run_id>.<nonce>, >= 128 bits, different every run
  AC3  a handle closes a run OLDER than the cache TTL (the point of the change)
  AC4  every refusal is fail-closed and says what is wrong (AC4 named seven;
       the implementation grew to more as the review found gaps)
  AC5  redeem-once is atomic
  AC6  the security predicate reads the receipt's files, not the caller's
  AC7  a keyless project is a NAMED mode, not a silent pass
  AC8  no handle → the previous freshness lookup, unchanged

The DDL comes from `conftest.canonical_ddl`, never a hand-written copy: this
table's copies have already twice produced green tests for a feature that
raised IntegrityError against a real database (test-ddl-drift-verification-runs).
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
from datetime import datetime, timedelta, timezone

import pytest

_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

import crypto_keys  # noqa: E402
import crypto_sign  # noqa: E402
import verify_handle as vh  # noqa: E402
from backend_schema_gate_runs import GATE_RUNS_SQL  # noqa: E402
from conftest import canonical_ddl  # noqa: E402
from crypto_receipt import build_receipt, missing_v3_fields  # noqa: E402
from verify_cache import _build_cache_command, resolve_gate_signature  # noqa: E402
from verify_files_hash import compute_files_hash  # noqa: E402
from verify_handle_check import check_handle, redeem_handle  # noqa: E402

_DDL = canonical_ddl("verification_runs")


def _iso(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.executescript(_DDL + ";")
    c.executescript(GATE_RUNS_SQL)
    yield c
    c.close()


@pytest.fixture
def keyed_project(tmp_path, monkeypatch):
    """A project directory with a real ed25519 keypair, cwd'd into."""
    crypto_keys.init_keys(str(tmp_path))
    monkeypatch.chdir(tmp_path)
    return str(tmp_path)


def _write_files(root, names) -> list[str]:
    """Create real files so `compute_files_hash` has something to read."""
    out = []
    for name in names:
        p = os.path.join(root, name)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(f"# {name}\n")
        out.append(name)
    return sorted(out)


def _make_run(
    conn,
    project_dir,
    *,
    slug="demo-task",
    files=("scripts/demo.py",),
    ran_at=None,
    ttl_s=3600,
    schema_v2=False,
    exit_code=0,
    command=None,
    sign=True,
):
    """Insert a green verify run + a signed v3 receipt + a minted handle.

    Deliberately assembled from the SAME helpers production uses
    (`_build_cache_command`, `compute_files_hash`, `build_receipt`,
    `crypto_sign.sign_receipt`, `vh.mint_handle`) rather than from literals. A
    fixture that hand-rolls the cache command would agree with itself and
    disagree with the code under test — which is how this area's previous
    defects stayed green.
    """
    declared = _write_files(project_dir, files)
    files_hash = compute_files_hash(declared)
    cmd = command if command is not None else _build_cache_command("verify", declared)
    ran = ran_at or _iso(datetime.now(timezone.utc))
    cur = conn.execute(
        "INSERT INTO verification_runs (task_slug, scope, command, exit_code, "
        "summary, files_hash, ran_at) VALUES (?,?,?,?,?,?,?)",
        (slug, "standard", cmd, exit_code, "pytest=PASS", files_hash, ran),
    )
    run_id = int(cur.lastrowid)
    expires_at = vh.compute_expires_at(ran, ttl_s)
    kwargs = dict(
        task_slug=slug,
        git_sha=None,
        scope="standard",
        gates=[{"name": "pytest", "passed": True, "severity": "block"}],
        passed=exit_code == 0,
        ran_at=ran,
        files_hash=files_hash,
    )
    if not schema_v2:
        kwargs.update(
            files=declared,
            gate_signature=resolve_gate_signature("verify"),
            expires_at=expires_at,
        )
    receipt = build_receipt(**kwargs)
    if schema_v2:
        # A genuine pre-v3 receipt: the three self-description keys absent
        # entirely, exactly as a v2 build_receipt produced them.
        receipt["schema"] = "tausik-receipt/v2"
        for key in ("files", "gate_signature", "expires_at"):
            receipt.pop(key, None)
    envelope = crypto_sign.sign_receipt(project_dir, receipt) if sign else None
    if envelope is not None:
        conn.execute(
            "UPDATE verification_runs SET receipt_json = ? WHERE id = ?",
            (json.dumps(envelope, ensure_ascii=True, sort_keys=True), run_id),
        )
    conn.commit()
    handle = vh.mint_handle(conn, run_id, expires_at=expires_at)
    return run_id, handle, declared


# ---------------------------------------------------------------- AC2: minting


class TestMinting:
    def test_handle_shape_and_entropy(self, conn, keyed_project):
        _, handle, _ = _make_run(conn, keyed_project)
        parsed = vh.parse_handle(handle)
        assert parsed is not None
        run_id, nonce = parsed
        assert run_id > 0
        # SEP-2567: "at least 128 bits of cryptographically secure entropy".
        assert len(nonce) == 32 and int(nonce, 16) >= 0

    def test_two_runs_get_different_nonces(self, conn, keyed_project):
        _, first, _ = _make_run(conn, keyed_project, slug="a")
        _, second, _ = _make_run(conn, keyed_project, slug="b")
        assert first.split(".")[1] != second.split(".")[1]

    def test_remint_replaces_the_nonce_and_clears_the_spend(self, conn, keyed_project):
        run_id, first, _ = _make_run(conn, keyed_project)
        assert redeem_handle(conn, first, task_slug="demo-task", project_dir=keyed_project).ok
        second = vh.mint_handle(conn, run_id, expires_at=vh.compute_expires_at(_iso(_now()), 3600))
        assert second != first
        row = conn.execute(
            "SELECT handle_redeemed_at FROM verification_runs WHERE id=?", (run_id,)
        ).fetchone()
        assert row[0] is None, "a re-minted handle must be spendable again"

    @pytest.mark.parametrize(
        "bad",
        [None, "", "nodot", "12.short", "abc." + "a" * 32, "12." + "z" * 32, "1.2." + "a" * 32],
    )
    def test_malformed_handles_are_rejected_before_any_query(self, bad):
        assert vh.parse_handle(bad) is None


def _now():
    return datetime.now(timezone.utc)


# ------------------------------------------------- AC3: TTL is no longer a gate


class TestAgeIsNotFreshness:
    def test_handle_closes_a_run_older_than_the_cache_ttl(self, conn, keyed_project):
        """The whole point of #218: a two-hour-old run whose files have not
        moved is still provable, where the 600 s freshness window said 'miss'."""
        from verify_constants import DEFAULT_CACHE_TTL_S

        old = _iso(_now() - timedelta(seconds=DEFAULT_CACHE_TTL_S * 12))
        _, handle, _ = _make_run(conn, keyed_project, ran_at=old, ttl_s=DEFAULT_CACHE_TTL_S * 24)
        verdict = redeem_handle(conn, handle, task_slug="demo-task", project_dir=keyed_project)
        assert verdict.ok, verdict.reason

    def test_expired_handle_is_refused(self, conn, keyed_project):
        _, handle, _ = _make_run(conn, keyed_project, ran_at=_iso(_now() - timedelta(hours=5)))
        verdict = check_handle(conn, handle, task_slug="demo-task", project_dir=keyed_project)
        assert not verdict.ok
        assert "expired" in verdict.reason


# --------------------------------------------------- AC4: the seven refusals


class TestRefusals:
    def test_unknown_run(self, conn, keyed_project):
        verdict = check_handle(
            conn, "999." + "a" * 32, task_slug="demo-task", project_dir=keyed_project
        )
        assert not verdict.ok and "no verify run #999" in verdict.reason

    def test_wrong_nonce(self, conn, keyed_project):
        run_id, _, _ = _make_run(conn, keyed_project)
        verdict = check_handle(
            conn, f"{run_id}." + "b" * 32, task_slug="demo-task", project_dir=keyed_project
        )
        assert not verdict.ok and "nonce does not match" in verdict.reason

    def test_handle_belongs_to_another_task(self, conn, keyed_project):
        _, handle, _ = _make_run(conn, keyed_project, slug="task-a")
        verdict = check_handle(conn, handle, task_slug="task-b", project_dir=keyed_project)
        assert not verdict.ok and "task-a" in verdict.reason and "task-b" in verdict.reason

    def test_files_changed_since_verify(self, conn, keyed_project):
        _, handle, files = _make_run(conn, keyed_project)
        with open(os.path.join(keyed_project, files[0]), "a", encoding="utf-8") as fh:
            fh.write("# edited after the verify run\n")
        verdict = check_handle(conn, handle, task_slug="demo-task", project_dir=keyed_project)
        assert not verdict.ok
        # The refusal must say WHAT is wrong. "cache miss" was the defect.
        assert "have changed since" in verdict.reason
        assert "not a cache miss" in verdict.reason

    def test_gate_set_changed_since_verify(self, conn, keyed_project, monkeypatch):
        _, handle, _ = _make_run(conn, keyed_project)
        monkeypatch.setattr(
            "verify_cache.resolve_gate_signature", lambda trigger="task-done": "0" * 16
        )
        verdict = check_handle(conn, handle, task_slug="demo-task", project_dir=keyed_project)
        assert not verdict.ok and "gate set changed" in verdict.reason

    def test_red_run_cannot_certify(self, conn, keyed_project):
        _, handle, _ = _make_run(conn, keyed_project, exit_code=1)
        verdict = check_handle(conn, handle, task_slug="demo-task", project_dir=keyed_project)
        assert not verdict.ok and "did NOT pass" in verdict.reason

    def test_noncacheable_run_cannot_certify(self, conn, keyed_project):
        _, handle, _ = _make_run(
            conn,
            keyed_project,
            command="noncacheable|" + _build_cache_command("verify", ["scripts/demo.py"]),
        )
        verdict = check_handle(conn, handle, task_slug="demo-task", project_dir=keyed_project)
        assert not verdict.ok and "non-replayable" in verdict.reason

    def test_tampered_receipt_is_refused(self, conn, keyed_project):
        run_id, handle, _ = _make_run(conn, keyed_project)
        raw = conn.execute(
            "SELECT receipt_json FROM verification_runs WHERE id=?", (run_id,)
        ).fetchone()[0]
        envelope = json.loads(raw)
        envelope["receipt"]["passed"] = True
        envelope["receipt"]["scope"] = "critical"  # signed bytes no longer match
        conn.execute(
            "UPDATE verification_runs SET receipt_json=? WHERE id=?",
            (json.dumps(envelope), run_id),
        )
        conn.commit()
        verdict = check_handle(conn, handle, task_slug="demo-task", project_dir=keyed_project)
        assert not verdict.ok and "INVALID ed25519 signature" in verdict.reason

    def test_corrupt_receipt_json_is_refused_not_skipped(self, conn, keyed_project):
        """Fail-CLOSED, the inversion of verify_receipt_check's degradation."""
        run_id, handle, _ = _make_run(conn, keyed_project)
        conn.execute("UPDATE verification_runs SET receipt_json='{not json' WHERE id=?", (run_id,))
        conn.commit()
        verdict = check_handle(conn, handle, task_slug="demo-task", project_dir=keyed_project)
        assert not verdict.ok and "corrupt" in verdict.reason

    def test_receipt_gate_signature_disagreeing_with_the_row_is_refused(self, conn, keyed_project):
        """The receipt and the ROW must tell the same story about the gate set.
        Checking the receipt only against the live config would miss a receipt
        that agrees with today's config but not with the run that produced it."""
        run_id, handle, files = _make_run(conn, keyed_project)
        # Rewrite the row's command with a different sig, leaving the receipt
        # (and therefore the live-config comparison) untouched.
        bad = _build_cache_command("verify", files).replace(
            f"sig={resolve_gate_signature('verify')}", "sig=" + "f" * 16
        )
        conn.execute("UPDATE verification_runs SET command=? WHERE id=?", (bad, run_id))
        conn.commit()
        verdict = check_handle(conn, handle, task_slug="demo-task", project_dir=keyed_project)
        assert not verdict.ok
        assert "does not match" in verdict.reason and "recorded gate set" in verdict.reason

    def test_receipt_files_hash_disagreeing_with_the_row_is_refused(self, conn, keyed_project):
        """Signed document and recorded run must describe the same file set.
        The live re-hash alone cannot catch this: it is compared to the ROW."""
        run_id, handle, _ = _make_run(conn, keyed_project)
        raw = conn.execute(
            "SELECT receipt_json FROM verification_runs WHERE id=?", (run_id,)
        ).fetchone()[0]
        envelope = json.loads(raw)
        # Re-sign so the signature stays VALID — otherwise the signature check
        # fires first and this branch is never reached.
        envelope["receipt"]["files_hash"] = "0" * 64
        resigned = crypto_sign.sign_receipt(keyed_project, envelope["receipt"])
        conn.execute(
            "UPDATE verification_runs SET receipt_json=? WHERE id=?",
            (json.dumps(resigned), run_id),
        )
        conn.commit()
        verdict = check_handle(conn, handle, task_slug="demo-task", project_dir=keyed_project)
        assert not verdict.ok
        assert "files_hash disagrees" in verdict.reason

    def test_missing_receipt_is_refused(self, conn, keyed_project):
        _, handle, _ = _make_run(conn, keyed_project, sign=False)
        verdict = check_handle(conn, handle, task_slug="demo-task", project_dir=keyed_project)
        assert not verdict.ok and "carries no receipt" in verdict.reason


# ------------------------------------------------------- AC1: v2 is PARTIAL


class TestLegacyReceiptIsPartial:
    def test_v2_receipt_does_not_satisfy_a_handle(self, conn, keyed_project):
        _, handle, _ = _make_run(conn, keyed_project, schema_v2=True)
        verdict = check_handle(conn, handle, task_slug="demo-task", project_dir=keyed_project)
        assert not verdict.ok

    def test_refusal_names_every_missing_field(self, conn, keyed_project):
        _, handle, _ = _make_run(conn, keyed_project, schema_v2=True)
        verdict = check_handle(conn, handle, task_slug="demo-task", project_dir=keyed_project)
        for field in ("files", "gate_signature", "expires_at"):
            assert field in verdict.reason, f"refusal must name {field}"
        assert "tausik-receipt/v2" in verdict.reason

    def test_missing_v3_fields_judges_by_value_not_key(self):
        """`build_receipt` writes None rather than omitting, so a key-only
        check would read 'knows nothing' as 'fully specified'."""
        assert missing_v3_fields({"files": None, "gate_signature": None, "expires_at": None}) == [
            "files",
            "gate_signature",
            "expires_at",
        ]
        assert missing_v3_fields({"files": [], "gate_signature": "x", "expires_at": "y"}) == [
            "files"
        ]
        assert missing_v3_fields("not a dict") == ["files", "gate_signature", "expires_at"]


# ------------------------------------------------------------ AC5: redeem-once


class TestRedeemOnce:
    def test_second_presentation_is_refused(self, conn, keyed_project):
        _, handle, _ = _make_run(conn, keyed_project)
        first = redeem_handle(conn, handle, task_slug="demo-task", project_dir=keyed_project)
        assert first.ok, first.reason
        second = redeem_handle(conn, handle, task_slug="demo-task", project_dir=keyed_project)
        assert not second.ok and "already spent" in second.reason

    def test_redeem_is_atomic_on_the_predicate(self, conn, keyed_project):
        """The guarantee is the UPDATE's `IS NULL`, not a prior read — so a
        direct second `redeem` (bypassing check_handle) must also fail."""
        run_id, handle, _ = _make_run(conn, keyed_project)
        _, nonce = vh.parse_handle(handle)
        assert vh.redeem(conn, run_id, nonce) is True
        assert vh.redeem(conn, run_id, nonce) is False

    def test_redeem_requires_the_matching_nonce(self, conn, keyed_project):
        run_id, _, _ = _make_run(conn, keyed_project)
        assert vh.redeem(conn, run_id, "c" * 32) is False

    def test_a_refused_handle_is_not_consumed(self, conn, keyed_project):
        """A close that fails validation must leave the handle spendable —
        otherwise one bad `task done` burns a green nobody got to use."""
        run_id, handle, _ = _make_run(conn, keyed_project, slug="task-a")
        assert not redeem_handle(conn, handle, task_slug="wrong-task", project_dir=keyed_project).ok
        row = conn.execute(
            "SELECT handle_redeemed_at FROM verification_runs WHERE id=?", (run_id,)
        ).fetchone()
        assert row[0] is None
        assert redeem_handle(conn, handle, task_slug="task-a", project_dir=keyed_project).ok


# ---------------------------------------------- AC6: security predicate source


class TestSecuritySensitiveScope:
    def test_security_paths_are_read_from_the_receipt(self, conn, keyed_project):
        """The predicate must judge what the receipt COVERED. Judging the
        caller's argument instead let a harmless declared scope at close time
        launder a receipt that covered auth/."""
        _, handle, _ = _make_run(conn, keyed_project, files=("auth/login.py",))
        verdict = check_handle(conn, handle, task_slug="demo-task", project_dir=keyed_project)
        assert not verdict.ok and "security-sensitive" in verdict.reason


# --------------------------------------------------------- AC7: keyless mode


class TestRedeemRespectsAnOpenTransaction:
    """REGRESSION (review, critical). `redeem`/`mint_handle` used a bare
    `conn.commit()`. The MCP server shares ONE connection across threads with no
    mutex, so that commit could land somebody else's half-written `task_done` —
    a task left marked done with none of the writes that justify it."""

    def test_redeem_does_not_commit_a_transaction_it_did_not_open(self, conn, keyed_project):
        run_id, handle, _ = _make_run(conn, keyed_project)
        conn.execute("CREATE TABLE bystander (v TEXT)")
        conn.commit()
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("INSERT INTO bystander (v) VALUES ('half-written')")
        assert vh.redeem(conn, *vh.parse_handle(handle))
        assert conn.in_transaction, "redeem committed a transaction it did not open"
        conn.rollback()
        assert conn.execute("SELECT COUNT(*) FROM bystander").fetchone()[0] == 0, (
            "the bystander's write survived a rollback — redeem committed it"
        )
        # The redemption rolled back with it, which is correct: our write was
        # part of the caller's transaction and shares its fate.
        row = conn.execute(
            "SELECT handle_redeemed_at FROM verification_runs WHERE id=?", (run_id,)
        ).fetchone()
        assert row[0] is None

    def test_redeem_commits_when_it_owns_the_transaction(self, conn, keyed_project):
        run_id, handle, _ = _make_run(conn, keyed_project)
        assert not conn.in_transaction
        assert vh.redeem(conn, *vh.parse_handle(handle))
        assert not conn.in_transaction
        row = conn.execute(
            "SELECT handle_redeemed_at FROM verification_runs WHERE id=?", (run_id,)
        ).fetchone()
        assert row[0] is not None


class TestGitScopeIsRecheckedAtRedemption:
    """REGRESSION (review, high). The handle branch is decided BEFORE the
    undeclared-scope block so the receipt can supply the scope — which meant a
    close declaring no files reached it, the task-done git comparison measured
    an empty set and said "unknown", and nothing noticed the tree had moved past
    what the receipt covered. The comparison is redone against the RECEIPT's
    list."""

    def test_undeclared_security_sensitive_change_blocks(self, conn, keyed_project, monkeypatch):
        _, handle, _ = _make_run(conn, keyed_project, files=("scripts/demo.py",))
        monkeypatch.setattr(
            "verify_scope_honesty.describe_declared_scope",
            lambda files, started: {
                "status": "under-declared",
                "undeclared": ["auth/login.py"],
                "undeclared_count": 1,
                # `security_block_reason` reads THIS key, not `undeclared` — the
                # security predicate is applied by describe_declared_scope, and
                # a stub that omitted it would silently exercise the
                # non-blocking branch while claiming to test the blocking one.
                "security_undeclared": ["auth/login.py"],
            },
        )
        verdict = check_handle(conn, handle, task_slug="demo-task", project_dir=keyed_project)
        assert not verdict.ok
        assert "security-sensitive" in verdict.reason
        assert "auth/login.py" in verdict.reason

    def test_plain_divergence_is_noted_but_does_not_block(self, conn, keyed_project, monkeypatch):
        """Decision #138: divergence fires on nearly every honest close
        (CHANGELOG, docs, generated constants). It is recorded, not blocked —
        but it IS said, because a divergence nobody sees is the same as one
        that was never measured."""
        _, handle, _ = _make_run(conn, keyed_project, files=("scripts/demo.py",))
        monkeypatch.setattr(
            "verify_scope_honesty.describe_declared_scope",
            lambda files, started: {
                "status": "under-declared",
                "undeclared": ["CHANGELOG.md"],
                "undeclared_count": 1,
            },
        )
        verdict = check_handle(conn, handle, task_slug="demo-task", project_dir=keyed_project)
        assert verdict.ok, verdict.reason
        assert "outside this receipt's scope" in verdict.reason
        assert "non-blocking" in verdict.reason


class TestKeylessProjectIsANamedMode:
    def test_keyless_refusal_says_so_explicitly(self, conn, tmp_path, monkeypatch):
        crypto_keys.init_keys(str(tmp_path))
        monkeypatch.chdir(tmp_path)
        _, handle, _ = _make_run(conn, str(tmp_path))
        # Remove the key AFTER minting: the project that verified had one, the
        # project presenting no longer does.
        import shutil

        shutil.rmtree(os.path.join(str(tmp_path), ".tausik", "keys"))
        verdict = check_handle(conn, handle, task_slug="demo-task", project_dir=str(tmp_path))
        assert not verdict.ok
        assert "keyless project, not a failed check" in verdict.reason
        assert "tausik key init" in verdict.reason

    def test_keyless_is_distinguishable_from_a_valid_check(self, conn, keyed_project):
        _, handle, _ = _make_run(conn, keyed_project)
        ok = check_handle(conn, handle, task_slug="demo-task", project_dir=keyed_project)
        assert ok.ok and "VALID" in ok.reason and "keyless" not in ok.reason
