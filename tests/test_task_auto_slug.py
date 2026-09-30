"""A Russian title gives a meaningful slug, and a hopeless one is refused
(task-quick-slugifier-drops-cyrillic-and-yields-deg)."""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from project_backend import SQLiteBackend
from project_service import ProjectService
from tausik_utils import ServiceError, slugify, task_slug_from_title


@pytest.mark.parametrize(
    "title,expected",
    [
        (
            "Комментарий храповика в gates.json цитирует тест",
            "kommentariy-hrapovika-v-gates-json-tsitiruet-test",
        ),
        ("Гейт рамок не видит записи через heredoc", "geyt-ramok-ne-vidit-zapisi-cherez-heredoc"),
        ("Fix the parser", "fix-the-parser"),
    ],
)
def test_a_title_in_any_script_gives_a_slug_that_reads_like_it(title, expected):
    assert task_slug_from_title(title) == expected


@pytest.mark.parametrize("title", ["!!!", "—", "🚀", "a"])
def test_a_title_with_nothing_usable_is_refused_not_stubbed(title):
    assert slugify(title) != "task"  # the old silent stub
    with pytest.raises(ServiceError, match="--slug"):
        task_slug_from_title(title)


def test_the_long_title_is_cut_on_a_word_boundary():
    slug = task_slug_from_title("Очень длинный заголовок задачи " * 5)
    assert len(slug) <= 50 and not slug.endswith("-")


def test_task_quick_uses_the_transliterated_slug(tmp_path):
    svc = ProjectService(SQLiteBackend(str(tmp_path / "q.db")))
    try:
        svc.task_quick("Гейт рамок не видит записи")
        assert svc.be.task_get("geyt-ramok-ne-vidit-zapisi") is not None
        with pytest.raises(ServiceError, match="--slug"):
            svc.task_quick("!!!")
    finally:
        svc.be.close()
