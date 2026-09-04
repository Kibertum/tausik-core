"""`replaces` names the manifest that actually preceded this one (§13.4.2).

TWO ways of composing this link have broken the chain, and the second is the
one that did most of the damage.

1. TODAY's date plus the previous version number — `CFM-<today>-tausik@v<n-1>`
   — names a real manifest only when the predecessor was written on the same
   calendar day. Seven regenerations in a row happened to be; the first
   cross-day one (session #208) published `replaces: CFM-2026-09-04-tausik@v13`
   for a predecessor whose id was `CFM-2026-09-03-tausik`. Found by the fix
   review, record #24.

2. The WORKING COPY's own version and id. §13.4.1 makes the artifact's git
   history the audit journal, and the counter advances on every `--write` while
   the journal records only commits — so versions v4, v5, v6, v8, v10 and v12
   were issued on disk and never became audit records. Measured over the live
   artifact in session #212: 9 versions in the journal, 8 back-links, FIVE of
   them resolving to nothing. The date explains none of those five.

The journal's own last entry is the only link that resolves by construction,
and these tests hold both the ranking (journal outranks disk) and the
distinction the ranking rests on: "the journal holds no manifest" is a fact,
"the journal could not be read" is not.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys

_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

import pytest  # noqa: E402

yaml = pytest.importorskip("yaml")

import project_cli_renar  # noqa: E402
from project_cli_renar import (  # noqa: E402
    MANIFEST_FILENAME,
    _existing_manifest,
    _existing_version,
    journal_manifest,
    next_version,
    previous_link,
)


def _manifest(tmp_path, *, version: int, manifest_id: str) -> str:
    p = tmp_path / "RENAR-CONFORMANCE.yaml"
    p.write_text(
        f"manifest-version: {version}\nmanifest-id: {manifest_id}\n"
        f"assessment-date: '{manifest_id[4:14]}'\n",
        encoding="utf-8",
    )
    return str(p)


@pytest.fixture
def no_journal(monkeypatch):
    """Force the working-copy branch: the journal is unreadable, deterministically.

    These cases are about the fallback reader, and `tmp_path` alone does not
    pin which branch runs — git searches UPWARD, so a temp dir that happened to
    sit inside a repository would answer with that repository's journal. Making
    git unavailable states the branch under test instead of assuming it.
    """

    def boom(*a, **k):
        raise OSError("no git in this scenario")

    monkeypatch.setattr(project_cli_renar.git_exec, "run", boom)


def test_the_link_names_the_predecessor_not_today(tmp_path, no_journal):
    """A predecessor written yesterday is still the predecessor today."""
    p = _manifest(tmp_path, version=13, manifest_id="CFM-2026-09-03-tausik")
    assert previous_link(p) == "CFM-2026-09-03-tausik@v13"
    assert _existing_manifest(p) == (13, "CFM-2026-09-03-tausik")
    assert _existing_version(p) == 13


def test_no_predecessor_means_no_link(tmp_path, no_journal):
    assert previous_link(str(tmp_path / "missing.yaml")) is None
    assert _existing_version(str(tmp_path / "missing.yaml")) == 0


def test_a_manifest_without_an_id_yields_no_link(tmp_path, no_journal):
    p = tmp_path / MANIFEST_FILENAME
    p.write_text("manifest-version: 2\n", encoding="utf-8")
    assert previous_link(str(p)) is None
    assert _existing_version(str(p)) == 2


def _git(repo, *args: str) -> subprocess.CompletedProcess:
    """git inside a synthetic repo, identity and signing pinned to the fixture.

    Identity and `commit.gpgsign=false` are supplied per-call so the test does
    not depend on — or disturb — whatever the developer's global git config
    says; a machine that signs by default would otherwise hang on a passphrase.
    """
    return subprocess.run(
        [
            "git",
            "-c",
            "user.email=t@example.invalid",
            "-c",
            "user.name=T",
            "-c",
            "commit.gpgsign=false",
            *args,
        ],
        cwd=str(repo),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
        stdin=subprocess.DEVNULL,
    )


def _write_manifest(root, *, version: int, manifest_id: str) -> str:
    p = os.path.join(str(root), MANIFEST_FILENAME)
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(
            f"manifest-version: {version}\nmanifest-id: {manifest_id}\n"
            f"assessment-date: '{manifest_id[4:14]}'\n"
        )
    return p


@pytest.mark.skipif(not shutil.which("git"), reason="git not on PATH")
class TestJournalOutranksWorkingCopy:
    """The predecessor is the last JOURNAL entry, not the last file written.

    Every case here is the double-`--write`-without-a-commit situation that
    issued v4, v5, v6, v8, v10 and v12 into nothing.
    """

    @pytest.fixture
    def repo(self, tmp_path):
        r = tmp_path / "repo"
        r.mkdir()
        _git(r, "init", "-q", "-b", "main")
        return r

    def test_the_journal_outranks_the_working_copy(self, repo):
        """A committed v1 beats an uncommitted v2 sitting right next to it."""
        path = _write_manifest(repo, version=1, manifest_id="CFM-2026-08-31-tausik")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-qm", "v1")
        # The uncommitted regeneration: on disk, absent from the journal.
        _write_manifest(repo, version=2, manifest_id="CFM-2026-09-01-tausik")

        assert _existing_manifest(path) == (2, "CFM-2026-09-01-tausik"), "disk really did move"
        assert journal_manifest(str(repo)) == (1, "CFM-2026-08-31-tausik")
        assert previous_link(path, str(repo)) == "CFM-2026-08-31-tausik@v1"
        # v2 was issued on disk, so reusing it is forbidden even though the
        # journal never saw it: the next version is 3, and it replaces v1.
        assert next_version(path, str(repo)) == 3

    def test_a_deleted_working_copy_does_not_reset_the_counter(self, repo):
        """§13.4.1 non-reuse survives `rm RENAR-CONFORMANCE.yaml`.

        NEGATIVE SCENARIO. The call site used to read the version from the file
        alone, so deleting it dropped the count to 0 and re-issued v1 over
        different content — while the comment above it said "never reset the
        version".
        """
        path = _write_manifest(repo, version=15, manifest_id="CFM-2026-09-04-tausik")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-qm", "v15")
        os.remove(path)

        assert _existing_version(path) == 0, "the working copy really is gone"
        assert next_version(path, str(repo)) == 16
        assert previous_link(path, str(repo)) == "CFM-2026-09-04-tausik@v15"

    def test_a_journal_entry_without_a_version_yields_no_link(self, repo):
        """NEGATIVE SCENARIO: an id with no version must not become `@v0`.

        The link is withheld unless BOTH halves are present, and until this
        test the `version` half was unverifiable: every producer of a
        (version, id) pair yields either (0, None) or (n>0, "id"), so the whole
        suite could not tell `version and mid` from a bare `mid` — a declared
        mutation dropping the version half SURVIVED. The pair is not
        guaranteed, though: a manifest carrying `manifest-id` and no
        `manifest-version` parses to (0, "id") and would publish `<id>@v0`, a
        version that can never legitimately exist — the very defect class
        (§13.4.2 naming something that never was) this module exists to close.
        """
        p = os.path.join(str(repo), MANIFEST_FILENAME)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write("manifest-id: CFM-2026-09-04-tausik\n")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-qm", "an id without a version")

        assert journal_manifest(str(repo)) == (0, "CFM-2026-09-04-tausik")
        assert previous_link(p, str(repo)) is None
        assert next_version(p, str(repo)) == 1

    def test_an_empty_journal_does_not_borrow_the_working_copy(self, repo):
        """A readable journal with no manifest in it yields NO link, not the disk's.

        NEGATIVE SCENARIO, and the exact case the None/(0, None) split exists
        for: the journal answered, and its answer was "nothing here". Naming the
        uncommitted file as predecessor would publish an unresolvable link.
        """
        (repo / "seed.txt").write_text("seed\n", encoding="utf-8")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-qm", "no manifest yet")
        path = _write_manifest(repo, version=2, manifest_id="CFM-2026-09-04-tausik")

        assert journal_manifest(str(repo)) == (0, None)
        assert previous_link(path, str(repo)) is None
        assert next_version(path, str(repo)) == 3

    def test_a_repository_without_commits_falls_back_to_the_working_copy(self, repo):
        """No HEAD means the journal is UNREADABLE — the disk is all there is.

        NEGATIVE SCENARIO. Distinct from the empty-journal case above, and the
        opposite answer: there, git spoke; here, it could not.
        """
        path = _write_manifest(repo, version=7, manifest_id="CFM-2026-09-04-tausik")

        assert journal_manifest(str(repo)) is None
        assert previous_link(path, str(repo)) == "CFM-2026-09-04-tausik@v7"
        assert next_version(path, str(repo)) == 8

    def test_a_manifest_committed_as_garbage_yields_no_link(self, repo):
        """NEGATIVE SCENARIO: an unparseable journal entry names no predecessor.

        Not an exception, and not a half-built link either — the parser returns
        (0, None) and the link is withheld.
        """
        p = os.path.join(str(repo), MANIFEST_FILENAME)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write("- this is a list, not a manifest\n")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-qm", "garbage")

        assert journal_manifest(str(repo)) == (0, None)
        assert previous_link(p, str(repo)) is None


@pytest.mark.skipif(not shutil.which("git"), reason="git not on PATH")
class TestProjectRootBelowTheWorktreeTop:
    """The project root need not be the repository top level, and usually isn't.

    `git show HEAD:<path>` resolves `<path>` against the TOP LEVEL of the
    worktree, not against the subprocess cwd — git says so itself: from
    `scripts/`, `git show HEAD:project.py` fails with "path
    'scripts/project.py' exists, but not 'project.py'" and hints at
    `HEAD:./project.py`. The project root comes from `find_tausik_dir()`, which
    walks UPWARD looking for `.tausik/` and is under no obligation to land on
    the worktree top: a package inside a monorepo is the ordinary case.

    Without the `./` prefix the read fails on a manifest that is committed and
    present, and the failure is indistinguishable from an empty journal — an
    ERROR recorded as a FACT, which is the whole defect class this module
    exists to close. Every other fixture here git-inits at the project root, so
    none of them can see it.
    """

    @pytest.fixture
    def nested(self, tmp_path):
        top = tmp_path / "top"
        proj = top / "pkg"
        proj.mkdir(parents=True)
        _git(top, "init", "-q", "-b", "main")
        return top, proj

    def test_a_committed_manifest_below_the_top_is_still_found(self, nested):
        top, proj = nested
        path = _write_manifest(proj, version=15, manifest_id="CFM-2026-09-04-tausik")
        _git(top, "add", "-A")
        _git(top, "commit", "-qm", "v15 under a subdirectory")

        assert journal_manifest(str(proj)) == (15, "CFM-2026-09-04-tausik")
        assert previous_link(path, str(proj)) == "CFM-2026-09-04-tausik@v15"
        assert next_version(path, str(proj)) == 16

    def test_a_nested_root_still_tells_an_empty_journal_from_an_unreadable_one(self, nested):
        """NEGATIVE SCENARIO: the distinction must survive the nesting too.

        Committed something, but not a manifest — the journal ANSWERED, and its
        answer is "nothing here": `(0, None)`, and no link borrowed from disk.
        """
        top, proj = nested
        (proj / "seed.txt").write_text("seed\n", encoding="utf-8")
        _git(top, "add", "-A")
        _git(top, "commit", "-qm", "no manifest yet")
        path = _write_manifest(proj, version=3, manifest_id="CFM-2026-09-04-tausik")

        assert journal_manifest(str(proj)) == (0, None)
        assert previous_link(path, str(proj)) is None
        assert next_version(path, str(proj)) == 4

    def test_a_sibling_directorys_manifest_is_not_mistaken_for_ours(self, nested):
        """NEGATIVE SCENARIO: `./` must scope the read, not merely make it succeed.

        A manifest committed at the worktree TOP is not this project's journal
        entry. Reading `HEAD:<name>` would have found it and named a
        predecessor belonging to a different project in the same repository.
        """
        top, proj = nested
        _write_manifest(top, version=99, manifest_id="CFM-2026-01-01-other")
        _git(top, "add", "-A")
        _git(top, "commit", "-qm", "someone else's manifest at the top")
        path = os.path.join(str(proj), MANIFEST_FILENAME)

        assert journal_manifest(str(proj)) == (0, None)
        assert previous_link(path, str(proj)) is None

    def test_our_own_entry_is_read_not_the_one_at_the_top(self, nested):
        """NEGATIVE SCENARIO: both manifests exist — the wrong one must not win.

        Written because a declared mutation SURVIVED. Dropping `./` from the
        blob read is caught by the two cases above only because the `ls-tree`
        probe short-circuits before the read whenever this project has no
        committed manifest of its own. When it HAS one, the probe passes and
        the read runs — and without `./` it returns the top-level manifest, so
        a well-formed `replaces` would name a DIFFERENT project's audit record.
        That is worse than the unresolvable link this whole chain of work
        started from: it resolves, to the wrong journal.
        """
        top, proj = nested
        _write_manifest(top, version=99, manifest_id="CFM-2000-01-01-other")
        path = _write_manifest(proj, version=4, manifest_id="CFM-2026-09-04-tausik")
        _git(top, "add", "-A")
        _git(top, "commit", "-qm", "two manifests, one repository")

        assert journal_manifest(str(proj)) == (4, "CFM-2026-09-04-tausik")
        assert previous_link(path, str(proj)) == "CFM-2026-09-04-tausik@v4"
        assert next_version(path, str(proj)) == 5


@pytest.mark.skipif(not shutil.which("git"), reason="git not on PATH")
class TestWriteChainEndToEnd:
    """`renar conformance --write` itself, not just the two readers under it.

    The seam that carries the link from the journal into the artifact — the
    `generate(..., link)` call — had no test of its own; the chain was asserted
    on either side of it. Two regenerations are driven through the real command
    here, and the second one is the shape that broke the chain historically:
    a `--write` whose predecessor on disk never reached a commit.
    """

    @pytest.fixture
    def project(self, tmp_path, monkeypatch):
        pytest.importorskip("yaml")
        from project_backend import SQLiteBackend
        from project_service import ProjectService

        root = tmp_path / "proj"
        (root / ".tausik").mkdir(parents=True)
        _git(root, "init", "-q", "-b", "main")
        (root / "seed.txt").write_text("seed\n", encoding="utf-8")
        _git(root, "add", "-A")
        _git(root, "commit", "-qm", "seed")

        import project_config

        monkeypatch.setattr(project_config, "find_tausik_dir", lambda: str(root / ".tausik"))
        svc = ProjectService(SQLiteBackend(str(root / ".tausik" / "p.db")))
        try:
            yield svc, root
        finally:
            svc.be.close()

    @staticmethod
    def _run(svc, date: str, monkeypatch) -> None:
        """One `tausik renar conformance --write` on a pinned assessment date."""

        class _Args:
            renar_cmd = "conformance"
            write = True
            assessor = "assessor-test"

        with monkeypatch.context() as mp:
            mp.setattr(project_cli_renar, "utcnow_iso", lambda: f"{date}T00:00:00Z")
            project_cli_renar.cmd_renar(svc, _Args())

    def _read(self, root):
        with open(root / MANIFEST_FILENAME, encoding="utf-8") as fh:
            return yaml.safe_load(fh)

    def test_the_first_write_starts_the_chain(self, project, capsys, monkeypatch):
        svc, root = project
        self._run(svc, "2026-09-04", monkeypatch)
        capsys.readouterr()
        m = self._read(root)
        assert m["manifest-version"] == 1
        assert m["replaces"] is None, "nothing in the journal to replace"

    def test_an_uncommitted_predecessor_is_skipped_not_named(self, project, capsys, monkeypatch):
        """The historical break, driven end to end: write, write, commit.

        v1 is written and never committed, so the journal never holds it. The
        second write must NOT name it — and must not reuse its number either.
        The old code named `CFM-<today>-tausik@v1`, an id no commit ever carried.
        """
        svc, root = project
        self._run(svc, "2026-09-04", monkeypatch)  # v1 — written, never committed
        self._run(svc, "2026-09-05", monkeypatch)  # v2 — the regeneration under test
        capsys.readouterr()

        m = self._read(root)
        assert m["manifest-version"] == 2, "a version issued on disk is never reused"
        assert m["replaces"] is None, "the journal held nothing — so the link is withheld"

    def test_one_write_reads_the_journal_exactly_once(self, project, capsys, monkeypatch):
        """The version and the link describe the SAME instant, so one read serves both.

        Asked separately they cost four git subprocesses per `--write` and, if
        HEAD moved between them, could be computed from two different journal
        states. The number is asserted rather than described: a second reader
        added later makes this red instead of making the next review's report.
        """
        svc, root = project
        self._run(svc, "2026-09-04", monkeypatch)
        _git(root, "add", "-A")
        _git(root, "commit", "-qm", "v1")

        calls: list[list[str]] = []
        real = project_cli_renar.git_exec.run

        def counting(args, **kwargs):
            calls.append(list(args))
            return real(args, **kwargs)

        monkeypatch.setattr(project_cli_renar.git_exec, "run", counting)
        self._run(svc, "2026-09-05", monkeypatch)
        capsys.readouterr()

        assert calls == [
            ["ls-tree", "--name-only", "HEAD", "--", MANIFEST_FILENAME],
            ["show", f"HEAD:./{MANIFEST_FILENAME}"],
        ], f"one journal read per --write, got {calls}"
        assert self._read(root)["replaces"] == "CFM-2026-09-04-tausik@v1"

    def test_a_committed_predecessor_is_named_by_its_own_id(self, project, capsys, monkeypatch):
        """Cross-day chain: yesterday's committed manifest, named by ITS date."""
        svc, root = project
        self._run(svc, "2026-09-04", monkeypatch)
        _git(root, "add", "-A")
        _git(root, "commit", "-qm", "v1")
        first = self._read(root)

        self._run(svc, "2026-09-05", monkeypatch)
        capsys.readouterr()
        second = self._read(root)

        assert second["manifest-version"] == 2
        assert second["manifest-id"] == "CFM-2026-09-05-tausik", "today's id is today's"
        assert second["replaces"] == f"{first['manifest-id']}@v1"
        assert second["replaces"] == "CFM-2026-09-04-tausik@v1", (
            "the predecessor is named by the date IT was assessed, not by today's"
        )


