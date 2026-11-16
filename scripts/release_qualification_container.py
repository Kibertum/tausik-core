#!/usr/bin/env python3
"""Trusted outer controller for isolated release-qualification pytest lanes."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable
from typing import cast
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parent))
import release_qualification_junit as junit
import release_qualification_container_context as context_builder
from release_qualification_evidence import MAX_EVIDENCE_BYTES
from release_qualification_container_runtime import (
    ControllerError,
    inside,
)


BASE_IMAGE = "python@sha256:bcaf104ef2827b827bdd0b8b351742783fc050296e1dc150113e6ec869e652d0"
NODE_IMAGE = "node@sha256:e9f565d32859f0cbfb52125eafe8be39390f24dac302dc3cdf566e8ba3ab21ee"
CONTROLLER_REQUIREMENTS = ".github/release-qualification-controller.txt"
RUNTIME_REQUIREMENTS = ".github/release-qualification-runtime.txt"
CANDIDATE_REQUIREMENTS_SHA256 = "d2dccf8065d7fb4c0233d05866bd194171ac8993b2ceda3fbe4c31adb52a585f"
MATRIX_TEST = "tests/test_codex_upgrade_matrix.py"
MATRIX_MANIFEST = "tests/fixtures/codex_upgrade_matrix_v1.json"
REMOTE_TEST = "test_anonymous_publication_remote_matches_immutable_observation"
DOCKERFILE = f"""FROM {NODE_IMAGE} AS node-runtime

FROM {BASE_IMAGE} AS candidate-dependencies
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /build
COPY . /source
RUN python -I -m pip wheel --no-cache-dir --require-hashes --only-binary=:all: --wheel-dir /candidate-wheelhouse \\
      -r /source/.release-controller/runtime-requirements.txt && \\
    python -I -m pip install --no-cache-dir --no-index --only-binary=:all: \\
      --find-links /candidate-wheelhouse --require-hashes --target /candidate-deps \\
      -r /source/.release-controller/runtime-requirements.txt

FROM {BASE_IMAGE} AS runtime
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY --from=node-runtime /usr/local/bin/node /usr/local/bin/node
COPY --from=node-runtime /usr/local/lib/node_modules /usr/local/lib/node_modules
COPY --from=candidate-dependencies /candidate-deps /candidate-deps
COPY --from=candidate-dependencies /candidate-wheelhouse /candidate-wheelhouse
COPY . /source
WORKDIR /build
RUN mkdir -p /opt/controller/site && \\
    python -I -m pip install --no-cache-dir --require-hashes --only-binary=:all: --target /opt/controller/site \\
      -r /source/.release-controller/requirements.txt && \\
    ln -s /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm && \\
    ln -s /usr/local/lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx && \\
    useradd --uid 10001 --create-home runner && \\
    mkdir -p /opt/controller /result && \\
    cp /source/.release-controller/controller.py /opt/controller/controller.py && \\
    cp /source/.release-controller/context.py /opt/controller/release_qualification_container_context.py && \\
    cp /source/.release-controller/runtime.py /opt/controller/release_qualification_container_runtime.py && \\
    cp /source/.release-controller/evidence.py /opt/controller/release_qualification_evidence.py && \\
    cp /source/.release-controller/junit.py /opt/controller/release_qualification_junit.py && \\
    cp /source/.release-controller/matrix.py /opt/controller/matrix.py && \\
    cp /source/.release-controller/manifest.json /opt/controller/manifest.json && \\
    cp /source/.release-controller/pyproject.toml /opt/controller/pyproject.toml && \\
    cp -R /source/.release-controller/objects.git /opt/controller/objects.git && \\
    if [ -f /source/.release-controller/candidate-dockerignore ]; then \\
      cp /source/.release-controller/candidate-dockerignore /source/.dockerignore; \\
    fi && \\
    printf '%s\\n' 'import sys' \"sys.path.insert(0, '/opt/controller/site')\" \"sys.path.append('/candidate-deps')\" > /usr/local/lib/python3.13/site-packages/sitecustomize.py && \\
    git config --system --add safe.directory /opt/controller/objects.git && \\
    chown 10001:10001 /result && \\
    chmod -R a-w /opt/controller /candidate-deps /candidate-wheelhouse
