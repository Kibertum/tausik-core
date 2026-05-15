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
| Codex/OpenCode | `.codex` | `AGENTS.md` | — |

## Как это работает

```
harness/
├── skills/          # 33 общих скилла (все IDE)
├── roles/           # роли (все IDE)
├── stacks/          # стеки (все IDE)
├── overrides/       # IDE-специфичные override-файлы
│   ├── claude/
│   └── cursor/
├── claude/mcp/      # MCP серверы для Claude Code
└── cursor/mcp/      # MCP серверы для Cursor
```

Bootstrap lookup chain: `harness/skills/` → `harness/{ide}/skills/` → `harness/claude/skills/`
