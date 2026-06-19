# Kilo Code + z.ai (GLM)

TAUSIK работает как полноценный MCP-хост внутри **Kilo Code** (аддон для VSCode и
его CLI) на моделях **z.ai GLM**. Это возможно благодаря двум проектным решениям
(Decision #119):

- **Kilo — это runtime-хост** (ось-1): ему принадлежат каталог bootstrap,
  конфиг MCP и детекция активной модели. Только это меняется при смене IDE.
- **z.ai GLM — это семейство моделей** (ось-2): чистые данные в `model_profiles`,
  не код. Переключение/добавление GLM-моделей **не требует изменений кода**.

Эндпоинт z.ai **Anthropic-совместим**, поэтому транскрипт сессии идентичен
Claude — отличается только поле `model` (`glm-*`). Маршрутизация, вердикты и
стоимость работают без изменений.

---

## 1. Направьте агент на z.ai

z.ai предоставляет Anthropic-совместимый эндпоинт. Задайте переменные для Claude
Code **или** Kilo (Kilo использует те же Anthropic-переменные):

```bash
export ANTHROPIC_BASE_URL="https://api.z.ai/api/anthropic"
export ANTHROPIC_AUTH_TOKEN="<ваш-ключ-z.ai>"   # НИКОГДА не коммитьте
```

> **Гигиена секретов:** ключ z.ai — это учётные данные. Держите его в профиле
> shell или хранилище секретов IDE — не в `.tausik/config.json`, `.kilo/` или
> чём-либо под git.

Тариф GLM Coding Plan (от $10/мес) даёт доступ к семейству GLM (`glm-4.5-air`,
`glm-4.6` и линейке `glm-5.x`).

## 2. Bootstrap TAUSIK для Kilo

```bash
python .tausik-lib/bootstrap/bootstrap.py --ide kilo
```

Записывает MCP-стансу TAUSIK в **оба** известных пути конфига Kilo (робастно к
версиям Kilo — Decision #120):

- `.kilo/kilo.jsonc` (актуальные доки kilo.ai)
- `.kilocode/mcp.json` (более старые сборки Cline-наследия)

Оба содержат одну и ту же запись `mcp`:

```json
{
  "mcp": {
    "tausik-project": {
      "type": "local",
      "command": ["<python>", "${workspaceFolder}/.kilo/mcp/project/server.py", "--project", "${workspaceFolder}"],
      "enabled": true
    }
  }
}
```

Пути **устойчивы к переименованию**: сервер внутри проекта и `--project`
используют `${workspaceFolder}` (Kilo раскрывает его при запуске), поэтому
переименование папки проекта не ломает конфиг. Внешний lib-сервер сохраняет
абсолютный путь. Существующие серверы и другие ключи **сливаются**, а не
перезаписываются. Повторный запуск идемпотентен.

**Перезапустите Kilo** после bootstrap, чтобы он подхватил новый MCP-конфиг.

### Если ваша сборка Kilo не читает ни один из путей по умолчанию

Переопределите цель(и) в `.tausik/config.json`:

```json
{ "kilo": { "config_paths": ["kilo.jsonc"] } }
```

(пути относительны корню проекта; список полностью заменяет значения по умолчанию.)

## 3. Сообщите TAUSIK активную GLM-модель

У Kilo нет JSONL-транскрипта в стиле Claude, поэтому TAUSIK читает активную
модель (по порядку):

1. переменная окружения `KILO_MODEL` — напр. `export KILO_MODEL=glm-4.6`
2. поле `model` в `.kilo/kilo.json` (или `~/.config/kilo/kilo.json`)

Тогда `task start` показывает рекомендации GLM и корректные вердикты
«слабее/мощнее». Без этого рекомендации откатываются к
`model_profiles.default_family` (ниже), затем к Claude.

## 4. Переключение/добавление GLM-моделей — без кода

Значения по умолчанию из `scripts/model_profiles.py`:

| Ранг capability | GLM-модель |
|-----------------|------------|
| лёгкая (`haiku`) | `glm-4.5-air` |
| средняя (`sonnet`) | `glm-4.6` |
| сильная (`opus`) | `glm-4.6` |
| флагман (`fable`) | `glm-4.6` |

Переопределите/расширьте любой ранг — и закрепите GLM как семейство по умолчанию
— в `.tausik/config.json`:

```json
{
  "model_profiles": {
    "default_family": "glm",
    "families": {
      "glm": {
        "opus":  { "model": "glm-5.2", "display": "GLM-5.2" },
        "fable": { "model": "glm-5.2", "display": "GLM-5.2" }
      }
    }
  }
}
```

`default_family: "glm"` заставляет `task start` рекомендовать GLM-модели ещё до
детекции через транскрипт/`KILO_MODEL` — идеально, когда вы работаете только в
Kilo + z.ai.

## Как это собирается вместе

```
Kilo Code (аддон/CLI)  ──MCP──▶  сервер tausik-project  (.kilo/kilo.jsonc | .kilocode/mcp.json)
        │
        └── model: glm-4.6  ──▶  model_profiles (family=glm) ──▶ ранг маршрутизации → glm-модель + вердикт
```

Runtime — это Kilo; модель — это GLM. Они не знают друг о друге — именно это
разделение превращает «TAUSIK в Kilo на любой модели z.ai» в задачу настройки,
а не написания кода.