USER 10001:10001
ENTRYPOINT ["python", "-I", "-S", "/opt/controller/controller.py", "inside"]
"""


def _run(
    argv: list[str],
    *,
    cwd: Path | None = None,
    timeout: int = 1800,
    text: bool = True,
) -> subprocess.CompletedProcess[str] | subprocess.CompletedProcess[bytes]:
    try:
        result = subprocess.run(
            argv,
            cwd=cwd,
            capture_output=True,
            text=text,
            encoding="utf-8" if text else None,
            errors="replace" if text else None,
            stdin=subprocess.DEVNULL,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ControllerError(f"controller command failed: {argv[0]}") from exc
    return result


def _check(result: subprocess.CompletedProcess[str] | subprocess.CompletedProcess[bytes]) -> None:
    if result.returncode:
        stdout = (
            result.stdout
            if isinstance(result.stdout, str)
            else result.stdout.decode("utf-8", errors="replace")
        )
        stderr = (
            result.stderr
            if isinstance(result.stderr, str)
            else result.stderr.decode("utf-8", errors="replace")
        )
        raise ControllerError(f"isolated lane failed:\n{stdout[-2000:]}\n{stderr[-1000:]}")


def _translate_context_error(action: Callable[[], None]) -> None:
    try:
        action()
    except ValueError as exc:
        raise ControllerError(str(exc)) from exc


def _extract_commit(root: Path, destination: Path) -> None:
    _translate_context_error(
        lambda: context_builder.extract_commit(root, destination, _run, _check)
    )


def _prepare_context(candidate: Path, trusted: Path, destination: Path) -> None:
    _translate_context_error(
        lambda: context_builder.prepare_context(
            candidate,
            trusted,
            destination,
            candidate_requirements_sha256=CANDIDATE_REQUIREMENTS_SHA256,
            controller_requirements=CONTROLLER_REQUIREMENTS,
            runtime_requirements=RUNTIME_REQUIREMENTS,
            matrix_test=MATRIX_TEST,
            matrix_manifest=MATRIX_MANIFEST,
            dockerfile=DOCKERFILE,
            run=_run,
            check=_check,
        )
    )


def _remote_case(trusted: Path) -> ET.Element:
    try:
        manifest = json.loads((trusted / MATRIX_MANIFEST).read_text(encoding="utf-8"))
        publication = manifest["publication"]
        rows = manifest["published"]
        remote = publication["anonymous_url"]
        refs = [f"refs/tags/{row['tag']}" for row in rows]
        expected = {ref: row["commit"] for ref, row in zip(refs, rows, strict=True)}
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise ControllerError("trusted publication manifest is malformed") from exc
    result = _run(["git", "ls-remote", remote, *refs], timeout=90)
    _check(result)
    assert isinstance(result.stdout, str)
    observed: dict[str, list[str]] = {}
    for line in result.stdout.splitlines():
        try:
            object_id, ref = line.split("\t", 1)
        except ValueError as exc:
            raise ControllerError("anonymous publication response is malformed") from exc
        observed.setdefault(ref, []).append(object_id)
    if observed != {ref: [object_id] for ref, object_id in expected.items()}:
        raise ControllerError("anonymous publication remote does not match trusted pins")
    return ET.Element("testcase", name=REMOTE_TEST, classname="qualification.remote")


def _complete_matrix(report: bytes, trusted: Path) -> bytes:
    try:
        document = ET.fromstring(report)
    except ET.ParseError as exc:
        raise ControllerError("isolated matrix JUnit is malformed") from exc
    suite = document if document.tag == "testsuite" else document.find(".//testsuite")
    if suite is None:
        raise ControllerError("isolated matrix JUnit has no test suite")
    suite.append(_remote_case(trusted))
    suite.set("tests", str(len(suite.findall("testcase"))))
    completed = cast(bytes, ET.tostring(document, encoding="utf-8", xml_declaration=True))
    junit.validate_matrix_report(completed)
    return completed


def _safe_output(path: Path, payload: bytes) -> None:
    pending = path.with_name(f".{path.name}.{secrets.token_hex(8)}.pending")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    published = False
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.is_symlink():
            raise OSError("outer evidence target is a symbolic link")
        fd = os.open(pending, flags, 0o600)
        try:
            remaining = memoryview(payload)
            while remaining:
                written = os.write(fd, remaining)
                if written <= 0:
                    raise OSError("short evidence write")
                remaining = remaining[written:]
            os.fsync(fd)
        finally:
            os.close(fd)
        # A hard link publishes without an overwrite window. Unlike replace(),
        # it fails when another writer already owns the authoritative path.
        os.link(pending, path)
        published = True
        pending.unlink()
        if os.name == "posix":
            directory_fd = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
    except OSError as exc:
        if published:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
        try:
            pending.unlink(missing_ok=True)
        except OSError:
            pass
        raise ControllerError("outer evidence path is not a fresh regular file") from exc


def _validate_container_boundary(record: object) -> None:
    """Validate Docker's effective container policy, not just the requested argv."""

    if not isinstance(record, dict):
        raise ControllerError("Docker returned a malformed container inspection")
    config = record.get("Config")
    host = record.get("HostConfig")
    if not isinstance(config, dict) or not isinstance(host, dict):
        raise ControllerError("Docker inspection is missing boundary configuration")
    if config.get("User") != "10001:10001":
        raise ControllerError("qualification container has an unexpected user")
    if host.get("NetworkMode") != "none" or host.get("ReadonlyRootfs") is not True:
        raise ControllerError("qualification container is not networkless and read-only")
    if host.get("CapDrop") != ["ALL"] or host.get("Privileged") is not False:
        raise ControllerError("qualification container retains privileges")
    security = host.get("SecurityOpt")
    if security not in (["no-new-privileges"], ["no-new-privileges:true"]):
        raise ControllerError("qualification container permits privilege escalation")
    if host.get("Binds") not in (None, []) or host.get("Devices") not in (None, []):
        raise ControllerError("qualification container exposes a host bind or device")
    if host.get("PidsLimit") != 2048:
        raise ControllerError("qualification container has an unexpected process limit")
    expected_tmpfs = {
        "/work": "rw,exec,nosuid,nodev,size=3g,uid=10001,gid=10001,mode=1770",
        "/tmp": "rw,exec,nosuid,nodev,size=6g,uid=10001,gid=10001,mode=1777",
        "/result": "rw,nosuid,nodev,noexec,size=64m,uid=10001,gid=10001,mode=0700",
    }
    if host.get("Tmpfs") != expected_tmpfs:
        raise ControllerError("qualification container has unexpected writable filesystems")
    # `docker inspect` reports effective mounts at the top level. HostConfig
    # only describes the requested mount settings and cannot prove what the
    # daemon actually attached.
    if record.get("Mounts") != []:
        raise ControllerError("qualification container has unexpected mounts")


