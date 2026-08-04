"""`TAUSIK_HOME` decides whether "it never leaves this machine" is true.

The shared store is written WITHOUT redaction, and the reason on record is that
it is a file in the user's own home. That is not a property of the code — it is
a property of a DIRECTORY, and an environment variable names that directory. So
these tests are about the premise, not about the plumbing: point the variable at
a synced folder or into a work tree and the recorded reason stops holding while
every other test in the suite still passes.

The split between refusing and neutralising is asserted deliberately. A guard
that refused every git work tree would reject the DEFAULT location for anyone
keeping their home directory in a dotfiles repository, and a guard whose first
act is a false alarm on an ordinary setup is a guard that gets switched off.
"""

from __future__ import annotations

import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import knowledge_db  # noqa: E402
import knowledge_home_guard as guard  # noqa: E402
from tausik_utils import ServiceError  # noqa: E402

CROSSCUTTING_SCOPE = ["scripts/knowledge_home_guard.py", "scripts/knowledge_db.py"]

DB = "knowledge.db"


@pytest.fixture(autouse=True)
def clean_cache():
    guard.reset_cache()
    yield
    guard.reset_cache()


def _git(*args: str, cwd: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )


def _init_repo(path) -> str:
    path.mkdir(parents=True, exist_ok=True)
    _git("init", cwd=str(path))
    _git("config", "user.email", "t@example.com", cwd=str(path))
    _git("config", "user.name", "t", cwd=str(path))
    return str(path)


class TestWhatIsRefusedOutright:
    """Cases nothing written locally can fix, so continuing is not an option."""

    @pytest.mark.parametrize("bad", ["", "   "])
    def test_an_empty_home_is_refused_rather_than_resolved_to_the_cwd(self, bad):
        """The dangerous default: `abspath("")` is the working directory, which
        changes with every command and is frequently inside a project."""
        with pytest.raises(ServiceError) as e:
            guard.assert_safe_knowledge_home(bad, DB)
        assert "empty" in str(e.value).lower()

    @pytest.mark.parametrize("unc", ["\\\\server\\share\\kn", "//server/share/kn"])
    def test_a_network_path_is_refused(self, unc):
        with pytest.raises(ServiceError) as e:
            guard.assert_safe_knowledge_home(unc, DB)
        assert "network" in str(e.value).lower()

    @pytest.mark.parametrize(
        "name",
        [
            "OneDrive",
            "Dropbox",
            "Google Drive",
            "YandexDisk",
            "iCloud Drive",
            # The default folder name on essentially every managed Windows
            # machine. Matching only the bare product name misses all of them.
            "OneDrive - Acme Corp",
        ],
    )
    def test_a_cloud_sync_directory_is_refused(self, tmp_path, name):
        home = tmp_path / name / "tausik-knowledge"
        with pytest.raises(ServiceError) as e:
            guard.assert_safe_knowledge_home(str(home), DB)
        assert "cloud-sync" in str(e.value)

    @pytest.mark.parametrize(
        "tail",
        [
            "CloudStorage/OneDrive-AcmeCorp/kn",
            "CloudStorage/GoogleDrive-someone@example.com/kn",
            "CloudStorage/Box-AcmeCorp/kn",
        ],
    )
    def test_the_macos_unified_cloud_layout_is_refused_whatever_the_provider(self, tmp_path, tail):
        """`~/Library/CloudStorage/<provider>-<account>` is where macOS 12+ puts
        every provider, and the account suffix means no product name matches. So
        the container is what is matched, and it catches all of them at once."""
        home = tmp_path / "Library" / tail
        with pytest.raises(ServiceError) as e:
            guard.assert_safe_knowledge_home(str(home), DB)
        assert "cloud-sync" in str(e.value)

    def test_a_mapped_or_mounted_network_volume_is_refused(self, tmp_path, monkeypatch):
        """UNC syntax is the obvious network path. This is the other one: a `Z:`
        handed out by a logon script, or an fstab mount — "in my home directory"
        by every name-based test, and somebody else's disk in fact.

        The volume probe is platform plumbing, so what is pinned here is the
        WIRING: when the probe says remote, the store is refused.
        """
        monkeypatch.setattr(guard, "_is_network_volume", lambda p: True)
        with pytest.raises(ServiceError) as e:
            guard.assert_safe_knowledge_home(str(tmp_path / "kn"), DB)
        assert "network" in str(e.value).lower()

    def test_the_refusal_says_what_to_do_instead(self, tmp_path):
        with pytest.raises(ServiceError) as e:
            guard.assert_safe_knowledge_home(str(tmp_path / "Dropbox" / "kn"), DB)
        assert "TAUSIK_HOME" in str(e.value)


