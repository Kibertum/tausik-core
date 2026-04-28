"""Tests for scripts/brain_init.py — wizard + schemas + config merge."""

from __future__ import annotations

import sys
import os

import pytest

_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

import brain_init  # noqa: E402
from brain_notion_client import NotionError  # noqa: E402


@pytest.fixture(autouse=True)
def _isolated_registry(tmp_path, monkeypatch):
    """Redirect brain registry to a throwaway path so wizard tests don't touch ~."""
    monkeypatch.setenv("TAUSIK_BRAIN_REGISTRY", str(tmp_path / "brain_registry.json"))
    yield


# --- Schema tests ---------------------------------------------------------


def test_db_schema_decisions_shape():
    s = brain_init.db_schema("decisions")
    assert s["Name"] == {"title": {}}
    assert s["Context"] == {"rich_text": {}}
    assert s["Decision"] == {"rich_text": {}}
    assert s["Rationale"] == {"rich_text": {}}
    assert s["Tags"] == {"multi_select": {}}
    assert s["Stack"] == {"multi_select": {}}
    assert s["Date"] == {"date": {}}
    assert s["Source Project Hash"] == {"rich_text": {}}
    assert s["Generalizable"] == {"checkbox": {}}
    assert s["Superseded By"] == {"url": {}}


def test_db_schema_web_cache_has_number_ttl():
    s = brain_init.db_schema("web_cache")
    assert s["TTL Days"] == {"number": {"format": "number"}}
    assert s["URL"] == {"url": {}}
    assert s["Domain"] == {"select": {}}
    assert s["Content Hash"] == {"rich_text": {}}


def test_db_schema_patterns_has_confidence_options():
    s = brain_init.db_schema("patterns")
    opts = s["Confidence"]["select"]["options"]
    names = {o["name"] for o in opts}
    assert names == {"experimental", "tested", "proven"}


def test_db_schema_gotchas_has_severity_options():
    s = brain_init.db_schema("gotchas")
    opts = s["Severity"]["select"]["options"]
    names = {o["name"] for o in opts}
    assert names == {"low", "medium", "high"}
    assert s["Evidence URL"] == {"url": {}}
    assert s["Wrong Way"] == {"rich_text": {}}
    assert s["Right Way"] == {"rich_text": {}}


def test_db_schema_unknown_raises():
    with pytest.raises(ValueError):
        brain_init.db_schema("unknown_category")


def test_db_schema_returns_fresh_dict_each_call():
    """Mutation of the returned dict must not leak into subsequent calls."""
    s1 = brain_init.db_schema("decisions")
    s1["Tags"]["multi_select"]["contaminated"] = True
    s2 = brain_init.db_schema("decisions")
    assert "contaminated" not in s2["Tags"]["multi_select"]


# --- create_brain_databases tests -----------------------------------------


class _FakeClient:
    """Fake Notion client.

    `existing_dbs` — dict {category: db_id} of canonical-titled BRAIN
    databases that should be returned by search() (simulates a workspace
    that already has BRAIN configured). Default empty (clean workspace).

    `query_404` — set of db_ids that databases_query should raise
    NotionNotFoundError for (simulates verify failure).
    """

    def __init__(
        self,
        fail_category: str | None = None,
        existing_dbs: dict[str, str] | None = None,
        query_404: set[str] | None = None,
    ):
        self.calls: list[dict] = []
        self.search_calls: list[dict] = []
        self.query_calls: list[dict] = []
        self.fail_category = fail_category
        self.existing_dbs = existing_dbs or {}
        self.query_404 = query_404 or set()

    def databases_create(self, *, parent_page_id, title, properties):
        self.calls.append(
            {"parent_page_id": parent_page_id, "title": title, "properties": properties}
        )
        category = next(
            (c for c, t in brain_init.DB_TITLES.items() if t == title), None
        )
        if self.fail_category and category == self.fail_category:
            raise NotionError("boom", status=500, body={})
        return {"id": f"db_{category}_id", "title": title}

    def search(self, *, query=None, filter=None, start_cursor=None, page_size=None):
        self.search_calls.append({"query": query, "filter": filter})
        results = []
        for category, db_id in self.existing_dbs.items():
            title = brain_init.DB_TITLES[category]
            results.append(
                {
                    "object": "database",
                    "id": db_id,
                    "title": [{"type": "text", "plain_text": title}],
                    "archived": False,
                }
            )
        return {"results": results, "has_more": False, "next_cursor": None}

    def databases_query(
        self, db_id, *, filter=None, sorts=None, start_cursor=None, page_size=None
    ):
        self.query_calls.append({"db_id": db_id, "page_size": page_size})
        if db_id in self.query_404:
            from brain_notion_client import NotionNotFoundError

            raise NotionNotFoundError(f"db not found: {db_id}", status=404)
        return {"results": [], "has_more": False}


