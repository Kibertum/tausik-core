"""Release qualification v2 binds evidence to both release-line objects."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import release_qualification_v2 as qualification  # noqa: E402
import release_qualification_cli as qualification_cli  # noqa: E402
import crypto_ed25519 as ed25519  # noqa: E402


def test_scenario_manifest_types_remain_available_from_v2_facade():
    assert qualification.ScenarioPublication.__name__ == "ScenarioPublication"
    assert qualification.ScenarioCurrent.__name__ == "ScenarioCurrent"
    assert qualification.ScenarioPublished.__name__ == "ScenarioPublished"
    assert qualification.ScenarioManifest.__name__ == "ScenarioManifest"


CROSSCUTTING_SCOPE = ["scripts/project_cli_publish.py", ".github/workflows/"]
EXPECTED_PRODUCTION_PUBLIC_KEY_HEX = (
    "32b34b3fbcab55280b02390bb6b7e529e0720efdaaa5f08b46db69025f2a1bb1"
)


@pytest.fixture(autouse=True)
def pinned_release_key(monkeypatch):
    monkeypatch.setattr(
        qualification, "PINNED_PUBLIC_KEY_HEX", ed25519.public_from_seed(b"k" * 32).hex()
    )
    monkeypatch.setattr(
        qualification,
        "PINNED_SCENARIO_HARNESS_SHA256",
        hashlib.sha256(b"trusted harness\n").hexdigest(),
    )
    monkeypatch.setattr(
        qualification,
        "PINNED_SCENARIO_MANIFEST_SHA256",
        hashlib.sha256(json.dumps(_manifest()).encode()).hexdigest(),
    )


def _manifest() -> dict[str, object]:
    historical = [name for name in qualification.REQUIRED_SCENARIOS if name != "clean-current"]
    tags = (
        "v1.11.7",
        "v1.11.8",
        "v1.11.9",
        "v1.11.10",
        "v1.11.11",
        "v1.11.12",
        "v1.11.13",
        "v1.12.0",
        "v1.13.0",
    )
    return {
        "schema": 1,
        "publication": {
            "observed_at": "2026-11-12T16:38:00Z",
            "anonymous_url": "https://github.com/Kibertum/tausik-core.git",
        },
        "current": {"boundary": "clean-current"},
        "published": [
            {
                "boundary": name,
                "tag": tag,
                "commit": f"{index + 1:040x}",
                "tree": f"{index + 101:040x}",
            }
            for index, (name, tag) in enumerate(zip(historical, tags, strict=True))
        ],
    }


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True, encoding="utf-8", check=False
    )
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


@pytest.fixture
def release_repo(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-b", "main")
    _git(root, "config", "user.email", "test@example.invalid")
    _git(root, "config", "user.name", "Test")
    for rel in qualification.PROJECTION_PATHS:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"projection:{rel}\n", encoding="utf-8")
    manifest = root / qualification.SCENARIO_MANIFEST_PATH
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps(_manifest()), encoding="utf-8")
    harness = root / qualification.SCENARIO_HARNESS_PATH
    harness.write_text("trusted harness\n", encoding="utf-8")
    (root / "pyproject.toml").write_text('[project]\nversion = "2.0.0"\n', encoding="utf-8")
    (root / "scripts" / "tausik_version.py").write_text('__version__ = "2.0.0"\n', encoding="utf-8")
    (root / "README.md").write_text("development\n", encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-m", "development")
    development = _git(root, "rev-parse", "HEAD")
    tree = _git(root, "rev-parse", "HEAD^{tree}")
    snapshot = _git(root, "commit-tree", tree, "-m", "public snapshot")
    _git(root, "tag", "v2.0.0", development)
    return root, development, snapshot


def _results(root: Path, snapshot: str):
    report_sha256 = "2" * 64
    lanes = {
        lane: {
            "conclusion": "success",
            "sha": snapshot,
            "run_id": 7,
            "report_sha256": "2" * 64,
        }
        for lane in qualification.REQUIRED_LANES
    }
    scenarios = {
        scenario: {
            "status": "passed",
            "report_sha256": report_sha256,
            "evidence_sha256": qualification.scenario_evidence_hash(
                root, snapshot, scenario, report_sha256
            ),
        }
        for scenario in qualification.REQUIRED_SCENARIOS
    }
    return lanes, scenarios


def _candidate(release_repo):
    root, development, snapshot = release_repo
    lanes, scenarios = _results(root, snapshot)
    return qualification.build_candidate(
        root,
        version="2.0.0",
        development_ref=development,
        public_snapshot_ref=snapshot,
        verifier_ref=snapshot,
        lane_results=lanes,
        platform_checks=qualification.native_windows_platform_checks(
            snapshot,
            conclusion="success",
            run_id=7,
            run_attempt=1,
            workflow_sha=snapshot,
        ),
        scenario_results=scenarios,
    )


def test_frozen_adherence_v1_release_artifacts_are_byte_identical():
    expected = {
        "scripts/adherence_release.py": "c795e607555648498bdb0e9f6af23f118dd84ccb2a2055d0c1349ad3c2c173ac",
        "tests/fixtures/adherence/release-manifest-v1.json": "cf5822d5071b4269d25b69a92a8e63d6d4a9e52fe5ec28210fe34ebfca5c96c1",
    }
    assert {
        rel: hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() for rel in expected
    } == expected


def test_candidate_binds_objects_projections_scenarios_and_exact_lanes(release_repo):
    root, development, snapshot = release_repo
    candidate = _candidate(release_repo)

    assert candidate["schema"] == 2
    assert candidate["version"] == "2.0.0"
    assert candidate["development"]["commit"] == development
    assert candidate["public_snapshot"]["commit"] == snapshot
    assert candidate["verifier_revision"] == snapshot
    assert set(candidate["scenarios"]) == set(qualification.REQUIRED_SCENARIOS)
    assert set(candidate["lanes"]) == set(qualification.REQUIRED_LANES)
    assert set(candidate["platform_checks"]) == set(qualification.REQUIRED_PLATFORM_CHECKS)
    assert candidate["development"]["tree"] == _git(root, "rev-parse", f"{development}^{{tree}}")
    assert candidate["public_snapshot"]["tree"] == _git(root, "rev-parse", f"{snapshot}^{{tree}}")
    assert set(candidate["development"]["projections"]) == set(qualification.PROJECTION_PATHS)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("status", "skipped"),
        ("candidate_sha", "0" * 40),
        ("workflow_sha", "0" * 40),
        ("job", "forged-job"),
        ("evidence_kind", "candidate-junit"),
        ("trust_class", "trusted-junit"),
        ("run_id", 8),
        ("run_attempt", 0),
    ],
)
def test_candidate_refuses_forged_native_windows_platform_binding(release_repo, field, value):
    candidate = _candidate(release_repo)
    candidate["platform_checks"]["native-windows"][field] = value

    with pytest.raises(qualification.QualificationError, match="Windows|platform"):
        qualification.issue_attestation(
            release_repo[0], candidate, signing_seed=b"k" * 32, now="2026-11-13T10:00:00Z"
        )


@pytest.mark.parametrize("weakening", ["version", "run", "report", "verifier"])
def test_candidate_refuses_cross_run_or_cross_revision_evidence(release_repo, weakening):
    root, development, snapshot = release_repo
    lanes, scenarios = _results(root, snapshot)
    version = "2.0.0"
    verifier = snapshot
    if weakening == "version":
        version = "2.0.1"
    elif weakening == "run":
        lanes["lint"]["run_id"] = 8
    elif weakening == "report":
        digest = "3" * 64
        for name in qualification.REQUIRED_SCENARIOS:
            scenarios[name]["report_sha256"] = digest
            scenarios[name]["evidence_sha256"] = qualification.scenario_evidence_hash(
                root, snapshot, name, digest
            )
    else:
        verifier = development

    with pytest.raises(qualification.QualificationError):
        qualification.build_candidate(
            root,
            version=version,
            development_ref=development,
            public_snapshot_ref=snapshot,
            verifier_ref=verifier,
            lane_results=lanes,
            platform_checks=qualification.native_windows_platform_checks(
                snapshot,
                conclusion="success",
                run_id=7,
                run_attempt=1,
                workflow_sha=snapshot,
            ),
            scenario_results=scenarios,
        )


@pytest.mark.parametrize("weakening", ["missing", "failed", "forged-evidence", "extra"])
def test_trusted_verifier_refuses_candidate_controlled_scenario_weakening(release_repo, weakening):
    candidate = _candidate(release_repo)
    if weakening == "missing":
        candidate["scenarios"].pop(qualification.REQUIRED_SCENARIOS[0])
    elif weakening == "failed":
        candidate["scenarios"][qualification.REQUIRED_SCENARIOS[0]]["status"] = "skipped"
    elif weakening == "forged-evidence":
        candidate["scenarios"][qualification.REQUIRED_SCENARIOS[0]]["evidence_sha256"] = "0" * 64
    else:
        candidate["required_scenarios"] = []

    with pytest.raises(qualification.QualificationError, match="scenario"):
        qualification.issue_attestation(
            release_repo[0], candidate, signing_seed=b"k" * 32, now="2026-11-13T10:00:00Z"
        )


def test_attestation_is_exact_fresh_and_single_use(release_repo, tmp_path):
    root, development, snapshot = release_repo
    candidate = _candidate(release_repo)
    key = b"k" * 32
    attestation = qualification.issue_attestation(
        root,
        candidate,
        signing_seed=key,
        now="2026-11-13T10:00:00Z",
        nonce="ab" * 32,
    )
    ledger = tmp_path / "used"

    qualification.consume_attestation(
        root,
        candidate,
        attestation,
        version="2.0.0",
        development_ref=development,
        public_snapshot_ref=snapshot,
        ledger_path=ledger,
        now=datetime(2026, 11, 13, 10, 5, tzinfo=timezone.utc),
    )
    with pytest.raises(qualification.QualificationError, match="replayed"):
        qualification.consume_attestation(
            root,
            candidate,
            attestation,
            version="2.0.0",
            development_ref=development,
            public_snapshot_ref=snapshot,
            ledger_path=ledger,
            now=datetime(2026, 11, 13, 10, 6, tzinfo=timezone.utc),
        )


def test_attestation_consumption_fails_closed_when_marker_exists(release_repo, tmp_path):
    root, development, snapshot = release_repo
    candidate = _candidate(release_repo)
    key = b"k" * 32
    attestation = qualification.issue_attestation(
        root, candidate, signing_seed=key, now="2026-11-13T10:00:00Z", nonce="ab" * 32
    )
    ledger = tmp_path / "used"
    qualification.ledger.consume(ledger, "ab" * 32)

    with pytest.raises(qualification.QualificationError, match="replayed"):
        qualification.consume_attestation(
            root,
            candidate,
            attestation,
            version="2.0.0",
            development_ref=development,
            public_snapshot_ref=snapshot,
            ledger_path=ledger,
            now=datetime(2026, 11, 13, 10, 5, tzinfo=timezone.utc),
        )


def test_nonce_consumption_is_atomic_under_concurrency(tmp_path):
    nonce = "ab" * 32

    def consume_once():
        try:
            qualification.ledger.consume(tmp_path / "used", nonce)
        except qualification.ledger.LedgerError:
            return "replay"
        return "consumed"

    with ThreadPoolExecutor(max_workers=8) as pool:
        outcomes = list(pool.map(lambda _index: consume_once(), range(8)))

    assert outcomes.count("consumed") == 1
    assert outcomes.count("replay") == 7
    assert (tmp_path / "used" / nonce).read_bytes() == b"consumed\n"


@pytest.mark.parametrize("mutation", ["candidate", "signature", "expired", "future", "snapshot"])
def test_attestation_refuses_stale_or_mismatched_evidence(release_repo, tmp_path, mutation):
    root, development, snapshot = release_repo
    candidate = _candidate(release_repo)
    key = b"k" * 32
    attestation = qualification.issue_attestation(
        root, candidate, signing_seed=key, now="2026-11-13T10:00:00Z", nonce="ab" * 32
    )
    now = datetime(2026, 11, 13, 10, 5, tzinfo=timezone.utc)
    snapshot_ref = snapshot
    if mutation == "candidate":
        candidate["version"] = "2.0.1"
    elif mutation == "signature":
        attestation["signature"] = "0" * 128
    elif mutation == "expired":
        now = datetime(2026, 11, 13, 12, 0, tzinfo=timezone.utc)
    elif mutation == "future":
        now = datetime(2026, 11, 13, 9, 59, tzinfo=timezone.utc)
    else:
        snapshot_ref = development

    with pytest.raises(qualification.QualificationError):
        qualification.consume_attestation(
            root,
            candidate,
            attestation,
            version="2.0.0",
            development_ref=development,
            public_snapshot_ref=snapshot_ref,
            ledger_path=tmp_path / "used",
            now=now,
        )


def test_trusted_verifier_ratchets_are_literal_and_reviewable():
    assert qualification.REQUIRED_LANES == (
        "lint",
        "qualification-matrix",
        "test-full",
    )
    assert qualification.REQUIRED_SCENARIOS == (
        "call-budget-recovery-retirement",
        "clean-current",
        "handoff",
        "lease-and-stop-baseline",
        "lease-completion",
        "obsolete-unbind",
        "post-tool-failure",
        "pre-lease-stop-regression",
        "repeated-stop",
        "terminal-unbind-next-lifecycle",
    )
    assert (
        hashlib.sha256((ROOT / qualification.SCENARIO_MANIFEST_PATH).read_bytes()).hexdigest()
        == "aff62c6d0ab079fc3746959916fa22c443fe87b76efa8f819a33cb05e567c128"
    )
    assert (
        hashlib.sha256((ROOT / qualification.SCENARIO_HARNESS_PATH).read_bytes()).hexdigest()
        == "e4cb6f5e6110b960316ee810e66dd989b39dbef6fe3362bed97217e651ec90d3"
    )


def test_untrusted_ci_artifacts_are_read_through_a_strict_byte_limit(monkeypatch, tmp_path):
    artifact = tmp_path / "windows.xml"
    artifact.write_bytes(b"1234")
    monkeypatch.setattr(qualification_cli, "MAX_EVIDENCE_BYTES", 3)

    with pytest.raises(qualification.QualificationError, match="byte limit"):
        qualification_cli._read_bounded(str(artifact), qualification=qualification)


@pytest.mark.parametrize(
    "mutation",
    ["extra-key", "local-path", "session-data", "private-time", "private-url"],
)
def test_public_upgrade_manifest_rejects_private_or_unstructured_data(mutation):
    manifest = _manifest()
    if mutation == "extra-key":
        manifest["local_path"] = "C:\\Users\\alice\\project"  # type: ignore[index]
    elif mutation == "local-path":
        manifest["published"][0]["boundary"] = "C:\\Users\\alice"  # type: ignore[index]
    elif mutation == "session-data":
        manifest["published"][0]["session_id"] = "thread-secret"  # type: ignore[index]
    elif mutation == "private-time":
        manifest["publication"]["observed_at"] = "C:\\Users\\alice\\secret"  # type: ignore[index]
    else:
        manifest["publication"]["anonymous_url"] = (  # type: ignore[index]
            "https://github.com/Kibertum/tausik-core/C:/Users/alice"
        )

    with pytest.raises(qualification.QualificationError, match="canonical public|canonical v1"):
        qualification.validate_scenario_manifest(manifest)

    assert qualification.validate_scenario_manifest(_manifest())["schema"] == 1


def test_shipped_upgrade_manifest_has_the_exact_public_schema():
    manifest = json.loads((ROOT / qualification.SCENARIO_MANIFEST_PATH).read_text(encoding="utf-8"))

    qualification.validate_scenario_manifest(manifest)
    assert set(manifest) == {"schema", "publication", "current", "published"}
    assert set(manifest["publication"]) == {"observed_at", "anonymous_url"}
    assert all(set(row) == {"tag", "commit", "tree", "boundary"} for row in manifest["published"])


def test_signing_seed_must_match_the_pinned_verifier_identity(release_repo):
    with pytest.raises(qualification.QualificationError, match="pinned"):
        qualification.issue_attestation(
            release_repo[0], _candidate(release_repo), signing_seed=b"z" * 32
        )


@pytest.mark.parametrize("value", ["A" * 64, "  " + "a" * 64, "ed25519:" + "a" * 64])
def test_ed25519_key_requires_exact_lowercase_hex(value):
    with pytest.raises(qualification.QualificationError, match="lowercase"):
        qualification.decode_ed25519_key(value, label="signing seed")


@pytest.mark.parametrize(
    "payload",
    [b'{"a":1,"a":2}\n', b'{\n  "a": 1\n}\n', b'{"a":1}'],
)
def test_qualification_document_requires_unique_canonical_json(tmp_path, payload):
    path = tmp_path / "document.json"
    path.write_bytes(payload)

    with pytest.raises(qualification.QualificationError):
        qualification.load_document(path)

    path.write_bytes(b'{"a":1}\n')
    assert qualification.load_document(path) == {"a": 1}


def test_scenario_manifest_cannot_delete_a_required_boundary(release_repo):
    root, _development, _snapshot = release_repo
    weakened = _manifest()
    weakened["published"].pop()  # type: ignore[union-attr]
    (root / qualification.SCENARIO_MANIFEST_PATH).write_text(json.dumps(weakened), encoding="utf-8")
    _git(root, "add", qualification.SCENARIO_MANIFEST_PATH)
    _git(root, "commit", "-m", "weaken manifest")

    with pytest.raises(qualification.QualificationError, match="trusted ratchet"):
        qualification.scenario_evidence_hash(
            root,
            _git(root, "rev-parse", "HEAD"),
            qualification.REQUIRED_SCENARIOS[0],
            "1" * 64,
        )


def test_scenario_harness_cannot_be_replaced_by_a_noop(release_repo):
    root, _development, _snapshot = release_repo
    (root / qualification.SCENARIO_HARNESS_PATH).write_text("pass\n", encoding="utf-8")
    _git(root, "add", qualification.SCENARIO_HARNESS_PATH)
    _git(root, "commit", "-m", "weaken harness")

    with pytest.raises(qualification.QualificationError, match="semantic ratchet"):
        qualification.scenario_evidence_hash(
            root,
            _git(root, "rev-parse", "HEAD"),
            qualification.REQUIRED_SCENARIOS[0],
            "1" * 64,
        )


@pytest.mark.parametrize("mutation", ["none", "missing", "skipped", "short"])
def test_junit_report_must_prove_every_real_journey(release_repo, mutation):
    root, _development, snapshot = release_repo
    cases = [f'<testcase name="{name}" />' for name in qualification.junit.EXACT_MATRIX_TESTS]
    if mutation == "missing":
        cases[0] = '<testcase name="unrelated-replacement" />'
    elif mutation == "skipped":
        cases[0] = cases[0].replace(" />", "><skipped /></testcase>")
    elif mutation == "short":
        cases.pop()
    report = ("<testsuites><testsuite>" + "".join(cases) + "</testsuite></testsuites>").encode()

    if mutation == "none":
        rows = qualification.scenario_results_from_junit(root, snapshot, report)
        assert set(rows) == set(qualification.REQUIRED_SCENARIOS)
        assert {row["status"] for row in rows.values()} == {"passed"}
    else:
        with pytest.raises(qualification.QualificationError, match="matrix"):
            qualification.scenario_results_from_junit(root, snapshot, report)


@pytest.mark.parametrize(
    "body", [b"<testsuite />", b"<testsuite><testcase><skipped /></testcase></testsuite>"]
)
def test_lane_junit_refuses_collected_or_skipped_only_suites(body):
    with pytest.raises(qualification.junit.JunitEvidenceError, match="passing test floor"):
        qualification.junit.validate_lane_report(body, minimum_cases=1, minimum_passes=1)


@pytest.mark.parametrize("body", [b"not-json", b"[{}]"])
def test_lint_report_must_be_machine_readable_and_empty(body):
    with pytest.raises(qualification.junit.JunitEvidenceError, match="lint result"):
        qualification.junit.validate_lint_report(body)


def _lane_report(passed: int, skipped: int) -> bytes:
    return (
        b"<testsuite>"
        + b"<testcase />" * passed
        + b"<testcase><skipped /></testcase>" * skipped
        + b"</testsuite>"
    )


@pytest.mark.parametrize(
    ("passed", "skipped", "valid"),
    [
        (13_879, 0, False),
        (13_799, 81, False),
        (13_800, 121, False),
        (13_800, 80, True),
    ],
    ids=["case-floor", "pass-floor", "skip-ceiling", "exact-boundary"],
)
def test_full_lane_ratchet_enforces_each_independent_boundary(passed, skipped, valid):
    assert (
        qualification.junit.FULL_LANE_MINIMUM_CASES,
        qualification.junit.FULL_LANE_MINIMUM_PASSES,
        qualification.junit.FULL_LANE_MAXIMUM_SKIPS,
    ) == (13_880, 13_800, 120)
    report = _lane_report(passed, skipped)

    if valid:
        assert (
            qualification.junit.validate_lane_report(report) == hashlib.sha256(report).hexdigest()
        )
    else:
        with pytest.raises(qualification.junit.JunitEvidenceError, match="passing test floor"):
            qualification.junit.validate_lane_report(report)


def test_failed_lane_junit_names_the_failure_without_becoming_evidence():
    report = (
        b'<testsuite><testcase classname="tests.test_boundary" name="test_refuses">'
        b'<failure message="expected refusal, got success" /></testcase></testsuite>'
    )

    assert qualification.junit.failure_summary(report) == (
        "tests.test_boundary.test_refuses: expected refusal, got success"
    )


def test_workflow_keeps_candidate_unprivileged_and_verifier_protected():
    import yaml

    workflow = (ROOT / ".github/workflows/release-qualification.yml").read_text(encoding="utf-8")
    workflow_document = yaml.safe_load(workflow)
    verifier = workflow.split("  protected-verifier:", 1)[1]
    windows = workflow.split("  qualification-windows:", 1)[1].split("\n  test-full:", 1)[0]

    assert "\n  candidate:\n" not in workflow
    assert "environment: release-qualification" in verifier
    assert "secrets.RELEASE_QUALIFICATION_SIGNING_SEED" in verifier
    assert "secrets.DEVELOPMENT_REPOSITORY_URL" in verifier
    assert "github.event.repository.default_branch" in verifier
    assert "github.ref == format('refs/heads/{0}'" in verifier
    assert "ref: ${{ github.workflow_sha }}" in verifier
    assert "trusted/scripts/release_qualification_v2.py" in verifier
    assert "release-qualification-v2.json" in verifier
    assert "scenarios-from-junit" in verifier
    assert workflow.count("release_qualification_container.py run") == 2
    assert workflow.count("PYTEST_DISABLE_PLUGIN_AUTOLOAD") == 1
    assert workflow.count("-p xdist.plugin -n auto") == 1
    assert workflow.count("--override-ini faulthandler_timeout=300") == 1
    assert "python trusted/scripts/release_qualification_windows.py" in windows
    assert "working-directory: candidate" not in windows
    assert "PYTEST_DISABLE_PLUGIN_AUTOLOAD" not in windows
    assert workflow.count("python bootstrap/bootstrap.py --no-detect --ide all") == 1
    assert "lanes-from-junit" in verifier
    assert "reports/full/test-full.xml" in verifier
    assert "test-macos.xml" not in workflow
    assert "test-macos" not in qualification.REQUIRED_LANES
    assert (
        "needs: [validate-inputs, lint, qualification-matrix, qualification-windows, "
        "test-full, test-macos]" in workflow
    )
    assert "${{ runner.temp }}/qualification-matrix.xml" in workflow
    assert "${{ runner.temp }}/test-full.xml" in workflow
    assert "qualification-windows.xml" in workflow
    assert "--windows-junit" not in verifier
    assert "--platform-checks platform-checks.json" in verifier
    assert "needs.qualification-windows.result" in verifier
    assert "success()" in verifier
    assert "--require-hashes" in workflow
    assert workflow.count("--only-binary=:all:") == 5
    assert "python -m pip download --require-hashes --only-binary=:all:" in workflow
    assert "PIP_NO_INDEX: '1'" in workflow
    assert "PIP_FIND_LINKS: ${{ runner.temp }}/runtime-wheelhouse" in workflow
    assert "ruff check --config ../trusted/.github/release-qualification-ruff.toml" in workflow
    assert "trusted/.github/release-qualification-runtime.txt" in workflow
    assert "reports/lint/lint-results.json" in verifier

    run_bodies = re.findall(r"run: \|\n((?:(?: {10}| {8}).*\n)+)", workflow)
    assert run_bodies and all("${{ inputs." not in body for body in run_bodies)
    action_refs = re.findall(r"uses: actions/[\w-]+@([^\s]+)", workflow)
    assert action_refs and all(re.fullmatch(r"[0-9a-f]{40}", ref) for ref in action_refs)
    checkout_steps = [
        step
        for job in workflow_document["jobs"].values()
        for step in job["steps"]
        if str(step.get("uses", "")).startswith("actions/checkout@")
    ]
    assert len(checkout_steps) == 11
    assert all(step.get("with", {}).get("persist-credentials") is False for step in checkout_steps)
    assert all("timeout-minutes" in job for job in workflow_document["jobs"].values())
    for name, job in workflow_document["jobs"].items():
        serialized = json.dumps(job)
        if name == "protected-verifier":
            assert job.get("environment") == "release-qualification"
            assert serialized.count("secrets.") == 2
        else:
            assert "environment" not in job
            assert "secrets." not in serialized


def test_controller_lock_carries_all_platform_wheels():
    from release_lock_hashes import render_all_artifact_hashes

    source = """demo==1.2.3
    # via controller
