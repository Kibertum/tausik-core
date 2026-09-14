"""Guards that keep the CI lanes honest — and that keep THIS repo's own workflow honest.

Two failures this project actually shipped motivate every assertion here:

  * The full (slow) lane was RED in main for a whole release, invisible because
    ``pyproject`` sets ``addopts = -m 'not slow'`` and CI ran a bare ``pytest tests/`` —
    i.e. the fast lane only. The release's own critical regression tests are slow-marked,
    so CI never ran them. A green badge over an untested third of the suite.
  * A hard ``ruff`` step ordered *before* the pytest step in the same job hid a Python
    3.13 incompatibility on a third of the matrix: ruff died first, pytest never ran, and
    the failure was masked until ruff was fixed.

So this file asserts, from the test suite itself (which the CI *does* run):
  1. the slow lane is not vacuous — there really are slow-marked tests, and a full
     collection sees strictly more than the fast lane. If someone drops the last slow
     marker, or a refactor makes ``-m ''`` and ``-m 'not slow'`` collect the same set,
     the "full lane" has silently become the fast lane and this test goes red.
  2. the workflow actually runs a full-lane job AND keeps lint decoupled from tests, so
     the two incidents above cannot recur structurally.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import DORMANT_ON_PUBLIC_SNAPSHOT, IS_PUBLIC_SNAPSHOT  # noqa: E402


# The CI lane definitions this file reads. Declared so the scoped-pytest gate
# runs these checks when a workflow changes — which is exactly when a lane can
# stop bootstrapping or start swallowing an exit code, and precisely the change
# a basename heuristic can never map to a test called "ci_lanes".
CROSSCUTTING_SCOPE = [
    ".github/workflows/",
    ".gitlab-ci.yml",
    "pyproject.toml",
]

_ROOT = Path(__file__).resolve().parents[1]
_WORKFLOW = _ROOT / ".github" / "workflows" / "tests.yml"

# ONE assignment: a second `pytestmark =` further down silently replaced the
# dormancy mark, and the built snapshot ran these against a .gitlab-ci.yml it
# does not carry (session #260).
pytestmark = [
    pytest.mark.slow,  # spawns pytest --collect-only subprocesses
    pytest.mark.skipif(IS_PUBLIC_SNAPSHOT, reason=DORMANT_ON_PUBLIC_SNAPSHOT),
]


def _collect_count(marker_expr: str | None) -> int:
    """Number of tests pytest collects under an optional -m expression.

    ``--override-ini addopts=`` strips the inherited ``-m 'not slow'`` so we control the
    marker filter explicitly and measure the true lane sizes.
    """
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/",
        "--collect-only",
        "-q",
        "--override-ini=addopts=",
        "-p",
        "no:cacheprovider",
    ]
    if marker_expr is not None:
        cmd += ["-m", marker_expr]
    proc = subprocess.run(
        cmd,
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
    )
    # The trailing summary line: "N tests collected" (or "N/M tests collected").
    m = re.search(r"(\d+)(?:/\d+)?\s+tests?\s+collected", proc.stdout)
    assert m, f"could not parse collection count from:\n{proc.stdout[-500:]}\n{proc.stderr[-500:]}"
    return int(m.group(1))


class TestSlowLaneIsNotVacuous:
    def test_slow_marked_tests_exist(self):
        """If this hits zero, the 'full lane' is identical to the fast lane and the whole
        test-full CI job is a no-op guarding nothing."""
        slow = _collect_count("slow")
        assert slow > 0, (
            "no slow-marked tests exist — the full CI lane now equals the fast lane and "
            "gates nothing beyond it. Either a marker was dropped or the split is dead."
        )

    def test_full_lane_strictly_larger_than_fast_lane(self):
        """The full lane must see MORE than the default fast lane — otherwise CI running
        the fast lane already covers everything and the extra job is theatre."""
        full = _collect_count(None)  # -m absent → everything
        fast = _collect_count("not slow")
        assert full > fast, (
            f"full lane collects {full}, fast lane collects {fast}: they are not distinct, "
            "so `pytest tests/` already runs everything and the slow split is meaningless."
        )


def _job_blocks() -> dict[str, str]:
    """Split the workflow into {job_name: block_text} using STDLIB only.

    Deliberately NOT PyYAML: this project keeps PyYAML an optional dependency (see
    test_no_hard_yaml_import + the v1.5.0 fresh-clone smoke), and CI installs only pytest.
    A yaml-based guard would silently SKIP in CI — the exact blind spot this file exists to
    kill. The workflow format is ours, so a 2-space-indent block scan is enough and runs
    everywhere. A job is a 2-space-indented ``<name>:`` under the top-level ``jobs:`` key,
    its block running until the next such key.
    """
    text = _WORKFLOW.read_text(encoding="utf-8")
    lines = text.splitlines()
    # find the `jobs:` line (top-level, no indent)
    try:
        start = next(i for i, ln in enumerate(lines) if ln.rstrip() == "jobs:")
    except StopIteration:
        return {}
    blocks: dict[str, str] = {}
    current: str | None = None
    buf: list[str] = []

    def _flush():
        if current is not None:
            blocks[current] = "\n".join(buf)

    for ln in lines[start + 1 :]:
        stripped = ln.strip()
        # Comment lines DESCRIBE adjacent jobs (a comment above `test:` mentions pytest);
        # they are not commands and must not count toward what a job RUNS. Drop them, so a
        # job's block reflects its steps only — otherwise the lint block inherits the
        # next job's descriptive comment and looks like it runs pytest.
        if stripped.startswith("#"):
            continue
        # a job header: exactly two leading spaces, then `name:` (a comment can't be one,
        # already filtered above).
        if len(ln) > 2 and ln[:2] == "  " and ln[2] != " " and stripped.endswith(":"):
            _flush()
            current = stripped.rstrip(":")
            buf = []
        elif current is not None:
            buf.append(ln)
    _flush()
    return blocks


class TestWorkflowStructureIsHonest:
    """Static checks on .github/workflows/tests.yml — the repo's own CI must embody the
    lessons, not just document them. Stdlib-only, so these run in CI too."""

    def test_workflow_parses_into_jobs(self):
        blocks = _job_blocks()
        assert blocks, f"no jobs parsed from {_WORKFLOW}"

    def test_lint_is_a_separate_job_from_tests(self):
        """Lint decoupled from tests: a ruff failure must not be able to hide test results
        (the v1.7.0 masking incident). Enforced structurally — no single job runs both."""
        blocks = _job_blocks()
        lint_jobs = [n for n, t in blocks.items() if "ruff check" in t]
        test_jobs = [n for n, t in blocks.items() if "pytest" in t]
        assert lint_jobs, "no job runs `ruff check`"
        assert test_jobs, "no job runs pytest"
        overlap = set(lint_jobs) & set(test_jobs)
        assert not overlap, (
            f"jobs {overlap} run BOTH ruff and pytest — a hard ruff step there hides the "
            "pytest step (the v1.7.0 masking incident). Split lint into its own job."
        )

    def test_a_job_runs_the_full_slow_lane(self):
        """Some job must run the full lane (-m '' / -m 'slow'), or the slow-marked
        regression tests are never gated by CI."""
        joined = "\n".join(_job_blocks().values())
        runs_full = "-m ''" in joined or '-m ""' in joined or "-m 'slow'" in joined
        assert runs_full, (
            "no CI job runs the full lane (`pytest -m ''`). The slow-marked regression "
            "tests — the ones that catch this project's own critical bugs — go ungated."
        )


class TestTheDevelopmentLineReachesTheSlowTests:
    """GitLab is the development line (decision #267). It must run the full lane.

    `test_a_job_runs_the_full_slow_lane` above is satisfied by GitHub alone — and
    the working branch deliberately never goes to GitHub (decision #260). So that
    assertion stayed green through the entire period in which every commit of the
    1.9 release was verified by the fast half only.

    MEASURED when this was written (session #232): the full lane costs 9m03s for
    10,023 tests on a 20-core machine with `-n auto`. It is affordable per push;
    it was never affordable to keep skipping it. Its first run found a red the
    fast lane could not see — the freshness ratchet over the committed ROADMAP,
    which is slow-marked.
    """

    @staticmethod
    def _gitlab_jobs() -> dict:
        import yaml

        path = Path(".gitlab-ci.yml")
        assert path.exists(), ".gitlab-ci.yml is missing — the development gate cannot be checked"
        doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return {
            name: job
            for name, job in doc.items()
            if isinstance(job, dict) and not name.startswith(".") and "script" in job
        }

    def _full_lane_jobs(self) -> list[str]:
        found = []
        for name, job in self._gitlab_jobs().items():
            script = " ".join(
                TestALaneThatRunsPytestDeploysFirstAndDoesNotSwallowIt._flatten(job["script"])
            )
            if "pytest" in script and ("-m ''" in script or '-m ""' in script):
                found.append(name)
        return found

    def test_gitlab_has_a_lane_that_reaches_slow_tests(self):
        assert self._full_lane_jobs(), (
            "no GitLab job runs `pytest -m ''`. Every lane there inherits "
            "`-m 'not slow'` from addopts, so this project's own regression tests — "
            "bootstrap wiring, MCP integration, subprocess smoke — would run on no "
            "branch anyone develops on. GitHub having a full lane does not help: the "
            "working branch does not go there (decision #260)."
        )

    def test_the_full_lane_does_not_share_a_stage_with_another_pytest_lane(self):
        """Every runner here is a SHELL executor with ONE reused workspace per
        project and `GIT_CLEAN_FLAGS=-ffdx`. Two pytest jobs in one stage run
        concurrently over the same directory and clean the tree underneath each
        other — the same argument this file's duplicate-pipeline guard makes."""
        by_stage: dict[str, list[str]] = {}
        for name, job in self._gitlab_jobs().items():
            script = " ".join(
                TestALaneThatRunsPytestDeploysFirstAndDoesNotSwallowIt._flatten(job["script"])
            )
            if "pytest" in script:
                by_stage.setdefault(str(job.get("stage") or "test"), []).append(name)
        clashes = {stage: names for stage, names in by_stage.items() if len(names) > 1}
        assert not clashes, (
            f"these stages run more than one pytest lane concurrently: {clashes}. "
            "The runners share one workspace; concurrent lanes would wipe it under "
            "each other. Put the second lane in a later stage."
        )

    def test_the_fast_lane_survives(self):
        """The other direction. Replacing the fast lane with the full one would
        close the blind spot by making every push wait nine minutes — trading the
        defect for the pain the owner actually named."""
        fast = [
            name
            for name, job in self._gitlab_jobs().items()
            if name not in self._full_lane_jobs()
            and "pytest"
            in " ".join(
                TestALaneThatRunsPytestDeploysFirstAndDoesNotSwallowIt._flatten(job["script"])
            )
        ]
        assert fast, (
            "GitLab has no fast lane left. A developer now waits for the full run "
            "on every push, which is the wait the full lane was supposed to move "
            "OFF the critical path, not onto it."
        )


class TestNoCiLaneExcludesTestFiles:
    """A ratchet against the exclusion that was added silently once already.

    Twelve tests — all of test_bootstrap_skills_coverage.py and all of
    test_bootstrap_real.py — ran NOWHERE for months. Three independent silences
    stacked into one: ``--ignore`` in both CI files, the ``slow`` marker in the
    fast lane, and the hang guard killing them in a local full run. None of the
    three was wrong on its own; together they meant twelve green tests that no
    machine had executed, and green-because-unrun is indistinguishable from
    green-because-passing in every report we produce.

    The exclusion was never decided. ``git log -S`` puts both flags in 3189f67, a
    combined v1.3 release commit that does not mention them; the first version of
    the workflow (a158380) had none. They were then copied into .gitlab-ci.yml
    (fd803f3) and into local measurement commands, so a choice nobody made
    propagated for a year. Decision #275 removed them after session #189 measured
    the two modules with the guard lifted: 22 passed, 824 s, exit 0 — slow, not
    broken.

    ``slow`` is this project's sanctioned way to say "not in the fast lane", and
    it is honest because ``-m ''`` still reaches it. ``--ignore`` is unreachable
    by any marker expression, so it hides tests from the lane whose entire job is
    to run everything. Hence: no CI lane may exclude a test file by path.
    """

    def test_no_ci_command_ignores_a_test_file(self):
        for path in (_WORKFLOW, _ROOT / ".gitlab-ci.yml"):
            assert path.exists(), f"{path} is missing — CI honesty cannot be checked"
            offenders = [
                line.strip()
                for line in path.read_text(encoding="utf-8").splitlines()
                if "--ignore" in line and "tests/" in line and not line.strip().startswith("#")
            ]
            assert not offenders, (
                f"{path.name} excludes test files by path: {offenders}. Use the `slow` "
                f"marker instead — `-m ''` still reaches slow tests, while `--ignore` is "
                f"reachable by nothing, so the excluded tests run in NO lane at all. That "
                f"is how twelve tests went unexecuted for a year (decision #275)."
            )


class TestEveryLaneInstallsWhatTheAddoptsDemand:
    """``addopts`` is a promise every runner has to be able to keep.

    ``-n auto`` moved into ``[tool.pytest.ini_options]`` so the suite is parallel
    wherever it runs, not only where somebody typed the flag. The cost of that is
    a HARD dependency: without pytest-xdist pytest exits on ``unrecognized
    arguments: -n`` before collecting a single test. That failure is loud, but it
    is loud in the wrong place — in CI, on a push, after the change that forgot it.

    There are FIVE install paths, and the two obvious ones are not the whole set:
    ``.github/workflows/tests.yml`` installs deps twice (fast lane and full lane),
    ``.github/workflows/test-coverage.yml`` is a third workflow that runs pytest
    with its own dependency list, ``.gitlab-ci.yml`` is the development gate, and
    ``CONTRIBUTING.md`` is what a new contributor's first ``pytest`` obeys. A
    ratchet that watched only the two CI files would have left a contributor
    meeting `unrecognized arguments: -n` as their first impression of the repo.

    The rule is derived from the config rather than hard-coded, so it retires
    itself: drop ``-n`` from addopts and nothing here demands the plugin.
    """

    _INSTALL_SOURCES = (
        Path(".github/workflows/tests.yml"),
        Path(".github/workflows/test-coverage.yml"),
        Path(".gitlab-ci.yml"),
        Path("CONTRIBUTING.md"),
    )

    # A flag in addopts -> the distribution that provides it.
    _FLAG_REQUIRES = {"-n": "pytest-xdist"}

    @staticmethod
    def _addopts() -> str:
        import tomllib

        with (_ROOT / "pyproject.toml").open("rb") as fh:
            data = tomllib.load(fh)
        return str(data["tool"]["pytest"]["ini_options"].get("addopts", ""))

    @staticmethod
    def _install_lines(path: Path) -> list[list[str]]:
        """Tokenised `pip install` command lines, comments and prose excluded."""
        out: list[list[str]] = []
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if line.startswith("#") or line.startswith(">"):
                continue  # a comment or a markdown quote DESCRIBES an install
            if "pip install" not in line:
                continue
            tokens = line.split("pip install", 1)[1].split()
            # Package names only: flags, and the file that follows `-r`, are not.
            packages, skip_next = [], False
            for tok in tokens:
                if skip_next:
                    skip_next = False
                    continue
                if tok in ("-r", "--requirement"):
                    skip_next = True
                    continue
                if tok.startswith("-"):
                    continue
                packages.append(tok)
            out.append(packages)
        return out

    def test_every_install_of_pytest_also_installs_what_addopts_needs(self):
        addopts = self._addopts()
        required = [
            dist for flag, dist in self._FLAG_REQUIRES.items() if f"{flag} " in f"{addopts} "
        ]
        if not required:
            return  # addopts asks for no plugin — the rule retires itself
        offenders = []
        checked = 0
        for rel in self._INSTALL_SOURCES:
            path = _ROOT / rel
            assert path.exists(), f"{rel} is missing — the install paths cannot be checked"
            for packages in self._install_lines(path):
                if "pytest" not in packages:
                    continue  # installs something else entirely
                checked += 1
                missing = [dist for dist in required if dist not in packages]
                if missing:
                    offenders.append(f"{rel.as_posix()}: {' '.join(packages)} misses {missing}")
        assert checked >= 5, (
            f"only {checked} pytest install lines found across {[p.as_posix() for p in self._INSTALL_SOURCES]}"
            " — a lane was renamed or moved and this ratchet is now guarding less than it thinks"
        )
        assert not offenders, (
            f"addopts is {addopts!r}, so every lane needs {required}. These install pytest "
            f"without it and will die on `unrecognized arguments`: {offenders}"
        )


class TestALaneThatRunsPytestDeploysFirstAndDoesNotSwallowIt:
    """A lane may choose not to gate. It may not choose to measure dishonestly.

    MEASURED, on a pristine `git clone` of this repository — the exact thing a
    CI runner checks out. The deployed IDE profiles and `.tausik/` are bootstrap
    OUTPUT and gitignored, so they are simply absent there, and FOURTEEN test
    files fail without them (identical list across two runs). The coverage lane
    ran pytest with `|| true` and no bootstrap step, so those failures became
    silence and the published percentage described only the remainder — a number
    that looks like a measurement and was taken on an incomplete run.

    Both halves are asserted because either alone is defeatable: bootstrapping
    while still discarding the exit code hides a real regression, and reporting
    the exit code without bootstrapping reports a failure that is the lane's own
    fault. The gating lanes already satisfied both before this test existed,
    which is what makes it a ratchet rather than a description of one file.

    Lanes are DISCOVERED, not listed: a workflow added later is covered without
    anyone remembering this test.
    """

    _BOOTSTRAP = "bootstrap/bootstrap.py"

    @staticmethod
    def _lane_files() -> list[Path]:
        found = [p for p in sorted(Path(".github/workflows").glob("*.yml"))]
        gitlab = Path(".gitlab-ci.yml")
        if gitlab.exists():
            found.append(gitlab)
        return found

    @staticmethod
    def _flatten(value) -> list[str]:
        """GitLab allows a nested list in `script`/`before_script` and flattens it."""
        out: list[str] = []
        if isinstance(value, str):
            out.append(value)
        elif isinstance(value, list):
            for item in value:
                out.extend(TestALaneThatRunsPytestDeploysFirstAndDoesNotSwallowIt._flatten(item))
        return out

    @classmethod
    def _gitlab_jobs(cls, path: Path, text: str) -> list[tuple[str, str]]:
        """[(label, every command the job really runs)] for GitLab lanes.

        Anchors are resolved by the YAML parser, so a step shared through
        `&anchor` counts for every job that takes it — which is what actually
        happens on the runner.
        """
        import yaml

        try:
            doc = yaml.safe_load(text) or {}
        except yaml.YAMLError as exc:  # pragma: no cover - a broken file is its own red
            raise AssertionError(f"{path} does not parse as YAML: {exc}") from exc

        found: list[tuple[str, str]] = []
        for name, job in doc.items():
            if not isinstance(job, dict) or name.startswith("."):
                continue
            steps = cls._flatten(job.get("before_script")) + cls._flatten(job.get("script"))
            body = "\n".join(steps)
            if any(re.match(r"^(- )?pytest\s", line.strip()) for line in steps):
                found.append((f"{path}::{name}", body))
        return found

    @classmethod
    def _jobs_running_pytest(cls) -> list[tuple[str, str]]:
        """[(label, job text)] for every CI job that invokes pytest.

        Jobs are split on the key shape each dialect actually uses: a GitHub
        job sits under `jobs:` at two spaces, a GitLab job is a top-level key.
        Splitting only the GitHub way cut `.gitlab-ci.yml` into fragments and
        reported its lane as missing a bootstrap step it has run all along —
        the test being wrong about a lane that was right, which is the
        direction that quietly erodes trust in a ratchet.
        """
        out: list[tuple[str, str]] = []
        for path in cls._lane_files():
            text = path.read_text(encoding="utf-8")
            if path.name == ".gitlab-ci.yml":
                # RESOLVED, not sliced. Splitting the file into text blocks reads
                # only what is written inside a job, so the day shared setup moved
                # into a YAML anchor — the ordinary way to keep two lanes from
                # drifting — this guard called both lanes broken, including the one
                # that had bootstrapped since it was written. The fact had not
                # changed; only where it was spelled had.
                out.extend(cls._gitlab_jobs(path, text))
                continue
            chunks = re.split(r"\n(?=  \w[\w-]*:\n)", text)
            for job in chunks:
                for line in job.splitlines():
                    stripped = line.strip()
                    # A real invocation — not the word in a comment, and not
                    # the `pip install pytest ...` that every lane also has.
                    if stripped.startswith("#") or "pip install" in stripped:
                        continue
                    if re.match(r"^(- )?(run: )?pytest\s", stripped):
                        out.append((f"{path}::{job.strip().splitlines()[0]}", job))
                        break
        return out

    def test_at_least_one_lane_is_discovered(self):
        """PREMISE. A discovery that finds nothing would pass every assertion."""
        assert len(self._jobs_running_pytest()) >= 2

    def test_every_pytest_lane_deploys_the_profiles_first(self):
        offenders = [
            label for label, job in self._jobs_running_pytest() if self._BOOTSTRAP not in job
        ]
        assert offenders == [], (
            f"these lanes run pytest without deploying the IDE profiles first: {offenders}. "
            "Fourteen test files need them, and a fresh clone has none."
        )

    def test_no_pytest_lane_discards_its_exit_code(self):
        offenders = [
            label
            for label, job in self._jobs_running_pytest()
            if re.search(r"pytest[^\n]*\|\|\s*true", job)
        ]
        assert offenders == [], (
            f"these lanes swallow pytest's exit code with `|| true`: {offenders}. "
            "An advisory lane may decline to gate, but the failure must still be visible."
        )
