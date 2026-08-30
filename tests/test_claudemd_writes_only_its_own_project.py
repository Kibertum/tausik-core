"""Обновление CLAUDE.md пишет в проект СВОЕЙ базы, а не туда, где стоит процесс.

claudemd-dynamic-block-wiped-to-an-empty-project. Обе точки записи — обработчик
MCP `tausik_update_claudemd` и команда CLI `update-claudemd` — брали АДРЕС из
`os.getcwd()`, а СОДЕРЖИМОЕ из переданного `svc`. Два источника вместо одного.
Пока процесс стоит в своём проекте, они совпадают; когда не совпадают, состояние
ЧУЖОЙ базы уезжает в НАСТОЯЩИЕ файлы репозитория.

Так и происходило, и это замерено, а не выведено: аудит-хук на событие `open`
поймал ровно две записи на всю ленту из 7452 тестов (CLAUDE.md и AGENTS.md, один
pid), и стек назвал `tests/test_mcp_integration.py::test_every_tool_name_has_handler` —
контрактный тест, который поднимает ВРЕМЕННЫЙ проект и зовёт каждый инструмент
MCP при cwd в корне репозитория. Блок переписывался на «Tasks: 0/1 done» с
полностью снесённым хвостом памяти и попал в ДВАДЦАТЬ коммитов между релизом
v1.0.0 и 2026-08. Тест-виновник честен: дефект был в продукте.

ПОЧЕМУ ЗДЕСЬ ПОДСТАВНОЙ КАТАЛОГ, А НЕ НАСТОЯЩИЙ КОРЕНЬ. Тест обязан утверждать
«чужой проект не тронут», и проверять это на живом репозитории значит завести
регрессионный тест, который при провале ПОРТИТ дерево — под `-n auto` ещё и на
глазах у остальных воркеров. Поэтому роль «каталога, где стоит процесс» играет
третий временный проект со своими CLAUDE.md и AGENTS.md: утверждение то же
самое, цена ошибки — временный файл.
"""

from __future__ import annotations

import hashlib
import os
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "harness", "claude", "mcp", "project"),
)

from claudemd_state import resolve_project_dir  # noqa: E402
from handlers_skill import handle_update_claudemd  # noqa: E402
from project_backend import SQLiteBackend  # noqa: E402
from project_cli_extra import cmd_update_claudemd  # noqa: E402
from project_service import ProjectService  # noqa: E402

_DOC = (
    "# Инструкции\n\nСтатический текст.\n\n"
    "<!-- DYNAMIC:START -->\n"
    "## Current State\n"
    "Session: none | Branch: main | Version: 0.0.0\n"
    "Tasks: 999/999 done, 0 active, 0 blocked\n"
    "<!-- DYNAMIC:END -->\n\nХвост файла.\n"
)


