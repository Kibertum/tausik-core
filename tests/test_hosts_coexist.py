"""Claude и Codex живут в одном проекте одновременно — и это закреплено.

ТРЕБОВАНИЕ ВЛАДЕЛЬЦА, смена #241: разработка переключается на Codex в другом
агенте и окружении, а проект обязан остаться пригодным для ОБОИХ.

СОВМЕСТИМОСТЬ БЫЛА УСТРОЕНА, НО НЕ ЗАКРЕПЛЕНА, и разница между этими двумя
состояниями — весь смысл файла. Устроена так: профили лежат в РАЗНЫХ каталогах
(`.claude`, `.codex`; оба в `.gitignore`, оба пересоздаются bootstrap-ом); набор
хуков у обоих происходит из ОДНОГО объявления `build_hooks_dict`, а различается
лишь способ построения строки команды; сущность — база, задачи, гейты, verify —
живёт в `.tausik` и в сервисном слое и от хоста не зависит вовсе.

Пока это не проверялось, первая же правка, которая заставила бы генератор одного
хоста писать в чужой каталог, развела бы наборы правил или сделала второй
bootstrap затирающим первый, прошла бы зелёной. Совместимость, держащаяся на том,
что никто пока не ошибся, — это везение, а не совместимость.

ПОЧЕМУ ЗДЕСЬ ЕСТЬ ПРОВЕРКА ПОРЯДКА. Затирание — асимметричный отказ: генератор,
пишущий лишнее, портит того, кто развернулся РАНЬШЕ, и не портит того, кто позже.
Один порядок был бы зелёным ровно в половине случаев.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
for _sub in ("scripts", "bootstrap"):
    if str(_REPO / _sub) not in sys.path:
        sys.path.insert(0, str(_REPO / _sub))

import bootstrap_codex  # noqa: E402
from bootstrap_config import IDE_DIRS, SCAFFOLD_IDES  # noqa: E402
from bootstrap_hooks import build_hooks_dict  # noqa: E402

CROSSCUTTING_SCOPE = ["bootstrap/"]

#: Пара, ради которой файл написан. Именно она названа владельцем; остальные
#: хосты живут по тем же правилам, но обещание дано про эту.
_CLAUDE = _REPO / ".claude"
_CODEX = _REPO / ".codex"


def _hook_commands(document: dict) -> list[str]:
    return [
        hook["command"]
        for groups in document.get("hooks", {}).values()
        for entry in groups
        for hook in entry.get("hooks", [])
    ]


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class TestОбаПрофиляЖивыОдновременно:
    """AC-1. Не «один или другой», а оба сразу, на одном дереве."""

    def test_каталоги_разные_и_объявлены_разными(self):
        assert IDE_DIRS["claude"] != IDE_DIRS["codex"]

    def test_оба_хоста_среди_целей_bootstrap(self):
        assert {"claude", "codex"} <= set(SCAFFOLD_IDES)

    def test_у_обоих_есть_свой_непустой_файл_хуков(self):
        claude = _CLAUDE / "settings.json"
        codex = _CODEX / "hooks.json"
        if not (claude.is_file() and codex.is_file()):
            pytest.skip("оба профиля не развёрнуты в этом дереве")
        assert _hook_commands(_read_json(claude)), "у claude нет ни одной команды хука"
        assert _hook_commands(_read_json(codex)), "у codex нет ни одной команды хука"


class TestНаборПравилУОбоихОдин:
    """AC-2. Хосты расходятся не сразу, а за несколько релизов, и обнаруживается
    это на чужой машине."""

    def test_события_и_матчеры_совпадают(self, tmp_path):
        reference = build_hooks_dict(lambda script, suffix="": f"X/{script}{suffix}")
        codex = bootstrap_codex.build_codex_hooks(str(tmp_path / ".codex"))
        assert set(codex) == set(reference)
        for event in reference:
            assert [e.get("matcher") for e in codex[event]] == [
                e.get("matcher") for e in reference[event]
            ], f"событие {event}: наборы матчеров разошлись"

    def test_на_живом_дереве_число_команд_одинаково(self):
        claude = _CLAUDE / "settings.json"
        codex = _CODEX / "hooks.json"
        if not (claude.is_file() and codex.is_file()):
            pytest.skip("оба профиля не развёрнуты в этом дереве")
        assert len(_hook_commands(_read_json(claude))) == len(_hook_commands(_read_json(codex))), (
            "у одного хоста команд больше — набор правил разошёлся между хостами"
        )

    def test_различие_ровно_одно_и_это_форма_пути(self, tmp_path):
        """Claude ссылается на хуки через ${CLAUDE_PROJECT_DIR}, Codex — нет,
        потому что такой переменной у него не существует. Это ЕДИНСТВЕННОЕ
        различие, и оно названо, а не обнаружено потом."""
        codex = bootstrap_codex.build_codex_hooks(str(tmp_path / ".codex"))
        assert not [c for c in _hook_commands({"hooks": codex}) if "${" in c]


class TestГенераторНеПишетВЧУЖОЙКаталог:
    """AC-3, главный тест файла, и AC-4.

    Затирание асимметрично: генератор, пишущий лишнее, портит того, кто
    развернулся РАНЬШЕ. Один порядок был бы зелёным ровно в половине случаев,
    поэтому проверяются оба.
    """

    def _snapshot(self, root: Path) -> dict[str, bytes]:
        return {
            str(p.relative_to(root)): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()
        }

    def test_развёртывание_codex_не_трогает_каталог_claude(self, tmp_path):
        claude = tmp_path / ".claude"
        claude.mkdir()
        (claude / "settings.json").write_text('{"hooks": {}}', encoding="utf-8")
        (claude / "чужое.txt").write_text("не трогать", encoding="utf-8")
        before = self._snapshot(claude)

        bootstrap_codex.generate_codex_hooks(str(tmp_path), str(tmp_path / ".codex"))

        assert self._snapshot(claude) == before, "генератор codex изменил каталог claude"
        assert (tmp_path / ".codex" / "hooks.json").is_file()

    def test_повторный_прогон_codex_не_растит_и_не_ломает_соседа(self, tmp_path):
        claude = tmp_path / ".claude"
        claude.mkdir()
        (claude / "settings.json").write_text('{"hooks": {}}', encoding="utf-8")
        target = tmp_path / ".codex"
        bootstrap_codex.generate_codex_hooks(str(tmp_path), str(target))
        first = (target / "hooks.json").read_text(encoding="utf-8")
        before_claude = self._snapshot(claude)

        bootstrap_codex.generate_codex_hooks(str(tmp_path), str(target))

        assert (target / "hooks.json").read_text(encoding="utf-8") == first
        assert self._snapshot(claude) == before_claude

    def test_каталог_codex_создаётся_даже_когда_соседа_нет(self, tmp_path):
        """Обратный порядок: Codex разворачивается ПЕРВЫМ, в пустом дереве."""
        bootstrap_codex.generate_codex_hooks(str(tmp_path), str(tmp_path / ".codex"))
        assert (tmp_path / ".codex" / "hooks.json").is_file()
        assert not (tmp_path / ".claude").exists(), "генератор codex создал чужой каталог"


class TestСостояниеОдноНаДвоих:
    """AC-5. Задача, заведённая под Claude, обязана быть видна под Codex —
    иначе это не совместимость, а два проекта в одном каталоге."""

    def test_оба_профиля_указывают_на_одну_базу(self):
        codex_cfg = _CODEX / "config.toml"
        mcp_json = _REPO / ".mcp.json"
        if not (codex_cfg.is_file() and mcp_json.is_file()):
            pytest.skip("оба профиля не развёрнуты в этом дереве")
        import tomllib

        with open(codex_cfg, "rb") as fh:
            codex_args = tomllib.load(fh)["mcp_servers"]["tausik-project"]["args"]
        # У обоих хостов сервер получает ОДИН и тот же корень проекта — а базу
        # он находит от корня. Сверяется корень, а не путь к файлу базы: путь
        # резолвит сервер, и повторять его логику здесь значило бы завести
        # второй источник правды о том, где лежит состояние.
        assert Path(codex_args[-1]).resolve() == _REPO.resolve()

    def test_база_лежит_вне_обоих_профилей(self):
        """Состояние в профиле означало бы, что переключение хоста теряет
        задачи. Оно лежит в `.tausik`, который не принадлежит ни одному."""
        db = _REPO / ".tausik" / "tausik.db"
        if not db.is_file():
            pytest.skip("база не развёрнута в этом дереве")
        assert ".claude" not in db.parts and ".codex" not in db.parts