def test_a_blob_listed_but_unreadable_is_an_error_not_an_absence(tmp_path, monkeypatch):
    """NEGATIVE SCENARIO: git ran, answered non-zero, and the answer is not "absent".

    `git_exec.run` does not raise on a non-zero exit, and git answers 128 to
    nearly everything — a pruned or corrupt blob, an object file locked by a
    scanner, a blobless partial clone that could not fetch. Read off `git show`
    alone, every one of those was filed as "the journal is empty", the one
    verdict that refuses to fall back to the working copy: the link was
    withheld AND the version floor dropped to zero. HEAD listing the path while
    the blob cannot be read is an ERROR, and the working copy answers instead.
    """
    import subprocess as sp

    path = _write_manifest(tmp_path, version=15, manifest_id="CFM-2026-09-04-tausik")

    def fake_run(args, **kwargs):
        if args[0] == "ls-tree":
            return sp.CompletedProcess(args, 0, stdout=f"{MANIFEST_FILENAME}\n", stderr="")
        return sp.CompletedProcess(args, 128, stdout="", stderr="fatal: bad object HEAD:./x\n")

    monkeypatch.setattr(project_cli_renar.git_exec, "run", fake_run)
    assert journal_manifest(str(tmp_path)) is None
    assert previous_link(path, str(tmp_path)) == "CFM-2026-09-04-tausik@v15"
    assert next_version(path, str(tmp_path)) == 16


