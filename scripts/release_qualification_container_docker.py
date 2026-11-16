"""Docker lifecycle helpers for the release-qualification outer controller."""

from __future__ import annotations

import json
from collections.abc import Callable
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time
from typing import cast

from release_qualification_container_runtime import ControllerError
from release_qualification_evidence import MAX_EVIDENCE_BYTES


def run(
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


def check(result: subprocess.CompletedProcess[str] | subprocess.CompletedProcess[bytes]) -> None:
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


def safe_output(path: Path, payload: bytes) -> None:
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


def validate_container_boundary(record: object) -> None:
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


def inspect_container_boundary(
    container: str,
    *,
    run_cmd: Callable[
        ..., subprocess.CompletedProcess[str] | subprocess.CompletedProcess[bytes]
    ] = run,
    check_cmd: Callable[..., None] = check,
) -> None:
    inspected = run_cmd(["docker", "inspect", container])
    check_cmd(inspected)
    try:
        payload = json.loads(cast(str, inspected.stdout))
    except (json.JSONDecodeError, TypeError) as exc:
        raise ControllerError("Docker returned malformed inspection JSON") from exc
    if not isinstance(payload, list) or len(payload) != 1:
        raise ControllerError("Docker returned an unexpected inspection count")
    validate_container_boundary(payload[0])


def wait_for_evidence(
    container: str,
    *,
    timeout: int = 1800,
    run_cmd: Callable[
        ..., subprocess.CompletedProcess[str] | subprocess.CompletedProcess[bytes]
    ] = run,
    check_cmd: Callable[..., None] = check,
) -> int:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        ready = run_cmd(["docker", "exec", container, "test", "-f", "/result/exit-code"])
        if ready.returncode == 0:
            status = run_cmd(["docker", "exec", container, "cat", "/result/exit-code"])
            check_cmd(status)
            try:
                return int(cast(str, status.stdout).strip())
            except (TypeError, ValueError) as exc:
                raise ControllerError("isolated lane returned a malformed status") from exc
        state = run_cmd(
            [
                "docker",
                "inspect",
                "--format",
                "{{.State.Status}} {{.State.ExitCode}}",
                container,
            ]
        )
        check_cmd(state)
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


def read_evidence(
    container: str,
    *,
    run_cmd: Callable[
        ..., subprocess.CompletedProcess[str] | subprocess.CompletedProcess[bytes]
    ] = run,
    check_cmd: Callable[..., None] = check,
    max_bytes: int = MAX_EVIDENCE_BYTES,
) -> bytes:
    copied = run_cmd(
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
                f"p=open('/result/report.xml','rb').read({max_bytes + 1});"
                "sys.stdout.buffer.write(p)"
            ),
        ],
        text=False,
    )
    check_cmd(copied)
    if not isinstance(copied.stdout, bytes):
        raise ControllerError("isolated lane evidence is not binary")
    if len(copied.stdout) > max_bytes:
        raise ControllerError("isolated lane evidence exceeds the trusted size limit")
    return copied.stdout


def wait_for_container(
    container: str,
    expected_exit_code: int,
    *,
    run_cmd: Callable[
        ..., subprocess.CompletedProcess[str] | subprocess.CompletedProcess[bytes]
    ] = run,
    check_cmd: Callable[..., None] = check,
) -> None:
    waited = run_cmd(["docker", "wait", container], timeout=60)
    check_cmd(waited)
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


def release_evidence(container: str, exit_code: int, *, strict: bool) -> None:
    touched = run(["docker", "exec", container, "touch", "/result/release"])
    if strict:
        check(touched)
        wait_for_container(container, exit_code)
        return
    try:
        wait_for_container(container, exit_code)
    except ControllerError as wait_exc:
        print(f"WARNING: {wait_exc}", file=sys.stderr)


def cleanup_resources(container: str, image: str) -> list[str]:
    errors: list[str] = []
    for kind, name, argv in (
        ("container", container, ["docker", "rm", "--force", container]),
        ("image", image, ["docker", "image", "rm", "--force", image]),
    ):
        try:
            result = run(argv)
        except ControllerError as exc:
            errors.append(f"{kind} {name}: {exc}")
            continue
        if result.returncode:
            stderr = result.stderr if isinstance(result.stderr, str) else ""
            errors.append(f"{kind} {name}: {' '.join(stderr.split())[-300:]}")
    return errors