def test_create_brain_databases_creates_all_four():
    client = _FakeClient()
    ids = brain_init.create_brain_databases(client, "parent-page")
    assert len(client.calls) == 4
    assert set(ids.keys()) == {"decisions", "web_cache", "patterns", "gotchas"}
    assert ids["decisions"] == "db_decisions_id"
    assert ids["gotchas"] == "db_gotchas_id"


def test_create_brain_databases_sends_correct_schemas():
    client = _FakeClient()
    brain_init.create_brain_databases(client, "p1")
    titles = [c["title"] for c in client.calls]
    assert titles == [brain_init.DB_TITLES[c] for c in brain_init.CATEGORIES]


def test_partial_create_surfaces_created_ids():
    """B4 fix: failure on Nth category surfaces N-1 created ids on the exception."""
    # CATEGORIES order: decisions, web_cache, patterns, gotchas — fail on patterns
    client = _FakeClient(fail_category="patterns")
    with pytest.raises(brain_init.PartialCreateError) as ei:
        brain_init.create_brain_databases(client, "p1")
    err = ei.value
    assert err.created_ids == {
        "decisions": "db_decisions_id",
        "web_cache": "db_web_cache_id",
    }


def test_first_category_failure_raises_plain_notion_error():
    """If even the first databases_create fails, no PartialCreateError (no orphans)."""
    client = _FakeClient(fail_category="decisions")
    with pytest.raises(NotionError) as ei:
        brain_init.create_brain_databases(client, "p1")
    # Plain NotionError, not the partial subclass
    assert not isinstance(ei.value, brain_init.PartialCreateError)


def test_run_wizard_partial_create_prints_real_orphan_ids(monkeypatch):
    """End-to-end: run_wizard surfaces partial-create orphan ids in guidance."""
    monkeypatch.setenv("T", "tok")
    io = _FakeIO(is_tty=False)
    cfg_ops = _FakeConfigOps()

    def factory(_token):
        return _FakeClient(fail_category="patterns")

    with pytest.raises(brain_init.WizardError, match="partially failed"):
        brain_init.run_wizard(
            {
                "parent_page_id": "p1",
                "token_env": "T",
                "project_name": "x",
                "yes": True,
            },
            io,
            factory,
            cfg_ops,
        )
    combined = "\n".join(io.prints)
    # The two created ids must appear in cleanup guidance
    assert "db_decisions_id" in combined
    assert "db_web_cache_id" in combined
    # Categories that never landed must NOT show fake ids
    assert "db_patterns_id" not in combined
    assert "db_gotchas_id" not in combined


def test_create_brain_databases_empty_parent_raises():
    with pytest.raises(ValueError):
        brain_init.create_brain_databases(_FakeClient(), "")


def test_create_brain_databases_propagates_notion_error():
    client = _FakeClient(fail_category="patterns")
    with pytest.raises(NotionError):
        brain_init.create_brain_databases(client, "p1")
    # first two succeeded before the raise
    assert len(client.calls) == 3


# --- merge_brain_config tests ---------------------------------------------


def test_merge_brain_config_on_empty_cfg():
    result = brain_init.merge_brain_config(
        None, {"enabled": True, "database_ids": {"decisions": "d1"}}
    )
    assert result["brain"]["enabled"] is True
    assert result["brain"]["database_ids"] == {"decisions": "d1"}


def test_merge_brain_config_deep_merges_database_ids():
    existing = {
        "brain": {
            "enabled": True,
            "database_ids": {"decisions": "old1", "patterns": "pat"},
        },
        "other_section": {"keep": 1},
    }
    result = brain_init.merge_brain_config(
        existing, {"database_ids": {"decisions": "new1", "gotchas": "got"}}
    )
    assert result["brain"]["database_ids"] == {
        "decisions": "new1",  # overwritten
        "patterns": "pat",  # preserved
        "gotchas": "got",  # added
    }
    assert result["other_section"] == {"keep": 1}  # non-brain untouched


