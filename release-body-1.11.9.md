# TAUSIK 1.11.9

TAUSIK 1.11.9 is an urgent Cursor hotfix for the execution-lease regression
introduced in 1.11.8.

Cursor `PostToolUse` now completes a protected action against the lease issued
for the Cursor host. In 1.11.8 the completion query was hard-coded to Codex, so
a valid Cursor action could not find its reserved memory-preflight token. That
false audit failure entered maintenance, revoked the lease, and left the agent
looping on `LEASE_MISSING` and a missing trusted turn.

The repair also covers the rest of the lifecycle exposed by that regression:
trusted PreToolUse recovery, long-turn renewal, compatible patch
upgrades without manual doctor, exact per-thread task-package and session
binding, lease-free read diagnostics, and Cursor `memory-only` without orphaned
enforcement. Pre-execution permission denials now terminalize their exact audit
reservation without entering maintenance. MCP dispatch revalidates the lease
immediately before mutation.

Regression tests exercise the same post-tool workflow for Codex and Cursor,
concurrent threads and tasks, live and expired leases, build drift, transcript-
free SessionEnd, and full versus memory-only bootstrap.

## Required upgrade step

Regenerate the Cursor profile in every consumer project, then restart the MCP
runtime:

```powershell
python .tausik-lib/bootstrap/bootstrap.py --project-dir . --ide cursor
```

Run **Developer: Reload Window** in Cursor, or disable and re-enable
`tausik-project`. An already-running MCP process keeps its imported 1.11.8 code;
the generated `TAUSIK_PROFILE_BUILD` identifies the refreshed runtime.

If 1.11.8 already persisted lease maintenance, TAUSIK keeps it fail-closed:
the stored state cannot safely distinguish the Cursor regression from a genuine
audit failure. From the project root, run `.tausik/tausik doctor
--reconcile-execution-leases revoke-and-reconcile` once, then reload Cursor.
This revokes technical lease bindings; it does not delete chats, tasks or files.

See [What’s new in 1.11 (English)](docs/en/whats-new-1.11.md) and
[Что нового в 1.11 (Русский)](docs/ru/whats-new-1.11.md).

---

TAUSIK 1.11.9 — срочный hotfix регрессии execution lease в Cursor из 1.11.8.

Cursor `PostToolUse` теперь завершает защищённое действие через lease,
выданный именно хосту Cursor. В 1.11.8 запрос завершения был жёстко привязан к
Codex, поэтому валидное действие Cursor не находило зарезервированный токен
memory preflight. Ложная ошибка аудита включала maintenance, отзывала lease и
оставляла агента в цикле `LEASE_MISSING` / missing trusted turn.

Исправление охватывает весь проявившийся lifecycle: восстановление на
доверенном PreToolUse, продление долгого хода, совместимое patch-обновление без
ручного doctor, точную привязку task package и сессии к потоку, read-диагностику
без lease и Cursor `memory-only` без осиротевшего enforcement. Отказ до
исполнения завершает точную audit reservation без maintenance, а MCP повторно
проверяет lease непосредственно перед мутацией.

Регрессионные тесты проверяют Codex и Cursor, параллельные потоки и задачи,
живые и истёкшие leases, смену build, SessionEnd без transcript и bootstrap
full/memory-only.

## Обязательный шаг обновления

В каждом consumer-проекте заново сгенерируйте Cursor-профиль и перезапустите
MCP runtime:

```powershell
python .tausik-lib/bootstrap/bootstrap.py --project-dir . --ide cursor
```

В Cursor выполните **Developer: Reload Window** либо выключите и снова включите
`tausik-project`. Уже запущенный MCP-процесс хранит импортированный код 1.11.8;
сгенерированный `TAUSIK_PROFILE_BUILD` идентифицирует новый runtime.

Если 1.11.8 уже сохранил lease maintenance, TAUSIK оставляет его fail-closed:
состояние в БД не позволяет безопасно отличить регрессию Cursor от настоящего
сбоя аудита. Один раз выполните из корня проекта `.tausik/tausik doctor
--reconcile-execution-leases revoke-and-reconcile`, затем перезагрузите Cursor.
Команда отзывает технические lease-привязки, но не удаляет чаты, задачи и файлы.

Подробности: [What’s new in 1.11 (English)](docs/en/whats-new-1.11.md) и
[Что нового в 1.11 (Русский)](docs/ru/whats-new-1.11.md).
