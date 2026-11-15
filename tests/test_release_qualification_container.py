"""The release controller isolates candidate execution from trusted evidence."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import release_qualification_container as controller  # noqa: E402
import release_qualification_container_runtime as container_runtime  # noqa: E402
import release_qualification_junit as junit  # noqa: E402
import release_qualification_windows as windows_controller  # noqa: E402


def test_candidate_requirements_and_trusted_runtime_lock_are_pinned_together():
    assert (
        hashlib.sha256((ROOT / "requirements.txt").read_text(encoding="utf-8").encode()).hexdigest()
        == controller.CANDIDATE_REQUIREMENTS_SHA256
    )
    lock = ROOT / controller.RUNTIME_REQUIREMENTS
    assert lock.is_file()
    assert "--hash=sha256:" in lock.read_text(encoding="utf-8")


def test_windows_controller_executes_only_the_trusted_harness_without_conftest(tmp_path):
    trusted = tmp_path / "trusted"
    candidate = tmp_path / "candidate"
    trusted.mkdir()
    candidate.mkdir()
    marker = tmp_path / "candidate-conftest-ran"
    (candidate / "conftest.py").write_text(
        f"from pathlib import Path\nPath({str(marker)!r}).write_text('ran')\n",
        encoding="utf-8",
    )
    harness = trusted / "trusted_harness.py"
    harness.write_text(
        "import pytest\n@pytest.mark.slow\ndef test_trusted_harness(): assert True\n",
        encoding="utf-8",
    )
    report = tmp_path / "windows.xml"

    command = windows_controller._pytest_command(harness, report)
    plugin = command.index("-p")
    assert command[plugin : plugin + 4] == ["-p", "xdist.plugin", "-n", "auto"]
    # The outer suite already runs under xdist.  This subprocess exercises the
    # isolation flags and trusted harness path; spawning another worker pool is
    # both redundant and resource-sensitive.  Production still uses -n auto,
    # asserted above and exercised by the native Windows canary.
    del command[plugin : plugin + 4]
    result = subprocess.run(
        command,
        cwd=candidate,
        env={**os.environ, "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"},
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert not marker.exists()
    assert 'name="test_trusted_harness"' in report.read_text(encoding="utf-8")


def test_windows_controller_refuses_oversized_evidence(monkeypatch, tmp_path):
    report = tmp_path / "windows.xml"
    report.write_bytes(b"1234")
    monkeypatch.setattr(windows_controller, "MAX_EVIDENCE_BYTES", 3)

    with pytest.raises(windows_controller.WindowsQualificationError, match="byte limit"):
        windows_controller._read_report(report)


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def test_controller_starts_under_the_isolated_python_flags_used_by_the_image():
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-S",
            str(ROOT / "scripts/release_qualification_container.py"),
            "--help",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Trusted outer controller" in result.stdout


def test_candidate_materialization_keeps_safe_git_history_and_excludes_uncommitted_files(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    assert _git(source, "init", "-b", "main").returncode == 0
    assert _git(source, "config", "user.email", "test@example.invalid").returncode == 0
    assert _git(source, "config", "user.name", "Test").returncode == 0
    (source / "tracked.txt").write_text("tracked\n", encoding="utf-8")
    assert _git(source, "add", "tracked.txt").returncode == 0
    assert _git(source, "commit", "-m", "candidate").returncode == 0
    (source / "untracked.txt").write_text("untracked\n", encoding="utf-8")
    destination = tmp_path / "candidate"

    controller._extract_commit(source, destination)

    assert (destination / ".git").is_dir()
    assert (destination / "tracked.txt").read_text(encoding="utf-8") == "tracked\n"
    assert not (destination / "untracked.txt").exists()
    assert _git(destination, "rev-parse", "HEAD").stdout == _git(source, "rev-parse", "HEAD").stdout


def test_container_build_separates_candidate_install_from_trusted_runtime():
    dockerfile = controller.DOCKERFILE

    assert "AS candidate-dependencies" in dockerfile
    assert "FROM node@sha256:" in dockerfile
    assert "FROM python@sha256:" in dockerfile
    assert "COPY --from=node-runtime /usr/local/bin/node" in dockerfile
    assert "--wheel-dir /candidate-wheelhouse" in dockerfile
    assert "runtime-requirements.txt" in dockerfile
    assert dockerfile.count("--require-hashes") >= 2
    assert "--target /candidate-deps" in dockerfile
    assert dockerfile.count("WORKDIR /build") == 2
    assert dockerfile.count("python -I -m pip") == 3
    assert "WORKDIR /source" not in dockerfile
    assert "FROM python@" in dockerfile.split("AS runtime", 1)[0]
    runtime = dockerfile.split("AS runtime", 1)[1]
    assert "--require-hashes --target /opt/controller/site" in runtime
    assert "pyproject.toml /opt/controller/pyproject.toml" in runtime
    assert "sitecustomize.py" in runtime
    assert "sys.path.insert(0, '/opt/controller/site')" in runtime
    assert "sys.path.append('/candidate-deps')" in runtime
    assert "USER 10001:10001" in runtime
    assert '["python", "-I", "-S", "/opt/controller/controller.py", "inside"]' in runtime


def test_prepared_context_stages_split_controller_under_importable_image_names(
    monkeypatch, tmp_path
):
    destination = tmp_path / "candidate"

    def materialize(_candidate, target, _run, _check):
        target.mkdir()
        source = (ROOT / "requirements.txt").read_bytes().replace(b"\r\n", b"\n")
        (target / "requirements.txt").write_bytes(source)

    def publication_store(_trusted, target, _manifest, _run, _check):
        target.mkdir()

    monkeypatch.setattr(controller.context_builder, "extract_commit", materialize)
    monkeypatch.setattr(controller.context_builder, "prepare_publication_store", publication_store)

    controller._prepare_context(ROOT, ROOT, destination)

    staged = destination / ".release-controller"
    expected = {
        "controller.py": "scripts/release_qualification_container.py",
        "context.py": "scripts/release_qualification_container_context.py",
        "runtime.py": "scripts/release_qualification_container_runtime.py",
        "evidence.py": "scripts/release_qualification_evidence.py",
    }
    for staged_name, source_name in expected.items():
        assert (staged / staged_name).read_bytes() == (ROOT / source_name).read_bytes()

    image_controller = tmp_path / "image-controller"
    image_controller.mkdir()
    for source_name, image_name in (
        ("controller.py", "controller.py"),
        ("context.py", "release_qualification_container_context.py"),
        ("runtime.py", "release_qualification_container_runtime.py"),
        ("evidence.py", "release_qualification_evidence.py"),
        ("junit.py", "release_qualification_junit.py"),
    ):
        shutil.copy2(staged / source_name, image_controller / image_name)
    result = subprocess.run(
        [sys.executable, "-I", "-S", str(image_controller / "controller.py"), "--help"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Trusted outer controller" in result.stdout
    assert (
        "context.py /opt/controller/release_qualification_container_context.py"
        in controller.DOCKERFILE
    )
    assert (
        "runtime.py /opt/controller/release_qualification_container_runtime.py"
        in controller.DOCKERFILE
    )


@pytest.mark.parametrize("hostile_name", ["sitecustomize.py", "pip.py"])
def test_isolated_pip_startup_ignores_candidate_python_files(tmp_path, hostile_name):
    marker = tmp_path / "executed"
    (tmp_path / hostile_name).write_text(
        f"from pathlib import Path\nPath({str(marker)!r}).write_text('executed')\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, "-I", "-m", "pip", "--version"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert not marker.exists()


def test_outer_controller_completes_and_validates_the_network_case(monkeypatch, tmp_path):
    names = [name for name in junit.EXACT_MATRIX_TESTS if name != controller.REMOTE_TEST]
    report = (
        "<testsuite>" + "".join(f'<testcase name="{name}" />' for name in names) + "</testsuite>"
    ).encode()
    monkeypatch.setattr(
        controller,
        "_remote_case",
        lambda _trusted: ET.Element("testcase", name=controller.REMOTE_TEST),
    )

    completed = controller._complete_matrix(report, tmp_path)

    assert len(junit.validate_matrix_report(completed)) == len(junit.EXACT_MATRIX_TESTS)


def test_outer_evidence_writer_refuses_preexisting_or_linked_targets(tmp_path):
    output = tmp_path / "report.xml"
    controller._safe_output(output, b"evidence")
    assert output.read_bytes() == b"evidence"

    with pytest.raises(controller.ControllerError, match="fresh regular file"):
        controller._safe_output(output, b"replacement")

    linked = tmp_path / "linked.xml"
    linked.symlink_to(tmp_path / "missing-target.xml")
    with pytest.raises(controller.ControllerError, match="fresh regular file"):
        controller._safe_output(linked, b"replacement")


def test_outer_evidence_writer_translates_parent_creation_failure(tmp_path):
    invalid_parent = tmp_path / "not-a-directory"
    invalid_parent.write_text("occupied", encoding="utf-8")
    output = invalid_parent / "report.xml"

    with pytest.raises(controller.ControllerError, match="fresh regular file"):
        controller._safe_output(output, b"evidence")

    assert invalid_parent.is_file()


@pytest.mark.parametrize("failure", ["fsync", "link", "partial-write", "pending-unlink"])
def test_outer_evidence_writer_leaves_no_artifact_after_io_failure(monkeypatch, tmp_path, failure):
    output = tmp_path / "report.xml"

    if failure == "fsync":
        monkeypatch.setattr(controller.os, "fsync", lambda _fd: (_ for _ in ()).throw(OSError()))
    elif failure == "link":
        monkeypatch.setattr(
            controller.os,
            "link",
            lambda _source, _target: (_ for _ in ()).throw(OSError()),
        )
    elif failure == "partial-write":
        original_write = controller.os.write
        calls = 0

        def interrupted_write(fd, payload):
            nonlocal calls
            calls += 1
            if calls == 1:
                return original_write(fd, payload[:1])
            raise OSError("injected write failure")

        monkeypatch.setattr(controller.os, "write", interrupted_write)
    else:
        original_unlink = Path.unlink
        failed = False

        def interrupted_unlink(path, *args, **kwargs):
            nonlocal failed
            if path.name.endswith(".pending") and not failed:
                failed = True
                raise OSError("injected pending cleanup failure")
            return original_unlink(path, *args, **kwargs)

        monkeypatch.setattr(Path, "unlink", interrupted_unlink)

    with pytest.raises(controller.ControllerError, match="fresh regular file"):
        controller._safe_output(output, b"evidence")

    assert not output.exists()
    assert list(tmp_path.iterdir()) == []


def _valid_boundary_record():
    return {
        "Config": {"User": "10001:10001"},
        "Mounts": [],
        "HostConfig": {
            "NetworkMode": "none",
            "ReadonlyRootfs": True,
            "CapDrop": ["ALL"],
            "Privileged": False,
            "SecurityOpt": ["no-new-privileges:true"],
            "Binds": None,
            "Devices": [],
            "PidsLimit": 2048,
            "Tmpfs": {
                "/work": "rw,exec,nosuid,nodev,size=3g,uid=10001,gid=10001,mode=1770",
                "/tmp": "rw,exec,nosuid,nodev,size=6g,uid=10001,gid=10001,mode=1777",
                "/result": "rw,nosuid,nodev,noexec,size=64m,uid=10001,gid=10001,mode=0700",
            },
        },
    }


def test_effective_container_inspection_accepts_the_exact_boundary():
    controller._validate_container_boundary(_valid_boundary_record())


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("NetworkMode", "default", "networkless"),
        ("ReadonlyRootfs", False, "read-only"),
        ("CapDrop", [], "privileges"),
        ("SecurityOpt", [], "escalation"),
        ("Binds", ["/host:/host"], "host bind"),
        ("PidsLimit", 0, "process limit"),
        ("Tmpfs", {}, "writable filesystems"),
    ],
)
def test_effective_container_inspection_refuses_weakened_boundaries(field, value, message):
    record = _valid_boundary_record()
    record["HostConfig"][field] = value

    with pytest.raises(controller.ControllerError, match=message):
        controller._validate_container_boundary(record)


@pytest.mark.parametrize("mount_type", ["bind", "volume", "device"])
def test_effective_container_inspection_refuses_top_level_mounts(mount_type):
    record = _valid_boundary_record()
    record["Mounts"] = [
        {
            "Type": mount_type,
            "Source": "/host/source",
            "Destination": "/work/attached",
            "RW": True,
        }
    ]

    with pytest.raises(controller.ControllerError, match="unexpected mounts"):
        controller._validate_container_boundary(record)


def test_effective_container_inspection_requires_the_real_mounts_field():
    record = _valid_boundary_record()
    del record["Mounts"]

    with pytest.raises(controller.ControllerError, match="unexpected mounts"):
        controller._validate_container_boundary(record)


@pytest.mark.parametrize("inspection", ["not-json", "{}", "[]", "[{}, {}]"])
def test_container_inspection_refuses_malformed_json_or_count(monkeypatch, inspection):
    monkeypatch.setattr(
        controller,
        "_run",
        lambda argv, **_kwargs: subprocess.CompletedProcess(argv, 0, inspection, ""),
    )

    with pytest.raises(controller.ControllerError, match="malformed|unexpected inspection count"):
        controller._inspect_container_boundary("container")


def _runtime_observation():
    return {
        "euid": 10001,
        "host_surface": False,
        "mount_rows": ["1 0 0:1 / / ro,relatime - overlay overlay ro"],
        "status_rows": [
            "CapEff:\t0000000000000000",
            "CapBnd:\t0000000000000000",
            "NoNewPrivs:\t1",
        ],
        "interface_rows": ["lo: 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0"],
        "route_rows": [],
        "controller_writable": False,
    }


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("euid", 0, "root privileges"),
        ("host_surface", True, "host surface"),
        ("mount_rows", ["1 0 0:1 / / rw - overlay overlay rw"], "root filesystem"),
        ("status_rows", ["CapEff:\t1", "CapBnd:\t0", "NoNewPrivs:\t1"], "capabilities"),
        (
            "status_rows",
            ["CapEff:\t0000000000000000", "CapBnd:\t0000000000000000", "NoNewPrivs:\t0"],
            "escalation",
        ),
        ("interface_rows", ["eth0: 0 0"], "non-loopback"),
        ("route_rows", ["eth0 00000000 00000000"], "default route"),
        ("controller_writable", True, "trusted controller"),
    ],
)
def test_runtime_observation_refuses_each_weakened_boundary(field, value, message):
    observation = _runtime_observation()
    observation[field] = value

    with pytest.raises(controller.ControllerError, match=message):
        container_runtime.validate_runtime_observation(**observation)


def test_runtime_observation_accepts_the_exact_boundary():
    container_runtime.validate_runtime_observation(**_runtime_observation())


def test_cleanup_attempts_every_resource_and_reports_each_failure(monkeypatch):
    calls = []

    def failed(argv, **_kwargs):
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 1, "", "busy")

    monkeypatch.setattr(controller, "_run", failed)

    errors = controller._cleanup_resources("container", "image")

    assert len(calls) == 2
    assert [error.split()[0] for error in errors] == ["container", "image"]


@pytest.mark.parametrize("primary_failure", [False, True])
def test_run_lane_never_hides_cleanup_failures(monkeypatch, tmp_path, capsys, primary_failure):
    monkeypatch.setattr(controller, "_prepare_context", lambda *_args: None)
    monkeypatch.setattr(controller, "_inspect_container_boundary", lambda *_args: None)
    monkeypatch.setattr(controller, "_wait_for_evidence", lambda *_args: 0)
    monkeypatch.setattr(controller, "_read_evidence", lambda *_args: b"<testsuite />")
    monkeypatch.setattr(controller, "_complete_matrix", lambda *_args: b"<testsuite />")
    monkeypatch.setattr(controller, "_wait_for_container", lambda *_args: None)
    monkeypatch.setattr(
        controller,
        "_cleanup_resources",
        lambda *_args: ["container could not be removed"],
    )

    def command(argv, **_kwargs):
        if primary_failure:
            raise controller.ControllerError("primary lane failure")
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(controller, "_run", command)
    candidate = tmp_path / "candidate"
    trusted = tmp_path / "trusted"
    candidate.mkdir()
    trusted.mkdir()

    expected = "primary lane failure" if primary_failure else "Docker cleanup failed"
    with pytest.raises(controller.ControllerError, match=expected):
        output = tmp_path / "evidence.xml"
        controller.run_lane(candidate, trusted, "matrix", output)

    warning = "WARNING: Docker cleanup failed"
    assert (warning in capsys.readouterr().err) is primary_failure
    assert not output.exists()


def test_run_lane_publishes_nothing_until_container_exit_is_verified(monkeypatch, tmp_path):
    monkeypatch.setattr(controller, "_prepare_context", lambda *_args: None)
    monkeypatch.setattr(controller, "_inspect_container_boundary", lambda *_args: None)
    monkeypatch.setattr(controller, "_wait_for_evidence", lambda *_args: 0)
    monkeypatch.setattr(controller, "_read_evidence", lambda *_args: b"<testsuite />")
    monkeypatch.setattr(controller, "_complete_matrix", lambda *_args: b"<testsuite />")
    monkeypatch.setattr(controller, "_cleanup_resources", lambda *_args: [])
    monkeypatch.setattr(
        controller,
        "_wait_for_container",
        lambda *_args: (_ for _ in ()).throw(controller.ControllerError("changed exit")),
    )
    monkeypatch.setattr(
        controller,
        "_run",
        lambda argv, **_kwargs: subprocess.CompletedProcess(argv, 0, "", ""),
    )
    candidate = tmp_path / "candidate"
    trusted = tmp_path / "trusted"
    output = tmp_path / "evidence.xml"
    candidate.mkdir()
    trusted.mkdir()

    with pytest.raises(controller.ControllerError, match="changed exit"):
        controller.run_lane(candidate, trusted, "matrix", output)

    assert not output.exists()


@pytest.mark.parametrize("state", ["paused", "restarting", "removing", "dead", "exited"])
def test_evidence_wait_refuses_a_nonproductive_container_state_without_waiting(monkeypatch, state):
    calls = []

    def completed(argv, **_kwargs):
        calls.append(argv)
        if argv[:3] == ["docker", "inspect", "--format"]:
            return subprocess.CompletedProcess(argv, 0, f"{state} 17\n", "")
        return subprocess.CompletedProcess(argv, 1, "", "not running")

    monkeypatch.setattr(controller, "_run", completed)

    with pytest.raises(
        controller.ControllerError,
        match=rf"cannot produce evidence .* status {state}, exit 17",
    ):
        controller._wait_for_evidence("container", timeout=1800)

    assert len(calls) == 2


@pytest.mark.parametrize("state", ["", "running", "running 0 extra", "unknown 0", "running nope"])
def test_evidence_wait_refuses_malformed_container_state_immediately(monkeypatch, state):
    def completed(argv, **_kwargs):
        if argv[:3] == ["docker", "inspect", "--format"]:
            return subprocess.CompletedProcess(argv, 0, state, "")
        return subprocess.CompletedProcess(argv, 1, "", "not ready")

    monkeypatch.setattr(controller, "_run", completed)

    with pytest.raises(controller.ControllerError, match="malformed|unknown"):
        controller._wait_for_evidence("container", timeout=1800)


def test_exit_status_is_published_atomically(tmp_path):
    container_runtime._publish_exit_code(tmp_path, 17)

    assert (tmp_path / "exit-code").read_text(encoding="ascii") == "17\n"
    assert not (tmp_path / ".exit-code.pending").exists()


@pytest.mark.parametrize("extra_byte", [False, True])
def test_evidence_reader_enforces_the_byte_limit(monkeypatch, extra_byte):
    monkeypatch.setattr(controller, "MAX_EVIDENCE_BYTES", 3)
    payload = b"x" * (3 + int(extra_byte))

    def completed(argv, **kwargs):
        assert argv[:3] == ["docker", "exec", "container"]
        assert kwargs == {"text": False}
        return subprocess.CompletedProcess(argv, 0, payload, b"")

    monkeypatch.setattr(controller, "_run", completed)

    if extra_byte:
        with pytest.raises(controller.ControllerError, match="size limit"):
            controller._read_evidence("container")
    else:
        assert controller._read_evidence("container") == payload


@pytest.mark.parametrize(
    ("reported", "message"),
    [("137\n", "status changed"), ("not-an-exit-code\n", "malformed")],
)
def test_container_wait_refuses_nonzero_or_malformed_exit(monkeypatch, reported, message):
    monkeypatch.setattr(
        controller,
        "_run",
        lambda argv, **_kwargs: subprocess.CompletedProcess(argv, 0, reported, ""),
    )

    with pytest.raises(controller.ControllerError, match=message):
        controller._wait_for_container("container", 0)


def test_container_wait_accepts_only_the_expected_exit(monkeypatch):
    monkeypatch.setattr(
        controller,
        "_run",
        lambda argv, **_kwargs: subprocess.CompletedProcess(argv, 0, "0\n", ""),
    )

    controller._wait_for_container("container", 0)


@pytest.mark.parametrize("language", ["en", "ru"])
def test_publishing_guide_describes_the_live_container_handshake(language):
    guide = (ROOT / "docs" / language / "publishing.md").read_text(encoding="utf-8")

    assert "64 MiB" in guide
    assert "32 MiB" in guide
    assert "`docker exec`" in guide
    assert "38" in guide
    assert "39" in guide
    assert "ten" in guide or "десять" in guide
    assert "evidence-volume" not in guide
    assert "dedicated volume" not in guide
    assert "отдельный volume" not in guide


def test_workflow_never_mounts_candidate_into_the_outer_artifact_directory():
    workflow = (ROOT / ".github/workflows/release-qualification.yml").read_text(encoding="utf-8")

    assert "--candidate candidate --trusted trusted" in workflow
    assert '--output "$RUNNER_TEMP/qualification-matrix.xml"' in workflow
    assert '--output "$RUNNER_TEMP/test-full.xml"' in workflow
    assert "release-qualification-v2-test-macos" not in workflow
    assert "reports/macos" not in workflow
    assert '"/tmp:rw,exec,nosuid,nodev' not in workflow


def test_runtime_bootstrap_is_offline_but_can_execute_its_generated_venv():
    source = "\n".join(
        (ROOT / path).read_text(encoding="utf-8")
        for path in (
            "scripts/release_qualification_container.py",
            "scripts/release_qualification_container_runtime.py",
        )
    )

    assert '"PIP_NO_INDEX": "/candidate-wheelhouse"' not in source
    assert '"PIP_NO_INDEX": "1"' in source
    assert '"PIP_FIND_LINKS": "/candidate-wheelhouse"' in source
    assert '"PYTHONPATH": "/opt/controller/site:/candidate-deps"' in source
    assert "_assert_runtime_boundary()" in source
    assert '"/work:rw,exec,nosuid,nodev' in source
    assert '"/tmp:rw,exec,nosuid,nodev' in source


def test_candidate_dependencies_precede_the_xdist_sys_path_snapshot():
    source = (ROOT / "scripts/release_qualification_container_runtime.py").read_text(
        encoding="utf-8"
    )

    assert source.index('sys.path.append("/candidate-deps")') < source.index("import xdist.plugin")


def test_controller_log_output_degrades_without_crashing_on_a_narrow_console(monkeypatch):
    class NarrowConsole:
        encoding = "ascii"
        value = ""

        def write(self, value):
            value.encode(self.encoding)
            self.value += value

        def flush(self):
            pass

    console = NarrowConsole()
    monkeypatch.setattr(container_runtime.sys, "stdout", console)

    container_runtime.emit("bootstrap → complete")

    assert console.value == "bootstrap \\u2192 complete"
