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
    def __init__(self, fail_category: str | None = None):
        self.calls: list[dict] = []
        self.fail_category = fail_category

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


def test_run_wizard_non_interactive_missing_parent_raises():
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
    monkeypatch.setenv("NOTION_TAUSIK_TOKEN", "tok")
    io = _FakeIO(
        answers=[
            "page-xyz",  # parent_page_id
            "",  # token_env (accept default)
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
        answers=["page-xyz", "", "", "n"],  # final "n" aborts
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
