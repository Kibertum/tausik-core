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

from conftest import IS_PUBLIC_SNAPSHOT  # noqa: E402

yaml = pytest.importorskip("yaml")

import project_cli_renar  # noqa: E402
from project_cli_renar import (  # noqa: E402
    MANIFEST_FILENAME,
    _batch_blobs,
    _existing_manifest,
    _existing_version,
    journal_high_water,
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

        Asked separately they cost extra git subprocesses per `--write` and, if
        HEAD moved between them, could be computed from two different journal
        states. The number is asserted rather than described: a second reader
        added later makes this red instead of making the next review's report.

        Four processes, two questions: the tip (ls-tree probe, then the blob)
        answers WHAT IS SUPERSEDED; the history (rev-list over every ref, then
        one cat-file streaming every blob) answers WHAT NUMBER IS FREE. The
        history read is two processes whatever its length — that is the
        measured cost the fix was chosen on, and it is pinned three commits
        deep below so an n+1 rewrite cannot pass as the same shape.
        """
        svc, root = project
        self._run(svc, "2026-09-04", monkeypatch)
        _git(root, "add", "-A")
        _git(root, "commit", "-qm", "v1")
        self._run(svc, "2026-09-04", monkeypatch)
        _git(root, "add", "-A")
        _git(root, "commit", "-qm", "v2")
        self._run(svc, "2026-09-04", monkeypatch)
        _git(root, "add", "-A")
        _git(root, "commit", "-qm", "v3")

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
            ["rev-list", "--all", "--full-history", "--", MANIFEST_FILENAME],
            ["cat-file", "--batch"],
        ], f"one journal read per --write, got {calls}"
        assert self._read(root)["manifest-version"] == 4
        assert self._read(root)["replaces"] == "CFM-2026-09-04-tausik@v3"

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
    if prev_id not in {mid for _v, mid in seen} and (_is_shallow(root) or IS_PUBLIC_SNAPSHOT):
        # A shallow clone, or the public snapshot whose history is one
        # flattened commit per release (decision #368): the predecessor was
        # never in this history, and "unreadable" is the honest answer.
        # The docstring promised a skip on a shallow checkout and delivered it
        # only when `git log` was EMPTY. With GIT_DEPTH=50 the previous version
        # sits past the horizon as soon as fifty commits separate two manifest
        # edits — true on the GitLab lane in session #251 — and the guard read
        # a truncated history as a broken chain. A shallow clone that cannot
        # see the predecessor has not measured anything; say so. Keyed on the
        # ID, not the (version, id) pair: an id that IS visible under another
        # version is the same-day reuse defect this file exists to catch, and a
        # truncated history is no excuse for it (review, session #251).
        pytest.skip(f"shallow checkout: {link} is past the clone horizon (known: {sorted(seen)})")
    assert (int(prev_v), prev_id) in seen, (
        f"replaces names {link}, but git holds no manifest with that id and version; "
        f"known: {sorted(seen)}"
    )


def _is_shallow(root: str) -> bool:
    import subprocess

    r = subprocess.run(
        ["git", "rev-parse", "--is-shallow-repository"],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return r.returncode == 0 and r.stdout.strip() == "true"


def test_the_committed_history_never_reuses_a_version_number():
    """The live artifact, over EVERY ref: one version number, one blob.

    The guard above resolves `replaces` against the SET of (version, id) pairs
    in history. A number re-issued over different content on the same day
    would carry the same id, so the pair would match twice — and the guard
    would accept an ambiguous hit as a resolution. This one closes that side:
    no manifest-version may map to two different blobs anywhere in the
    journal. Read-only; skipped without git or without history.

    Walked with `--full-history` and read with ONE `cat-file --batch`, the same
    shape the production reader uses (review #38: the first version walked
    with default simplification — the blind spot it exists to catch — and ran
    two processes per commit).
    """
    import hashlib
    import subprocess

    root = os.path.abspath(os.path.join(_SCRIPTS, ".."))
    if not shutil.which("git"):
        pytest.skip("git not on PATH")
    revs = subprocess.run(
        ["git", "rev-list", "--all", "--full-history", "--", MANIFEST_FILENAME],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdin=subprocess.DEVNULL,
    )
    if revs.returncode != 0 or not revs.stdout.strip():
        pytest.skip("git history unavailable")
    wanted = "".join(f"{sha}:./{MANIFEST_FILENAME}\n" for sha in revs.stdout.split())
    batch = subprocess.run(
        ["git", "cat-file", "--batch"],
        cwd=root,
        capture_output=True,
        input=wanted.encode("ascii"),
    )
    assert batch.returncode == 0, batch.stderr
    blobs_by_version: dict[int, set[str]] = {}
    for blob in _batch_blobs(batch.stdout):
        version = int((yaml.safe_load(blob.decode("utf-8")) or {}).get("manifest-version", 0))
        blobs_by_version.setdefault(version, set()).add(hashlib.sha1(blob).hexdigest())
    reused = {v: sorted(b) for v, b in blobs_by_version.items() if len(b) > 1}
    assert not reused, f"a manifest-version was issued twice over different content: {reused}"


@pytest.mark.skipif(not shutil.which("git"), reason="git not on PATH")
class TestFloorIsTheWholeHistory:
    """The number to issue is one past the highest EVER committed, on any ref.

    Every case here is a HEAD that carries less than the history does. The
    live one: `main` in this repository has never carried the manifest, so
    reading the tip alone gave a floor of 0 and a `--write` from `main` would
    have re-issued v1 over different content.
    """

    @pytest.fixture
    def repo(self, tmp_path):
        r = tmp_path / "repo"
        r.mkdir()
        _git(r, "init", "-q", "-b", "main")
        (r / "seed.txt").write_text("seed\n", encoding="utf-8")
        _git(r, "add", "-A")
        _git(r, "commit", "-qm", "seed")
        return r

    def test_a_branch_that_never_carried_the_manifest_does_not_reissue_v1(self, repo):
        """AC-1: HEAD holds nothing, another ref holds v3 — the next number is 4."""
        _git(repo, "checkout", "-qb", "wave")
        for v in (1, 2, 3):
            _write_manifest(repo, version=v, manifest_id="CFM-2026-09-04-tausik")
            _git(repo, "add", "-A")
            _git(repo, "commit", "-qm", f"v{v}")
        _git(repo, "checkout", "-q", "main")
        path = os.path.join(str(repo), MANIFEST_FILENAME)

        assert not os.path.isfile(path), "main really carries no manifest"
        assert journal_manifest(str(repo)) == (0, None), "the tip answered: nothing here"
        assert journal_high_water(str(repo)) == 3
        assert next_version(path, str(repo)) == 4
        assert previous_link(path, str(repo)) is None, "nothing on this branch to supersede"

    def test_a_tip_below_the_high_water_mark_is_still_the_predecessor(self, repo):
        """AC-2: the floor is the history's, the predecessor is the tip's.

        Reading history only when HEAD carried nothing would miss this: HEAD
        carries v1, and v1 is a perfectly good predecessor to name — but v5
        exists on another ref, so v2 is not a free number.
        """
        path = _write_manifest(repo, version=1, manifest_id="CFM-2026-09-01-tausik")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-qm", "v1")
        _git(repo, "checkout", "-qb", "wave")
        _write_manifest(repo, version=5, manifest_id="CFM-2026-09-04-tausik")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-qm", "v5")
        _git(repo, "checkout", "-q", "main")

        assert _existing_manifest(path) == (1, "CFM-2026-09-01-tausik")
        assert journal_manifest(str(repo)) == (1, "CFM-2026-09-01-tausik")
        assert journal_high_water(str(repo)) == 5
        assert next_version(path, str(repo)) == 6
        assert previous_link(path, str(repo)) == "CFM-2026-09-01-tausik@v1"

    def test_the_mark_survives_the_commit_that_deleted_the_file(self, repo):
        """AC-3: a deletion commit lists in rev-list and reads back `missing`.

        That is a fact about the commit, not a failure of the read: the
        entries before it still count, and the answer is 2, not None and not 0.
        """
        for v in (1, 2):
            _write_manifest(repo, version=v, manifest_id="CFM-2026-09-04-tausik")
            _git(repo, "add", "-A")
            _git(repo, "commit", "-qm", f"v{v}")
        _git(repo, "rm", "-q", MANIFEST_FILENAME)
        _git(repo, "commit", "-qm", "gone")
        path = os.path.join(str(repo), MANIFEST_FILENAME)

        assert journal_manifest(str(repo)) == (0, None)
        assert journal_high_water(str(repo)) == 2
        assert next_version(path, str(repo)) == 3

    def test_a_journal_that_never_held_one_answers_zero_not_none(self, repo, tmp_path):
        """AC-3: the three answers are distinct, and each one is reachable.

        A repository with commits but no manifest ANSWERS — zero. A directory
        that is no repository at all cannot answer — None. A repository with
        no commits yet answers too: rev-list over no refs is empty, not an error.
        """
        assert journal_high_water(str(repo)) == 0
        outside = tmp_path / "outside"
        outside.mkdir()
        assert journal_high_water(str(outside)) is None
        bare = tmp_path / "unborn"
        bare.mkdir()
        _git(bare, "init", "-q", "-b", "main")
        assert journal_high_water(str(bare)) == 0

    def test_a_version_discarded_by_a_merge_is_still_in_the_floor(self, repo):
        """NEGATIVE SCENARIO, found by external review #38 and reproduced.

        main issued v1 and v2; a branch cut at v1 issued v3; the merge kept
        main's side (`-s ours`) and the branch was deleted. v3 is REACHABLE
        through the merge commit, yet a path-limited `rev-list` simplifies
        history and follows only the parent the merge is treesame to, so v3
        was unlisted and the next `--write` handed it out again. Without
        `--full-history` this reads 2 and issues 3.
        """
        for v in (1, 2):
            _write_manifest(repo, version=v, manifest_id="CFM-2026-09-04-tausik")
            _git(repo, "add", "-A")
            _git(repo, "commit", "-qm", f"v{v}")
        _git(repo, "checkout", "-qb", "wave", "HEAD~1")
        _write_manifest(repo, version=3, manifest_id="CFM-2026-09-05-tausik")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-qm", "v3 on the losing side")
        _git(repo, "checkout", "-q", "main")
        _git(repo, "merge", "-q", "-s", "ours", "wave", "-m", "merge keeping main's v2")
        _git(repo, "branch", "-qD", "wave")
        path = os.path.join(str(repo), MANIFEST_FILENAME)

        assert _existing_manifest(path)[0] == 2, "the merge kept v2 on disk"
        assert journal_manifest(str(repo)) == (2, "CFM-2026-09-04-tausik"), "the tip is v2"
        assert journal_high_water(str(repo)) == 3, "v3 is reachable, so it counts"
        assert next_version(path, str(repo)) == 4

    def test_the_history_read_is_two_processes_whatever_its_length(self, repo, monkeypatch):
        """AC-4: five commits, still `rev-list` then one `cat-file --batch`."""
        for v in range(1, 6):
            _write_manifest(repo, version=v, manifest_id="CFM-2026-09-04-tausik")
            _git(repo, "add", "-A")
            _git(repo, "commit", "-qm", f"v{v}")
        calls: list[list[str]] = []
        real = project_cli_renar.git_exec.run

        def counting(args, **kwargs):
            calls.append(list(args))
            return real(args, **kwargs)

        monkeypatch.setattr(project_cli_renar.git_exec, "run", counting)
        assert journal_high_water(str(repo)) == 5
        assert [c[0] for c in calls] == ["rev-list", "cat-file"], calls

    def test_an_unreadable_stream_is_an_error_not_an_empty_journal(self, repo, monkeypatch):
        """NEGATIVE SCENARIO: cat-file failing, or answering nonsense, is None.

        A non-zero cat-file, and a stream whose header parses as neither a blob
        line nor a `missing` line, both land on the unreadable side — never on
        "the journal holds nothing", which would drop the floor to zero.
        """
        import subprocess as sp

        real = project_cli_renar.git_exec.run

        def failing(args, **kwargs):
            if args[0] == "cat-file":
                return sp.CompletedProcess(args, 128, stdout=b"", stderr=b"fatal: bad object\n")
            return real(args, **kwargs)

        def garbled(args, **kwargs):
            if args[0] == "cat-file":
                return sp.CompletedProcess(args, 0, stdout=b"what is this\n", stderr=b"")
            return real(args, **kwargs)

        _write_manifest(repo, version=1, manifest_id="CFM-2026-09-04-tausik")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-qm", "v1")
        monkeypatch.setattr(project_cli_renar.git_exec, "run", failing)
        assert journal_high_water(str(repo)) is None
        monkeypatch.setattr(project_cli_renar.git_exec, "run", garbled)
        assert journal_high_water(str(repo)) is None


@pytest.mark.skipif(not shutil.which("git"), reason="git not on PATH")
class TestHistoryBelowTheWorktreeTop:
    """AC-7: the history read is scoped by cwd, like the tip read is.

    `rev-list -- <name>` takes a cwd-relative pathspec and `cat-file` an object
    name anchored with `./`; drop either and a nested project counts the
    manifest of whatever sits at the worktree top.
    """

    @pytest.fixture
    def nested(self, tmp_path):
        top = tmp_path / "top"
        proj = top / "pkg"
        proj.mkdir(parents=True)
        _git(top, "init", "-q", "-b", "main")
        return top, proj

    def test_a_sibling_manifest_at_the_top_is_not_our_history(self, nested):
        top, proj = nested
        _write_manifest(top, version=99, manifest_id="CFM-2000-01-01-other")
        _git(top, "add", "-A")
        _git(top, "commit", "-qm", "someone else's, at the top")
        path = os.path.join(str(proj), MANIFEST_FILENAME)

        assert journal_high_water(str(proj)) == 0
        assert next_version(path, str(proj)) == 1

    def test_our_own_history_is_read_under_a_nested_root(self, nested):
        """NEGATIVE SCENARIO: both exist, and only ours must count.

        v4 of ours sits on another ref, v99 of theirs at the top on HEAD; the
        floor must be 4, not 99 and not 0.
        """
        top, proj = nested
        _git(top, "checkout", "-qb", "wave")
        _write_manifest(proj, version=4, manifest_id="CFM-2026-09-04-tausik")
        _git(top, "add", "-A")
        _git(top, "commit", "-qm", "ours, v4, on a branch")
        _git(top, "checkout", "-q", "--orphan", "main")
        _git(top, "rm", "-rfq", ".")
        proj.mkdir(exist_ok=True)  # `rm -r` took the emptied directory with it
        _write_manifest(top, version=99, manifest_id="CFM-2000-01-01-other")
        _git(top, "add", "-A")
        _git(top, "commit", "-qm", "theirs, at the top")
        path = os.path.join(str(proj), MANIFEST_FILENAME)

        assert journal_manifest(str(proj)) == (0, None)
        assert journal_high_water(str(proj)) == 4
        assert next_version(path, str(proj)) == 5


class TestBatchBlobs:
    """The `cat-file --batch` stream, one shape per branch of the parser."""

    def test_missing_entries_carry_no_body_and_are_skipped(self):
        raw = b"abc:./m.yaml missing\n" + b"1111 blob 4\nv: 1\n" + b"abc:./x ambiguous\n"
        assert _batch_blobs(raw) == [b"v: 1"]

    def test_sizes_are_bytes_and_a_body_may_contain_newlines(self):
        body = "manifest-version: 7\nassessor: Юмашев\n".encode()
        raw = (
            b"1111 blob " + str(len(body)).encode() + b"\n" + body + b"\n" + b"2222 blob 4\nv: 2\n"
        )
        assert _batch_blobs(raw) == [body, b"v: 2"]

    def test_a_tree_is_stepped_over_not_read_as_a_manifest(self):
        raw = b"3333 tree 5\nxxxxx\n" + b"1111 blob 4\nv: 1\n"
        assert _batch_blobs(raw) == [b"v: 1"]

    def test_a_header_of_neither_shape_is_an_error(self):
        with pytest.raises(ValueError):
            _batch_blobs(b"what is this\n")
        with pytest.raises(ValueError):
            _batch_blobs(b"1111 blob")

    def test_a_body_that_does_not_fit_the_stream_is_an_error(self):
        """NEGATIVE SCENARIO, found by review: a size is a promise, not a fact.

        Oversized: the slice came back short and a truncated blob was parsed
        as whole. Negative: `pos` walked backwards, a negative start clamps to
        the beginning, and the loop re-read the first header forever — a hang
        that no subprocess timeout could reach. Both are `ValueError`, which
        the caller files under "unreadable", never under "empty".
        """
        with pytest.raises(ValueError):
            _batch_blobs(b"1111 blob 100\nshort body only\n")
        with pytest.raises(ValueError):
            _batch_blobs(b"1111 blob -1000000\n" + b"X" * 50 + b"\n")
        # Boundary: the last record's body ends exactly one LF before the end.
        assert _batch_blobs(b"1111 blob 4\nv: 1\n") == [b"v: 1"]
        with pytest.raises(ValueError):
            _batch_blobs(b"1111 blob 4\nv: 1")  # the LF after the body is missing

    def test_an_empty_stream_is_no_blobs(self):
        assert _batch_blobs(b"") == []


@pytest.mark.skipif(not shutil.which("git"), reason="git not on PATH")
class TestUnreadableHistoryIsRefused:
    """NEGATIVE SCENARIO, found by review: an unreadable history is not a floor of 0.

    The tip reader's None falls back to the working copy, and the first shape
    of the fix let the history reader's None do the same — `history or 0` —
    so a transient `rev-list` or `cat-file` failure degraded, silently, to the
    exact defect this task closes: from a branch that never carried the
    manifest, `next_version` went back to 1.
    """

    @pytest.fixture
    def repo(self, tmp_path):
        r = tmp_path / "repo"
        r.mkdir()
        _git(r, "init", "-q", "-b", "main")
        _write_manifest(r, version=1, manifest_id="CFM-2026-09-04-tausik")
        _git(r, "add", "-A")
        _git(r, "commit", "-qm", "v1")
        return r

    @staticmethod
    def _failing_cat_file(monkeypatch):
        import subprocess as sp

        real = project_cli_renar.git_exec.run

        def failing(args, **kwargs):
            if args[0] == "cat-file":
                return sp.CompletedProcess(args, 128, stdout=b"", stderr=b"fatal: bad object\n")
            return real(args, **kwargs)

        monkeypatch.setattr(project_cli_renar.git_exec, "run", failing)

    def test_a_tip_that_answered_and_a_history_that_did_not_is_refused(self, repo, monkeypatch):
        from tausik_utils import ServiceError

        path = os.path.join(str(repo), MANIFEST_FILENAME)
        self._failing_cat_file(monkeypatch)
        assert journal_manifest(str(repo)) == (1, "CFM-2026-09-04-tausik"), "the tip is readable"
        assert journal_high_water(str(repo)) is None, "the history is not"
        with pytest.raises(ServiceError, match="refusing to issue"):
            next_version(path, str(repo))

    def test_the_write_command_refuses_too_and_leaves_no_file_behind(
        self, repo, monkeypatch, capsys
    ):
        """The refusal reaches the CLI: no manifest is written over an unknown floor."""
        from tausik_utils import ServiceError

        pytest.importorskip("yaml")
        import project_config
        from project_backend import SQLiteBackend
        from project_service import ProjectService

        (repo / ".tausik").mkdir()
        monkeypatch.setattr(project_config, "find_tausik_dir", lambda: str(repo / ".tausik"))
        svc = ProjectService(SQLiteBackend(str(repo / ".tausik" / "p.db")))
        before = (repo / MANIFEST_FILENAME).read_bytes()
        self._failing_cat_file(monkeypatch)

        class _Args:
            renar_cmd = "conformance"
            write = True
            assessor = "assessor-test"

        try:
            with pytest.raises(ServiceError):
                project_cli_renar.cmd_renar(svc, _Args())
        finally:
            svc.be.close()
        capsys.readouterr()
        assert (repo / MANIFEST_FILENAME).read_bytes() == before, "nothing was written"

    def test_no_repository_at_all_still_falls_back_to_the_working_copy(self, tmp_path):
        """The refusal is for a journal that half-answered, not for no journal.

        Both readers None — not a repository — is the state the fallback
        exists for, unchanged.
        """
        outside = tmp_path / "outside"
        outside.mkdir()
        path = _write_manifest(outside, version=4, manifest_id="CFM-2026-09-04-tausik")
        assert journal_manifest(str(outside)) is None
        assert journal_high_water(str(outside)) is None
        assert next_version(path, str(outside)) == 5

    def test_a_rev_list_line_that_is_not_hex_is_unreadable(self, repo, monkeypatch):
        """NEGATIVE SCENARIO, found by review: git's output is decoded with
        errors="replace", so a damaged stream reaches the encoder as U+FFFD,
        which is not ASCII — an error to file as None, not a traceback."""
        import subprocess as sp

        real = project_cli_renar.git_exec.run

        def damaged(args, **kwargs):
            if args[0] == "rev-list":
                return sp.CompletedProcess(args, 0, stdout="��\n", stderr="")
            return real(args, **kwargs)

        monkeypatch.setattr(project_cli_renar.git_exec, "run", damaged)
        assert journal_high_water(str(repo)) is None
