**English** | [Русский](../ru/upgrade.md)

# Upgrade Safety

<!-- doc-map: reader=user; zone=getting-started -->

Use this procedure for a project that installs TAUSIK in `.tausik-lib`. Run it
from the project root. Before backup, close Cursor, VSCode, every agent turn,
and every TAUSIK CLI or MCP process that can write the project database.

## What an upgrade changes

| Path | Ownership | Upgrade behaviour |
|---|---|---|
| `.tausik-lib/` | Framework | Checked out at the selected release tag. |
| `.cursor/`, `.codex/` | Mixed | TAUSIK-managed scripts, hooks, MCP configuration and rules are regenerated. Supported user entries are preserved. |
| `AGENTS.md`, `CLAUDE.md`, `QWEN.md`, `.cursor/rules/tausik.mdc` | Mixed | The marked dynamic block is refreshed. Bootstrap refuses when a required target cannot be updated. |
| `.tausik/tausik.db` | User data | Preserved, but opening it with a newer release may run forward schema migrations. |
| `.tausik/config.json` | User configuration | Read and may be rewritten with current framework/profile provenance. |
| `.tausik/venv/`, `.tausik/tausik`, `.tausik/tausik.cmd` | Bootstrap output | Created or refreshed by bootstrap. |
| `.tausik/stacks/` | User overrides | Preserved; validate them after the upgrade. |
| `.cursorrules` | Legacy mixed ownership | Removed only when its TAUSIK ownership hash still matches its static content and `.cursor/rules/tausik.mdc` exists. Customized or unrecognized files remain byte-identical. |

Bootstrap therefore does write inside `.tausik/`. The database and stack
overrides are not disposable bootstrap output.

## Back up before changing the tag

The backup must contain one matching set: database, configuration, framework
tag and every host profile in use. Store it outside `.tausik`.
The commands below use SQLite's online backup API, so committed WAL frames are
included in the standalone backup database. Keep all writer processes closed
until the copy and integrity check finish.

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

## Upgrade Cursor and Codex

Replace `<release-tag>` with the exact published tag. Bootstrap each host that
the project uses; do not rely on host auto-detection during an upgrade.

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

Run only the host-specific bootstrap command when the project uses one host.
After bootstrap succeeds, use **Developer: Reload Window** in Cursor and in the
VSCode window that runs Codex. Open a new agent thread and verify that
SessionStart, one read-only turn and one task lifecycle complete.

Published qualification begins at v1.11.7 for both Cursor and Codex. At the
v1.11.7 boundary it proves the pre-lease tables are absent before upgrade and
created by migration. At later boundaries it preserves existing lease, turn,
Stop, continuity, task, dependency, log, and referenced host-session rows. The
native Windows canary covers drive-letter paths with spaces, CRLF hook input,
byte preservation of a user-owned CRLF rule, PowerShell, and a fresh process
after Reload Window.

## Failure and rollback

Do not continue working after a failed bootstrap, doctor or smoke test. Keep the
failed project intact for diagnosis.

A checkout of the previous tag alone is **not** a rollback after the newer code
has opened the database. TAUSIK does not promise down migrations. Choose one:

- restore the complete matching backup while Cursor, VSCode and agent processes
  are closed; or
- keep the migrated data and install a newer patch that explicitly supports it.

To restore, keep every writer closed and preserve the failed paths. Then restore
the matching set and bootstrap only the host profiles present in the backup.

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

Never combine an old framework checkout with a database already migrated by a
newer release.

## Version policy

Patch releases may contain additive forward database migrations when a bug fix
requires them. Every migration must be documented and covered by the published
upgrade qualification. Incompatible API or schema changes require a major
release. The changelog, not the version number alone, is the source of truth for
migration and rollback requirements.

## See also

- [Customization](customization.md)
- [Architecture](architecture.md)
- [Doctor](doctor.md)