def test_merge_brain_config_skips_empty_db_ids():
    existing = {"brain": {"database_ids": {"decisions": "d_old"}}}
    result = brain_init.merge_brain_config(
        existing, {"database_ids": {"decisions": "", "patterns": "p_new"}}
    )
    assert result["brain"]["database_ids"] == {
        "decisions": "d_old",  # empty incoming value did NOT overwrite
        "patterns": "p_new",
    }


def test_merge_brain_config_does_not_mutate_input():
    existing = {"brain": {"enabled": False, "database_ids": {"decisions": "d1"}}}
    snapshot = {
        "brain": {"enabled": False, "database_ids": {"decisions": "d1"}},
    }
    brain_init.merge_brain_config(existing, {"enabled": True})
    assert existing == snapshot


def test_merge_brain_config_ignores_none_values():
    existing = {"brain": {"project_names": ["x"]}}
    result = brain_init.merge_brain_config(
        existing, {"project_names": None, "enabled": True}
    )
    assert result["brain"]["project_names"] == ["x"]
    assert result["brain"]["enabled"] is True


# --- run_wizard tests -----------------------------------------------------


class _FakeIO:
    def __init__(self, answers: list[str] | None = None, is_tty: bool = False):
        self._answers = list(answers or [])
        self.prints: list[str] = []
        self.is_tty = is_tty

    def prompt(self, msg: str) -> str:
        if not self._answers:
            raise AssertionError(f"Unexpected prompt: {msg!r}")
        return self._answers.pop(0)

    def print(self, msg: str) -> None:
        self.prints.append(msg)


class _FakeConfigOps:
    def __init__(self, initial: dict | None = None):
        self._cfg = initial or {}
        self.saved: list[dict] = []

    def load(self) -> dict:
        return self._cfg

    def save(self, cfg: dict) -> None:
        self.saved.append(cfg)
        self._cfg = cfg


def _client_factory(tokens: list[str]):
    def factory(token: str):
        tokens.append(token)
        return _FakeClient()

    return factory


def test_run_wizard_non_interactive_success(monkeypatch):
    monkeypatch.setenv("MY_TOKEN", "secret-token")
    io = _FakeIO(is_tty=False)
    cfg_ops = _FakeConfigOps()
    tokens: list[str] = []

    result = brain_init.run_wizard(
        {
            "parent_page_id": "page-abc",
            "token_env": "MY_TOKEN",
            "project_name": "test-proj",
            "yes": True,
        },
        io,
        _client_factory(tokens),
        cfg_ops,
    )

    assert tokens == ["secret-token"]
    assert result["database_ids"]["decisions"] == "db_decisions_id"
    saved = cfg_ops.saved[-1]
    assert saved["brain"]["enabled"] is True
    assert saved["brain"]["notion_integration_token_env"] == "MY_TOKEN"
    assert saved["brain"]["database_ids"]["gotchas"] == "db_gotchas_id"
    assert "test-proj" in saved["brain"]["project_names"]


def test_run_wizard_non_interactive_missing_parent_raises(monkeypatch):
    """v1.3.3: token must be set so the workspace pre-flight can run; parent
    is only required once we reach the create branch (clean workspace, no
    --join-existing, no --force-create)."""
    monkeypatch.setenv("X", "tok")
    io = _FakeIO(is_tty=False)
    cfg_ops = _FakeConfigOps()
    with pytest.raises(brain_init.WizardError, match="parent-page-id"):
        brain_init.run_wizard(
            {"token_env": "X", "yes": True},
            io,
            _client_factory([]),
            cfg_ops,
        )
    assert cfg_ops.saved == []


def test_run_wizard_token_env_not_set_raises(monkeypatch):
    monkeypatch.delenv("NOPE_TOKEN", raising=False)
    io = _FakeIO(is_tty=False)
    cfg_ops = _FakeConfigOps()
    with pytest.raises(brain_init.WizardError, match="NOPE_TOKEN"):
        brain_init.run_wizard(
            {
                "parent_page_id": "p1",
                "token_env": "NOPE_TOKEN",
                "project_name": "x",
                "yes": True,
            },
            io,
            _client_factory([]),
            cfg_ops,
        )


