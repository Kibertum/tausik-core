"""Мёртвый commit-хук обязан быть НАЗВАН, а выключенный решением — нет.

commit-hooks-are-dead-hookspath-points-at-a-missing-repo. В .git/config этого
репозитория стоял core.hooksPath на несуществующий репозиторий, git молчал, и
на каждом коммите не исполнялись memory_route (блокирующий контроль), mypy и
переиндекс RAG. Настройку починил владелец 2026-08-31; здесь закреплён ДЕФЕКТ —
то, что повторение никто бы не заметил.

ВСЕ ТЕСТЫ РАБОТАЮТ НА ВРЕМЕННЫХ РЕПОЗИТОРИЯХ, И ЭТО ТРЕБОВАНИЕ, А НЕ УДОБСТВО
(AC3). Проверка читает и сравнивает git-конфиг; тест, промахнувшийся мимо
tmp_path, испортил бы конфиг репозитория, в котором идёт работа, — ровно тот
файл, порча которого и завела эту задачу.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from service_doctor_hooks import (  # noqa: E402
    HOOK_NAME,
    check_commit_hooks,
    read_hooks_path,
    resolve_hook,
)


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=str(repo),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdin=subprocess.DEVNULL,
        timeout=20,
    )


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """Настоящий git-репозиторий во временном каталоге, без core.hooksPath."""
    proc = _git(tmp_path, "init", "-q")
    if proc.returncode != 0:
        pytest.skip(f"git init недоступен: {proc.stderr}")
    return tmp_path


def _severities(repo: Path) -> list[str]:
    return [row[0] for row in check_commit_hooks(str(repo))]


def _detail(repo: Path) -> str:
    return check_commit_hooks(str(repo))[0][2]


class TestTheThreeStatesAreDistinguished:
    """Двух состояний не хватает: «выключено решением» и «мертво» — разные
    события, и одно из них законно."""

    def test_unset_is_a_pass_because_ci_is_told_to_leave_it_unset(self, repo):
        # docs/ru/hooks.md:107 прямо предписывает не выставлять core.hooksPath
        # на CI-раннере без mypy. Красное здесь научило бы читателя пропускать
        # эту строку на каждой машине CI — так и теряется настоящее красное.
        assert read_hooks_path(str(repo)) is None
        assert _severities(repo) == ["ok"]
        assert "not set" in _detail(repo)

    def test_a_live_path_is_a_pass_and_names_itself(self, repo):
        hooks = repo / "scripts" / "hooks"
        hooks.mkdir(parents=True)
        (hooks / HOOK_NAME).write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        _git(repo, "config", "core.hooksPath", "scripts/hooks")
        assert _severities(repo) == ["ok"]
        assert "scripts/hooks" in _detail(repo)
        assert "resolves and will run" in _detail(repo)

    def test_a_dead_path_is_the_only_red_and_names_the_path(self, repo):
        # Ровно форма дефекта: путь ЗАДАН и ведёт в никуда.
        dead = str(repo / "no" / "such" / "dir")
        _git(repo, "config", "core.hooksPath", dead)
        rows = check_commit_hooks(str(repo))
        assert [r[0] for r in rows] == ["warn"]
        detail = rows[0][2]
        assert dead in detail, "путь обязан быть НАЗВАН — дефект был невидим именно потому"
        assert "says\n" in detail or "says nothing" in detail
        assert "git config core.hooksPath scripts/hooks" in detail, (
            "отказ без следующего действия — тупик #182 под новым именем"
        )

    def test_a_path_that_exists_but_holds_no_hook_is_also_dead(self, repo):
        # Каталог есть, pre-commit в нём нет. Для git это тот же случай: хук не
        # разрешается. Проверка каталога вместо проверки ФАЙЛА пропустила бы это.
        empty = repo / "hooks_dir"
        empty.mkdir()
        _git(repo, "config", "core.hooksPath", "hooks_dir")
        assert _severities(repo) == ["warn"]


class TestItAsksGitRatherThanParsingTheConfig:
    def test_the_value_comes_from_git_not_from_a_file_read(self, repo):
        # Значение может прийти из local/global/system тира, и порядок знает
        # только git. Разбор .git/config руками был бы вторым источником правды
        # о настройке, за которой как раз никто не следил.
        _git(repo, "config", "core.hooksPath", "some/where")
        assert read_hooks_path(str(repo)) == "some/where"
        _git(repo, "config", "--unset", "core.hooksPath")
        assert read_hooks_path(str(repo)) is None

    def test_a_relative_path_resolves_against_the_repo_root(self, repo):
        hooks = repo / "scripts" / "hooks"
        hooks.mkdir(parents=True)
        (hooks / HOOK_NAME).write_text("#!/bin/sh\n", encoding="utf-8")
        assert resolve_hook(str(repo), "scripts/hooks") is not None
        assert resolve_hook(str(repo), "scripts/missing") is None

    def test_an_absolute_path_is_used_as_given(self, repo, tmp_path):
        elsewhere = tmp_path / "elsewhere"
        elsewhere.mkdir()
        (elsewhere / HOOK_NAME).write_text("#!/bin/sh\n", encoding="utf-8")
        assert resolve_hook(str(repo), str(elsewhere)) is not None


class TestTheCheckNeverRunsTheHookItDiagnoses:
    def test_a_hook_that_would_fail_loudly_is_still_only_probed(self, repo):
        """Диагностика, запускающая то, что диагностирует, — не диагностика.

        Хук пишет файл и возвращает 1. Проверка обязана назвать состояние
        ALIVE, не создав файла: `git hook run pre-commit` из замера задачи
        исполнял бы mypy, переиндекс RAG и гейты на каждый вызов doctor.
        """
        hooks = repo / "hooks_dir"
        hooks.mkdir()
        marker = repo / "hook-was-executed"
        (hooks / HOOK_NAME).write_text(
            f"#!/bin/sh\ntouch {marker.as_posix()!r}\nexit 1\n", encoding="utf-8"
        )
        _git(repo, "config", "core.hooksPath", "hooks_dir")
        assert _severities(repo) == ["ok"]
        assert not marker.exists(), "проверка ИСПОЛНИЛА хук вместо того, чтобы его найти"


class TestItIsWiredIntoDoctor:
    def test_doctor_actually_runs_the_check(self, tmp_path):
        """Ранее здесь искалась строка импорта в конкретном файле. Проверка
        переехала в соседний модуль — и тест покраснел, хотя doctor звал её как
        и звал. Теперь спрашивается ФАКТ: прогоняем набор необязательных проверок
        и смотрим, появилась ли строка про хуки коммита.
        """
        from service_doctor_external import run_optional_checks

        rows = []
        run_optional_checks(
            str(tmp_path),
            None,
            lambda label, detail: rows.append(("ok", label, detail)),
            lambda label, detail: rows.append(("warn", label, detail)),
            lambda label, detail: rows.append(("fail", label, detail)),
        )
        assert any(label == "Commit hooks" for _, label, _ in rows), (
            "проверка, которую doctor не зовёт, диагностирует ноль репозиториев: "
            f"напечатано {[label for _, label, _ in rows]}"
        )
