"""Smoke test for `tausik skill ...` CLI: help consistency + friendly errors.

Covers v14-skill-cli-help-pass: every help text reads as a noun phrase, every
negative scenario (unknown skill / repo / URL) prints `Error: ...` to stderr
and exits non-zero — no Python traceback in user-facing output.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

# v14b-pytest-fast-lane: every assertion spawns the tausik CLI subprocess.
pytestmark = pytest.mark.slow

REPO = Path(__file__).resolve().parents[1]
PYTHON = REPO / ".tausik" / "venv" / "Scripts" / "python.exe"
if not PYTHON.is_file():
    # Linux/macOS layout
    PYTHON = REPO / ".tausik" / "venv" / "bin" / "python"
PROJECT_PY = REPO / "scripts" / "project.py"

sys.path.insert(0, str(REPO / "scripts"))
import project_config  # noqa: E402  — читается ПОСЛЕ вставки scripts/ в путь

# Инвариантная голова отказа «команда запущена вне проекта». Берётся ИЗ
# продукта, а не переписывается литералом: если формулировку поменяют, страж
# ниже поедет за ней сам и не превратится в проверку музейного текста.
PROJECT_MISSING_HEAD = project_config.project_missing_message("<handle>").split(":", 1)[0]


def _run(args: list[str], cwd: Path = REPO) -> subprocess.CompletedProcess:
    return subprocess.run(
        [str(PYTHON), str(PROJECT_PY), *args],
        cwd=str(cwd),
        capture_output=True,
        text=True, encoding="utf-8",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    """Настоящий пустой проект TAUSIK в tmp_path.

    Негативные сценарии ниже спрашивают, что отвечает СЛОЙ SKILL. Чтобы вопрос
    вообще дошёл до него, нужен проект: `assert_project_exists` отказывает
    раньше и своими словами. Ровно на этом тесты и сломались — гейт приехал
    2026-08-12 (b487f87), тесты правились 2026-07-20, и тринадцать дней они
    проверяли чужой отказ, потому что помечены `slow` и в ленту по умолчанию
    не попадают.

    `init` — единственная команда, которой позволено создать проект, поэтому
    подготовка идёт через публичный вход, а не раскладыванием файлов руками.
    """
    r = _run(["init"], cwd=tmp_path)
    assert r.returncode == 0, f"`tausik init` в tmp_path не отработал: {r.stderr}"
    assert (tmp_path / ".tausik").is_dir(), "init не создал .tausik в tmp_path"
    return tmp_path


def _assert_refusal_came_from_the_skill_layer(r: subprocess.CompletedProcess) -> None:
    """Отказ обязан быть про навык, а не про отсутствие проекта.

    Без этого утверждения любой отказ, пришедший СЛОЕМ РАНЬШЕ, читается как
    успех проверки: `Error: ` печатают оба, и тест остаётся зелёным, ничего не
    проверяя. Именно так и жил test_activate_unknown_skill.
    """
    assert "Traceback" not in r.stderr
    assert r.stderr.startswith("Error: ")
    assert PROJECT_MISSING_HEAD not in r.stderr, (
        "отказ пришёл не со слоя skill, а с проверки существования проекта — "
        f"тест снова ничего не проверяет:\n{r.stderr}"
    )


class TestSkillHelpConsistency:
    def test_skill_help_lists_subcommands(self):
        r = _run(["skill", "--help"])
        assert r.returncode == 0
        for sub in ("activate", "deactivate", "list", "install", "uninstall", "repo"):
            assert sub in r.stdout, f"`tausik skill --help` missing '{sub}'"

    def test_repo_help_lists_subcommands(self):
        r = _run(["skill", "repo", "--help"])
        assert r.returncode == 0
        for sub in ("add", "remove", "list"):
            assert sub in r.stdout, f"`tausik skill repo --help` missing '{sub}'"


class TestSkillNegativeExitCode:
    """Negative scenarios must print friendly `Error: ...` and exit 1, not a traceback.

    Каждый тест утверждает СОДЕРЖАНИЕ отказа — имя навыка, подсказку по
    исправлению — и отдельно то, что отказ пришёл с нужного слоя. Второе так же
    обязательно, как первое: проверка на один префикс `Error: ` удовлетворяется
    любым отказом любого слоя и потому не является проверкой.
    """

    def test_install_unknown_skill(self, project):
        r = _run(["skill", "install", "nonexistent-skill-xyz"], cwd=project)
        assert r.returncode == 1
        _assert_refusal_came_from_the_skill_layer(r)
        assert "nonexistent-skill-xyz" in r.stderr

    def test_repo_add_untrusted_url(self, project):
        r = _run(["skill", "repo", "add", "https://example.com/foo.git"], cwd=project)
        assert r.returncode == 1
        _assert_refusal_came_from_the_skill_layer(r)
        assert "--force" in r.stderr  # remediation hint

    def test_activate_unknown_skill(self, project):
        r = _run(["skill", "activate", "nonexistent-skill-xyz"], cwd=project)
        assert r.returncode == 1
        _assert_refusal_came_from_the_skill_layer(r)
        # Раньше здесь стоял только префикс `Error: `, и тест был зелёным
        # тринадцать дней подряд на отказе «здесь нет проекта». Имя навыка —
        # то, ради чего сценарий написан.
        assert "nonexistent-skill-xyz" in r.stderr