def test_run_wizard_already_configured_without_force_raises(monkeypatch):
    monkeypatch.setenv("T", "tok")
    io = _FakeIO(is_tty=False)
    cfg_ops = _FakeConfigOps(
        {"brain": {"enabled": True, "database_ids": {"decisions": "existing"}}}
    )
    with pytest.raises(brain_init.WizardError, match="already configured"):
        brain_init.run_wizard(
            {"parent_page_id": "p1", "token_env": "T", "yes": True},
            io,
            _client_factory([]),
            cfg_ops,
        )


def test_run_wizard_force_overwrites_existing(monkeypatch):
    monkeypatch.setenv("T", "tok")
    io = _FakeIO(is_tty=False)
    cfg_ops = _FakeConfigOps(
        {"brain": {"enabled": True, "database_ids": {"decisions": "old"}}}
    )
    brain_init.run_wizard(
        {
            "parent_page_id": "p1",
            "token_env": "T",
            "project_name": "ovr",
            "yes": True,
            "force": True,
        },
        io,
        _client_factory([]),
        cfg_ops,
    )
    saved = cfg_ops.saved[-1]
    # deep merge keeps old value if new is empty, but _FakeClient returns non-empty
    # so new values win
    assert saved["brain"]["database_ids"]["decisions"] == "db_decisions_id"


def test_run_wizard_interactive_prompts_for_missing_fields(monkeypatch):
    """v1.3.3 prompt order: token_env first (needed for workspace search),
    then parent_page_id (only if create branch reached), then project_name,
    then confirm."""
    monkeypatch.setenv("NOTION_TAUSIK_TOKEN", "tok")
    io = _FakeIO(
        answers=[
            "",  # token_env (accept default)
            "page-xyz",  # parent_page_id
            "",  # project_name (accept default)
            "y",  # confirm
        ],
        is_tty=True,
    )
    cfg_ops = _FakeConfigOps()
    result = brain_init.run_wizard(
        {},  # no args — force interactive to drive everything
        io,
        _client_factory([]),
        cfg_ops,
    )
    assert result["parent_page_id"] == "page-xyz"
    assert result["token_env"] == "NOTION_TAUSIK_TOKEN"
    assert cfg_ops.saved  # saved was called


def test_run_wizard_interactive_abort(monkeypatch):
    monkeypatch.setenv("NOTION_TAUSIK_TOKEN", "tok")
    io = _FakeIO(
        answers=["", "page-xyz", "", "n"],  # token, parent, project, abort
        is_tty=True,
    )
    cfg_ops = _FakeConfigOps()
    with pytest.raises(brain_init.WizardError, match="Aborted"):
        brain_init.run_wizard({}, io, _client_factory([]), cfg_ops)
    assert cfg_ops.saved == []


def test_run_wizard_notion_api_error_bubbles_as_wizard_error(monkeypatch):
    monkeypatch.setenv("T", "tok")
    io = _FakeIO(is_tty=False)
    cfg_ops = _FakeConfigOps()

    def failing_factory(_token):
        return _FakeClient(fail_category="decisions")

    with pytest.raises(brain_init.WizardError, match="databases_create failed"):
        brain_init.run_wizard(
            {
                "parent_page_id": "p1",
                "token_env": "T",
                "project_name": "x",
                "yes": True,
            },
            io,
            failing_factory,
            cfg_ops,
        )
    assert cfg_ops.saved == []


def test_run_wizard_appends_project_name_preserving_existing(monkeypatch):
    monkeypatch.setenv("T", "tok")
    io = _FakeIO(is_tty=False)
    cfg_ops = _FakeConfigOps({"brain": {"project_names": ["old-proj"]}})
    brain_init.run_wizard(
        {
            "parent_page_id": "p1",
            "token_env": "T",
            "project_name": "new-proj",
            "yes": True,
        },
        io,
        _client_factory([]),
        cfg_ops,
    )
    saved = cfg_ops.saved[-1]
    assert saved["brain"]["project_names"] == ["old-proj", "new-proj"]


def test_run_wizard_token_never_persisted(monkeypatch):
    """Regression: the token value must NEVER be written to config (only its env-var name)."""
    monkeypatch.setenv("SUPER_SECRET", "do-not-leak")
    io = _FakeIO(is_tty=False)
    cfg_ops = _FakeConfigOps()
    brain_init.run_wizard(
        {
            "parent_page_id": "p1",
            "token_env": "SUPER_SECRET",
            "project_name": "x",
            "yes": True,
        },
        io,
        _client_factory([]),
        cfg_ops,
    )
    import json

    blob = json.dumps(cfg_ops.saved[-1])
    assert "do-not-leak" not in blob
    assert "SUPER_SECRET" in blob