class TestWhatIsNotRefused:
    """The false alarms a name-matching guard would produce."""

    @pytest.mark.parametrize(
        "name",
        [
            "my-dropbox-notes",
            # A bare `onedrive` PREFIX rule would swallow this one — an ordinary
            # directory named after what it backs up. The business-folder rule
            # spells its separator out to keep them apart.
            "onedrive-backup-scripts",
            "boxes",
            "megabytes",
            # Ordinary English words. `box` and `mega` are real products and are
            # deliberately absent from the list for exactly this reason.
            "box",
            "mega",
        ],
    )
    def test_a_directory_merely_NAMED_after_a_sync_tool_is_fine(self, tmp_path, name):
        """Matching is by whole path component, never by substring."""
        home = tmp_path / name
        assert guard.assert_safe_knowledge_home(str(home), DB)

    def test_an_ordinary_home_needs_no_gitignore(self, tmp_path):
        home = tmp_path / "kn"
        home.mkdir()
        guard.assert_safe_knowledge_home(str(home), DB)
        guard.protect_home_in_git(str(home), DB)
        assert not (home / ".gitignore").exists(), (
            "a .gitignore appeared where there is no git tree to hide from"
        )

    def test_a_directory_that_does_not_exist_yet_is_validated_not_crashed_on(self, tmp_path):
        home = tmp_path / "not" / "created" / "yet"
        assert guard.assert_safe_knowledge_home(str(home), DB)


class TestSymlinksAreResolvedBeforeAnythingIsJudged:
    """A name-based check reads the name it was given, not the place it leads."""

    def test_a_link_pointing_into_a_synced_directory_is_refused(self, tmp_path):
        target = tmp_path / "Dropbox" / "kn"
        target.mkdir(parents=True)
        link = tmp_path / "innocent-looking-home"
        try:
            os.symlink(target, link, target_is_directory=True)
        except (OSError, NotImplementedError) as e:  # pragma: no cover
            pytest.skip(f"symlinks unavailable in this environment: {e}")
        with pytest.raises(ServiceError) as excinfo:
            guard.assert_safe_knowledge_home(str(link), DB)
        assert "cloud-sync" in str(excinfo.value)

    def test_the_resolved_path_is_what_callers_get_back(self, tmp_path):
        target = tmp_path / "real"
        target.mkdir()
        link = tmp_path / "link"
        try:
            os.symlink(target, link, target_is_directory=True)
        except (OSError, NotImplementedError) as e:  # pragma: no cover
            pytest.skip(f"symlinks unavailable in this environment: {e}")
        got = guard.assert_safe_knowledge_home(str(link), DB)
        assert os.path.realpath(got) == os.path.realpath(str(target))