"""
    expected = ["1" * 64, "2" * 64, "3" * 64]

    rendered = render_all_artifact_hashes(source, lambda name, version: expected)

    assert rendered.count("--hash=sha256:") == 3
    assert all(digest in rendered for digest in expected)
    assert "# via controller" in rendered

    lock = (ROOT / ".github/release-qualification-controller.txt").read_text(encoding="utf-8")
    librt = lock.split("librt==0.16.0", 1)[1].split("\n    # via mypy", 1)[0]
    digests = set(re.findall(r"sha256:([0-9a-f]{64})", librt))
    # Multi-platform wheel set: a single-platform compile cannot produce this many.
    assert len(digests) >= 3
    assert {
        "17bac7f7a16b328fff77e440287693eb017abde913595b5827ebccbc21ecd8a6",
        "14ed6ebe3e4f85f326d7920011ad30ff49ed9334e62cf88caef9ba973d9e3a92",
        "33f41443a1f4e1f099331b3d8120e409fbff84b9760bc1cc9ea496f37ddaa5cc",
    } <= digests


def test_controller_lock_uses_wheels_and_excludes_source_archives():
    from release_lock_hashes import wheel_hashes_from_pypi_payload

    win = "1" * 64
    mac = "2" * 64
    linux = "3" * 64
    source = "4" * 64
    payload = {
        "info": {"version": "1.2.3"},
        "urls": [
            {
                "packagetype": "bdist_wheel",
                "filename": "demo-1.2.3-cp313-cp313-win_amd64.whl",
                "digests": {"sha256": win},
            },
            {
                "packagetype": "bdist_wheel",
                "filename": "demo-1.2.3-cp313-cp313-macosx_11_0_arm64.whl",
                "digests": {"sha256": mac},
            },
            {
                "packagetype": "bdist_wheel",
                "filename": "demo-1.2.3-cp313-cp313-manylinux2014_x86_64.whl",
                "digests": {"sha256": linux},
            },
            {
                "packagetype": "sdist",
                "filename": "demo-1.2.3.tar.gz",
                "digests": {"sha256": source},
            },
        ],
    }

    assert wheel_hashes_from_pypi_payload(payload, "demo", "1.2.3") == [win, mac, linux]


def test_controller_lock_render_keeps_win_mac_linux_wheel_set():
    from release_lock_hashes import render_all_artifact_hashes

    win, mac, linux = "a" * 64, "b" * 64, "c" * 64
    source = "demo==1.2.3 \\\n    --hash=sha256:" + ("d" * 64) + "\n"

    def lookup(name: str, version: str):
        assert (name, version) == ("demo", "1.2.3")
        return [linux, win, mac]  # unsorted on purpose

    rendered = render_all_artifact_hashes(source, lookup)
    digests = re.findall(r"sha256:([0-9a-f]{64})", rendered)
    assert digests == sorted([win, mac, linux])
    assert "d" * 64 not in digests


@pytest.mark.parametrize(
    "source, error",
    [
        ("# no pins\n", "no exact package pins"),
        ("demo==1.2.3 \\\n    --hash=sha256:not-a-digest\n", "malformed hash line"),
    ],
)
def test_controller_lock_expansion_fails_closed(source, error):
    from release_lock_hashes import render_all_artifact_hashes

    with pytest.raises(ValueError, match=error):
        render_all_artifact_hashes(source, lambda _name, _version: ["1" * 64])


def test_production_public_key_is_the_reviewed_identity_and_rejects_an_unrelated_seed():
    source = (ROOT / "scripts/release_qualification_v2.py").read_text(encoding="utf-8")
    match = re.search(r'^PINNED_PUBLIC_KEY_HEX = "([0-9a-f]+)"$', source, re.MULTILINE)

    assert match is not None
    assert match.group(1) == EXPECTED_PRODUCTION_PUBLIC_KEY_HEX
    public_key = bytes.fromhex(match.group(1))
    unrelated_seed = b"u" * 32
    message = b"release qualification production identity ratchet"

    assert len(public_key) == 32
    assert public_key != ed25519.public_from_seed(unrelated_seed)
    assert not ed25519.verify(public_key, message, ed25519.sign(unrelated_seed, message))


def test_cli_refuses_missing_junit_without_a_traceback(tmp_path, capsys):
    exit_code = qualification.main(
        [
            "--root",
            str(ROOT),
            "scenarios-from-junit",
            "--public-snapshot-ref",
            "0" * 40,
            "--junit",
            str(tmp_path / "missing.xml"),
            "--output",
            str(tmp_path / "result.json"),
        ]
    )

    assert exit_code == 1
    assert capsys.readouterr().out.startswith("REFUSED: qualification file operation failed:")


def test_cli_refuses_non_ascii_object_version_without_a_traceback(release_repo, tmp_path, capsys):
    root, _development, _snapshot = release_repo
    (root / "pyproject.toml").write_text('[project]\nversion = "é"\n', encoding="utf-8")
    _git(root, "add", "pyproject.toml")
    _git(root, "commit", "-m", "non-ascii version")
    commit = _git(root, "rev-parse", "HEAD")
    lanes, scenarios = _results(root, commit)
    lane_path = tmp_path / "lanes.json"
    platform_path = tmp_path / "platforms.json"
    scenario_path = tmp_path / "scenarios.json"
    lane_path.write_bytes(qualification.canonical_bytes(lanes) + b"\n")
    platform_path.write_bytes(
        qualification.canonical_bytes(
            qualification.native_windows_platform_checks(
                commit,
                conclusion="success",
                run_id=7,
                run_attempt=1,
                workflow_sha=commit,
            )
        )
        + b"\n"
    )
    scenario_path.write_bytes(qualification.canonical_bytes(scenarios) + b"\n")

    exit_code = qualification.main(
        [
            "--root",
            str(root),
            "candidate",
            "--version",
            "2.0.0",
            "--development-ref",
            commit,
            "--public-snapshot-ref",
            commit,
            "--verifier-ref",
            commit,
            "--lane-results",
            str(lane_path),
            "--platform-checks",
            str(platform_path),
            "--scenario-results",
            str(scenario_path),
            "--output",
            str(tmp_path / "candidate.json"),
        ]
    )

    output = capsys.readouterr().out
    assert exit_code == 1
    assert output.startswith("REFUSED: release version in pyproject.toml is not canonical ASCII")
    assert "Traceback" not in output
