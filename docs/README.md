# TAUSIK Documentation / Документация TAUSIK

TAUSIK is an engineering governance framework for AI coding agents. It forces planning before code, evidence before completion, and preserves project memory across sessions. Read more in the [main README](../README.md).

**Start here:** [Quick Start](en/quickstart.md) -> [What is SENAR?](en/senar.md) -> [Workflow](en/workflow.md) -> [Skills](en/skills.md) -> then explore topics you need.

## English

### Getting started

| Document | Audience |
|----------|----------|
| **[Quick Start](en/quickstart.md)** | First setup — 10-15 minutes |
| **[What is SENAR?](en/senar.md)** | The methodology behind TAUSIK |
| **[Workflow](en/workflow.md)** | A typical day with TAUSIK |
| **[Upgrade](en/upgrade.md)** | Migrating between TAUSIK versions |

### Core surface

| Document | Audience |
|----------|----------|
| **[Skills](en/skills.md)** | What the agent can do |
| **[Hooks](en/hooks.md)** | Real-time enforcement: blockers, firewall, drift guards |
| **[CLI Commands](en/cli.md)** | Full terminal command reference |
| **[MCP Tools](en/mcp.md)** | 124 tools for the AI agent |
| **[Architecture](en/architecture.md)** | How the framework works inside |
| **[Roles](en/roles.md)** | Free-text roles (developer, qa, architect…) |
| **[Stacks](en/stacks.md)** | Tech stacks and stack-scoped gates |

### Quality & verification

| Document | Audience |
|----------|----------|
| **[Verify glossary](en/verify-glossary.md)** | Opt-out vs bypass vs test shim — single terminology |
| **[Testing principles](en/testing-principles.md)** | When to add tests, scoped pytest, anti-patterns |
| **[Doctor](en/doctor.md)** | Health-check command — venv + DB + drift + gates |
| **[Zero-defect mode](en/zero-defect.md)** | High-stakes precision mode for security/migration |
| **[Dev doc checks](en/dev-doc-checks.md)** | Doc-constants drift + audit scripts how-to |

### Configuration

| Document | Audience |
|----------|----------|
| **[Configuration](en/configuration.md)** | `.tausik/config.json` keys, defaults, validation |
| **[Customization](en/customization.md)** | Custom stacks, gates, skill repos |
| **[Environment](en/environment.md)** | Environment variables and CI integration |
| **[Permissions](en/permissions.md)** | Permission allowlists and tool gates |
| **[Model providers](en/model-providers.md)** | Multi-model routing (Haiku/Sonnet/Opus, GigaCode/Qwen) |

### IDE integration & skills

| Document | Audience |
|----------|----------|
| **[Adding New IDE](en/adding-new-ide.md)** | How to add IDE support |
| **[Vendor Skills](en/vendor-skills.md)** | External skill packages |
| **[Skill Adaptation](en/skill-adaptation.md)** | Adapt any skill repo for TAUSIK |
| **[Skill ecosystem](en/skill-ecosystem.md)** | Repo skills: install/activate flow + risks |
| **[Skill profiles](en/skill-profiles.md)** | Multi-model variants (frontmatter + variants/) |
| **[CLAUDE.md guide](en/claude-md-guide.md)** | Anatomy of CLAUDE.md (static + dynamic blocks) |

### Memory & shared brain

| Document | Audience |
|----------|----------|
| **[Memory merge guidelines](en/memory-merge-guidelines.md)** | When to merge entries vs add new |
| **[Shared Brain](en/shared-brain.md)** | Optional cross-project Notion knowledge base |
| **[Brain DB schema](en/brain-db-schema.md)** | 4 Notion databases — structure & properties |
| **[Brain search ranking](en/brain-search-ranking.md)** | Stack-aware bm25 boost rules |
| **[Brain artifact taxonomy](en/brain-artifact-taxonomy.md)** | Artifact / pattern / snippet boundaries |

### Sessions & lifecycle

| Document | Audience |
|----------|----------|
| **[Session active time](en/session-active-time.md)** | Gap-based tracking, idle threshold, retro recompute |
| **[Task archive spec](en/task-archive-spec.md)** | Read-only archive of old done tasks (design) |

### Security

| Document | Audience |
|----------|----------|
| **[Security](en/security.md)** | Threat model and protection rules |
| **[Security checklist](en/security-checklist.md)** | OWASP-aligned review checklist |

### Reference

| Document | Audience |
|----------|----------|
| **[Troubleshooting](en/troubleshooting.md)** | Common issues and resolutions |
| **[SENAR compliance matrix](en/senar-compliance-matrix.md)** | Rule-by-rule SENAR coverage |
| **[i18n strategy](en/i18n-strategy.md)** | Bilingual EN/RU localization approach |

### Internal agent specs *(EN only)*

These are agent-facing specifications consumed by AI assistants — not user-facing documentation. RU mirrors are not produced.

| Document | Audience |
|----------|----------|
| **[Skill spec](en/skill-spec.md)** | Formal skill contract (frontmatter, output shape) |
| **[Skill patterns](en/skill-patterns.md)** | Cross-skill helper patterns |
| **[Plan review](en/plan-review.md)** | `/plan` review heuristics |
| **[Plan stacks](en/plan-stacks.md)** | Stack-detection logic for `/plan` |

