# Общие паттерны скиллов

Общие паттерны, используемые в нескольких скиллах. Ссылайся на этот файл вместо дублирования.

## Проверка здоровья сессии
```bash
.tausik/tausik status
```
Смотри на строку «Session: Xm active / Ym wall». Если active близко к
`session_warn_threshold_minutes` (по умолчанию 150) → предложи `/checkpoint`. На
`session_max_minutes` (по умолчанию 180) → `task start` жёстко блокируется;
пользователь должен сделать `/end` или `session extend`.

## Обновление динамической секции CLAUDE.md
Замени содержимое между `<!-- DYNAMIC:START -->` и `<!-- DYNAMIC:END -->`:
```
Current State
Session: #{id} | Branch: {branch} | Version: {version}
Tasks: {done}/{total} done, {active} active, {blocked} blocked
{IF handoff: Last session: {summary}}
{IF warnings: Warnings: ...}
```
Используй `.tausik/tausik update-claudemd`, чтобы перегенерировать эту секцию автоматически.

## Handoff JSON
```json
{"summary":"...","completed":["slug1","slug2"],"in_progress":[],
 "blocked":[],"key_files":["path1"],"dead_ends":[],"next_steps":["slug1 — reason"],
 "warnings":["..."]}
```

## Захват знаний (при task done)
На `task done` агент должен зафиксировать значимые выводы через `tausik decide`,
`tausik dead-end` или `tausik memory add`. SENAR Rule 8 принуждает к этому как
предупреждение, если задача не закрыта с `--no-knowledge`.
