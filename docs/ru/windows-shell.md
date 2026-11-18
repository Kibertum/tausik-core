# Windows shell: гигиена для агентов

<!-- doc-map: reader=agent; zone=getting-started -->

На Windows вложенные кавычки и remote one-liner часто ломаются и сжигают ходы.
Пишите **файл**, а не однострочник. Это day-0 поверхность; warn-only PreToolUse
`windows_shell_hygiene.py` называет те же правила в момент вызова.

## Правила

1. **Вложенные кавычки → файл.** Скрипт в `.ps1` / `.cmd` / `.py`, затем запуск
   файла. Не гнездите `"…'…\"…\"…"` в Shell one-liner.
2. **Ничего после `-EncodedCommand`.** PowerShell отвергает аргументы после
   base64 (dead_end #1019).
3. **`gh api --jq` с фигурными скобками ломается в PowerShell.** `--jq` через
   файл или `cmd /c` / Git Bash без разбора PowerShell (gotcha #975).
4. **SSH / remote bash:** локальный LF-скрипт, `scp`, затем `ssh … bash
   script.sh`. Избегайте heredoc из CRLF-шелла (#1063).
5. **MCP-first.** Предпочитайте `tausik_*` MCP, если есть близнец; shell — для
   цепочек и длинных аргументов из файла.

## См. также

- Consumer export-only: [quickstart](quickstart.md) (продукт + `tausik/`)
- Хуки: [hooks](hooks.md)