# --- Orphan cleanup guidance (brain-init-orphan-cleanup) -----------------


def _assert_orphan_guidance_printed(io, db_ids: dict) -> None:
    """Every created db_id must appear in io.prints, with cleanup framing."""
    combined = "\n".join(io.prints)
    assert "orphan" in combined.lower() or "Archive" in combined, combined
    for category, db_id in db_ids.items():
        assert db_id in combined, f"{category}={db_id} not in output: {combined}"


def test_run_wizard_registry_failure_prints_orphan_guidance(monkeypatch):
    """register_project raises after databases are created → orphan guidance."""
    monkeypatch.setenv("T", "tok")
    io = _FakeIO(is_tty=False)
    cfg_ops = _FakeConfigOps()

    def boom(*_a, **_kw):
        raise brain_init.brain_project_registry.RegistryLockError("locked by pid 42")

    monkeypatch.setattr(brain_init.brain_project_registry, "register_project", boom)

    with pytest.raises(brain_init.WizardError, match="Post-create step failed"):
        brain_init.run_wizard(
            {
                "parent_page_id": "p1",
                "token_env": "T",
                "project_name": "x",
                "yes": True,
            },
            io,
            _client_factory([]),
            cfg_ops,
        )

    assert cfg_ops.saved == []
    _assert_orphan_guidance_printed(
        io,
        {
            "decisions": "db_decisions_id",
            "web_cache": "db_web_cache_id",
            "patterns": "db_patterns_id",
            "gotchas": "db_gotchas_id",
        },
    )


def test_run_wizard_config_save_failure_prints_orphan_guidance(monkeypatch):
    """config_ops.save raises after register → orphan guidance, all 4 db_ids printed."""
    monkeypatch.setenv("T", "tok")
    io = _FakeIO(is_tty=False)

    class FailingSaveConfigOps(_FakeConfigOps):
        def save(self, cfg):
            raise OSError("disk full")

    cfg_ops = FailingSaveConfigOps()

    with pytest.raises(brain_init.WizardError, match="Post-create step failed"):
        brain_init.run_wizard(
            {
                "parent_page_id": "p1",
                "token_env": "T",
                "project_name": "x",
                "yes": True,
            },
            io,
            _client_factory([]),
            cfg_ops,
        )

    _assert_orphan_guidance_printed(
        io,
        {
            "decisions": "db_decisions_id",
            "web_cache": "db_web_cache_id",
            "patterns": "db_patterns_id",
            "gotchas": "db_gotchas_id",
        },
    )


# --- CliIO EOF / KeyboardInterrupt handling (brain-init-input-error-handling) ---


class TestCliIOPrompt:
    """Default CliIO turns input() failures into clean WizardError aborts."""

    def test_returns_input_normally(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda _msg: "page-xyz")
        io = brain_init.CliIO()
        assert io.prompt("Notion parent page id: ") == "page-xyz"

    def test_eof_raises_wizard_error(self, monkeypatch):
        def boom(_msg):
            raise EOFError()

        monkeypatch.setattr("builtins.input", boom)
        io = brain_init.CliIO()
        with pytest.raises(brain_init.WizardError, match="no input available"):
            io.prompt("anything: ")

    def test_keyboard_interrupt_raises_wizard_error(self, monkeypatch):
        def boom(_msg):
            raise KeyboardInterrupt()

        monkeypatch.setattr("builtins.input", boom)
        io = brain_init.CliIO()
        with pytest.raises(brain_init.WizardError, match="Ctrl\\+C"):
            io.prompt("anything: ")

    def test_eof_and_ctrl_c_messages_distinct(self, monkeypatch):
        """B5: each exception type emits its own diagnostic wording."""

        def eof(_msg):
            raise EOFError()

        monkeypatch.setattr("builtins.input", eof)
        try:
            brain_init.CliIO().prompt("x")
        except brain_init.WizardError as e:
            eof_msg = str(e)
        assert "stdin" in eof_msg

        def ctrl_c(_msg):
            raise KeyboardInterrupt()

        monkeypatch.setattr("builtins.input", ctrl_c)
        try:
            brain_init.CliIO().prompt("x")
        except brain_init.WizardError as e:
            kbi_msg = str(e)
        assert "Ctrl+C" in kbi_msg
        assert eof_msg != kbi_msg