class TestAGitTreeIsNeutralisedRatherThanRefused:
    """The whole point of not simply refusing: dotfiles repositories are normal."""

    def test_a_store_inside_a_work_tree_is_allowed(self, tmp_path):
        repo = _init_repo(tmp_path / "dotfiles")
        home = os.path.join(repo, ".tausik-knowledge")
        assert guard.assert_safe_knowledge_home(home, DB)

    def test_and_it_is_hidden_from_git_add_dash_A(self, tmp_path):
        """The property that matters is not "a file was written" but "git does
        not pick it up", so that is what is asserted — through git itself."""
        repo = _init_repo(tmp_path / "dotfiles")
        home = os.path.join(repo, ".tausik-knowledge")
        guard.assert_safe_knowledge_home(home, DB)
        os.makedirs(home, exist_ok=True)
        guard.protect_home_in_git(home, DB)

        with open(os.path.join(home, DB), "w", encoding="utf-8") as fh:
            fh.write("pretend this is a database naming every client")

        _git("add", "-A", cwd=repo)
        staged = _git("diff", "--cached", "--name-only", cwd=repo).stdout
        assert ".tausik-knowledge" not in staged, f"`git add -A` staged the shared store:\n{staged}"

        ignored = _git("check-ignore", "-v", os.path.join(home, DB), cwd=repo)
        assert ignored.returncode == 0, "git does not consider the store ignored"

    def test_a_gitignore_that_already_covers_the_store_is_left_alone(self, tmp_path):
        """Rewriting a person's file on every open would be arguing with them."""
        repo = _init_repo(tmp_path / "dotfiles")
        home = os.path.join(repo, ".tausik-knowledge")
        os.makedirs(home)
        with open(os.path.join(home, ".gitignore"), "w", encoding="utf-8") as fh:
            fh.write("# mine\n*\n")
        guard.assert_safe_knowledge_home(home, DB)
        guard.protect_home_in_git(home, DB)
        with open(os.path.join(home, ".gitignore"), encoding="utf-8") as fh:
            assert fh.read() == "# mine\n*\n"

    def test_a_gitignore_that_does_NOT_cover_the_store_is_not_mistaken_for_protection(
        self, tmp_path
    ):
        """The failure mode: a leftover `.gitignore` from scaffolding or an
        editor makes the guard think the job is done. `*.log` protects nothing,
        and treating the file's mere PRESENCE as an answer is how the guard
        silently does nothing in the one case it exists for."""
        repo = _init_repo(tmp_path / "dotfiles")
        home = os.path.join(repo, ".tausik-knowledge")
        os.makedirs(home)
        with open(os.path.join(home, ".gitignore"), "w", encoding="utf-8") as fh:
            fh.write("*.log\n")
        guard.assert_safe_knowledge_home(home, DB)
        guard.protect_home_in_git(home, DB)

        with open(os.path.join(home, DB), "w", encoding="utf-8") as fh:
            fh.write("every client this person has")
        _git("add", "-A", cwd=repo)
        staged = _git("diff", "--cached", "--name-only", cwd=repo).stdout
        assert DB not in staged, f"an unrelated .gitignore left the store stageable:\n{staged}"

    def test_the_other_rules_in_that_file_survive(self, tmp_path):
        """Appending, not replacing: the rules already there are somebody's."""
        repo = _init_repo(tmp_path / "dotfiles")
        home = os.path.join(repo, ".tausik-knowledge")
        os.makedirs(home)
        with open(os.path.join(home, ".gitignore"), "w", encoding="utf-8") as fh:
            fh.write("*.log\n")
        guard.assert_safe_knowledge_home(home, DB)
        guard.protect_home_in_git(home, DB)
        with open(os.path.join(home, ".gitignore"), encoding="utf-8") as fh:
            body = fh.read()
        assert "*.log" in body
        assert body.rstrip().endswith("*")


class TestAnAlreadyTrackedStoreIsRefused:
    """`.gitignore` does not untrack what is already indexed."""

    def test_it_refuses_and_names_the_situation(self, tmp_path):
        repo = _init_repo(tmp_path / "dotfiles")
        home = os.path.join(repo, ".tausik-knowledge")
        os.makedirs(home)
        db_path = os.path.join(home, DB)
        with open(db_path, "w", encoding="utf-8") as fh:
            fh.write("already leaked")
        _git("add", "-f", db_path, cwd=repo)

        guard.reset_cache()
        with pytest.raises(ServiceError) as e:
            guard.protect_home_in_git(home, DB)
        message = str(e.value)
        assert "ALREADY" in message
        assert "untrack" in message.lower()


