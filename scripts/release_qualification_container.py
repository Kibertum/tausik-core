#!/usr/bin/env python3
"""Trusted outer controller for isolated release-qualification pytest lanes."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import secrets
import sys
import tempfile
from collections.abc import Callable
from typing import cast
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parent))
import release_qualification_junit as junit
import release_qualification_container_context as context_builder
import release_qualification_container_docker as docker
from release_qualification_container_runtime import (
    ControllerError,
    inside,
)
from release_qualification_evidence import MAX_EVIDENCE_BYTES


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
RUN python -I -m pip wheel --no-cache-dir --require-hashes --only-binary=:all: --wheel-dir /candidate-wheelhouse \
      -r /source/.release-controller/runtime-requirements.txt && \
    python -I -m pip install --no-cache-dir --no-index --only-binary=:all: \
      --find-links /candidate-wheelhouse --require-hashes --target /candidate-deps \
      -r /source/.release-controller/runtime-requirements.txt

FROM {BASE_IMAGE} AS runtime
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY --from=node-runtime /usr/local/bin/node /usr/local/bin/node
COPY --from=node-runtime /usr/local/lib/node_modules /usr/local/lib/node_modules
COPY --from=candidate-dependencies /candidate-deps /candidate-deps
COPY --from=candidate-dependencies /candidate-wheelhouse /candidate-wheelhouse
COPY . /source
WORKDIR /build
RUN mkdir -p /opt/controller/site && \
    python -I -m pip install --no-cache-dir --require-hashes --only-binary=:all: --target /opt/controller/site \
      -r /source/.release-controller/requirements.txt && \
    ln -s /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm && \
    ln -s /usr/local/lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx && \
    useradd --uid 10001 --create-home runner && \
    mkdir -p /opt/controller /result && \
    cp /source/.release-controller/controller.py /opt/controller/controller.py && \
    cp /source/.release-controller/context.py /opt/controller/release_qualification_container_context.py && \
    cp /source/.release-controller/runtime.py /opt/controller/release_qualification_container_runtime.py && \
    cp /source/.release-controller/docker.py /opt/controller/release_qualification_container_docker.py && \
    cp /source/.release-controller/evidence.py /opt/controller/release_qualification_evidence.py && \
    cp /source/.release-controller/junit.py /opt/controller/release_qualification_junit.py && \
    cp /source/.release-controller/matrix.py /opt/controller/matrix.py && \
    cp /source/.release-controller/manifest.json /opt/controller/manifest.json && \
    cp /source/.release-controller/pyproject.toml /opt/controller/pyproject.toml && \
    cp -R /source/.release-controller/objects.git /opt/controller/objects.git && \
    if [ -f /source/.release-controller/candidate-dockerignore ]; then \
      cp /source/.release-controller/candidate-dockerignore /source/.dockerignore; \
    fi && \
    printf '%s\\n' 'import sys' \"sys.path.insert(0, '/opt/controller/site')\" \"sys.path.append('/candidate-deps')\" > /usr/local/lib/python3.13/site-packages/sitecustomize.py && \
    git config --system --add safe.directory /opt/controller/objects.git && \
    chown 10001:10001 /result && \
    chmod -R a-w /opt/controller /candidate-deps /candidate-wheelhouse
USER 10001:10001
ENTRYPOINT ["python", "-I", "-S", "/opt/controller/controller.py", "inside"]
"""

# Compatibility aliases / wrappers so monkeypatches on this module stay effective.
_run = docker.run
_check = docker.check
_safe_output = docker.safe_output
_validate_container_boundary = docker.validate_container_boundary


def _inspect_container_boundary(container: str) -> None:
    docker.inspect_container_boundary(container, run_cmd=_run, check_cmd=_check)


def _wait_for_evidence(container: str, *, timeout: int = 1800) -> int:
    return docker.wait_for_evidence(container, timeout=timeout, run_cmd=_run, check_cmd=_check)


def _read_evidence(container: str) -> bytes:
    return docker.read_evidence(
        container, run_cmd=_run, check_cmd=_check, max_bytes=MAX_EVIDENCE_BYTES
    )


def _wait_for_container(container: str, expected_exit_code: int) -> None:
    docker.wait_for_container(container, expected_exit_code, run_cmd=_run, check_cmd=_check)


def _release_evidence(container: str, exit_code: int, *, strict: bool) -> None:
    touched = _run(["docker", "exec", container, "touch", "/result/release"])
    if strict:
        _check(touched)
        _wait_for_container(container, exit_code)
        return
    try:
        _wait_for_container(container, exit_code)
    except ControllerError as wait_exc:
        print(f"WARNING: {wait_exc}", file=sys.stderr)


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


def run_lane(candidate: Path, trusted: Path, lane: str, output: Path) -> None:
    token = secrets.token_hex(8)
    image = f"tausik-rq-{token}"
    container = f"tausik-rq-run-{token}"
    with tempfile.TemporaryDirectory(prefix="tausik-rq-context-") as raw_context:
        context = Path(raw_context)
        _prepare_context(candidate.resolve(), trusted.resolve(), context)
        report: bytes | None = None
        floor_error: Exception | None = None
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
                try:
                    junit.validate_lane_report(report)
                except junit.JunitEvidenceError as exc:
                    floor_error = exc
            _release_evidence(container, exit_code, strict=floor_error is None)
        finally:
            cleanup_errors = _cleanup_resources(container, image)
            if cleanup_errors:
                detail = "; ".join(cleanup_errors)[:1000]
                if sys.exc_info()[0] is None and floor_error is None:
                    raise ControllerError(f"Docker cleanup failed: {detail}")
                print(f"WARNING: Docker cleanup failed: {detail}", file=sys.stderr)
        if report is None:
            raise ControllerError("qualification lane produced no publishable evidence")
        _safe_output(output.absolute(), report)
        if floor_error is not None:
            raise floor_error


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
