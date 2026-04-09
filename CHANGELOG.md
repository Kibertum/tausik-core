# Changelog

All notable changes to this project will be documented in this file.

This project adheres to [Semantic Versioning](https://semver.org/).

## [1.0.0] — 2026-04-05

### Public Release / Публичный релиз

First public release of TAUSIK. Cross-IDE AI agent framework implementing [SENAR v1.3 Core](https://senar.tech).
Первый публичный релиз TAUSIK. Кросс-IDE фреймворк для AI-агентов, реализующий [SENAR v1.3 Core](https://senar.tech).

### Highlights / Основное

- **Cross-IDE support** — Claude Code, Cursor, Windsurf, Codex with unified skill/role/stack system — Поддержка Claude Code, Cursor, Windsurf, Codex с единой системой скиллов/ролей/стеков
- **31 skills** — from `/start` to `/ship`, covering the full development lifecycle — 31 скилл, покрывающих полный цикл разработки
- **SENAR v1.3 Core compliance (100%)** — Quality gates, metrics, dead ends, explorations, verification checklists — Полное соответствие SENAR v1.3 Core
- **Graph memory** — Project knowledge base with edges, soft-invalidation, FTS5 search — Графовая память проекта с рёбрами, soft-invalidation, FTS5 поиском
- **Autonomous batch mode** — `/run plan.md` executes multi-task plans with subagents — Автономный batch-режим для выполнения планов

### Added / Добавлено

- **Quality Gates** — QG-0 (context gate: goal + AC + negative scenario) and QG-2 (implementation gate: evidence + tests + ac-verified) — Quality gates с жёстким enforcement
- **Claude Code Hooks** — task gate, bash firewall, git push gate, auto-format — Хуки для контроля в реальном времени
- **SENAR Metrics** — Throughput, Lead Time, FPSR, DER, Dead End Rate, Cost per Task — Автоматические метрики
- **Multi-language gates** — pytest, ruff, go-vet, clippy, phpstan, eslint, tsc, and more — Gates для 10+ языков
- **5-agent review pipeline** — quality, implementation, testing, simplification, documentation agents with iterative cycle — 5 параллельных review-агентов с итеративным циклом
- **Dead ends & explorations** — `dead-end` for documenting failures, `explore` for time-bounded research — Документирование тупиков и исследования
- **Graph memory** — Polymorphic edges between memory/decision nodes, 4 relation types, recursive CTE traversal — Полиморфные рёбра, 4 типа связей, обход графа через CTE
- **Structured task logs** — `task_logs` table with phase tracking and FTS5 index — Структурированные логи задач
- **Vendor skills** — `skills.example.json` + `skill activate/deactivate` for third-party extensions — Поддержка сторонних скиллов
- **Bootstrap** — `bootstrap.py --smart --init` for one-command setup with stack detection — Настройка одной командой с детекцией стека
- **Apache 2.0 license** — Open source license — Лицензия Apache 2.0
- **Bilingual docs** — Full documentation in English and Russian — Полная документация на EN и RU
- **CONTRIBUTING.md** — Contributor guide — Гайд для контрибьюторов
- **837 tests** — Comprehensive test suite — Полный набор тестов