def test_run_wizard_happy_path_prints_no_orphan_guidance(monkeypatch):
    """Regression: happy path must NOT print orphan warning."""
    monkeypatch.setenv("T", "tok")
    io = _FakeIO(is_tty=False)
    cfg_ops = _FakeConfigOps()

    brain_init.run_wizard(
        {
            "parent_page_id": "p1",
            "token_env": "T",
            "project_name": "x",
            "yes": True,
        },
        io,
        _client_factory([]),
        cfg_ops,
    )
    combined = "\n".join(io.prints).lower()
    assert "orphan" not in combined
    assert "archive" not in combined


# --- v1.3.3 anti-hallucination guards ------------------------------------


def test_find_workspace_brain_databases_empty_workspace():
    """Clean workspace → search returns no canonical BRAIN databases."""
    client = _FakeClient()
    found = brain_init.find_workspace_brain_databases(client)
    assert found == {}


def test_find_workspace_brain_databases_full_match():
    """All 4 canonical-titled BRAIN databases present → all 4 categories returned."""
    client = _FakeClient(
        existing_dbs={
            "decisions": "ws-dec",
            "web_cache": "ws-wc",
            "patterns": "ws-pat",
            "gotchas": "ws-got",
        }
    )
    found = brain_init.find_workspace_brain_databases(client)
    assert found == {
        "decisions": "ws-dec",
        "web_cache": "ws-wc",
        "patterns": "ws-pat",
        "gotchas": "ws-got",
    }


def test_find_workspace_brain_databases_partial_match():
    """Only some canonical-titled databases exist → return just those."""
    client = _FakeClient(existing_dbs={"decisions": "ws-dec", "patterns": "ws-pat"})
    found = brain_init.find_workspace_brain_databases(client)
    assert found == {"decisions": "ws-dec", "patterns": "ws-pat"}


def test_find_workspace_brain_databases_skips_archived():
    """Archived databases must NOT count as existing."""

    class _ArchivedClient(_FakeClient):
        def search(self, **_kw):
            return {
                "results": [
                    {
                        "object": "database",
                        "id": "ws-dec",
                        "title": [
                            {
                                "type": "text",
                                "plain_text": brain_init.DB_TITLES["decisions"],
                            }
                        ],
                        "archived": True,
                    }
                ],
                "has_more": False,
                "next_cursor": None,
            }

    found = brain_init.find_workspace_brain_databases(_ArchivedClient())
    assert found == {}


def test_find_workspace_brain_databases_ignores_non_canonical_titles():
    """Databases titled e.g. 'My Brain' or 'Brain Notes' must NOT match."""

    class _NonCanonicalClient(_FakeClient):
        def search(self, **_kw):
            return {
                "results": [
                    {
                        "object": "database",
                        "id": "x1",
                        "title": [{"type": "text", "plain_text": "My Brain"}],
                        "archived": False,
                    },
                    {
                        "object": "database",
                        "id": "x2",
                        "title": [{"type": "text", "plain_text": "Brain Notes"}],
                        "archived": False,
                    },
                ],
                "has_more": False,
                "next_cursor": None,
            }

    found = brain_init.find_workspace_brain_databases(_NonCanonicalClient())
    assert found == {}


def test_verify_brain_databases_all_ok():
    client = _FakeClient()
    errors = brain_init.verify_brain_databases(
        client,
        {"decisions": "d", "web_cache": "w", "patterns": "p", "gotchas": "g"},
    )
    assert errors == {}


def test_verify_brain_databases_missing_id():
    client = _FakeClient()
    errors = brain_init.verify_brain_databases(
        client,
        {"decisions": "d", "web_cache": "", "patterns": "p", "gotchas": "g"},
    )
    assert "web_cache" in errors


def test_verify_brain_databases_404_id():
    client = _FakeClient(query_404={"bad-id"})
    errors = brain_init.verify_brain_databases(
        client,
        {"decisions": "d", "web_cache": "bad-id", "patterns": "p", "gotchas": "g"},
    )
    assert "web_cache" in errors
    assert "not found" in errors["web_cache"]


