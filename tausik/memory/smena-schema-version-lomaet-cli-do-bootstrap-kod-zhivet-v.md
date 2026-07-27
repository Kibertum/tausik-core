---
slug: smena-schema-version-lomaet-cli-do-bootstrap-kod-zhivet-v
title: "Смена SCHEMA_VERSION ломает CLI до bootstrap: код живёт в зеркале .claude/scripts, а не в scripts/"
type: gotcha
tags:
  - bootstrap
  - gotcha
  - mirror
  - schema
  - session-117
task: l26-gate-results-persist
edges: []
---

НАСТУПИЛ ЛИЧНО (задача l26-gate-results-persist, сессия #117). Поднял SCHEMA_VERSION с 38 до 39 в scripts/backend_schema.py, проверил метрики скриптом через sys.path.insert('scripts') — и живая .tausik/tausik.db мигрировала на v39. После этого ЛЮБАЯ команда .tausik/tausik падала с RuntimeError: «Database schema v39 is newer than code v38. Update .tausik-lib».

ПРИЧИНА: CLI .tausik/tausik исполняет НЕ scripts/, а сгенерированное зеркало .claude/scripts/. Пока bootstrap не прогнан, зеркало остаётся на прежней версии кода, а БД уже мигрирована. Миграции необратимы по дизайну (run_migrations: «Migrations are irreversible -- no rollback support»), поэтому откат SCHEMA_VERSION в коде НЕ чинит — станет код v38 против БД v39, та же ошибка с другой стороны.

ЛЕЧЕНИЕ: python bootstrap/bootstrap.py (без флагов). Копирует scripts/ в .claude/, CLI оживает. .claude/ в gitignore, поэтому в отслеживаемый диф это не попадает.

ПОРЯДОК ДЕЙСТВИЙ НА БУДУЩЕЕ при любой правке схемы: сначала прогнать тесты, потом bootstrap, и только потом трогать живую БД чем-либо, что её откроет. Открытие БД кодом из scripts/ — уже миграция, отдельного разрешения она не спрашивает.

ЧТО ЭТО ГОВОРИТ ШИРЕ: страж версии сработал ПРАВИЛЬНО — отказал громко вместо порчи данных, это образец fail-closed. Но зеркало как источник исполнения означает, что гейты фреймворка, запускаемые через CLI и MCP, исполняют НЕ тот код, который я только что отредактировал, пока не прогнан bootstrap. Для задач без правки схемы это незаметно и потому опаснее: тесты гоняют канонический scripts/ (tests/ импортируют ../scripts), а tausik verify — зеркало. Два разных дерева под видом одной проверки.

СВЯЗАНО: [[Рой в TAUSIK: три уровня допустимости и почему порядок именно такой]] — там же отмечено, что .tausik/ в gitignore и переживёт ли БД worktree-изоляцию не проверено; здесь тот же корень, зеркала и генерируемые артефакты вне git.
