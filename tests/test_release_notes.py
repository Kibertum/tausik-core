"""The release body links both whats-new pages (release-notes-language-policy-is-unstated)."""

from __future__ import annotations

import os
import sys
from types import SimpleNamespace

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

from project_cli_publish import cmd_publish  # noqa: E402
from release_notes import missing_links, whats_new_page  # noqa: E402

# The line the v1.9.0 GitHub Release carries, copied from it on 2026-09-23.
V190_LINE = (
    "Read before upgrading: **[What changed in 1.9](https://github.com/Kibertum/tausik-core/"
    "blob/main/docs/en/whats-new-1.9.md)** · **[Что изменилось в 1.9](https://github.com/"
    "Kibertum/tausik-core/blob/main/docs/ru/whats-new-1.9.md)**"
)


def test_the_published_1_9_body_passes():
    assert missing_links(V190_LINE, "1.9.0") == []


def test_a_body_without_the_russian_page_is_refused():
    body = V190_LINE.split(" · ")[0]
    assert missing_links(body, "v1.9.0") == ["docs/ru/whats-new-1.9.md"]


def test_the_page_is_named_by_major_minor():
    assert whats_new_page("1.10.2", "ru") == "docs/ru/whats-new-1.10.md"
    with pytest.raises(ValueError):
        whats_new_page("next", "en")


def _run(tmp_path, body):
    f = tmp_path / "body.md"
    f.write_text(body, encoding="utf-8")
    args = SimpleNamespace(publish_cmd="notes", version="1.9.0", body_file=str(f))
    cmd_publish(SimpleNamespace(tausik_dir=lambda: str(tmp_path / ".tausik")), args)


def test_the_cli_refuses_a_body_missing_a_page(tmp_path, capsys):
    with pytest.raises(SystemExit) as exc:
        _run(tmp_path, "notes without links")
    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert "REFUSED" in out and "docs/ru/whats-new-1.9.md" in out


def test_the_cli_accepts_a_body_with_both_pages(tmp_path, capsys):
    _run(tmp_path, V190_LINE)
    assert "OK" in capsys.readouterr().out


@pytest.mark.parametrize("lang", ["en", "ru"])
def test_the_procedure_states_the_rule_and_names_the_check(lang):
    with open(os.path.join(_ROOT, "docs", lang, "publishing.md"), encoding="utf-8") as f:
        text = f.read()
    assert "tausik publish notes --version" in text
    assert "whats-new-X.Y.md" in text