def _inspect_container_boundary(container: str) -> None:
    inspected = _run(["docker", "inspect", container])
    _check(inspected)
    try:
        payload = json.loads(cast(str, inspected.stdout))
    except (json.JSONDecodeError, TypeError) as exc:
        raise ControllerError("Docker returned malformed inspection JSON") from exc
    if not isinstance(payload, list) or len(payload) != 1:
        raise ControllerError("Docker returned an unexpected inspection count")
    _validate_container_boundary(payload[0])


def _wait_for_evidence(container: str, *, timeout: int = 1800) -> int:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        ready = _run(["docker", "exec", container, "test", "-f", "/result/exit-code"])
        if ready.returncode == 0:
            status = _run(["docker", "exec", container, "cat", "/result/exit-code"])
            _check(status)
            try:
                return int(cast(str, status.stdout).strip())
            except (TypeError, ValueError) as exc:
                raise ControllerError("isolated lane returned a malformed status") from exc
        state = _run(
            [
                "docker",
                "inspect",
                "--format",
                "{{.State.Status}} {{.State.ExitCode}}",
                container,
            ]
        )
        _check(state)
        fields = cast(str, state.stdout).split()
        if len(fields) != 2:
            raise ControllerError("Docker returned a malformed container state")
        container_state, raw_exit_code = fields
        if container_state not in {"running", "paused", "restarting", "removing", "exited", "dead"}:
            raise ControllerError("Docker returned an unknown container state")
        try:
            observed_exit_code = int(raw_exit_code)
        except ValueError as exc:
            raise ControllerError("Docker returned a malformed container state") from exc
        if container_state != "running":
            raise ControllerError(
                "isolated lane cannot produce evidence "
                f"(container status {container_state}, exit {observed_exit_code})"
            )
        time.sleep(1)
    raise ControllerError("isolated lane did not produce evidence before timeout")


def _read_evidence(container: str) -> bytes:
    copied = _run(
        [
            "docker",
            "exec",
            container,
            "/usr/local/bin/python",
            "-I",
            "-S",
            "-c",
            (
                "import sys;"
                f"p=open('/result/report.xml','rb').read({MAX_EVIDENCE_BYTES + 1});"
                "sys.stdout.buffer.write(p)"
            ),
        ],
        text=False,
    )
    _check(copied)
    if not isinstance(copied.stdout, bytes):
        raise ControllerError("isolated lane evidence is not binary")
    if len(copied.stdout) > MAX_EVIDENCE_BYTES:
        raise ControllerError("isolated lane evidence exceeds the trusted size limit")
    return copied.stdout


