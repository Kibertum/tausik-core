"""Candidate-context construction for the release-qualification controller."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import subprocess
from typing import Callable


Result = subprocess.CompletedProcess[str] | subprocess.CompletedProcess[bytes]
Runner = Callable[..., Result]
Checker = Callable[[Result], None]


def extract_commit(root: Path, destination: Path, run: Runner, check: Checker) -> None:
    head = run(["git", "-C", str(root), "rev-parse", "HEAD"])
    listing = run(["git", "-C", str(root), "ls-tree", "-rz", "--name-only", "HEAD"], text=False)
    check(head)
    check(listing)
    assert isinstance(head.stdout, str)
    assert isinstance(listing.stdout, bytes)
    try:
        names = [name.decode("utf-8") for name in listing.stdout.split(b"\0") if name]
    except UnicodeDecodeError as exc:
        raise ValueError("candidate tree contains a non-UTF-8 path") from exc
    for name in names:
        path = PurePosixPath(name)
        reserved = path.parts[:1] == (".release-controller",) or (
            len(path.parts) == 1 and path.name.startswith("Dockerfile.release-qualification")
        )
        if path.is_absolute() or ".." in path.parts or reserved:
            raise ValueError("candidate tree contains an unsafe controller path")
    cloned = run(
        [
            "git",
            "-c",
            "core.autocrlf=false",
            "-c",
            "core.eol=lf",
            "clone",
            "--no-local",
            "--no-hardlinks",
            str(root),
            str(destination),
        ],
        timeout=300,
    )
    check(cloned)
    observed = run(["git", "-C", str(destination), "rev-parse", "HEAD"])
    check(observed)
    if not isinstance(observed.stdout, str) or observed.stdout.strip() != head.stdout.strip():
        raise ValueError("candidate clone did not preserve the exact committed HEAD")


def prepare_publication_store(
    trusted: Path,
    destination: Path,
    manifest_path: str,
    run: Runner,
    check: Checker,
) -> None:
    try:
        manifest = json.loads((trusted / manifest_path).read_text(encoding="utf-8"))
        remote = manifest["publication"]["anonymous_url"]
        rows = manifest["published"]
        refspecs = [f"+refs/tags/{row['tag']}:refs/tags/{row['tag']}" for row in rows]
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise ValueError("trusted publication manifest is malformed") from exc
    check(run(["git", "init", "--bare", str(destination)]))
    check(
        run(
            ["git", "-C", str(destination), "fetch", "--no-tags", "--depth=1", remote, *refspecs],
            timeout=300,
        )
    )
    for row in rows:
        commit = run(["git", "-C", str(destination), "rev-parse", f"{row['tag']}^{{commit}}"])
        tree = run(["git", "-C", str(destination), "rev-parse", f"{row['commit']}^{{tree}}"])
        check(commit)
        check(tree)
        if not isinstance(commit.stdout, str) or commit.stdout.strip() != row["commit"]:
            raise ValueError("publication store commit does not match trusted pin")
        if not isinstance(tree.stdout, str) or tree.stdout.strip() != row["tree"]:
            raise ValueError("publication store tree does not match trusted pin")


def prepare_context(
    candidate: Path,
    trusted: Path,
    destination: Path,
    *,
    candidate_requirements_sha256: str,
    controller_requirements: str,
    runtime_requirements: str,
    matrix_test: str,
    matrix_manifest: str,
    dockerfile: str,
    run: Runner,
    check: Checker,
) -> None:
    extract_commit(candidate, destination, run, check)
    requirements = destination / "requirements.txt"
    try:
        requirements_hash = hashlib.sha256(requirements.read_bytes()).hexdigest()
    except OSError as exc:
        raise ValueError("candidate requirements are missing") from exc
    if requirements_hash != candidate_requirements_sha256:
        raise ValueError("candidate requirements do not match the trusted runtime lock")
    controller = destination / ".release-controller"
    controller.mkdir()
    dockerignore = destination / ".dockerignore"
    if dockerignore.is_symlink():
        raise ValueError("candidate .dockerignore must be a regular file")
    if dockerignore.exists():
        dockerignore.replace(controller / "candidate-dockerignore")
    shutil.copy2(trusted / controller_requirements, controller / "requirements.txt")
    shutil.copy2(trusted / runtime_requirements, controller / "runtime-requirements.txt")
    shutil.copy2(
        trusted / "scripts/release_qualification_container.py", controller / "controller.py"
    )
    shutil.copy2(
        trusted / "scripts/release_qualification_container_context.py", controller / "context.py"
    )
    shutil.copy2(
        trusted / "scripts/release_qualification_container_runtime.py", controller / "runtime.py"
    )
    shutil.copy2(
        trusted / "scripts/release_qualification_container_docker.py", controller / "docker.py"
    )
    shutil.copy2(trusted / "scripts/release_qualification_evidence.py", controller / "evidence.py")
    shutil.copy2(trusted / "scripts/release_qualification_junit.py", controller / "junit.py")
    shutil.copy2(trusted / matrix_test, controller / "matrix.py")
    shutil.copy2(trusted / matrix_manifest, controller / "manifest.json")
    shutil.copy2(trusted / "pyproject.toml", controller / "pyproject.toml")
    prepare_publication_store(trusted, controller / "objects.git", matrix_manifest, run, check)
    (destination / "Dockerfile.release-qualification").write_text(dockerfile, encoding="utf-8")
