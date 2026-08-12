"""mcp-update-claudemd-erases-the-memory-tail — паритет MCP и CLI на CLAUDE.md.

Обработчик MCP `tausik_update_claudemd` был ВТОРОЙ независимой копией
`project_cli_extra.cmd_update_claudemd`, и в копии отсутствовали две вещи,
которые есть в оригинале: впрыск хвоста памяти и обновление файла-побратима
AGENTS.md. Поскольку /start Phase 2 предписывает именно MCP-вызов, а правило
проекта — MCP-first, штатный старт сессии УДАЛЯЛ из CLAUDE.md блок памяти,
который тот же /start обещает впрыснуть. Потеря была тихой: команда
рапортовала «CLAUDE.md updated».

Тесты пришпиливают не текст блока, а ПАРИТЕТ двух путей: пока обе стороны
строят блок одной функцией, третья потеря невозможна. Проверять текст было бы
слабее — копию можно выправить руками, и она разойдётся снова.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "harness", "claude", "mcp", "project"),
)

from handlers import handle_tool as _handle_tool  # noqa: E402
from project_backend import SQLiteBackend  # noqa: E402
from project_service import ProjectService  # noqa: E402

_CLAUDEMD = """# CLAUDE.md

Статическая часть, которую трогать нельзя.

<!-- DYNAMIC:START -->
## Current State
Session: #1 (active) | Branch: main | Version: 0.0.0
<!-- DYNAMIC:END -->

Хвост файла, который тоже обязан уцелеть.
"""


@pytest.fixture
def project(tmp_path, monkeypatch):
    """Каталог проекта с CLAUDE.md, маркерами и сервисом поверх реальной базы.

    Бэкенд закрывается ОБЯЗАТЕЛЬНО: на Windows незакрытый дескриптор SQLite не
    даёт pytest убрать временный каталог, и уборка падает не здесь, а в тесте,
    который запустится через несколько файлов, — ошибка приезжает с чужим
    именем. Именно так и вышло: полный прогон дал ERROR в
    test_memory_cleanup_cli, следующем по алфавиту, а в одиночку тот файл
    проходил.
    """
    (tmp_path / ".tausik").mkdir()
    (tmp_path / "CLAUDE.md").write_text(_CLAUDEMD, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    svc = ProjectService(SQLiteBackend(str(tmp_path / ".tausik" / "tausik.db")))
    yield tmp_path, svc
    svc.be.close()


@pytest.fixture
def seeded(project):
    """Проект, в памяти которого есть что терять."""
    tmp_path, svc = project
    svc.decide("Квитанция предъявляется, а не ищется в кэше")
    svc.memory_add("convention", "Слаги в kebab-case", "Слаги задач пишутся в kebab-case")
    svc.memory_add("dead_end", "Свой парсер PDF", "Отброшено: поддержка дороже пользы")
    svc.memory_add("context", "Прогон набора идёт ~18 минут", "Запускать в фоне")
    return tmp_path, svc


def _dynamic_block(path) -> str:
    text = path.read_text(encoding="utf-8")
    start = text.index("<!-- DYNAMIC:START -->")
    end = text.index("<!-- DYNAMIC:END -->")
    return text[start:end]


def test_mcp_update_claudemd_injects_memory_tail(seeded):
    """Красный до правки: обработчик MCP писал только Current State.

    Это и есть наблюдённый дефект — вызов /start удалял из CLAUDE.md 34 строки
    памяти, отчитываясь об успешном обновлении.
    """
    tmp_path, svc = seeded
    result = _handle_tool(svc, "tausik_update_claudemd", {})
    assert "updated" in result

    block = _dynamic_block(tmp_path / "CLAUDE.md")
    assert "## Current State" in block
    assert "### Memory tail" in block, (
        "обработчик MCP обязан впрыскивать хвост памяти — /start Phase 2 обещает "
        "именно это и другого вызова для впрыска не делает"
    )
    assert "Квитанция предъявляется" in block
    assert "kebab-case" in block
    assert "Свой парсер PDF" in block
    assert "~18 минут" in block


def test_mcp_and_cli_build_the_same_dynamic_block(seeded):
    """Паритет по СТРОКЕ, а не по наличию подстрок.

    Пока обе стороны зовут одну функцию, расхождение невозможно по
    конструкции. Тест на «в блоке есть слово Memory» пропустил бы третью
    потерю ровно так же, как прежние тесты пропустили эту.
    """
    tmp_path, svc = seeded
    from claudemd_state import build_dynamic_state

    _handle_tool(svc, "tausik_update_claudemd", {})
    mcp_block = _dynamic_block(tmp_path / "CLAUDE.md")

    cli_block = build_dynamic_state(svc, str(tmp_path))
    for line in cli_block.splitlines():
        assert line in mcp_block, f"строка CLI отсутствует в блоке MCP: {line!r}"


def test_mcp_refreshes_the_agents_md_sibling(seeded):
    """AGENTS.md рядом с CLAUDE.md обновляется и по пути MCP.

    resolve_sibling_targets звал только CLI, поэтому у пользователей Codex и
    прочих IDE, читающих AGENTS.md, файл устаревал молча.
    """
    tmp_path, svc = seeded
    (tmp_path / "AGENTS.md").write_text(_CLAUDEMD, encoding="utf-8")

    _handle_tool(svc, "tausik_update_claudemd", {})

    agents = _dynamic_block(tmp_path / "AGENTS.md")
    assert "### Memory tail" in agents
    assert "kebab-case" in agents


def test_empty_memory_adds_no_empty_tail_heading(project):
    """Пустая база не порождает заголовок без содержимого."""
    tmp_path, svc = project
    _handle_tool(svc, "tausik_update_claudemd", {})

    block = _dynamic_block(tmp_path / "CLAUDE.md")
    assert "## Current State" in block
    assert "### Memory tail" not in block


def test_memory_failure_still_writes_current_state(project, monkeypatch):
    """Сломанная память НЕ роняет обновление: Current State записан всё равно."""
    tmp_path, svc = project

    import service_knowledge_aggregates

    def _boom(_be):
        raise RuntimeError("memory subsystem down")

    monkeypatch.setattr(service_knowledge_aggregates, "build_compact_memory_tail", _boom)

    result = _handle_tool(svc, "tausik_update_claudemd", {})
    assert "updated" in result
    assert "## Current State" in _dynamic_block(tmp_path / "CLAUDE.md")


def test_static_body_and_file_tail_survive(seeded):
    """Замена динамической секции не съедает то, что вокруг неё."""
    tmp_path, svc = seeded
    _handle_tool(svc, "tausik_update_claudemd", {})

    text = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
    assert "Статическая часть, которую трогать нельзя." in text
    assert "Хвост файла, который тоже обязан уцелеть." in text
    assert text.count("<!-- DYNAMIC:START -->") == 1
    assert text.count("<!-- DYNAMIC:END -->") == 1
