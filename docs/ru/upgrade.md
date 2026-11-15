[English](../en/upgrade.md) | **Русский**

# Безопасное обновление

<!-- doc-map: reader=user; zone=getting-started -->

Эта процедура предназначена для проекта, где TAUSIK установлен в
`.tausik-lib`. Выполняйте команды из корня проекта. Перед резервным копированием
закройте Cursor, VSCode, все ходы агентов и все процессы TAUSIK CLI/MCP, которые
могут писать в базу проекта.

## Что меняет обновление

| Путь | Владелец | Поведение при обновлении |
|---|---|---|
| `.tausik-lib/` | Фреймворк | Переключается на выбранный релизный тег. |
| `.cursor/`, `.codex/` | Смешанное владение | Управляемые TAUSIK scripts, hooks, MCP-конфигурация и rules генерируются заново. Поддерживаемые пользовательские записи сохраняются. |
| `AGENTS.md`, `CLAUDE.md`, `QWEN.md`, `.cursor/rules/tausik.mdc` | Смешанное владение | Помеченный dynamic-блок обновляется. Bootstrap отказывает, если обязательный target нельзя обновить. |
| `.tausik/tausik.db` | Пользовательские данные | Сохраняется, но новая версия может выполнить необратимую вперёд миграцию схемы. |
| `.tausik/config.json` | Пользовательская конфигурация | Читается и может быть перезаписана с актуальными provenance фреймворка и профиля. |
| `.tausik/venv/`, `.tausik/tausik`, `.tausik/tausik.cmd` | Вывод bootstrap | Создаётся или обновляется bootstrap. |
| `.tausik/stacks/` | Пользовательские overrides | Сохраняется; после обновления требуется валидация. |
| `.cursorrules` | Устаревшее смешанное владение | Удаляется только когда ownership hash TAUSIK совпадает со статическим содержимым и существует `.cursor/rules/tausik.mdc`. Изменённый пользователем или неопознанный файл остаётся байт-в-байт прежним. |

Следовательно, bootstrap пишет внутрь `.tausik/`. База данных и stack-overrides
не являются одноразовым выводом bootstrap.

## Резервная копия до смены тега

Копия должна содержать один согласованный комплект: базу, конфигурацию, тег
фреймворка и все используемые host-профили. Храните её вне `.tausik`.
Команды ниже используют SQLite online backup API, поэтому отдельный `tausik.db`
включает зафиксированные WAL-кадры. Не запускайте процессы записи до завершения
копии и проверки целостности.

POSIX shell:

```sh
backup="../tausik-backup-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$backup"
python -c 'import sqlite3,sys; s=sqlite3.connect("file:.tausik/tausik.db?mode=ro",uri=True); d=sqlite3.connect(sys.argv[1]); s.backup(d); assert d.execute("PRAGMA integrity_check").fetchone()==("ok",); d.close(); s.close()' "$backup/tausik.db"
cp -a .tausik/config.json "$backup/"
[ ! -d .tausik/stacks ] || cp -a .tausik/stacks "$backup/"
for path in .cursor .codex .cursorrules AGENTS.md CLAUDE.md QWEN.md; do
  [ ! -e "$path" ] || cp -a "$path" "$backup/"
done
git -C .tausik-lib describe --tags --always > "$backup/framework-version.txt"
```

PowerShell:

```powershell
$backup = Join-Path .. ("tausik-backup-" + (Get-Date -Format "yyyyMMdd-HHmmss"))
New-Item -ItemType Directory -Path $backup | Out-Null
py -c 'import sqlite3,sys; s=sqlite3.connect("file:.tausik/tausik.db?mode=ro",uri=True); d=sqlite3.connect(sys.argv[1]); s.backup(d); assert d.execute("PRAGMA integrity_check").fetchone()==("ok",); d.close(); s.close()' (Join-Path $backup 'tausik.db')
Copy-Item -LiteralPath .tausik\config.json -Destination $backup
if (Test-Path .tausik\stacks) { Copy-Item -Recurse -LiteralPath .tausik\stacks -Destination $backup }
foreach ($path in '.cursor','.codex','.cursorrules','AGENTS.md','CLAUDE.md','QWEN.md') {
  if (Test-Path $path) { Copy-Item -Recurse -LiteralPath $path -Destination $backup }
}
git -C .tausik-lib describe --tags --always | Set-Content (Join-Path $backup 'framework-version.txt')
```

## Обновление Cursor и Codex

Замените `<release-tag>` точным опубликованным тегом. Запускайте bootstrap для
каждого используемого хоста; при обновлении не полагайтесь на auto-detect.

POSIX shell:

```sh
git -C .tausik-lib fetch --tags
git -C .tausik-lib checkout <release-tag>
python .tausik-lib/bootstrap/bootstrap.py --project-dir . --ide cursor --no-detect
python .tausik-lib/bootstrap/bootstrap.py --project-dir . --ide codex --no-detect
./.tausik/tausik doctor
./.tausik/tausik stack lint
```

PowerShell:

```powershell
git -C .tausik-lib fetch --tags
git -C .tausik-lib checkout <release-tag>
py .tausik-lib\bootstrap\bootstrap.py --project-dir . --ide cursor --no-detect
py .tausik-lib\bootstrap\bootstrap.py --project-dir . --ide codex --no-detect
.\.tausik\tausik.cmd doctor
.\.tausik\tausik.cmd stack lint
```

Если проект использует один хост, выполните только соответствующую команду.
После успешного bootstrap выполните **Developer: Reload Window** в Cursor и в
окне VSCode с Codex. Откройте новый поток агента и проверьте SessionStart, один
read-only ход и один полный жизненный цикл задачи.

Опубликованная квалификация начинается с v1.11.7 для Cursor и Codex. На границе
v1.11.7 она доказывает отсутствие pre-lease таблиц до обновления и их создание
миграцией. На более новых границах она сохраняет существующие строки lease,
turn, Stop, continuity, задач, зависимостей, логов и связанных host-сессий.
Нативный Windows canary покрывает путь с буквой диска и пробелами, CRLF-вход
хуков, побайтовое сохранение пользовательского CRLF rule, PowerShell и новый
процесс после Reload Window.

## Сбой и откат

Не продолжайте работу после неуспешного bootstrap, doctor или smoke-теста.
Сохраните отказавший проект для диагностики.

Обычный checkout предыдущего тега **не является откатом**, если новый код уже
открыл базу. TAUSIK не обещает down-миграции. Выберите один вариант:

- восстановите полный согласованный backup при закрытых Cursor, VSCode и
  процессах агентов;
- сохраните мигрированные данные и установите более новый patch, который явно
  их поддерживает.

Оставьте все процессы записи закрытыми. Сохраните отказавшие `.tausik`,
`.cursor`, `.codex`, `.cursorrules`, `AGENTS.md`, `CLAUDE.md` и `QWEN.md` с
суффиксом `.failed-<timestamp>`. Затем восстановите согласованный комплект,
запустите bootstrap записанной версии только для host-профилей из копии и
выполните `doctor`. Никогда не соединяйте старый framework checkout с базой,
уже мигрированной новой версией.

POSIX shell:

```sh
stamp=$(date +%Y%m%d-%H%M%S)
for path in .tausik .cursor .codex .cursorrules AGENTS.md CLAUDE.md QWEN.md; do [ ! -e "$path" ] || mv "$path" "$path.failed-$stamp"; done
git -C .tausik-lib checkout "$(cat "$backup/framework-version.txt")"
mkdir .tausik
cp -a "$backup/tausik.db" "$backup/config.json" .tausik/
[ ! -d "$backup/stacks" ] || cp -a "$backup/stacks" .tausik/
for path in .cursor .codex .cursorrules AGENTS.md CLAUDE.md QWEN.md; do [ ! -e "$backup/$path" ] || cp -a "$backup/$path" .; done
[ ! -d "$backup/.cursor" ] || python .tausik-lib/bootstrap/bootstrap.py --project-dir . --ide cursor --no-detect
[ ! -d "$backup/.codex" ] || python .tausik-lib/bootstrap/bootstrap.py --project-dir . --ide codex --no-detect
./.tausik/tausik doctor
```

PowerShell:

```powershell
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
foreach ($path in '.tausik','.cursor','.codex','.cursorrules','AGENTS.md','CLAUDE.md','QWEN.md') { if (Test-Path $path) { Move-Item -LiteralPath $path -Destination ($path + '.failed-' + $stamp) } }
$tag = (Get-Content (Join-Path $backup 'framework-version.txt') -Raw).Trim()
git -C .tausik-lib checkout $tag
New-Item -ItemType Directory -Path .tausik | Out-Null
Copy-Item -LiteralPath (Join-Path $backup 'tausik.db'),(Join-Path $backup 'config.json') -Destination .tausik
if (Test-Path (Join-Path $backup 'stacks')) { Copy-Item -Recurse -LiteralPath (Join-Path $backup 'stacks') -Destination .tausik }
foreach ($path in '.cursor','.codex','.cursorrules','AGENTS.md','CLAUDE.md','QWEN.md') { $source = Join-Path $backup $path; if (Test-Path $source) { Copy-Item -Recurse -LiteralPath $source -Destination . } }
if (Test-Path (Join-Path $backup '.cursor')) { py .tausik-lib\bootstrap\bootstrap.py --project-dir . --ide cursor --no-detect }
if (Test-Path (Join-Path $backup '.codex')) { py .tausik-lib\bootstrap\bootstrap.py --project-dir . --ide codex --no-detect }
.\.tausik\tausik.cmd doctor
```

## Версионная политика

Patch-релиз может содержать аддитивную миграцию базы, если она требуется для
исправления ошибки. Каждая миграция документируется и покрывается published
upgrade qualification. Несовместимые изменения API или схемы требуют major.
Источником истины для миграций и отката служит changelog, а не только номер
версии.

## См. также

- [Кастомизация](customization.md)
- [Архитектура](architecture.md)
- [Doctor](doctor.md)