def _sha(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _make_project(root, name: str):
    """Проект с базой в `.tausik/` и парой файлов агентских инструкций."""
    project = root / name
    (project / ".tausik").mkdir(parents=True)
    for doc in ("CLAUDE.md", "AGENTS.md"):
        (project / doc).write_text(_DOC, encoding="utf-8")
    return project


def _service(project):
    be = SQLiteBackend(str(project / ".tausik" / "tausik.db"))
    return ProjectService(be), be


@pytest.fixture
def two_projects(tmp_path, monkeypatch):
    """Свой проект и ЧУЖОЙ, в котором стоит процесс. Возвращает (свой, чужой, svc)."""
    mine = _make_project(tmp_path, "mine")
    stranger = _make_project(tmp_path, "stranger")
    svc, be = _service(mine)
    monkeypatch.chdir(stranger)
    yield mine, stranger, svc
    be.close()


class TestTheAddressComesFromTheDatabase:
    def test_resolve_project_dir_derives_the_project_from_the_db_path(self, tmp_path):
        project = _make_project(tmp_path, "p")
        svc, be = _service(project)
        try:
            assert resolve_project_dir(svc) == str(project)
        finally:
            be.close()

    def test_a_database_outside_a_tausik_dir_cannot_name_its_project(self, tmp_path):
        """Отказ, а не догадка: сказать, чей это проект, нечем."""
        loose = tmp_path / "loose"
        loose.mkdir()
        be = SQLiteBackend(str(loose / "tausik.db"))
        try:
            assert resolve_project_dir(ProjectService(be)) is None
        finally:
            be.close()

    def test_a_service_without_a_backend_yields_nothing(self):
        assert resolve_project_dir(SimpleNamespace()) is None


class TestTheStrangersFilesAreNeverTouched:
    """Тот самый сценарий: чужая база, cwd в другом проекте."""

    def test_the_mcp_handler_writes_to_its_own_project(self, two_projects):
        mine, stranger, svc = two_projects
        before = {doc: _sha(stranger / doc) for doc in ("CLAUDE.md", "AGENTS.md")}

        handle_update_claudemd(svc)

        for doc in ("CLAUDE.md", "AGENTS.md"):
            assert _sha(stranger / doc) == before[doc], (
                f"обработчик записал в ЧУЖОЙ проект ({doc}) — адрес снова берётся "
                "из текущего каталога, а не из базы"
            )
        assert "Tasks: 0/0 done" in (mine / "CLAUDE.md").read_text(encoding="utf-8"), (
            "свой проект не обновлён — починка сломала штатный путь"
        )

    def test_the_cli_writes_to_the_databases_project_not_the_cwd(self, two_projects):
        mine, stranger, svc = two_projects
        before = {doc: _sha(stranger / doc) for doc in ("CLAUDE.md", "AGENTS.md")}

        cmd_update_claudemd(svc, SimpleNamespace(claudemd=None, dry_run=False))

        for doc in ("CLAUDE.md", "AGENTS.md"):
            assert _sha(stranger / doc) == before[doc], f"CLI записал в ЧУЖОЙ проект ({doc})"
        assert "Tasks: 0/0 done" in (mine / "CLAUDE.md").read_text(encoding="utf-8")

    def test_the_sibling_agents_md_of_the_own_project_is_refreshed(self, two_projects):
        """Побратим обновляется — но побратим СВОЕГО проекта."""
        mine, _stranger, svc = two_projects
        handle_update_claudemd(svc)
        assert "Tasks: 0/0 done" in (mine / "AGENTS.md").read_text(encoding="utf-8")


class TestItRefusesRatherThanGuessing:
    def test_the_handler_refuses_a_database_it_cannot_place(self, tmp_path, monkeypatch):
        """Молча подставить cwd значит вернуть тот же дефект под другим именем."""
        stranger = _make_project(tmp_path, "stranger")
        loose = tmp_path / "loose"
        loose.mkdir()
        be = SQLiteBackend(str(loose / "tausik.db"))
        monkeypatch.chdir(stranger)
        before = {doc: _sha(stranger / doc) for doc in ("CLAUDE.md", "AGENTS.md")}
        try:
            message = handle_update_claudemd(ProjectService(be))
        finally:
            be.close()

        assert message.startswith("Refused:"), message
        for doc in ("CLAUDE.md", "AGENTS.md"):
            assert _sha(stranger / doc) == before[doc], "отказ отказал, но всё-таки записал"


class TestTheNormalPathIsUnchanged:
    """Починка не должна стоить штатному случаю ничего."""

    def test_standing_inside_your_own_project_still_works(self, tmp_path, monkeypatch):
        mine = _make_project(tmp_path, "mine")
        svc, be = _service(mine)
        monkeypatch.chdir(mine)
        try:
            handle_update_claudemd(svc)
        finally:
            be.close()
        assert "Tasks: 0/0 done" in (mine / "CLAUDE.md").read_text(encoding="utf-8")

    def test_the_cli_honours_an_explicit_claudemd_path(self, tmp_path, monkeypatch):
        """`--claudemd` — высказанное намерение, и оно сильнее вывода из базы."""
        mine = _make_project(tmp_path, "mine")
        elsewhere = tmp_path / "elsewhere.md"
        elsewhere.write_text(_DOC, encoding="utf-8")
        svc, be = _service(mine)
        monkeypatch.chdir(tmp_path)
        try:
            cmd_update_claudemd(svc, SimpleNamespace(claudemd=str(elsewhere), dry_run=False))
        finally:
            be.close()
        assert "Tasks: 0/0 done" in elsewhere.read_text(encoding="utf-8")

    def test_running_from_a_subdirectory_of_your_project_now_works(self, tmp_path, monkeypatch):
        """Побочный выигрыш: раньше cwd-подкаталог не находил файла вовсе."""
        mine = _make_project(tmp_path, "mine")
        deep = mine / "src" / "nested"
        deep.mkdir(parents=True)
        svc, be = _service(mine)
        monkeypatch.chdir(deep)
        try:
            handle_update_claudemd(svc)
        finally:
            be.close()
        assert "Tasks: 0/0 done" in (mine / "CLAUDE.md").read_text(encoding="utf-8")
