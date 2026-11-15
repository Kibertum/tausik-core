"""In-container execution and kernel-boundary checks for release qualification."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
import time


REMOTE_TEST = "test_anonymous_publication_remote_matches_immutable_observation"
WINDOWS_NATIVE_TEST = (
    "test_windows_native_cursor_upgrade_executes_registered_session_start_after_reload"
)


class ControllerError(RuntimeError):
    """The isolated lane could not produce trusted evidence."""


def emit(text: str) -> None:
    encoding = sys.stdout.encoding or "utf-8"
    sys.stdout.write(text.encode(encoding, errors="backslashreplace").decode(encoding))
    sys.stdout.flush()


def _publish_exit_code(result_dir: Path, exit_code: int) -> None:
    pending = result_dir / ".exit-code.pending"
    with pending.open("w", encoding="ascii", newline="\n") as stream:
        stream.write(f"{exit_code}\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(pending, result_dir / "exit-code")


def inside(lane: str) -> int:
    _assert_runtime_boundary()
    sys.path.insert(0, "/opt/controller/site")
    os.environ.update(
        {
            "HOME": "/work/home",
            "PATH": f"/opt/controller/site/bin:{os.environ.get('PATH', '')}",
            "PIP_FIND_LINKS": "/candidate-wheelhouse",
            "PIP_NO_INDEX": "1",
            "PYTHONPATH": "/opt/controller/site:/candidate-deps",
            "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
            "TAUSIK_QUALIFICATION_MANIFEST": "/opt/controller/manifest.json",
            "TAUSIK_QUALIFICATION_OBJECTS": "/opt/controller/objects.git",
            "TAUSIK_QUALIFICATION_ROOT": "/work/repo",
        }
    )
    sys.path.append("/candidate-deps")
    import pytest
    import xdist.plugin  # type: ignore[import-untyped]  # noqa: F401

    source = Path("/source")
    work = Path("/work/repo")
    shutil.copytree(
        source,
        work,
        symlinks=True,
        ignore=shutil.ignore_patterns(".release-controller", "Dockerfile.release-qualification"),
    )
    Path("/work/home").mkdir()
    if lane == "full":
        config = work / ".tausik/config.json"
        config.parent.mkdir(exist_ok=True)
        config.write_text('{"context_tier":"standard"}\n', encoding="utf-8")
    bootstrap = subprocess.run(
        [sys.executable, "bootstrap/bootstrap.py", "--no-detect", "--ide", "all"],
        cwd=work,
        check=False,
        stdin=subprocess.DEVNULL,
    )
    if bootstrap.returncode:
        return bootstrap.returncode
    common = [
        "-c",
        "/opt/controller/pyproject.toml",
        "--override-ini",
        "addopts=",
        "--override-ini",
        "faulthandler_timeout=300",
        "--override-ini",
        "faulthandler_exit_on_timeout=true",
        "--rootdir=/work/repo",
        "-p",
        "no:cacheprovider",
        "-p",
        "xdist.plugin",
        "-n",
        "auto",
        "--tb=short",
        "-rs",
        "--junitxml=/result/report.xml",
        "-k",
        f"not {REMOTE_TEST} and not {WINDOWS_NATIVE_TEST}",
    ]
    if lane == "matrix":
        args = [*common, "--noconftest", "-m", "slow", "/opt/controller/matrix.py"]
    elif lane == "full":
        args = [*common, "-m", "", str(work / "tests")]
    else:
        raise ControllerError("unknown isolated lane")
    os.chdir(work)
    exit_code = int(pytest.main(args))
    _publish_exit_code(Path("/result"), exit_code)
    deadline = time.monotonic() + 300
    while time.monotonic() < deadline:
        if Path("/result/release").exists():
            return exit_code
        time.sleep(1)
    raise ControllerError("outer controller did not release the evidence container")


def _assert_runtime_boundary() -> None:
    get_effective_uid = getattr(os, "geteuid", None)
    if not callable(get_effective_uid):
        raise ControllerError("qualification runtime is not a POSIX environment")
    euid = get_effective_uid()
    host_surface = Path("/var/run/docker.sock").exists() or Path("/host-artifacts").exists()
    try:
        mount_rows = Path("/proc/self/mountinfo").read_text(encoding="utf-8").splitlines()
        status_rows = Path("/proc/self/status").read_text(encoding="utf-8").splitlines()
        interface_rows = Path("/proc/net/dev").read_text(encoding="utf-8").splitlines()[2:]
        route_rows = Path("/proc/net/route").read_text(encoding="utf-8").splitlines()[1:]
    except OSError as exc:
        raise ControllerError("qualification runtime cannot inspect its kernel boundary") from exc
    try:
        Path("/opt/controller/controller.py").write_bytes(b"tamper")
    except OSError:
        controller_writable = False
    else:
        controller_writable = True
    validate_runtime_observation(
        euid,
        host_surface,
        mount_rows,
        status_rows,
        interface_rows,
        route_rows,
        controller_writable,
    )


def validate_runtime_observation(
    euid: int,
    host_surface: bool,
    mount_rows: list[str],
    status_rows: list[str],
    interface_rows: list[str],
    route_rows: list[str],
    controller_writable: bool,
) -> None:
    if euid == 0:
        raise ControllerError("qualification runtime unexpectedly has root privileges")
    if host_surface:
        raise ControllerError("qualification runtime exposes a forbidden host surface")
    root_mount = next(
        (row for row in mount_rows if len(row.split()) > 5 and row.split()[4] == "/"), None
    )
    if root_mount is None or "ro" not in root_mount.split()[5].split(","):
        raise ControllerError("qualification runtime root filesystem is writable")
    status = {
        key: value.strip()
        for row in status_rows
        if ":" in row
        for key, value in [row.split(":", 1)]
    }
    if status.get("CapEff") != "0000000000000000" or status.get("CapBnd") != "0000000000000000":
        raise ControllerError("qualification runtime retains Linux capabilities")
    if status.get("NoNewPrivs") != "1":
        raise ControllerError("qualification runtime permits privilege escalation")
    interfaces = {row.split(":", 1)[0].strip() for row in interface_rows if ":" in row}
    if interfaces - {"lo"}:
        raise ControllerError("qualification runtime exposes a non-loopback interface")
    if any(len(row.split()) > 1 and row.split()[1] == "00000000" for row in route_rows):
        raise ControllerError("qualification runtime exposes a default route")
    if controller_writable:
        raise ControllerError("qualification runtime can modify the trusted controller")