class TestWhatIsCachedAndWhatIsDeliberatelyNot:
    """`knowledge_home()` is on essentially every shared-store operation, so the
    PATH verdict is cached. The GIT verdict is not, and that is the point."""

    def test_the_path_verdict_is_computed_once_per_resolved_home(self, tmp_path, monkeypatch):
        calls: list[str] = []
        real = guard._is_network_volume

        def counting(path):
            calls.append(path)
            return real(path)

        monkeypatch.setattr(guard, "_is_network_volume", counting)
        home = str(tmp_path / "kn")
        for _ in range(5):
            guard.assert_safe_knowledge_home(home, DB)
        assert len(calls) == 1, f"the path check ran {len(calls)} times"

    def test_a_directory_that_BECOMES_a_repository_is_still_protected(self, tmp_path):
        """The staleness bug this split exists to prevent. A long-lived MCP
        server is exactly the process that validates a location early and keeps
        running while the filesystem changes underneath it; a remembered "that
        was not a repository" would be the guard switching itself off."""
        home = tmp_path / "dotfiles" / ".tausik-knowledge"
        home.mkdir(parents=True)
        guard.assert_safe_knowledge_home(str(home), DB)
        guard.protect_home_in_git(str(home), DB)
        assert not (home / ".gitignore").exists()

        repo = _init_repo(tmp_path / "dotfiles")  # it is a repository NOW

        guard.assert_safe_knowledge_home(str(home), DB)  # cached path verdict
        guard.protect_home_in_git(str(home), DB)  # git verdict must be fresh
        with open(os.path.join(str(home), DB), "w", encoding="utf-8") as fh:
            fh.write("every client this person has")
        _git("add", "-A", cwd=repo)
        staged = _git("diff", "--cached", "--name-only", cwd=repo).stdout
        assert DB not in staged, f"the store was staged after the repo appeared:\n{staged}"

    def test_a_different_home_is_checked_separately(self, tmp_path, monkeypatch):
        """Caching must not be a way for a second, unsafe location to slip past."""
        guard.assert_safe_knowledge_home(str(tmp_path / "safe"), DB)
        with pytest.raises(ServiceError):
            guard.assert_safe_knowledge_home(str(tmp_path / "Dropbox" / "kn"), DB)


class TestGitBeingUnavailableIsNotAnAnswer:
    """AC7(в): "we could not ask" must not be reported as "there is no repo"."""

    def test_a_missing_git_does_not_produce_a_false_refusal(self, tmp_path, monkeypatch):
        def no_git(*a, **k):
            raise FileNotFoundError("git")

        monkeypatch.setattr(subprocess, "run", no_git)
        assert guard.assert_safe_knowledge_home(str(tmp_path / "kn"), DB)

    def test_no_gitignore_is_written_where_there_is_no_repository(self, tmp_path, monkeypatch):
        home = tmp_path / "kn"
        home.mkdir()

        def no_git(*a, **k):
            raise FileNotFoundError("git")

        monkeypatch.setattr(subprocess, "run", no_git)
        guard.assert_safe_knowledge_home(str(home), DB)
        guard.protect_home_in_git(str(home), DB)
        assert not (home / ".gitignore").exists()

    def test_protection_still_happens_without_git_on_the_path(self, tmp_path, monkeypatch):
        """The failure this prevents: "cannot run git" silently becoming "no
        repository here", which switches the protection off on exactly the
        machine least likely to notice."""
        repo = tmp_path / "dotfiles"
        (repo / ".git").mkdir(parents=True)
        home = repo / ".tausik-knowledge"
        home.mkdir()

        def no_git(*a, **k):
            raise FileNotFoundError("git")

        monkeypatch.setattr(subprocess, "run", no_git)
        guard.assert_safe_knowledge_home(str(home), DB)
        guard.protect_home_in_git(str(home), DB)
        assert (home / ".gitignore").read_text(encoding="utf-8").rstrip().endswith("*")


class TestTheStoreItselfGoesThroughTheGuard:
    """The wiring: a guard nothing calls is a guard that guards nothing."""

    def test_knowledge_home_refuses_a_synced_override(self, tmp_path, monkeypatch):
        monkeypatch.setenv("TAUSIK_HOME", str(tmp_path / "OneDrive" / "kn"))
        with pytest.raises(ServiceError):
            knowledge_db.knowledge_home()

    def test_opening_the_store_inside_a_repo_leaves_it_ignored(self, tmp_path, monkeypatch):
        repo = _init_repo(tmp_path / "dotfiles")
        monkeypatch.setenv("TAUSIK_HOME", os.path.join(repo, ".tausik-knowledge"))
        conn = knowledge_db.connect_knowledge_db(create=True)
        assert conn is not None
        conn.close()

        _git("add", "-A", cwd=repo)
        staged = _git("diff", "--cached", "--name-only", cwd=repo).stdout
        assert "knowledge.db" not in staged, f"opening the store left it stageable:\n{staged}"

    def test_a_read_only_check_creates_nothing(self, tmp_path, monkeypatch):
        """The laziness contract: someone who never asked for a shared store
        must not acquire a directory by running `status`."""
        repo = _init_repo(tmp_path / "dotfiles")
        home = os.path.join(repo, ".tausik-knowledge")
        monkeypatch.setenv("TAUSIK_HOME", home)
        assert knowledge_db.knowledge_db_exists() is False
        assert not os.path.exists(home), "a read path brought the home into being"