def _wait_for_container(container: str, expected_exit_code: int) -> None:
    waited = _run(["docker", "wait", container], timeout=60)
    _check(waited)
    fields = cast(str, waited.stdout).split()
    try:
        actual_exit_code = int(fields[0]) if len(fields) == 1 else None
    except ValueError:
        actual_exit_code = None
    if actual_exit_code is None:
        raise ControllerError("Docker returned a malformed container exit status")
    if actual_exit_code != expected_exit_code:
        raise ControllerError(
            "qualification container exit status changed after evidence publication "
            f"(expected {expected_exit_code}, got {actual_exit_code})"
        )


def run_lane(candidate: Path, trusted: Path, lane: str, output: Path) -> None:
    token = secrets.token_hex(8)
    image = f"tausik-rq-{token}"
    container = f"tausik-rq-run-{token}"
    with tempfile.TemporaryDirectory(prefix="tausik-rq-context-") as raw_context:
        context = Path(raw_context)
        _prepare_context(candidate.resolve(), trusted.resolve(), context)
        report: bytes | None = None
        try:
            built = _run(
                [
                    "docker",
                    "build",
                    "--platform",
                    "linux/amd64",
                    "--tag",
                    image,
                    "--file",
                    str(context / "Dockerfile.release-qualification"),
                    str(context),
                ],
                timeout=1200,
            )
            _check(built)
            created = _run(
                [
                    "docker",
                    "create",
                    "--platform",
                    "linux/amd64",
                    "--name",
                    container,
                    "--network",
                    "none",
                    "--read-only",
                    "--cap-drop",
                    "ALL",
                    "--security-opt",
                    "no-new-privileges",
                    "--pids-limit",
                    "2048",
                    "--tmpfs",
                    "/work:rw,exec,nosuid,nodev,size=3g,uid=10001,gid=10001,mode=1770",
                    "--tmpfs",
                    "/tmp:rw,exec,nosuid,nodev,size=6g,uid=10001,gid=10001,mode=1777",
                    "--tmpfs",
                    "/result:rw,nosuid,nodev,noexec,size=64m,uid=10001,gid=10001,mode=0700",
                    "--env",
                    f"TAUSIK_RQ_LANE={lane}",
                    image,
                ]
            )
            _check(created)
            _inspect_container_boundary(container)
            _check(_run(["docker", "start", container]))
            exit_code = _wait_for_evidence(container)
            try:
                report_bytes = _read_evidence(container)
            except ControllerError as exc:
                if exit_code:
                    raise ControllerError(
                        f"isolated lane failed and evidence was unreadable: {exc}"
                    ) from exc
                raise
            if exit_code:
                raise ControllerError(
                    f"isolated lane failed: {junit.failure_summary(report_bytes)}"
                )
            report = _complete_matrix(report_bytes, trusted) if lane == "matrix" else report_bytes
            if lane == "full":
                junit.validate_lane_report(report)
            _check(_run(["docker", "exec", container, "touch", "/result/release"]))
            _wait_for_container(container, exit_code)
        finally:
            cleanup_errors = _cleanup_resources(container, image)
            if cleanup_errors:
                detail = "; ".join(cleanup_errors)[:1000]
                if sys.exc_info()[0] is None:
                    raise ControllerError(f"Docker cleanup failed: {detail}")
                print(f"WARNING: Docker cleanup failed: {detail}", file=sys.stderr)
        if report is None:
            raise ControllerError("qualification lane produced no publishable evidence")
        _safe_output(output.absolute(), report)


def _cleanup_resources(container: str, image: str) -> list[str]:
    errors: list[str] = []
    for kind, name, argv in (
        ("container", container, ["docker", "rm", "--force", container]),
        ("image", image, ["docker", "image", "rm", "--force", image]),
    ):
        try:
            result = _run(argv)
        except ControllerError as exc:
            errors.append(f"{kind} {name}: {exc}")
            continue
        if result.returncode:
            stderr = result.stderr if isinstance(result.stderr, str) else ""
            errors.append(f"{kind} {name}: {' '.join(stderr.split())[-300:]}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run")
    run.add_argument("--candidate", required=True, type=Path)
    run.add_argument("--trusted", required=True, type=Path)
    run.add_argument("--lane", required=True, choices=("matrix", "full"))
    run.add_argument("--output", required=True, type=Path)
    inside_parser = commands.add_parser("inside")
    inside_parser.add_argument("--lane", choices=("matrix", "full"))
    args = parser.parse_args(argv)
    try:
        if args.command == "inside":
            lane = args.lane or os.environ.get("TAUSIK_RQ_LANE", "")
            return inside(lane)
        run_lane(args.candidate, args.trusted, args.lane, args.output)
    except (ControllerError, junit.JunitEvidenceError) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