## Русский

**Начните здесь:** [Быстрый старт](ru/quickstart.md) -> [Что такое SENAR?](ru/senar.md) -> [Рабочий процесс](ru/workflow.md) -> [Навыки](ru/skills.md) -> далее по необходимости.

### Начало работы

| Документ | Для кого |
|----------|----------|
| **[Быстрый старт](ru/quickstart.md)** | Первое знакомство — 10-15 минут |
| **[Что такое SENAR?](ru/senar.md)** | Методология за TAUSIK |
| **[Рабочий процесс](ru/workflow.md)** | Типичный день с TAUSIK |
| **[Обновление](ru/upgrade.md)** | Миграция между версиями TAUSIK |

### Основная поверхность

| Документ | Для кого |
|----------|----------|
| **[Навыки (Skills)](ru/skills.md)** | Что умеет AI-агент |
| **[Хуки (Hooks)](ru/hooks.md)** | Real-time контроль: блокировки, firewall, drift guards |
| **[CLI-команды](ru/cli.md)** | Справочник команд терминала |
| **[MCP-инструменты](ru/mcp.md)** | 124 инструмента для AI-агента |
| **[Архитектура](ru/architecture.md)** | Как устроен фреймворк внутри |
| **[Роли](ru/roles.md)** | Free-text роли (developer, qa, architect…) |
| **[Стэки](ru/stacks.md)** | Технологические стэки и stack-scoped gates |

### Качество и верификация

| Документ | Для кого |
|----------|----------|
| **[Глоссарий verify](ru/verify-glossary.md)** | Opt-out, bypass и тестовый shim — единая терминология |
| **[Принципы тестирования](ru/testing-principles.md)** | Когда писать тесты, scoped pytest, анти-паттерны |
| **[Doctor](ru/doctor.md)** | Health-check: venv + DB + drift + gates |
| **[Zero-defect режим](ru/zero-defect.md)** | High-stakes precision для security/миграций |
| **[Dev doc checks](ru/dev-doc-checks.md)** | Doc-constants drift + audit скрипты |

### Конфигурация

| Документ | Для кого |
|----------|----------|
| **[Конфигурация](ru/configuration.md)** | `.tausik/config.json` ключи, defaults, валидация |
| **[Кастомизация](ru/customization.md)** | Custom stacks, gates, skill репозитории |
| **[Окружение](ru/environment.md)** | Переменные окружения и CI-интеграция |
| **[Разрешения](ru/permissions.md)** | Allowlist разрешений и tool gates |
| **[Поставщики моделей](ru/model-providers.md)** | Multi-model маршрутизация (Haiku/Sonnet/Opus, GigaCode/Qwen) |

### IDE-интеграция и скиллы

| Документ | Для кого |
|----------|----------|
| **[Добавление IDE](ru/adding-new-ide.md)** | Поддержка нового IDE |
| **[Внешние скиллы](ru/vendor-skills.md)** | Vendor-скиллы |
| **[Адаптация скиллов](ru/skill-adaptation.md)** | Как адаптировать скиллы под TAUSIK |
| **[Экосистема скиллов](ru/skill-ecosystem.md)** | Репо-скиллы: поток установки, риски |
| **[Профили скиллов](ru/skill-profiles.md)** | Multi-model варианты (frontmatter + variants/) |
| **[Гайд по CLAUDE.md](ru/claude-md-guide.md)** | Анатомия CLAUDE.md (static + dynamic блоки) |

### Память и Shared Brain

| Документ | Для кого |
|----------|----------|
| **[Память: merge vs новая запись](ru/memory-merge-guidelines.md)** | Редакция записей; classifier и scrubbing |
| **[Shared Brain](ru/shared-brain.md)** | Опциональная кросс-проектная база на Notion |
| **[Brain DB schema](ru/brain-db-schema.md)** | 4 Notion-базы — структура и свойства |
| **[Brain search ranking](ru/brain-search-ranking.md)** | Stack-aware bm25 boost правила |
| **[Brain artifact taxonomy](ru/brain-artifact-taxonomy.md)** | Границы artifact / pattern / snippet |

### Сессии и lifecycle

| Документ | Для кого |
|----------|----------|
| **[Active time сессии](ru/session-active-time.md)** | Gap-based tracking, idle threshold, retro recompute |
| **[Спека архива done-задач](ru/task-archive-spec.md)** | Read-only архив старых done (дизайн) |

### Безопасность

| Документ | Для кого |
|----------|----------|
| **[Безопасность](ru/security.md)** | Модель угроз и правила защиты |
| **[Чеклист безопасности](ru/security-checklist.md)** | OWASP-чеклист для ревью |

### Справочник

| Документ | Для кого |
|----------|----------|
| **[Troubleshooting](ru/troubleshooting.md)** | Типичные проблемы и решения |
| **[SENAR матрица](ru/senar-compliance-matrix.md)** | Rule-by-rule SENAR покрытие |
| **[Стратегия i18n](ru/i18n-strategy.md)** | Bilingual EN/RU локализация |

## Other

| Document | Description |
|----------|-------------|
| **[CHANGELOG](../CHANGELOG.md)** | Version history (EN) |
| **[CHANGELOG.ru](../CHANGELOG.ru.md)** | История версий (RU) |
