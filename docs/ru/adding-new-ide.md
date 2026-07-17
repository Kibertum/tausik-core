[English](/docs/adding-new-ide) | **Русский**

# Добавление новой IDE в TAUSIK

TAUSIK поддерживает несколько IDE через абстракцию в `scripts/ide_utils.py`.

## Шаги для добавления нового IDE

### 1. Зарегистрировать IDE в реестре

Добавить запись в `IDE_REGISTRY` в `scripts/ide_utils.py`:

```python
IDE_REGISTRY["myide"] = {
    "config_dir": ".myide",        # директория конфигурации IDE
    "rules_file": ".myiderules",   # файл с правилами для агента
    "skills_subdir": "skills",     # поддиректория для скиллов
}
```

### 2. Добавить генератор правил

В `bootstrap/bootstrap_generate.py` добавить функцию:

```python
def generate_myiderules(project_dir, project_name, stacks):
    # Сгенерировать .myiderules
    ...
```

И добавить ветку в dispatch-блок `bootstrap/bootstrap.py` (ищи цепочку `if ide == "claude"` / `elif ide == "cursor"` ~строка 170 — добавь `elif ide == "myide"`, который зовёт твой генератор).

### 3. (Опционально) Добавить override-файлы

Если IDE требует специфические правила, создать:
```
harness/overrides/myide/rules.md
```

Этот файл **автоматически дописывается** в сгенерированный `CLAUDE.md` /
`.cursorrules` / `QWEN.md` (в зависимости от `ide=`, переданного в
`bootstrap_templates.build_full_body`). Блок встаёт перед маркером
`<!-- DYNAMIC:START -->`, поэтому doctor-drift игнорирует пользовательское
state, но трактует override как часть канонического тела. В вашем
`generate_myiderules()` передавайте `ide="myide"` — это включит
override. `ide=None` (используется намеренно для `AGENTS.md`, который
хост-агностичен) полностью отбрасывает блок.

### 4. Добавить автодетекцию

В `detect_ide()` в `ide_utils.py` добавить проверку env vars или директорий:

```python
if os.environ.get("MYIDE_DIR"):
    return "myide"
```

### 5. Добавить тесты

В `tests/test_ide_utils.py` добавить тесты для нового IDE.

## Текущие поддерживаемые IDE

| IDE | Config dir | Rules file | Auto-detect |
|-----|-----------|------------|-------------|
| Claude Code | `.claude` | `CLAUDE.md` | default |
| Cursor | `.cursor` | `.cursorrules` | `CURSOR_DIR` env |
| Windsurf | `.windsurf` | `.windsurfrules` | `WINDSURF_DIR` env |
| Codex | `.codex` | `AGENTS.md` | `CODEX_SANDBOX_DIR` env |
| OpenCode | `.opencode` | `.opencode/tausik-rules.md` | каталог `.opencode/` (+ env `OPENCODE_DIR`, не проверено на живой сборке) |

Для IDE без ветки-генератора (Windsurf, Codex) TAUSIK не генерирует конфиг и не
ставит хук принуждения QG-0 — хост настраивается руками.

**OpenCode — отдельный хост, а не псевдоним Codex** (до v1.7.0 переменная
`OPENCODE_DIR` ошибочно резолвилась в `codex`, и сессия OpenCode получала пути
`.codex/`, которые сам OpenCode не читает). Он читает `opencode.json` (не
`.codex/config.toml`), грузит плагины из `.opencode/plugins/` (мн. ч.) и подмешивает
файлы правил, перечисленные в ключе `instructions`.

Файл правил у OpenCode единственный из всех — не в корне проекта: правила лежат в
`.opencode/tausik-rules.md` и подключаются через `instructions`. Причина в том, что
`AGENTS.md` у OpenCode работает по принципу «побеждает первый найденный файл», то есть
пользовательский `AGENTS.md` всегда вытеснил бы наш. Ключ `instructions`, наоборот,
**мерджится** с любым `AGENTS.md` — поэтому для `--ide opencode` TAUSIK свой `AGENTS.md`
намеренно не генерирует (иначе одни и те же правила попали бы в контекст дважды).

## Как это работает

```
harness/
├── skills/          # 13 core + 20 vendor-скиллов (opt-in), общие для всех IDE
├── roles/           # роли (все IDE)
├── stacks/          # стеки (все IDE)
├── overrides/       # IDE-специфичные override-файлы
│   ├── claude/
│   ├── cursor/
│   └── qwen/
├── claude/mcp/      # MCP-серверы — КАНОН для всех IDE (copy_mcp откатывается сюда)
└── opencode/plugins/ # Плагин принуждения QG-0 (единственный по-настоящему IDE-специфичный артефакт)
```

**Не заводи** каталог `harness/<своя-ide>/mcp/`. `copy_mcp` предпочитает его канону, поэтому
копия под IDE молча продолжит отдавать старый сервер в тот день, когда кто-то поправит только
claude-версию. Побайтовое зеркало `harness/cursor/mcp/` существовало ровно поэтому и удалено в
v1.7.0; `tests/test_mcp_single_canonical_tree.py` больше не даст ему отрасти обратно.

Bootstrap lookup chain: `harness/skills/` → `harness/{ide}/skills/` → `harness/claude/skills/`
