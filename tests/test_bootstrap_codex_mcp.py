"""MCP для Codex: блок ДОПИСЫВАЕТСЯ, чужой TOML не переписывается.

ПОЧЕМУ ДОПИСЫВАНИЕ — ЭТО ОГРАНИЧЕНИЕ, А НЕ ВКУС. В stdlib 3.11 `tomllib` умеет
только читать; писателя нет, зависимость в bootstrap тянуть нельзя. Разобрать и
сериализовать обратно значило бы потерять комментарии, порядок секций и форму
записей пользователя — ровно то, ради сохранения чего слово preserve-first и
произносится. Поэтому чтение отвечает на один вопрос («наш блок уже там?»), а
запись добавляет текст между маркерами и не трогает ни байта выше.

ЧТО ЗДЕСЬ ПРОВЕРЯЕТСЯ СИЛЬНЕЕ ОБЫЧНОГО. Запись «сервер прописан» ничего не
стоит, если сервер не запускается: ровно этим и был плох лежавший в проекте
`.codex/hooks.json` — он перечислял все гейты и не запускал ни одного. Поэтому
здесь есть тест, который поднимает сервер КОМАНДОЙ ИЗ КОНФИГА и ждёт ответа на
`initialize`.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
for _sub in ("scripts", "bootstrap"):
    if str(_REPO / _sub) not in sys.path:
        sys.path.insert(0, str(_REPO / _sub))

import bootstrap_codex_mcp as mcp  # noqa: E402

CROSSCUTTING_SCOPE = ["bootstrap/"]

_LIVE = _REPO / ".codex" / "config.toml"


@pytest.fixture(scope="module")
def live() -> dict:
    if not _LIVE.is_file():
        pytest.skip("профиль .codex не развёрнут в этом дереве")
    with open(_LIVE, "rb") as fh:
        return tomllib.load(fh)


class TestЗаписанноеЯвляетсяВалиднымTOML:
    """AC-2. Дописанный текст обязан оставить файл разбираемым — и узнать об
    обратном должен тот, кто писал, а не хост при следующем запуске."""

    def test_живой_конфиг_разбирается(self, live):
        assert "mcp_servers" in live

    def test_записаны_ожидаемые_серверы(self, live):
        assert "tausik-project" in live["mcp_servers"]

    def test_путь_в_windows_экранирован_а_не_съеден(self, live):
        """Обратная косая в пути Windows — первый способ получить синтаксически
        валидный TOML с НЕВЕРНЫМ путём: `\\t` внутри кавычек это табуляция."""
        args = live["mcp_servers"]["tausik-project"]["args"]
        assert Path(args[0]).is_file(), f"путь после разбора не существует: {args[0]}"


class TestКаждыйПутьСуществует:
    """AC-1. На ЖИВОМ дереве: во временном каталоге серверов нет по построению."""

    def test_интерпретатор_и_сервер_на_месте(self, live):
        for name, cfg in live["mcp_servers"].items():
            assert Path(cfg["command"]).is_file(), f"{name}: интерпретатор не найден"
            assert Path(cfg["args"][0]).is_file(), f"{name}: server.py не найден"

    def test_серверов_действительно_несколько(self, live):
        """Предпосылка: пустая таблица прошла бы проверку выше молча."""
        assert len(live["mcp_servers"]) >= 1


@pytest.mark.slow
class TestСерверДЕЙСТВИТЕЛЬНОЗапускается:
    """Сильнейший тест файла. «Прописан» — не то же, что «запускается», и вся
    эта история началась с файла, который перечислял гейты и не запускал ни
    одного."""

    def test_ответ_на_initialize_командой_из_конфига(self, live, tmp_path):
        cfg = live["mcp_servers"]["tausik-project"]
        # Интерпретатор и server.py — из конфига, как записаны; ПРОЕКТ — временный.
        # С `--project <корень репозитория>` сервер на initialize создавал
        # `.tausik/tausik.db` в корне дерева, и каждая проверка, спящая без живой
        # базы, дальше по прогону просыпалась над пустой — то ли пропуск, то ли
        # красное, по порядку запуска (conftest, смена #203; пойман поимённо в
        # смене #253). Предмет теста — что команда запускается и отвечает, а не
        # чью базу она при этом заводит.
        (tmp_path / ".tausik").mkdir()
        args = list(cfg["args"])
        if "--project" in args:
            args[args.index("--project") + 1] = str(tmp_path)
        request = json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "pytest", "version": "1"},
                },
            }
        )
        proc = subprocess.Popen(
            [cfg["command"], *args],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        try:
            out, err = proc.communicate(request + "\n", timeout=60)
        except subprocess.TimeoutExpired:
            proc.kill()
            pytest.fail("сервер не ответил на initialize за 60 с")
        assert '"result"' in (out or ""), f"нет ответа. stdout={out[:200]!r} stderr={err[:200]!r}"


class TestПовторныйПрогонИЧужойТекст:
    """AC-3 и AC-4. Чужая часть файла переживает правку ПОБАЙТОВО."""

    def _target(self, tmp_path: Path) -> Path:
        target = tmp_path / ".codex"
        (target / "mcp" / "project").mkdir(parents=True)
        (target / "mcp" / "project" / "server.py").write_text("# сервер", encoding="utf-8")
        return target

    def test_чужой_текст_и_комментарии_сохраняются_побайтово(self, tmp_path):
        target = self._target(tmp_path)
        foreign = '# мой комментарий\n[mcp_servers.my_server]\ncommand = "node"\nargs = []\n'
        (target / "config.toml").write_text(foreign, encoding="utf-8")
        mcp.register_mcp_servers(str(tmp_path), str(target))
        after = (target / "config.toml").read_text(encoding="utf-8")
        assert after.startswith(foreign), "чужая часть файла изменилась"
        assert mcp.BEGIN in after

    def test_два_прогона_дают_один_файл(self, tmp_path):
        target = self._target(tmp_path)
        mcp.register_mcp_servers(str(tmp_path), str(target))
        once = (target / "config.toml").read_text(encoding="utf-8")
        path, written = mcp.register_mcp_servers(str(tmp_path), str(target))
        assert (target / "config.toml").read_text(encoding="utf-8") == once
        assert written == 0, "повторный прогон отчитался о записи, которой не было"

    def test_блок_опознаётся_по_маркеру_а_не_по_имени(self, tmp_path):
        """Пользователь мог прописать `tausik-project` сам и своим способом —
        тогда опознание по имени приняло бы его запись за нашу и не дописало
        ничего; а мог упомянуть имя в комментарии, и было бы наоборот."""
        target = self._target(tmp_path)
        (target / "config.toml").write_text(
            '# про tausik-project я слышал\n[mcp_servers.tausik-project]\ncommand = "мой"\nargs = []\n',
            encoding="utf-8",
        )
        assert mcp.already_registered((target / "config.toml").read_text(encoding="utf-8")) is False


class TestНенайденныйСерверНеЗаписывается:
    """AC-5. Запись команды, которая не запустится, ХУЖЕ отсутствия записи:
    отсутствие видно, а мёртвая запись выглядит настроенной."""

    def test_пустой_профиль_не_даёт_блока(self, tmp_path):
        target = tmp_path / ".codex"
        target.mkdir()
        block = mcp.build_block(str(tmp_path), str(target), None, lib_dir=None)
        assert block == ""

    def test_записывается_только_найденный(self, tmp_path):
        target = tmp_path / ".codex"
        (target / "mcp" / "project").mkdir(parents=True)
        (target / "mcp" / "project" / "server.py").write_text("#", encoding="utf-8")
        block = mcp.build_block(str(tmp_path), str(target), None, lib_dir=None)
        assert "[mcp_servers.tausik-project]" in block
        assert "codebase-rag" not in block, "записан сервер, которого нет на диске"

    def test_отсутствие_серверов_сообщается_а_не_замалчивается(self, tmp_path, capsys):
        target = tmp_path / ".codex"
        target.mkdir()
        _, written = mcp.register_mcp_servers(str(tmp_path), str(target))
        assert written == 0
        assert "WARNING" in capsys.readouterr().out


class TestНашБлокПерегенерируется:
    """Блок с маркерами переписывается на месте: сервер, которого больше нет
    (tausik-brain ушёл с Notion, решение #358), исчезает из него, а чужой текст
    вокруг блока не меняется."""

    def _target(self, tmp_path: Path) -> Path:
        target = tmp_path / ".codex"
        (target / "mcp" / "project").mkdir(parents=True)
        (target / "mcp" / "project" / "server.py").write_text("# сервер", encoding="utf-8")
        return target

    def test_устаревший_сервер_уходит_из_нашего_блока(self, tmp_path):
        target = self._target(tmp_path)
        foreign = '# мой комментарий\n[mcp_servers.my_server]\ncommand = "node"\nargs = []\n'
        stale = (
            f"{foreign}\n{mcp.BEGIN}\n[mcp_servers.tausik-project]\ncommand = \"old\"\nargs = []\n\n"
            f"[mcp_servers.tausik-brain]\ncommand = \"old\"\nargs = []\n\n{mcp.END}\n"
        )
        (target / "config.toml").write_text(stale, encoding="utf-8")
        _path, written = mcp.register_mcp_servers(str(tmp_path), str(target))
        after = (target / "config.toml").read_text(encoding="utf-8")
        assert after.startswith(foreign), "чужая часть файла изменилась"
        assert "tausik-brain" not in after
        assert "[mcp_servers.tausik-project]" in after and after.count(mcp.BEGIN) == 1
        assert written == 2, "the count is every server the parsed file holds: ours plus my_server"

    def test_блок_без_конца_не_трогается(self, tmp_path):
        target = self._target(tmp_path)
        broken = f"{mcp.BEGIN}\n[mcp_servers.tausik-brain]\ncommand = \"old\"\nargs = []\n"
        (target / "config.toml").write_text(broken, encoding="utf-8")
        _path, written = mcp.register_mcp_servers(str(tmp_path), str(target))
        assert written == 0
        assert (target / "config.toml").read_text(encoding="utf-8") == broken