def test_run_wizard_refuses_when_full_workspace_match_no_force_create(monkeypatch):
    """Pre-flight guard: full canonical match in workspace → refuse + suggest --join-existing."""
    monkeypatch.setenv("T", "tok")
    io = _FakeIO(is_tty=False)
    cfg_ops = _FakeConfigOps()

    def factory(_token):
        return _FakeClient(
            existing_dbs={
                "decisions": "ws-dec",
                "web_cache": "ws-wc",
                "patterns": "ws-pat",
                "gotchas": "ws-got",
            }
        )

    with pytest.raises(brain_init.WizardError, match="--join-existing"):
        brain_init.run_wizard(
            {
                "parent_page_id": "p1",
                "token_env": "T",
                "project_name": "x",
                "yes": True,
            },
            io,
            factory,
            cfg_ops,
        )
    assert cfg_ops.saved == []


def test_run_wizard_refuses_partial_match_workspace(monkeypatch):
    """Partial canonical match (1-3 of 4) → refuse, ambiguous state."""
    monkeypatch.setenv("T", "tok")
    io = _FakeIO(is_tty=False)
    cfg_ops = _FakeConfigOps()

    def factory(_token):
        return _FakeClient(existing_dbs={"decisions": "d", "patterns": "p"})

    with pytest.raises(brain_init.WizardError, match="partial set"):
        brain_init.run_wizard(
            {
                "parent_page_id": "p1",
                "token_env": "T",
                "project_name": "x",
                "yes": True,
            },
            io,
            factory,
            cfg_ops,
        )
    assert cfg_ops.saved == []


def test_run_wizard_force_create_overrides_full_match(monkeypatch):
    """--force-create bypasses the pre-flight guard, creates new DBs."""
    monkeypatch.setenv("T", "tok")
    io = _FakeIO(is_tty=False)
    cfg_ops = _FakeConfigOps()
    fake = _FakeClient(
        existing_dbs={
            "decisions": "ws-dec",
            "web_cache": "ws-wc",
            "patterns": "ws-pat",
            "gotchas": "ws-got",
        }
    )

    def factory(_token):
        return fake

    result = brain_init.run_wizard(
        {
            "parent_page_id": "p1",
            "token_env": "T",
            "project_name": "x",
            "yes": True,
            "force_create": True,
        },
        io,
        factory,
        cfg_ops,
    )
    assert result["mode"] == "create"
    # databases_create was called 4 times (NOT skipped)
    assert len(fake.calls) == 4
    # New ids were saved (not the existing workspace ids)
    saved = cfg_ops.saved[-1]
    assert saved["brain"]["database_ids"]["decisions"] == "db_decisions_id"


def test_run_wizard_join_existing_auto_discovers_workspace(monkeypatch):
    """--join-existing with no explicit ids → wizard finds them via search."""
    monkeypatch.setenv("T", "tok")
    io = _FakeIO(is_tty=False)
    cfg_ops = _FakeConfigOps()
    fake = _FakeClient(
        existing_dbs={
            "decisions": "ws-dec",
            "web_cache": "ws-wc",
            "patterns": "ws-pat",
            "gotchas": "ws-got",
        }
    )

    def factory(_token):
        return fake

    result = brain_init.run_wizard(
        {
            "token_env": "T",
            "project_name": "second-proj",
            "yes": True,
            "join_existing": True,
        },
        io,
        factory,
        cfg_ops,
    )
    assert result["mode"] == "join"
    # No databases_create calls — we joined, not created
    assert fake.calls == []
    saved = cfg_ops.saved[-1]
    assert saved["brain"]["database_ids"] == {
        "decisions": "ws-dec",
        "web_cache": "ws-wc",
        "patterns": "ws-pat",
        "gotchas": "ws-got",
    }
    assert "second-proj" in saved["brain"]["project_names"]


def test_run_wizard_join_existing_with_explicit_ids(monkeypatch):
    """--join-existing with all 4 explicit ids skips search; uses provided ids verbatim."""
    monkeypatch.setenv("T", "tok")
    io = _FakeIO(is_tty=False)
    cfg_ops = _FakeConfigOps()
    fake = _FakeClient()  # empty workspace, but explicit ids should override

    def factory(_token):
        return fake

    result = brain_init.run_wizard(
        {
            "token_env": "T",
            "project_name": "p",
            "yes": True,
            "join_existing": True,
            "decisions_id": "ex-dec",
            "web_cache_id": "ex-wc",
            "patterns_id": "ex-pat",
            "gotchas_id": "ex-got",
        },
        io,
        factory,
        cfg_ops,
    )
    assert result["mode"] == "join"
    # Pre-flight skipped because all 4 explicit ids supplied
    assert fake.search_calls == []
    # Verify was called for each id
    queried = {c["db_id"] for c in fake.query_calls}
    assert queried == {"ex-dec", "ex-wc", "ex-pat", "ex-got"}
    saved = cfg_ops.saved[-1]
    assert saved["brain"]["database_ids"]["decisions"] == "ex-dec"