def test_a_git_failure_is_not_a_fabricated_link(tmp_path, monkeypatch):
    """NEGATIVE SCENARIO: git missing or hanging degrades, it does not invent.

    `journal_manifest` must report "unreadable" (None) rather than let an OSError
    escape into a CLI traceback or, worse, be swallowed into a (0, None) that
    reads as "the journal is empty".
    """
    path = _write_manifest(tmp_path, version=4, manifest_id="CFM-2026-09-04-tausik")

    def boom(*a, **k):
        raise OSError("no git on this machine")

    monkeypatch.setattr(project_cli_renar.git_exec, "run", boom)
    assert journal_manifest(str(tmp_path)) is None
    assert previous_link(path, str(tmp_path)) == "CFM-2026-09-04-tausik@v4"
    assert next_version(path, str(tmp_path)) == 5


def test_the_committed_manifest_chain_resolves():
    """The live artifact: `replaces` must name the id git holds one version back.

    Read-only; skipped when the file or git history is unavailable (a fresh
    clone without the artifact, a shallow CI checkout).
    """
    import subprocess

    root = os.path.abspath(os.path.join(_SCRIPTS, ".."))
    path = os.path.join(root, "RENAR-CONFORMANCE.yaml")
    if not os.path.isfile(path):
        pytest.skip("no manifest in this tree")
    with open(path, encoding="utf-8") as f:
        cur = yaml.safe_load(f) or {}
    link = cur.get("replaces")
    if not link or int(cur.get("manifest-version", 0)) <= 1:
        pytest.skip("first manifest of the chain")
    prev_id, _, prev_v = str(link).rpartition("@v")
    r = subprocess.run(
        ["git", "log", "--format=%H", "-n", "40", "--", "RENAR-CONFORMANCE.yaml"],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if r.returncode != 0 or not r.stdout.strip():
        pytest.skip("git history unavailable")
    seen: set[tuple[int, str]] = set()
    for sha in r.stdout.split():
        show = subprocess.run(
            ["git", "show", f"{sha}:RENAR-CONFORMANCE.yaml"],
            cwd=root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if show.returncode != 0:
            continue
        old = yaml.safe_load(show.stdout) or {}
        seen.add((int(old.get("manifest-version", 0)), str(old.get("manifest-id"))))
    assert (int(prev_v), prev_id) in seen, (
        f"replaces names {link}, but git holds no manifest with that id and version; "
        f"known: {sorted(seen)}"
    )
