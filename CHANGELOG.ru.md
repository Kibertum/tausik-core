# Changelog (Русская версия)

Все значимые изменения проекта.

Проект следует [Семантическому версионированию](https://semver.org/lang/ru/).

> Английское зеркало: [`CHANGELOG.md`](CHANGELOG.md) — содержит ту же
> структуру плюс полную историю до v1.3.2. RU-версия ведётся параллельно
> начиная с v1.3.2; для более ранних релизов смотри английскую версию.
> При добавлении новой записи держи оба файла синхронизированными.

## [1.4.0] — 2026-05-02 — Verify-First Contract + 1.4 epic batch

> Релиз готовности к публике, основанный на аудите 1.4 и мастер-плане
> 10 эпиков (research-артефакты удалены перед релизом, см. историю коммитов).
> Главное изменение: тяжёлая верификация (pytest, tsc, cargo, phpstan, …)
> отделена от `task done`. Закрытие задачи теперь миллисекундная операция,
> а верификация — отдельный явный кешируемый шаг.
> Все 10 v14-* эпиков закрыты; бэклог приземлён полностью —
> `v14-brain-snippets`, `v14-model-prompts`, `v14-verify-integrity`,
> `v14-cost-telemetry`, `v14-framework-lean` приехали в Composer-батче
> (сессия #42); оставшиеся `v14-project-hygiene`, `v14-test-philosophy`,
> `v14-doc-automation`, `v14-dead-code-audit`, `v14-skill-store`
> закрылись в Phase B follow-up перед релиз-коммитом. Ретро сессии #42 —
> `docs/ru/research/tausik-1.4-composer-retro-2026-05-02.md`.

### BREAKING (с opt-out)

- **Verify-First Contract.** Тяжёлые quality gates переехали с триггера
  `task-done` на новый триггер `verify`. `task done` теперь отказывается
  закрывать задачу, пока в `verification_runs` нет свежего green-запуска
  `tausik verify` для этой задачи (TTL 10 мин, настраивается через
  `verify_cache_ttl_seconds`). Затронутые гейты: `pytest`, `tsc`,
  `cargo-check`, `cargo-test`, `go-vet`, `go-test`, `phpstan`, `phpunit`,
  `javac`, `js-test`, `terraform-validate`, `helm-lint`, `kubeval`,
  `hadolint`, `ansible-lint`.
  - **Зачем:** в VS Code Claude Extension и подобных хостах
    многоминутные синхронные pytest-прогоны внутри `task_done` выглядели
    как зависание агента. Новый контракт делает верификацию видимой и
    прерываемой.
  - **Opt-out:** добавьте `{ "task_done": { "auto_verify": true } }` в
    `.tausik/config.json` — вернётся inline-поведение v1.3 (heavy гейты
    запускаются внутри `task_done`). Полезно для CI.
  - **Миграция:** достаточно вставить `tausik verify --task <slug>` перед
    `task done`. Скилл `/ship` и CLI-доки уже обновлены.

### Добавлено — Verify-First инфраструктура

- `VALID_GATE_TRIGGERS` расширен на `"verify"` (project_config + stack_schema).
- `service_verification.has_fresh_verify_run()` и
  `service_verification._build_cache_command(trigger, files)` — ключ кеша
  включает триггер, чтобы verify- и task-done-кеши не пересекались.
- `service_gates._enforce_verify_first()` синтезирует blocking_failure
  с явной remediation, если свежего verify-запуска нет.
- `tests/test_verify_first_contract.py` — 14 тестов end-to-end (блок,
  разблокировка через cache hit, auto_verify opt-out, разделение
  buckets кеша, проекты-исключения, миграция стек-гейтов).
- Маркер pytest `verify_first` и autouse opt-out фикстура в `conftest.py`,
  чтобы legacy-тесты не падали на новом контракте.
- **Envelope-таймаут на verify pipeline** (`verify_pipeline_timeout_seconds`,
  по умолчанию 60с) — общий wall-time лимит на весь цикл `run_gates`,
  чтобы зависший gate не делал `task done` похожим на завис. `0`
  отключает (CI). При превышении: `GateEnvelopeTimeoutError` с явным
  remediation (поднять лимит, включить `auto_verify=true`, сузить
  `relevant_files`).
- **Восстановление relevant_files из последнего verify-row.** Когда
  `task done` вызван без CLI/MCP `relevant_files` И в `task.relevant_files`
  тоже пусто, `service_task` теперь читает список из последнего fresh
  verify-row (≤ TTL, exit 0) — `tausik verify --task X` + `tausik task
  done X` (без аргументов) попадает в cache. Security-sensitive paths
  (auth/payment/…) bypass fallback — там всегда требуется явный список.
- **Relaxed cache hit при mismatch файлов.** Строгий cache lookup ключует
  по `(slug, files_hash, command)` — mtime / gate-signature drift
  корректно инвалидирует. Единственный sharp edge, который он создавал
  — `verify --task X` с manual scope (`files=[]`), затем `task done X
  relevant_files=[…]` миссился и запускал `run_gates` повторно — закрыт:
  если strict miss имеет fresh exit-zero row с пустым files set, он
  принимается как "manual scope подтвердил slug". Mismatch когда
  записанный run назвал конкретные файлы — по-прежнему miss
  (mtime/signature invalidation сохранён). Security-sensitive
  `relevant_files` обходят relaxed тоже.

### Добавлено — Эпик v14-brain-snippets (Shared Brain artifact pipeline)

- Логическая схема `agents/schemas/brain-artifact-card.schema.json` —
  валидируемая нагрузка для patterns / gotchas перед записью в Notion.
- `scripts/brain_artifact_taxonomy.py`, `scripts/brain_artifact_card.py`,
  `scripts/brain_store_format.py` — таксономия (artifact / pattern / snippet),
  валидатор карточки, нормализатор store-format на стороне сервера.
- `scripts/brain_publish_flow.py` + `scripts/brain_publish_cli.py` +
  `scripts/brain_cli_ops.py` — поток propose → audit → publish со
  scrub-перед-risk и явным гейтом `confirm_high_risk`.
- MCP `brain_draft_artifact` (Claude + Cursor) для предложения артефактов
  до публикации.
- Опциональное поле `external_repo_url` в карточке артефакта (валидируется,
  не пишется в Notion props в v1).
- Stack-aware ранжирование артефактов в `brain_search`.
- EN/RU документы: `brain-artifact-taxonomy.md`, `brain-search-ranking.md`.

### Добавлено — Эпик v14-model-prompts (мульти-модельные skill profiles)

- `scripts/skill_profile.py` — резолвер frontmatter + `variants/<model>.md`
  с безопасным fallback на неизвестный профиль.
- `agents/skills/_profile-demo/` — демо-skill (`SKILL.md` + `variants/`),
  показывающий формат. Префикс `_` заставляет bootstrap пропускать демо
  при реальной генерации.
- `bootstrap_copy.py` — profile-aware копирование skill (выбор тела варианта).
- `bootstrap_qwen.py` + `.qwen/` + шаблон `QWEN.md` — Qwen Code agent
  как ещё одна целевая IDE рядом с Claude / Cursor.
- `TAUSIK_MODEL_PROFILE` env → ключ `model_profile` в `.tausik/config.json`
  (валидация на bootstrap; невалидное значение → exit non-zero).
- Опциональный ключ `task_next.model_hint` (off по умолчанию) — добавляет
  non-blocking рекомендацию модели (Haiku / Sonnet / Opus) в `task next`
  и `hud` на основе complexity.
- Таблица AGENTS.md «модель → tool surface».
- EN/RU документы: `skill-profiles.md` плюс обновления `skills.md`.

### Добавлено — Эпик v14-verify-integrity (anti-gaming QG-2)

- Подкоманда `doctor` показывает non-blocking предупреждение, когда
  `auto_verify=true` сочетается с интерактивным профилем (люди обычно
  не хотят полный pytest внутри `task_done`). Тестировано в
  `tests/test_doctor_auto_verify_hint.py`.
- `tests/conftest.py` `_verify_first_autouse_compat_shim` задокументирован:
  helper-предикат `tests/verify_first_compat_predicate.py` объявляет,
  какие тестовые пути обходят `_enforce_verify_first` и почему.
- `scripts/verify_recent_lookup.py` — небольшой compat-shim для lookup
  verify-кеша вне `service_verification`.
- EN/RU документы: `verify-glossary.md` (opt-out vs bypass vs test shim —
  единый источник правды).

### Добавлено — Эпик v14-cost-telemetry (учёт токенов и долларов)

- Таблица `usage_events` (миграция в `backend_schema.py`) — пишет
  model_id, input/output токены, опциональный cost, task_slug,
  session, created_at. Отрицательные токены / неизвестная модель
  отвергаются.
- Ключ `llm_pricing_usd_per_million` в config (валидируется
  `normalize_llm_pricing_config`) — цена за 1M токенов по модели;
  отсутствующая модель → `UNKNOWN`.
- `usage_events_cost_rollup_by_task` + `usage_cost_rollup_by_task` —
  агрегаты per-task / per-period. Пустые окна возвращают `[]`,
  не исключения.
- `tausik metrics --cost` (CLI + MCP `tausik_metrics`) — табличный
  rollup с дружелюбным сообщением для пустого состояния.

### Добавлено — Эпик v14-framework-lean (снижение токен-стоимости)

- Ключ конфига `context_tier` (`minimal` / `standard` / `full`) +
  `resolve_context_tier()` со строгой валидацией. Bootstrap рендерит
  короткие / средние / полные правила соответственно. Тестировано в
  `tests/test_context_tier.py`.
- `tausik status --compact` (CLI флаг) и MCP `tausik_status({compact:
  true})` — однострочный JSON-ответ для агентов, которым не нужен
  человекочитаемый блок. Дефолтный человеческий вывод не изменён.
- Trim-проход AGENTS.md: убраны дубликаты со skills без потери
  жёстких правил.

### Добавлено — Doc-автоматизация (эпик v14-doc-automation, частично)

- `docs/_generated/constants.json` — единый источник правды для
  `tausik_version` и MCP tool counts (project / brain / RAG / total).
- `scripts/gen_doc_constants.py` — генератор с режимом `--check`
  (exit 1 на drift). Доступен как `tausik doc constants [--check]`.
- `scripts/mcp_tool_counts.py` — выводит числа `mcp_*_tools` из
  живых `agents/{claude,cursor}/mcp/*/tools.py`. Тестировано в
  `tests/test_gen_doc_constants.py`, `tests/test_mcp_doc_tool_counts.py`.

### Добавлено — Hygiene и test-philosophy документация (частично)

- EN/RU документы: `task-archive-spec.md` (политика read-only архива
  done-задач старше N дней), `memory-merge-guidelines.md` (когда
  объединять memory vs. заводить новую запись), `testing-principles.md`
  (критерии нового теста; антипаттерн: копипаста без нового поведения),
  `skill-ecosystem.md` (one-pager для потока repo → install → activate).
- `agents/skills/_profile-demo/` показан в `skills.md` — когда
  использовать мульти-модельные варианты.

### Изменено

- `agents/{claude,cursor}/mcp/project/server.py`:
  - `chdir(args.project)` при старте с явной проверкой directory
    (exit 2, stderr-сообщение). Паритет с `tausik-brain`.
  - Исключения tool теперь печатают полный `traceback.format_exc()` в
    stderr, а агент видит минимальное `Error: …` — стек-фреймы не
    утекают в model context.
- `service_verification.run_gates_with_cache(..., trigger="task-done")`
  параметризован; CLI `verify` и MCP `_handle_verify` зовут с
  `trigger="verify"`.
- Стек-конфиги `python`, `typescript`, `rust`, `go`, `php`, `javascript`,
  `java`, `terraform`, `helm`, `kubernetes`, `docker`, `ansible` обновлены:
  тяжёлые гейты с `task-done` переведены на `verify`.
- `bootstrap_templates.py` HARD_CONSTRAINTS, SENAR_RULES, COMMANDS и
  QUALITY_GATES секции описывают Verify-First workflow — новые проекты
  через bootstrap получают правильные CLAUDE.md / AGENTS.md / .cursorrules.
- `docs/{en,ru}/cli.md` и `docs/{en,ru}/quickstart.md` обновлены.
- Скиллы `/ship` и `/task done` явно вызывают `tausik_verify` перед
  закрытием задачи.

### Исправлено

- Pre-existing баг тестов: `tests/test_service_verification.py` lambdas,
  мокающие `gate_runner.run_gates`, не принимали kwargs и тихо падали
  на реальном `progress_callback=`. Lambdas получили `**_kw`. (4 теста
  разблокированы.)
- Test pollution между `test_hud_cli.py`, `test_memory_block.py`,
  `test_memory_compact.py`, `test_qg0_dimensions.py` и любым тестом,
  читающим `.tausik/config.json` через `find_tausik_dir()`. Эти четыре
  файла ставили `os.environ["TAUSIK_DIR"]` напрямую без cleanup, и env
  утекала в последующие тесты, указывая на удалённый tmp_path. Заменено
  на `monkeypatch.setenv` — cleanup автоматический. Поверхность всплыла
  через новый `tests/test_task_next_model_hint.py::test_hint_via_config_file`
  — единственный тест, который реально проходит `load_config()` с диска.

### Тесты

- Suite расширен **2318 → 2513** (`tests/`); полный прогон зелёный
  (`2506 passed, 7 skipped`).
- Новые test-файлы: `test_bootstrap_model_profile`,
  `test_brain_artifact_external_repo`, `test_context_tier`,
  `test_doctor_auto_verify_hint`, `test_gen_doc_constants`,
  `test_llm_pricing_config`, `test_mcp_doc_tool_counts`,
  `test_skill_profile`, `test_task_next_model_hint`,
  `test_metrics_session_usage`.

### Версионирование

- `__version__` поднят `1.3.7` → `1.4.0`.
- `pyproject.toml` `version` поднят `1.3.7` → `1.4.0`.
- `docs/_generated/constants.json` перегенерирован.

> Все 10 v14-* эпиков закрыты в этом релизе. Оставшиеся 5 эпиков из
> мастер-плана приземлены сразу после Composer-batch и разнесены ниже на
> отдельные секции для согласованности с первыми пятью.

### Добавлено — Эпик v14-project-hygiene (гигиена долгоживущего проекта)

- **`tausik hygiene archive`** (CLI, в v1 только dry-run) — список `done`
  задач старше `task_archive.done_age_days`. Активные / blocked /
  planning / review задачи не включаются; `--confirm` зарезервирован
  под будущие деструктивные операции и сейчас отвергается с понятным
  сообщением. Источники: `scripts/project_cli_hygiene.py`,
  parser dispatch в `scripts/project_parser_ops.py::add_hygiene`.

### Добавлено — Эпик v14-test-philosophy (дисциплина тестов)

- **`scripts/audit_pytest_dedupe.py`** — AST-нормализация и группировка
  тест-функций со структурно идентичным телом (детектор копипасты).
  Артефакт: `docs/ru/research/tausik-1.4-pytest-dedupe-2026-05-02.md`.

### Добавлено — Эпик v14-dead-code-audit (инвентаризация мёртвого кода и мусора)

- **`scripts/audit_orphan_files.py`** — Python-файлы в `scripts/`,
  на которые никто не ссылается. Зеркала EN/RU и soft doc-ссылки
  учтены — standalone CLI скрипты не false-positive.
- **`scripts/audit_stale_docs.py`** — markdown в `docs/` без входящих
  ссылок. EN/RU mirror партнёры держатся парой; research и
  release-notes архивы исключены glob'ами.
- **`scripts/audit_unused_python.py`** — top-level `def` / `class`
  без ссылок в репо. EXEMPT_MODULES + приватные хелперы исключены;
  политика false-positive задокументирована в render_markdown.

### Добавлено — Эпик v14-doc-automation (генерация и drift-проверки docs)

- **`scripts/hooks/check_docs.py`** — pre-commit / CI обёртка над
  `gen_doc_constants.py --check`; корректно skip'ает когда нет
  `pyproject.toml` выше cwd.
- **Шаг `Doc-constants drift check` в `.github/workflows/tests.yml`** —
  матрица падает при drift `docs/_generated/constants.json`.
- **EN/RU dev-документы:** `dev-doc-checks.md` — как запускать всё это
  локально; описывает negative-поведение.

### Добавлено — Эпик v14-skill-store (UX и доверие skill CLI)

- **Skill CLI consistency** (`tausik skill ...`) — каждый subcommand
  имеет noun-phrase help и hint "see: tausik skill list" на `name`
  args. Negative сценарии теперь дают friendly `Error: ...` + exit 1
  вместо Python traceback; `SkillManagerError` ловится наравне
  с `ServiceError` в `main()`.

### Рефакторинг

- `scripts/project_parser.py` 465 → 372 строки: `add_skill` и
  `add_metrics` вынесены в `scripts/project_parser_ops.py`, чтобы
  пройти 400-строчный filesize gate.

## [1.3.7] — 2026-04-29 — MCP-прозрачность для Cursor/VSCode + docs consistency sweep

Патч усиливает агентный UX MCP и синхронизирует документацию с фактическим
статусом multi-IDE валидации.

### Добавлено
- **MCP-инструмент `tausik_task_done_v2`** (в поверхностях Claude и Cursor)
  со structured JSON-ответом: stage-флаги, per-gate results, blocking failures,
  remediation hints, warnings и cache status.
- **Progress events по quality gates** в `gate_runner` и вывод прогресса в
  MCP stderr: `[gate X/N] running ...`, `PASS/FAIL/SKIP`, duration.
- **Генерация Cursor project MCP-конфига** в bootstrap:
  `.cursor/mcp.json` теперь генерируется/мерджится вместе с корневым `.mcp.json`.

### Изменено
- Внутренности `task_done` переведены на общий structured report pipeline при
  сохранении backward-compatible plain-text поведения для legacy-вызовов.
- README EN/RU теперь явно маркирует **официально протестированные** IDE-связки:
  `VSCode + Claude Extension` и `Cursor`; остальные хосты отмечены как
  expected/partial.
- Quickstart EN/RU теперь фиксирует dual MCP config locations:
  `.mcp.json` (экосистема Claude) и `.cursor/mcp.json` (Cursor project).
- MCP docs EN/RU дополнены описанием `tausik_task_done_v2` и structured-ответа.

### Исправлено
- Устранён docs drift в RU-индексе и hooks-доках:
  - в русскоязычном docs index счётчик MCP выровнен до 96;
  - описание триггера `brain_search_proactive.py` синхронизировано с
    фактической генерацией hook wiring (`WebSearch|WebFetch`, а не общий prompt).
- Синхронизированы устаревшие значения dogfooding/test-count в RU/agent docs.

### Тесты
- Добавлены/обновлены тесты для:
  - MCP-диспетчеризации/формата `task_done_v2`;
  - генерации Cursor MCP config и сохранения пользовательских server entries;
  - списка MCP-инструментов в integration с новым v2 endpoint.
- Целевой набор зелёный локально:
  `tests/test_project_mcp.py`,
  `tests/test_mcp_integration.py`,
  `tests/test_bootstrap_generate_mcp.py`.

### Версионирование
- `__version__` повышен `1.3.6` → `1.3.7`.
- Версия в `pyproject.toml` повышена `1.3.6` → `1.3.7`.

## [1.3.6] — 2026-04-29 — Чистка мёртвого кода + целостность фреймворка

Закрывает два упавших CI-workflow и более широкий аудит целостности.
Поведенческих изменений для пользователей нет — surface фреймворка тот же,
просто чище.

### Удалено
- `scripts/generate_cli_ref.py` — orphan (CLI-справочник переехал в
  `docs/{en,ru}/cli.md` ещё в v1.3.0; генератор так и не перевели на
  новый путь).
- `.github/workflows/docs-update.yml` — писал в удалённую директорию
  `references/`, был источником второго красного CI.
- `scripts/hooks/notify_on_done.py` + `scripts/notifier.py` +
  `tests/test_notifier.py` — фича уведомлений была реализована, но нигде
  не регистрировалась в bootstrap-template'ах, по факту мёртвый код.
  Parking-lot запись добавлена в `TODO.md` на случай возврата фичи.

### Исправлено
- **CI red — `ruff check scripts/`.** Удалены 6 неиспользуемых импортов
  в `scripts/project_cli_doctor.py`, `scripts/service_task.py`,
  `bootstrap/analyzer.py`.
- **Bootstrap drift.** `scripts/project_service.py` и
  `scripts/service_task_team.py` редактировались в source без
  re-bootstrap'а `.claude/`; `tausik doctor` теперь отдаёт ноль
  предупреждений.
- **Устаревшие doc-пути.** Шесть документов (`docs/{en,ru}/i18n-strategy.md`,
  `docs/en/environment.md`, `docs/en/troubleshooting.md`,
  `docs/en/skill-spec.md`, `docs/{en,ru}/architecture.md`) ссылались на
  удалённый корневой `references/`; обновлены на `docs/{en,ru}/cli.md`.
- **Hooks-документация.** `docs/{en,ru}/hooks.md` больше не упоминает
  удалённый `notify_on_done.py` ни в таблице PostToolUse, ни в pipeline-схеме.
- **Test count.** Обновлено 2270 → 2318 в `CLAUDE.md`, `README.md` и
  `docs/{en,ru}/architecture.md` после удаления `test_notifier.py`.

### Изменено
- **CI: ruff расширен.** Теперь запускается на `scripts/ tests/ bootstrap/`
  (раньше только `scripts/`) — чтобы будущий drift в tests/bootstrap
  ловился на PR.
- **`pyproject.toml`.** Добавлен `[tool.ruff]` блок с per-file `E402`
  ignore для семи test/bootstrap-модулей, которые намеренно делают
  `sys.path.insert` перед импортом project-модулей. Поле version
  поднято со старой заглушки `1.0.0` до `1.3.6`.
- **Lint hygiene.** Почищены 4× F541 (бесполезные `f""` префиксы),
  2× B007 (unused loop var `dirpath`, `f`), 1× E741 (`l` → `row`),
  1× E401 (combined imports), 7× F841 (unused locals в тестах — включая
  два тест-бага, где assert полностью отсутствовал:
  `test_dotfile_not_ignored_by_default` и `test_case_insensitive_ext`
  в `tests/test_rag_edge.py`).
- **Mypy override.** Удалён obsolete `module = "generate_cli_ref"` —
  файл больше не существует.

### Версионирование
- `__version__` повышен `1.3.5` → `1.3.6`.
- `pyproject.toml` `version` синхронизирован со stale `1.0.0` на `1.3.6`.

## [1.3.5] — 2026-04-28 — метрики token/cost для Cursor (auto + CLI)

### Добавлено
- CLI-подкоманда `tausik metrics record-session` для записи метрик
  сессии (токены/cost/tool/model) в БД проекта.
- Новая таблица `session_usage_metrics` (schema `v19`) с upsert по
  `session_id` и индексами для выборки.
- В `tausik metrics` добавлен блок `LLM Usage` (суммарно + последняя
  записанная сессия).

### Изменено
- `session end` теперь best-effort вызывает
  `scripts/hooks/session_metrics.py --auto --record` (не блокирует
  завершение сессии при ошибке).
- `scripts/hooks/session_metrics.py --auto` теперь ищет транскрипты и в
  `~/.claude/projects`, и в `~/.cursor/projects`.

### Тесты
- Добавлен `tests/test_metrics_session_usage.py`.
- Добавлен `tests/test_session_end_metrics_hook.py`.

### Версионирование
- `__version__` повышен `1.3.4` -> `1.3.5`.

## [1.3.4] — 2026-04-28 — Security & QG hardening + doc-truth

Закрывает HIGH/MED security и QG-байпасы из v1.3.1 blind-review, которые
не вошли в v1.3.0 релиз. Три коммита:

### Doc-truth: тестовый счётчик (`fcbefb4`)
- README.md / README.ru.md badges + Stats-таблицы, AGENTS.md,
  CONTRIBUTING.md, docs/{en,ru}/architecture.md — `2246` → `2270`
  (число после v1.3.3 +24 теста). Записи в CHANGELOG не трогали —
  историческое.

### Verify cache cross-check vs git diff (`d8838f1`) — закрывает 1 HIGH (Sec)
- `scripts/verify_git_diff.py` (новый): `changed_files_since(timestamp,
  root, runner)` дёргает `git log --since=<ts> --name-only` +
  `git diff --name-only HEAD`, объединяет, нормализует пути в forward
  slashes. Возвращает `None` при любой ошибке (нет git, нет `.git`,
  ненулевой exit, OSError) — не ломаем non-git users.
- `is_declared_consistent_with_git_diff(declared, ts)` возвращает False
  если declared_set — строгое подмножество фактически изменённых
  (under-declaration). Over-declaration — нормально.
- `service_verification.run_gates_with_cache`: новый параметр
  `task_created_at`. Когда передан — cache lookup также проверяет
  git-diff consistency (плюс к существующим security-bypass + files_hash).
  Новый статус-код `git-mismatch` рядом с `hit`/`miss`/`bypass`.
- `service_gates._run_quality_gates` и `project_cli_verify.cmd_verify`
  пробрасывают `task["created_at"]`.
- Закрывает байпас: агент мог объявить `relevant_files=[docs/x.md]`,
  редактируя `scripts/auth.py` — кэш хешировал только декларированные
  файлы → следующий `task_done` видел stale-green и пропускал security check.
- Рефакторинг под filesize: `qg0_dimensions_score` вынесен в
  `scripts/gate_qg0_score.py` (47 строк), `service_gates` упал с 408 до 381.
- 16 новых тестов в `tests/test_service_verification.py`.

### Hook hardening batch (`b48d230`) — закрывает 5 MED (Sec) + 1 audit-clean
- **#1 bash_firewall regex.** WARN_PATTERNS теперь — regex с word-boundary
  (та же форма что у `git_push_gate.py`: command-start anchor + optional
  path + optional `git -c` flags). `echo 'git push --force is dangerous'`
  больше не false-positive. `gitfoo push --force` не матчится.
  `/usr/bin/git push --force` всё ещё блокируется. 11 новых тестов.
- **#2 skill_manager pip hardening.** `install_skill_deps` передаёт
  `--no-config` (отключает все pip.conf scope) и чистит `PIP_INDEX_URL`,
  `PIP_EXTRA_INDEX_URL`, `PIP_TRUSTED_HOST`, `PIP_FIND_LINKS`, `PIP_INDEX`
  из env subprocess'а. Вместе с существующим `_SAFE_PKG` regex закрывает
  supply-chain redirect surface для третьесторонних скиллов. 3 новых теста.
- **#3 copytree symlinks=False.** 3 call site'а — `skill_manager.copy_skill`,
  `service_skills.skill_install`, `bootstrap_copy.copy_dir` — теперь
  явно передают `symlinks=False`. Новый `tests/test_copy_symlinks_disabled.py`
  с hostile-repo fixture (skip на Windows non-admin где `os.symlink`
  падает); покрывает все 3 call site'а.
- **#4 hooks детектируют TAUSIK по `.tausik/` dir, не `.db` file.** Новый
  хелпер `_common.is_tausik_project(project_dir)`. `task_gate.py` и
  `memory_pretool_block.py` мигрированы. Закрывает окно
  bootstrap-но-не-init, где хуки молча пропускали. 3 новых теста.
- **#5 `last_user_prompt_text` bounded tail-read.** Новый
  `_read_transcript_tail()` seek'ает последние 50 KB JSONL транскрипта,
  дропает partial first line на seek-границе. Длинные сессии больше не
  грузят весь файл в память на каждом PreToolUse. 3 новых теста.
- **#6 brain symlinks — AUDIT CLEAN.** `git grep` по
  `copytree|os\.symlink|os\.readlink|os\.lstat|shutil\.` в
  `scripts/brain_*.py` + `agents/claude/mcp/brain/` дал НОЛЬ совпадений.
  Фикс не нужен; сам аудит — deliverable.

### QG hardening batch (этот коммит) — закрывает 5 MED (QG)
- **#1 Negative-scenario detection: regex с negation filter.** Старый
  код делал `kw in ac_text` substring match — "Works without errors"
  удовлетворял gate, потому что "error" substring был внутри. Новый
  `has_negative_scenario(ac_text)` сплитит AC по строкам-критериям
  (обрабатывает inline `1. ... 2. ...` нумерацию), редактирует
  negation-фразы ("no", "without", "never", "нет", "без", "не должно")
  плюс их ~60-char span, потом ищет выжившие NEGATIVE_SCENARIO_KEYWORDS
  на word boundaries. 8 новых тестов.
- **#2 Tier чек-листа учитывает `relevant_files`.** Новая сигнатура
  `_determine_checklist_tier(task, relevant_files=None)`: если
  `is_security_sensitive(relevant_files)` True, tier поднимается до
  `critical` независимо от title. Закрывает кейс где "fix typo"
  (title=trivial) на `scripts/auth.py` получал `lightweight` (4 пункта)
  вместо critical-tier ревью. 3 новых теста.
- **#3 `files_hash` включает 4 KiB content head.** Новый per-file tuple
  `(path, mtime_ns, size, sha256(first_4KiB))`. Закрывает false cache
  hits на ФС с грубым mtime разрешением (FAT/HFS+/SMB) и на
  deliberate `touch -d` revert. Hash format version bumped
  `verification_runs.v1` → `v2`. 3 новых теста.
- **#4 `task_unblock` проверяет session_capacity.** Pre-v1.3.4 байпас:
  агент мог `task_block` затем `task_unblock` чтобы обойти 180-min
  ACTIVE-time чек на `task_start`. Новый `force=True` флаг — audit-logged
  escape hatch. 4 новых теста.
- **#5 `--no-knowledge` отказывается для complex/defect.** SENAR Rule 8
  поднимается с warning до refusal когда `complexity=complex` или
  `defect_of` задан. Complex задачи генерят паттерны, defect задачи —
  root-cause/gotcha записи. Simple/medium non-defect задачи не затронуты.
  5 новых тестов.

### Тесты
- 2332 проходят, 1 skipped (было 2270 в v1.3.3). +62 новых через
  четыре батча.

### Совместимость
- Verify cache: format version bumped (`verification_runs.v1` → `v2`).
  Старые кэш-строки молча инвалидируются новой формой files_hash —
  они не совпадут с новыми хешами. DB миграция не нужна.
- `task_unblock(slug)` работает как раньше для общего пути; новый
  `force=True` keyword — opt-in.
- `task_done(no_knowledge=True)` работает для simple/medium non-defect
  задач. Отказ для complex/defect — агенту нужно убрать флаг (либо
  сначала зафиксировать knowledge).

### Версионирование
- `__version__` bumped 1.3.3 → 1.3.4.

## [1.3.3] — 2026-04-27 — Анти-галлюцинации в `brain init`

Hardening релиз. `tausik brain init` теперь отказывается молча создать
дубликат набора из 4 BRAIN баз когда канонически-озаглавленные уже есть
в том же Notion workspace. Триггер — реальный инцидент: агент во втором
проекте запустил `brain init`, создал параллельный комплект и
рационализировал дубликаты как "per-project DBs для приватности" — что
прямо противоположно дизайну Shared Brain.

### Архитектурное правило (теперь enforced в коде, документации и brain skill)

Shared Brain имеет **ОДИН набор из 4 Notion баз на workspace, общий
для ВСЕХ проектов**. Per-project приватность обеспечивает колонка
`Source Project Hash` на каждой строке, НЕ создание отдельных копий
4 баз для каждого проекта.

### Изменения wizard

- **Pre-flight workspace search.** Перед созданием wizard вызывает
  `POST /v1/search` для канонически-озаглавленных BRAIN баз
  (`Brain · Decisions / Patterns / Gotchas / Web Cache`).
- **Отказ при полном совпадении.** Все 4 найдены → wizard отказывается
  с явной ошибкой и направляет к `--join-existing`.
- **Отказ при частичном совпадении.** 1-3 из 4 найдены → также отказ
  (ambiguous state); пользователь должен либо восстановить недостающие
  базы, либо передать все 4 ID явно через `--decisions-id /
  --web-cache-id / --patterns-id / --gotchas-id`.
- **`--join-existing`** — новый флаг. Полностью пропускает create и
  пишет `.tausik/config.json` с указанием на существующие 4 базы.
  Auto-discovers через search; явные ID перекрывают discovery и
  верифицируются через `databases_query(page_size=1)` перед save.
- **`--force-create`** — новый escape hatch. Обходит duplicate guard
  для редкого случая нового workspace (другой Notion account/integration).
  В interactive mode — extra confirmation prompt.
- **Search failure tolerance.** Если сам workspace search падает
  (network, auth) — wizard логирует warning и продолжает create вместо
  блокировки (defensive default).

### Brain skill (`agents/skills/brain/SKILL.md`)

Добавлен top-of-file ARCHITECTURE блок. Переписан раздел "Brain
disabled?": агенты должны СПРАШИВАТЬ пользователя перед запуском любой
setup-команды, и должны использовать `--join-existing` когда в
workspace уже есть BRAIN. Явное "NEVER guess" + "do not invent
--force-create".

### Документация

`docs/en/shared-brain.md` и `docs/ru/shared-brain.md` — раздел Setup
реструктурирован на "First project — create" / "Second / third project —
join existing", плюс новый блок **Common mistakes** перечисляющий
duplicate-DB pitfall и per-project-copies "privacy" anti-pattern.

### Тесты
- `tests/test_brain_init.py` — 16 новых тестов (find_workspace,
  verify_brain_databases, все 4 ветки wizard'а, search-failure
  tolerance, no-regression на clean-workspace).
- Существующие interactive-wizard тесты обновлены под новый prompt
  order (token first, parent-page-id second).
- Drive-by isolation: `tests/test_edge_cases.py` +
  `tests/test_e2e_workflow.py` нуждались в том же
  `brain_config.load_brain` stub что v1.3.2 добавила в
  `test_service_knowledge_decide.py`. Без него тесты молча роутили
  `decide()` в живой Notion brain.
- `tests/test_skills_maturity.py::test_all_stack_guides_have_valid_stack`
  починен под v1.3 plugin-stack-arch layout (`stacks/<name>/guide.md`).

### Совместимость
- Полностью обратно совместима. Проекты с уже сконфигурированным brain
  не затронуты — guard срабатывает только на самом `brain init`.
  Токены, mirror paths, database IDs и существующие данные не трогаются.

### Версионирование
- `__version__` bumped 1.3.2 → 1.3.3.

## [1.3.2] — 2026-04-28 — Гибкое хранение токена brain

Quality-of-life patch: токен Notion-интеграции для Shared Brain теперь
можно хранить в трёх местах, в порядке приоритета:

1. **`os.environ[NOTION_TAUSIK_TOKEN]`** — высший приоритет. Best для CI/ops.
2. **`.tausik/.env`** — project-local KEY=VALUE файл. Gitignored
   (`.tausik/` полностью игнорируется). Рекомендуется для отдельных
   разработчиков, потому что персистится без shell-rc setup и
   переживает reboot.
3. **`brain.notion_integration_token`** в `.tausik/config.json` —
   эмитит stderr warning ("stored inline; prefer .tausik/.env").
   Допустимо для read-only setup'ов, но не рекомендуется.

### Зачем

До 1.3.2 токен мог жить только в env-переменной. Это создавало трение:
пользователи делали `$env:NOTION_TAUSIK_TOKEN = "..."` в PowerShell,
brain работал в этой сессии, потом ломался после reboot или закрытия
окна. MCP сервер (subprocess IDE) не видел env-переменные, заданные
после старта IDE. Несколько отчётов "brain configured но говорит token
missing".

### Как
- Новый хелпер `brain_runtime.resolve_brain_token(cfg, project_dir=None)`
  — каскад.
- Новый парсер `brain_runtime._parse_dotenv(path)` — минимальный
  KEY=VALUE reader (игнорирует пустые строки, `#` комменты, strip'ает
  кавычки; никогда не raises).
- `brain_runtime._build_notion_client`, `try_brain_write_decision` и
  `try_brain_write_web_cache` теперь используют `resolve_brain_token`
  вместо прямого чтения `os.environ`.
- `brain_config.validate_brain` обновлён: doctor и `brain init` больше
  не репортят "env var not set" когда токен в `.tausik/.env` или
  config.json.
- 7 новых тестов в `tests/test_brain_token_resolve.py` покрывают
  env-wins, dotenv fallback, config-inline + warning, all-empty,
  dotenv parser quotes/comments/whitespace, missing file, default
  env-name fallback.

### Документация
- `docs/en/shared-brain.md` и `docs/ru/shared-brain.md` — Notion token
  UI path обновлён под текущие ntn_/secret_ префикс-варианты.
  Заменена старая секция "export / setx" на 3-option storage cascade
  и cross-platform persistence guide (Linux/macOS/Windows).

### Совместимость
Полностью обратно совместима. Проекты с токеном в env продолжают
работать — env побеждает по приоритету. Миграция config не нужна.

### Версионирование
`__version__` bumped 1.3.0 → 1.3.2. Без 1.3.1 (по указанию пользователя
— один patch на линии 1.3.0).

Файл `.tausik/.env` gitignored (правило `.tausik/` его покрывает).
Токен никогда не попадает в репо.

---

## Более ранние релизы

История до v1.3.2 (включая v1.3.0 docs overhaul, v1.3.1 blind-review
fixes, v1.2.x, v1.1.x, v1.0.x) ведётся в [`CHANGELOG.md`](CHANGELOG.md)
на английском. Если есть запрос на перевод старых записей — открой
issue или скажи в чате.