def test_run_wizard_join_existing_explicit_overrides_discovered(monkeypatch):
    """When both explicit and discovered ids exist, explicit wins."""
    monkeypatch.setenv("T", "tok")
    io = _FakeIO(is_tty=False)
    cfg_ops = _FakeConfigOps()
    fake = _FakeClient(
        existing_dbs={
            "decisions": "ws-dec",
            "web_cache": "ws-wc",
            "patterns": "ws-pat",
            "gotchas": "ws-got",
        }
    )

    def factory(_token):
        return fake

    brain_init.run_wizard(
        {
            "token_env": "T",
            "project_name": "p",
            "yes": True,
            "join_existing": True,
            "decisions_id": "explicit-dec",  # only override decisions
        },
        io,
        factory,
        cfg_ops,
    )
    saved = cfg_ops.saved[-1]
    assert saved["brain"]["database_ids"]["decisions"] == "explicit-dec"
    # Other 3 came from auto-discovery
    assert saved["brain"]["database_ids"]["web_cache"] == "ws-wc"


def test_run_wizard_join_existing_fails_when_no_ids_resolvable(monkeypatch):
    """--join-existing on empty workspace + no explicit ids → clear error."""
    monkeypatch.setenv("T", "tok")
    io = _FakeIO(is_tty=False)
    cfg_ops = _FakeConfigOps()

    def factory(_token):
        return _FakeClient()  # empty

    with pytest.raises(brain_init.WizardError, match="could not resolve"):
        brain_init.run_wizard(
            {
                "token_env": "T",
                "yes": True,
                "join_existing": True,
            },
            io,
            factory,
            cfg_ops,
        )
    assert cfg_ops.saved == []


def test_run_wizard_join_existing_fails_when_id_404(monkeypatch):
    """--join-existing with bad id → verify catches it before save."""
    monkeypatch.setenv("T", "tok")
    io = _FakeIO(is_tty=False)
    cfg_ops = _FakeConfigOps()

    def factory(_token):
        return _FakeClient(query_404={"ex-pat"})

    with pytest.raises(brain_init.WizardError, match="verification failed"):
        brain_init.run_wizard(
            {
                "token_env": "T",
                "yes": True,
                "join_existing": True,
                "decisions_id": "ex-dec",
                "web_cache_id": "ex-wc",
                "patterns_id": "ex-pat",
                "gotchas_id": "ex-got",
            },
            io,
            factory,
            cfg_ops,
        )
    assert cfg_ops.saved == []


def test_run_wizard_clean_workspace_creates_normally(monkeypatch):
    """Empty workspace → pre-flight finds nothing → create proceeds (no regression)."""
    monkeypatch.setenv("T", "tok")
    io = _FakeIO(is_tty=False)
    cfg_ops = _FakeConfigOps()
    fake = _FakeClient()  # empty

    def factory(_token):
        return fake

    result = brain_init.run_wizard(
        {
            "parent_page_id": "p1",
            "token_env": "T",
            "project_name": "x",
            "yes": True,
        },
        io,
        factory,
        cfg_ops,
    )
    assert result["mode"] == "create"
    assert len(fake.calls) == 4
    # Pre-flight search was performed (proves the guard ran but found nothing)
    assert fake.search_calls != []


def test_run_wizard_search_failure_logged_then_proceeds(monkeypatch):
    """If workspace search fails, wizard prints warning and proceeds (defensive)."""
    monkeypatch.setenv("T", "tok")
    io = _FakeIO(is_tty=False)
    cfg_ops = _FakeConfigOps()

    class _SearchFailClient(_FakeClient):
        def search(self, **_kw):
            raise NotionError("network down", status=None)

    def factory(_token):
        return _SearchFailClient()

    result = brain_init.run_wizard(
        {
            "parent_page_id": "p1",
            "token_env": "T",
            "project_name": "x",
            "yes": True,
        },
        io,
        factory,
        cfg_ops,
    )
    assert result["mode"] == "create"
    combined = "\n".join(io.prints).lower()
    assert "search failed" in combined or "skipping" in combined
