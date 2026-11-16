# TAUSIK 1.11.8

TAUSIK 1.11.8 is the final bug-fix consolidation before the standalone 2.0
line. It repairs Codex/Cursor initialization, identity and MCP transport;
hardens Cursor Agents and native hooks; and adds durable execution leases,
bounded task packages, continuity, memory preflight and trusted Stop/handoff.

The release is accepted without a manual walkthrough. Run:

```powershell
python scripts/adherence_release.py
```

Publication is allowed only when the command writes
`dist/adherence-1.11.8.json` and exits zero. Attach that file to this GitHub
Release as `adherence-1.11.8.json`. The report binds the
exact commit/tree, frozen contract and migration hashes, installed Codex/Cursor
projections, negative controls and native Windows test counts. Its top-level
`content_sha256` is the release evidence identifier.

---

TAUSIK 1.11.8 — финальная консолидация багфиксов перед отдельной линейкой 2.0.
Релиз исправляет инициализацию, identity и MCP transport Codex/Cursor, укрепляет
Cursor Agents и нативные hooks, а также добавляет долговечные execution leases,
bounded task packages, continuity, memory preflight и доверенный Stop/handoff.

Ручной walkthrough не требуется. Публикация разрешена только после успешного
запуска команды выше и появления
`dist/adherence-1.11.8.json`. Прикрепите файл к GitHub Release под именем
`adherence-1.11.8.json`. Верхнее поле `content_sha256` —
идентификатор релизного доказательства.
