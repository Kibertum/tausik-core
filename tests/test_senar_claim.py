"""The SENAR claim names the edition, discloses what it must, and waits for the
edition to be public before a release (senar-claim-names-the-published-edition)."""

from __future__ import annotations

import os
import sys
from types import SimpleNamespace

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

import senar_claim as sc  # noqa: E402
from project_cli_publish import cmd_publish  # noqa: E402
from senar_standard_drift import corpus_root, released_versions  # noqa: E402

CROSSCUTTING_SCOPE = ["README.md", "README.ru.md", "CLAUDE.md", "docs/ru/agent-contract.md"]
PLACES = ["README.md", "README.ru.md", "CLAUDE.md", "docs/ru/agent-contract.md"]


def _read(rel):
    with open(os.path.join(_ROOT, rel), encoding="utf-8") as f:
        return f.read()


@pytest.mark.parametrize("rel", PLACES)
def test_the_claim_is_stated_verbatim_in_every_place(rel):
    assert sc.claim_sentence() in _read(rel)


def test_the_claimed_edition_is_what_the_corpus_released():
    root = corpus_root()
    if root is None:
        pytest.skip("no SENAR corpus configured on this machine (senar_standard_corpus)")
    assert sc.claim_sentence().split("SENAR v", 1)[1].split(" ", 1)[0] in released_versions(root)


@pytest.mark.parametrize("rel,lang", [("README.md", "en"), ("README.ru.md", "ru")])
def test_the_readme_discloses_with_the_claim(rel, lang):
    assert sc.missing_disclosures(_read(rel), lang) == []


def test_a_record_the_readme_does_not_carry_is_a_finding(monkeypatch):
    monkeypatch.setattr(sc, "NONCONFORMITIES", [{"clause": "Rule 5 (SENAR Core)"}])
    assert sc.missing_disclosures(_read("README.md"), "en") == ["Rule 5 (SENAR Core)"]


def test_published_needs_the_tag_of_the_claimed_edition():
    assert sc.published("1.5", lambda _u: ["v1.3", "v1.3^{}"])[0] == "not-published"
    assert sc.published("1.5", lambda _u: ["v1.3", "v1.5"])[0] == "published"
    assert sc.published("1.5", lambda _u: ["v1.5.0"])[0] == "published"
    assert sc.published("1.5", lambda _u: ["v1.50"])[0] == "not-published"


def test_no_network_is_not_verified_never_published():
    def down(_u):
        raise OSError("could not resolve host")

    status, detail = sc.published("1.5", down)
    assert status == "not-verified" and "resolve host" in detail


def test_the_refusal_names_both_versions_and_the_releases_link():
    msg = sc.check_message("not-published", "tags on GitHub: v1.3 (newest v1.3)", "1.5")
    assert msg.startswith("REFUSED") and "v1.5" in msg and "v1.3" in msg
    assert sc.SENAR_RELEASES in msg
    assert sc.check_message("not-verified", "OSError", "1.5").startswith("NOT VERIFIED")


@pytest.mark.parametrize(
    "tags,code", [(["v1.3"], 1), (None, 2), (["v1.3", "v" + sc.DECLARED_SENAR_VERSION], 0)]
)
def test_the_release_step_exits_by_the_answer(monkeypatch, capsys, tags, code):
    def lister(_u):
        if tags is None:
            raise OSError("offline")
        return tags

    monkeypatch.setattr(sc, "_git_tags", lister)
    monkeypatch.setattr(sc.published, "__defaults__", (sc.DECLARED_SENAR_VERSION, lister))
    args = SimpleNamespace(publish_cmd="senar-check")
    if code:
        with pytest.raises(SystemExit) as exc:
            cmd_publish(SimpleNamespace(tausik_dir=lambda: "."), args)
        assert exc.value.code == code
    else:
        cmd_publish(SimpleNamespace(tausik_dir=lambda: "."), args)
    assert sc.SENAR_RELEASES in capsys.readouterr().out or code == 0


@pytest.mark.parametrize("lang", ["en", "ru"])
def test_the_release_procedure_runs_the_check(lang):
    assert "tausik publish senar-check" in _read(f"docs/{lang}/publishing.md")
