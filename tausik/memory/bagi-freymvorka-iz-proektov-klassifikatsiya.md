---
slug: bagi-freymvorka-iz-proektov-klassifikatsiya
title: "Баги фреймворка из проектов — классификация"
type: context
tags: []
task: null
edges: []
---

## Баги найденные при использовании Frai в проектах (март 2026)

### MCP (4 бага — самая проблемная область)
1. _get_service() hang — MCP сервер зависал при инициализации ([вычеркнуто: third-party-project], [вычеркнуто: third-party-project])
2. MCP timeout — таймаут при долгих операциях ([вычеркнуто: third-party-project])
3. async context manager — stdio_server требовал async with (frai)
4. RAG subprocess hang на Windows — subprocess.run для git зависал, заменено на прямое чтение .git/HEAD + asyncio.to_thread (frai)

### Bootstrap (3 бага)
5. Path resolution — неправильные пути при bootstrap в подпроектах ([вычеркнуто: third-party-project], [вычеркнуто: third-party-project])
6. Scripts copy — не все скрипты копировались при bootstrap ([вычеркнуто: third-party-project], [вычеркнуто: third-party-project])
7. Unicode arrow на Windows — charmap codec error cp1252 при выводе стрелки (frai)

### DB/Backend (2 бага)
8. Auto-create DB on project_register — БД не создавалась автоматически ([вычеркнуто: third-party-project], [вычеркнуто: third-party-project])
9. task_slug FK validation — отсутствовала валидация внешнего ключа (frai)

### CLI (2 бага)
10. task list --status all — пустой результат, 'all' трактовался как литерал (frai)
11. status hides done tasks — done задачи не скрывались по умолчанию (frai)

### Infra (1 баг)
12. Hyper-V port reservation — порт 7700 зарезервирован Windows, пришлось менять на 7600 (frai)

### Паттерны
- **MCP — 33% всех багов.** Основной источник проблем: async, таймауты, Windows-совместимость.
- **Bootstrap — 25%.** Пути и копирование файлов ломаются при разных структурах проектов.
- **Windows-специфичные — 3 из 12 (25%).** Unicode, subprocess hang, port reservation.
