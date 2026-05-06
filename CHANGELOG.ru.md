# Changelog (Русская версия)

Все значимые изменения проекта.

Проект следует [Семантическому версионированию](https://semver.org/lang/ru/).

> Английское зеркало: [`CHANGELOG.md`](CHANGELOG.md) — содержит ту же
> структуру плюс полную историю до v1.3.2. RU-версия ведётся параллельно
> начиная с v1.3.2; для более ранних релизов смотри английскую версию.
> При добавлении новой записи держи оба файла синхронизированными.

## [Unreleased] — v1.4.0 polish (Phase B)

### Добавлено

- **Cross-file проверка pytest test-count консистентности (`v14b-doc-gen-test-count`).**
  Follow-up к `v14b-doc-gen-mcp-tool-counts`. Новый `scripts/pytest_test_count.py` запускает `pytest --collect-only -q --override-ini="addopts="` (60s timeout, `stdin=DEVNULL` по gotcha #88) и парсит финальную строку `N tests collected` — возвращает ПОЛНЫЙ размер сьюта независимо от fast-lane `-m 'not slow'` фильтра. `gen_doc_constants.py` добавляет `test_count` в `constants.json` (с сохранением старого значения если collection упал — чтобы транзитная ошибка pytest не отравила payload). Cross-file scanner расширен 4 узкими context-tight паттернами: `pytest suite (N tests)`, badge URL `tests-N%20passed`, badge alt-text `[!N tests]`, markdown bold `**N tests**` — намеренно узкие, чтобы не ловить illustrative фразы типа "Never add 5 tests where one parametrized test covers". Новый CLI-флаг `--skip-test-count` изолирует новый scan; `--skip-cross-files` пропускает все три. Первый прогон по живому дереву всплыл два реальных drift'а: README.md + README.ru.md badge показывали `2590 tests` (реально 3056) и `AGENTS.md` repo-layout `pytest suite (2590 tests)` — исправлено во всех четырёх. Drift в AGENTS.md был внутри fenced code-блока (вырезается scanner'ом); manual fix оставлен поскольку scanner намеренно не заглядывает в fenced-блоки для контроля false-positive'ов. Тесты: +6 кейсов (clean-when-all-match, pytest-suite drift, badge URL+label drift, fenced-code skip, illustrative-numbers safety, изоляция `--skip-test-count`). pytest 3050 → 3056 passed; ruff + mypy чистые.

- **Cross-file проверка MCP tool-count консистентности (`v14b-doc-gen-mcp-tool-counts`).**
  Follow-up к `v14b-doc-gen-cross-files`. `scripts/gen_doc_constants.py --check` теперь также флаги drift'а в формулировках MCP tool-count в `README.md`, `README.ru.md`, `AGENTS.md`, `CLAUDE.md`, `docs/{en,ru}/architecture.md`, `docs/{en,ru}/mcp.md` (последние два добавлены в scan targets) — каждый match `**N tools**`, `N project tools`, `N brain tools`, `(N project + M brain`, ``` `tausik-brain`, N tools ``` сравнивается с `constants.json` (`mcp_project_tools` / `mcp_brain_tools` / `mcp_main_tools`). Паттерны RU/EN-aware (ловят `tools?` и `инструмент(а|ов)?`). Fenced code-блоки вырезаются перед сканированием, чтобы примеры в доках (например `90 project tools (legacy example)`) не триггерили сканер. Новый CLI-флаг `--skip-mcp-counts` отключает только новый scan, оставляя version-ref scan включённым; `--skip-cross-files` по-прежнему отключает оба. Первый прогон по живому дереву вскрыл два реальных drift'а в `docs/{en,ru}/mcp.md`: заголовок `## Shared Brain (`tausik-brain`, 6 tools)` устарел (реально 7), а таблица не содержала `brain_draft_artifact` — оба исправлены, trailing "is 6" в прозе тоже поправлен. Тесты: +6 кейсов (clean-when-all-match, brain-header drift, project drift, project+brain pair drift, fenced-code skip, изоляция `--skip-mcp-counts`). pytest 2917 → 2923 passed; ruff + mypy чистые.

- **Compound RPC `tausik_session_open` для Phase 1 `/start` (`v14b-session-open-compound-rpc-impl`).**
  Один MCP-вызов возвращает JSON-конверт `{session, status, handoff, tasks{active,blocked}, self_check}` — замещает 5 последовательных вызовов (session_start + status compact + last_handoff + task_list active+blocked + self_check) одним round-trip'ом. Каждая под-секция best-effort: при сбое sub-вызова в секцию вставляется inline `error`-ключ, но envelope не падает — `/start` рендерит degraded dashboard. Счёт MCP-инструментов: 99 → 100 (93 project + 7 brain). Phase 1 в SKILL.md схлопнут с "5 параллельных вызовов" до "1 compound call"; CLI fallback при `self_check.drift_detected=true` сохранён.

- **Cross-file проверка version-ref консистентности (`v14b-doc-gen-cross-files`).**
  `scripts/gen_doc_constants.py --check` теперь также обходит
  README.md, README.ru.md, AGENTS.md, CLAUDE.md,
  docs/en/architecture.md, docs/ru/architecture.md и проверяет каждое
  вхождение `vX.Y` / `vX.Y.Z` вне fenced code-блоков против
  `constants.json["tausik_version"]`. 2-part refs (`v1.4`) сверяются
  только по major+minor; 3-part refs (`v1.4.0`) требуют точного
  совпадения. Чужие версионные таймлайны (`SENAR vX`, `Python vX`,
  `OWASP vX`) детектируются 24-символьным lookback'ом и
  пропускаются — эти продукты версионируются независимо. Fenced
  code-блоки вырезаются заменой на пробелы с сохранением номеров
  строк, чтобы `file:line` в отчёте указывал на реальную строку
  источника. Новый CLI-флаг `--skip-cross-files` сохраняет старое
  single-file поведение для контекстов, где doc-scan запускается
  отдельно. Первый прогон по живому дереву всплыл 4 устаревших
  `v1.3` ref в `docs/{en,ru}/architecture.md` (секция Scripts
  утверждала "73 source files (v1.3)" — текущий счёт 117 в v1.4)
  плюс 2 parenthetical `v1.3 CLI handlers` заметки. Все четыре
  обновлены. Тесты: +7 кейсов — clean-when-all-match, minor-drift
  detection, patch-drift detection, foreign-version skip
  (SENAR/Python/OWASP), fenced-code-block skip, run_main cross-file
  drift exit-1, --skip-cross-files preserves legacy. pytest
  2910 → 2917 passed; ruff + mypy чистые.

- **Translation-drift audit: skip-маркер + учёт code-fence'ов (`v14b-audit-translation-skip-marker`).**
  Два улучшения `scripts/audit_translation_drift.py`, закрывающие
  оставшиеся 3 отложенные пары без принудительной structural parity
  на намеренно сокращённых документах. (a) Audit теперь учитывает
  HTML-комментарий `<!-- audit-translation-drift: skip -->`,
  размещённый в любой стороне пары — такие пары перечисляются в
  новой секции "Intentionally abbreviated" и исключаются из подсчёта
  drift'а (и из --check exit-1 триггера). Маркер добавлен в три RU
  саммари, которые уже явно ссылаются на полную EN-версию:
  `docs/ru/claude-md-guide.md`, `docs/ru/brain-db-schema.md`,
  `docs/ru/environment.md`. (b) Regex заголовков теперь вырезает
  fenced-code-блоки перед подсчётом — строки `# BAD` / `# GOOD`
  внутри ` ```markdown ... ``` ` примеров больше не считаются за
  заголовки документа (false-positive, который раньше раздувал EN
  heading count в tutorial-style документах). `audit_pairs()`
  возвращает 4-кортеж `(drifts, en_only, ru_only, abbreviated)`;
  рендереры принимают новый опциональный `abbreviated` арг и
  добавляют секцию "Intentionally abbreviated". Тесты: +7 кейсов
  (skip marker EN/RU стороны, исключение заголовков в code-fence'е,
  fence-close sanity, рендеринг abbreviated, --check exit-0 при
  только abbreviated парах, has_skip_marker форма) — pytest 2903 →
  2910 passed; ruff + mypy чистые. Финальное состояние audit'а:
  нулевой paired drift, 3 intentionally abbreviated, 4 EN-only + 1
  RU-only unpaired (информационно). Полный v14b RU-mirror sweep
  (8 изначально drift'нувших пар) теперь закрыт тремя коммитами.

- **Подбивка RU-зеркал, batch 2: 2 из 5 отложенных пар закрыты bilaterally (`v14b-ru-mirror-sync-batch-2`).**
  Второй проход по drift-отчёту. Закрыто bilaterally:
  `architecture.md` (Δ-2 hd / +2 tbl) — удалена broken пустая 3-кол
  таблица в EN на строках 51-52 (заголовок + separator без строк;
  новый audit-скрипт всплыл это как doc-баг); EN line 18 ASCII art
  `|                |` заменён на `v                v` (regex audit'а
  больше не считает вертикальные `|` пайпы диаграмм за table-separator
  — устранение false-positive); в EN добавлены секции
  `## Hooks (anti-drift)` и `## Memory Aggregates`, переведённые из
  уже существующего RU-контента про регистрацию `scripts/hooks/` и
  `service_knowledge_aggregates.py`. `security.md` (Δ-10 hd / -2 cb)
  — backport 4 RU-only секций в EN: `## Authentication` (Password
  requirements + Cookie security), реструктурирован `## Secrets
  management` с подразделами Never / Do this instead / `.gitignore`
  и fenced `.gitignore` example, реструктурирован `## Audit logging`
  с What to log / What NOT to log, новый `## Checklists` с
  Pre-commit / Pre-deploy. В RU добавлен `## Гарантии TAUSIK`,
  переведённый с существующего EN `## TAUSIK-specific guards`. Обе
  пары теперь в нулевом drift'е.

  Отложено в `v14b-audit-translation-skip-marker`: оставшиеся 3 пары
  (`claude-md-guide.md`, `brain-db-schema.md`, `environment.md`) —
  намеренно сокращённые RU-зеркала, явно указывающие читателю на
  полную EN-версию. Принудительная structural parity ломает их
  дизайн. Follow-up добавит два улучшения audit-скрипта: (a) учёт
  HTML-comment маркера `<!-- audit-translation-drift: skip -->`,
  чтобы сокращённые зеркала отображались в своей секции, а не как
  drift; (b) regex заголовков отслеживает fenced-code-block контекст,
  чтобы triple-backtick markdown-примеры (строки `# BAD` / `# GOOD`
  внутри code fence'ов) не считались за реальные заголовки.

  Drift count: 5 → 3 paired (после batch 1: 8 → 5 + batch 2: 5 → 3);
  pytest 2903 passed; ruff + mypy чистые.

- **Подбивка RU-зеркал, batch 1: закрыто 3 из 8 drift-пар (`v14b-ru-mirror-sync-batch`).**
  Первый проход по drift-отчёту нового translation-drift скрипта.
  Закрыто: `docs/ru/stacks.md` (удалён RU-only список
  `## DEFAULT_STACKS (25)` — TODO followup: добавить его в
  `docs/en/stacks.md`); `docs/ru/upgrade.md` (удалены RU-only
  секции `## Версионная политика` и `## См. также` — TODO followup:
  бэкпортировать обе в `docs/en/upgrade.md`); `docs/ru/senar-compliance-matrix.md`
  (добавлен пропущенный подраздел `### Gaps и план закрытия` с
  gap-таблицей в зеркало EN-овского `### Gaps and Plan to Close`).
  Отложено в `v14b-ru-mirror-sync-batch-2` с пояснением по каждому:
  `architecture.md` — EN имеет broken пустую таблицу на строках 51-52,
  закрытие parity требует правки EN (заблокировано
  one-direction-sweep AC); `security.md` — RU имеет 10+ лишних
  секций, требуется informed review (RU устарел или EN дропнул
  контент); `claude-md-guide.md` (Δ+21 заголовок),
  `brain-db-schema.md` (Δ+10 hd / +6 tbl), `environment.md`
  (Δ+43 hd / +12 cb / +4 tbl) — последние три требуют реальной
  работы по переводу, скоупиться отдельной сессией. Drift count:
  8 → 5 paired; полный pytest всё ещё зелёный (нулевая регрессия
  на markdown-only правках).

- **Скрипт аудита translation-drift (`v14b-junk-translation-drift-audit`).**
  Новый `scripts/audit_translation_drift.py` сообщает о структурном
  расхождении EN/RU зеркал документации (`docs/en/foo.md` ↔
  `docs/ru/foo.md`) по трём грубым метрикам на пару: число ATX
  заголовков (`#`..`######`), число fenced code-блоков (тройные
  backtick'и), число markdown-таблиц (по separator-строкам
  `|---|---|`). Парность по basename — секции `paired-with-drift`,
  `en-only`, `ru-only` рендерятся отдельно. Три режима, повторяющие
  `audit_stale_docs.py`: дефолтный markdown-отчёт, `--json`, `--check`.
  Дефолтный режим всегда advisory (exit 0 даже при наличии drift'а).
  `--check` возвращает 1 ТОЛЬКО при drift'е на спаренных файлах,
  никогда — на одиноких файлах (они информационные). Pure-stdlib
  (`re` + `pathlib` + `argparse` + `json`); нет NLP, нет семантического
  сравнения, нет auto-fix, нет интеграции в pre-commit hooks или
  `gate_runner.py`. Первый прогон по живому дереву surface'ит 8 пар
  с drift'ом (architecture, brain-db-schema, claude-md-guide,
  environment, security, senar-compliance-matrix, stacks, upgrade)
  плюс 4 EN-only и 1 RU-only документа — ровно та видимость, ради
  которой spin-off задумывался. Тесты: 14 кейсов в
  `tests/test_audit_translation_drift.py` покрывают подсчёт метрик,
  детекцию drift'а на каждой метрике, категоризацию unpaired,
  exit-коды и JSON-shape. ruff + mypy чистые; полный pytest
  2889 → 2903 passed (+14, нулевая регрессия).

### Изменено

- **Filesize debt paydown: `scripts/service_gates.py` 653 → 368 на три
  файла (`v14b-service-gates-debt-paydown`).**
  Финальный filesize-debt кандидат в v1.4-tail треде (после
  `tools_extra` / `project_backend` / `bootstrap_copy` / `brain_init`).
  `service_gates.py` нёс 253 строки сверх 400-строчного gate'а. Сплит
  по ответственности, не по количеству строк (Pattern #91): QG-0
  Context Gate (`check_qg0_start` плюс кортежи ключевых слов
  `SECURITY_KEYWORDS` и `SECURITY_AC_KEYWORDS`, к которым он
  обращается) вынесен в новый `scripts/gate_qg0_check.py` (171
  строка); QG-2 хелперы для acceptance criteria, завершения плана и
  SENAR Rule 5 checklist (`verify_ac`, `verify_plan_complete`,
  `determine_checklist_tier`, `check_verification_checklist`)
  вынесены в новый `scripts/gate_ac_check.py` (223 строки) как
  чистые функции, которые принимают task dict и возвращают
  предупреждения либо поднимают `ServiceError`. Verify-pipeline и
  методы Verify-First Contract остались в `service_gates.py`,
  поскольку зависят от `self.be._conn` / `self.be.task_append_notes`.
  `GatesMixin` сохраняет те же публичные имена методов
  (`_check_qg0_start`, `_verify_ac`, `_verify_plan_complete`,
  `_determine_checklist_tier`, `_check_verification_checklist`) —
  они теперь делегаторы из 2-3 строк. `_check_qg0_start` пробрасывает
  опциональные коллбэки `audit_check` / `session_check_duration`
  через `getattr(self, ..., None)` вместо прежнего внутреннего
  `try/except (AttributeError, ...)` — так чистая функция работает
  за пределами `ProjectService` (например, на голых экземплярах
  `GatesMixin` в юнит-тестах). Обратная совместимость сохранена:
  `from service_gates import SECURITY_KEYWORDS`,
  `SECURITY_AC_KEYWORDS`, `has_negative_scenario`,
  `NEGATIVE_SCENARIO_KEYWORDS`, `qg0_dimensions_score` и
  `check_qg0_start` продолжают работать через re-export с
  `# noqa: F401`. Результат: полный pytest зелёный (2889 passed /
  7 skipped / 120 deselected); 244 тестов на гейты прицельно
  зелёные; ruff + mypy чистые на трёх файлах; filesize gate PASS
  для `service_gates.py` (368 < 400) без exemption. Массив
  `exempt_files` в filesize-gate остаётся пустым — весь debt-тред
  структурно чист.

- **Filesize debt paydown: `scripts/brain_init.py` 722 → 367 на четыре
  файла (`v14b-followup-brain-init-filesize-debt`).**
  У модуля brain init wizard висел липкий 322-строчный exempt в
  `.tausik/config.json` `gates.filesize.exempt_files` ещё со времён
  v1.4 split'а, который вынес `brain_discovery.py`. Чтобы погасить
  долг без изменения семантики, поделили wizard по ответственности,
  а не по строкам: schemas + Notion DB ops переехали в новый
  `scripts/brain_init_schemas.py` (186 строк — `CATEGORIES`,
  `DB_TITLES`, четыре `_<category>_schema()`-хелпера, `_SCHEMAS`
  диспатч, `db_schema`, `PartialCreateError`, `create_brain_databases`,
  `verify_brain_databases`); ветка `--join-existing` + post-create
  config save мигрировала в `scripts/brain_init_join.py` (190 строк —
  `run_join_branch`, `_finalize_join`, полные диагностики для
  integration-not-shared / non-canonical-titles); ветка
  `--force-create` / clean-workspace ушла в
  `scripts/brain_init_create.py` (138 строк — `run_create_branch` с
  prompt'ами parent_page_id / project_name, регистрацией,
  orphan-cleanup guidance для partial creates и post-create save
  failures). `brain_init.py` оставил себе dispatcher: token
  resolution, pre-flight `users.me()`, workspace search, branch
  selection (Branch B/C refusals остались inline, Branch A/D
  делегируют новым модулям), CLI IO classes (`WizardIO`, `ConfigOps`,
  `WizardError`, `CliIO`), shared helpers
  (`_print_orphan_cleanup_guidance`, `_has_existing_brain`,
  `_collect_explicit_join_ids`), `merge_brain_config`. Все 19
  публичных имён, которые тесты или другие модули исторически
  импортировали из `brain_init.*` (CATEGORIES, DB_TITLES, db_schema,
  create_brain_databases, verify_brain_databases, merge_brain_config,
  PartialCreateError, WizardError, WizardIO, ConfigOps, CliIO,
  run_wizard, _finalize_join, _has_existing_brain,
  _collect_explicit_join_ids, _print_orphan_cleanup_guidance,
  find_workspace_brain_databases, inspect_workspace_brain_databases,
  _extract_db_title), re-export'нуты через `# noqa: F401`, так что
  тестовый код менять не пришлось вообще. `import
  brain_project_registry` остался на module-level в `brain_init.py`,
  чтобы существующий `monkeypatch.setattr(brain_init.brain_project_registry,
  ...)` в `test_brain_init.py:559` продолжал работать — модули в
  `sys.modules` это singleton'ы, патч проброшен в `brain_init_create.py`
  через тот же объект. Cycle избежан через ленивые импорты
  `run_join_branch` / `run_create_branch` внутри `run_wizard`. Итого:
  все 69 кейсов `tests/test_brain_init.py` зелёные, плюс 192 более
  широких brain-тестов проходят; ruff + mypy чисты по всем 4 файлам;
  filesize gate PASS для всех четырёх; `scripts/brain_init.py`
  удалён из `.tausik/config.json` `gates.filesize.exempt_files`
  (строковая запись убрана, массив пуст).

- **Filesize debt paydown: `bootstrap/bootstrap_copy.py` 420 → 311
  (`v14b-bootstrap-copy-debt-paydown`).**
  Skill-специфичные хелперы (`parse_skill_frontmatter`,
  `validate_skill_frontmatter`, `_resolve_skill`, `_generate_stub`,
  `_load_registry` плюс константы `VALID_CONTEXT` / `VALID_EFFORT`)
  вынесены в новый `bootstrap/bootstrap_skill_helpers.py` (139 строк).
  `bootstrap_copy.py` re-export'ит имена с `# noqa: F401`, чтобы все
  внешние импорты продолжили работать без изменений: `bootstrap.py`
  (через `copy_skills`, который замыкает `_resolve_skill`),
  `scripts/skill_profile.py` (`parse_skill_frontmatter`),
  `tests/test_bootstrap_frontmatter.py` (обе frontmatter-функции),
  `tests/test_vendor.py`, `tests/test_v13_hardening.py`,
  `tests/test_copy_symlinks_disabled.py`. Импорт `import re` тоже
  ушёл из `bootstrap_copy.py` — нужен только новому хелпер-модулю.
  Поведение байт-в-байт идентично: повторный
  `python bootstrap/bootstrap.py --ide claude --smart` после split'а
  не дал ни одного diff'а в `.claude/`. 76 bootstrap-тестов
  (frontmatter + vendor + non-destructive + symlink-disable +
  v13-hardening) зелёные. Filesize gate clean для обоих файлов.

- **Filesize debt paydown: `scripts/project_backend.py` 403 → 327
  (`v14b-project-backend-debt-paydown`).**
  67-строчный метод `_init_schema` (DDL bootstrap + version-guard +
  migration backup + FTS rebuild) вынесен в free function
  `init_schema(conn)` в новый `scripts/backend_init.py` (96 строк).
  `SQLiteBackend.__init__` вызывает её напрямую; метод удалён, других
  caller'ов кроме `__init__` не было. Поведение байт-в-байт идентично:
  тот же skip-DDL-если-current-version путь, тот же `RuntimeError` на
  newer-than-code on-disk schema, тот же идемпотентный `.bak.v<old>`
  backup перед `run_migrations`, тот же FTS rebuild для
  `fts_{tasks,memory,decisions}`. Импорты `shutil` + `run_migrations`
  переехали в новый модуль — `project_backend.py` их больше не ссылает.
  Full pytest 2889 passed (0 регрессий). Ruff + mypy clean.

- **Preempt-split `harness/{claude,cursor}/mcp/project/tools_extra.py`
  (`v14b-tools-extra-preempt-split`).**
  Файл был на 399/400 строк после приземления session-open compound RPC —
  одна следующая добавка tool schema упёрлась бы в filesize gate. Roles
  CRUD (`tausik_role_{list,show,create,update,delete,seed}`) и
  `tausik_stack_scaffold` вынесены в новый список
  `tools_extra_admin.TOOLS_EXTRA_ADMIN` (admin / config-modifying tools —
  когезивная тематическая группа). `tools.py` импортирует оба списка и
  extends `TOOLS` каждым. После split: `tools_extra.py` 317 строк (было
  399), `tools_extra_admin.py` 97 строк. Tool count не изменился (93
  project + 7 brain = 100 total, sanity-check: дубликатов нет, все 7
  admin tools резолвятся после split). Cursor mirror байт-в-байт
  идентичен. Bootstrap регенерирует `.claude/mcp/project/tools_extra_admin.py`
  рядом с существующей копией. Full pytest 2889 passed (mirror-sync тесты
  `test_mcp_mirrors_in_sync` + `test_mirror_in_sync` падали до bootstrap'а
  — ожидаемо; после ресинка `.claude/` зелёные).

- **Source-директория `agents/` переименована в `harness/` (`v14b-rename-harness`).**
  Устраняет долгую коллизию с нативным `.claude/agents/` namespace в
  Claude Code (профили sub-agents). `git mv` сохраняет историю;
  bootstrap-скрипты, docstrings, комментарии, тесты и help-тексты CLI
  все обновлены и читают из `harness/`. Чистый разрыв — без backward-
  compat alias на старый путь. **Миграция:** если есть форк или локальный
  скрипт с захардкоженным source-путём, замени `agents/skills/`,
  `agents/roles/`, `agents/stacks/`, `agents/{ide}/mcp/`,
  `agents/overrides/`, `agents/schemas/`, `agents/aidd-templates/` на
  соответствующий `harness/...`. Три понятия намеренно остались как
  `agents/`: хостовая `.claude/agents/` (sub-agents в Claude Code),
  vendor-skill `agents/` namespace внутри vendor-tarball (всё ещё
  устанавливается в хостовую `.claude/agents/`), и внутренний подкаталог
  `harness/skills/review/agents/<name>.md` (инструкции параллельных
  ревьюеров в `/review` — это не framework-source `agents/`).
  Проверено: pytest 2812 passed, `tausik doctor` clean, bootstrap dry-run
  + полный прогон чисто регенерируют `.claude/`, `.cursor/`, `.qwen/` из
  `harness/`.

### Изменено

- **Дедуп пути `.tausik/config.json` (`v14b-review57-followups` M2).**
  Новый helper `tausik_utils.tausik_config_path(project_dir)` — единый
  источник истины, заменяет 8 inline-сайтов
  `os.path.join(project_dir, ".tausik", "config.json")` в
  `bootstrap/bootstrap.py`, `bootstrap/bootstrap_modes.py`,
  `harness/{claude,cursor}/mcp/project/handlers.py` (cq-клиент),
  `harness/{claude,cursor}/mcp/project/handlers_skill.py` (`_skill_paths`),
  `scripts/project_cli_extra.py` и
  `scripts/hooks/session_cleanup_check.py`. Регрессионный тест
  (`tests/test_tausik_utils.py::test_no_inline_duplicates_in_production`)
  сканирует `scripts/`, `harness/`, `bootstrap/` и падает на любых
  будущих inline-дубликатах.

- **`/start --brain` opt-in primer документирует `brain.ignored:` фильтр
  (`v14b-review57-followups` M1).** `harness/skills/start/SKILL.md`
  теперь говорит агенту фильтровать page id с префиксом
  `brain.ignored:` в `tausik_memory_list type=convention` — та же
  дисциплина, что в /task и /plan. Регрессия в
  `tests/test_tausik_utils.py` гарантирует, что строка не отвалится.

  /review session #57 L1 (preempt-split `scripts/project_cli_extra.py`
  до 400-line gate) — no-op: файл оказался 353 строки, ниже порога.

### Добавлено

- **Структурированный `--evidence-json` для `task done` (`v14b-token-t15-evidence-json`).**
  Новый флаг принимает JSON от агента:
  `{"ac_evidence":[{"n":1,"status":"pass","evidence":"tests/foo.py::test_bar"}, ...]}`
  с опциональными per-item флагами `manual` / `negative`. Хелпер
  `service_ac_evidence.evidence_json_to_prose()` конвертирует JSON в
  каноническую prose-форму ("AC verified: 1. ✓ ..."), которая дальше
  проходит через существующий пайплайн `task_log` +
  `service_ac_evidence` без изменений. Mutually exclusive с
  `--evidence` (argparse отвергает на уровне CLI;
  `_task_done_report` дублирует проверку для MCP-вызовов). MCP-tool
  `tausik_task_done` получил аргумент `evidence_json` с теми же
  семантиками; полная обратная совместимость — prose-форма
  `--evidence` / `evidence` работает как раньше. Тесты в
  `tests/test_ac_evidence_json.py` — 19 кейсов (5 positive с round-trip
  по 3 AC, 12 negative по схеме, 1 SQL-payload, 1 service-layer mutex).

- **AIDD project scaffold (`v14b-aidd-scaffold-basic`).** Новая CLI-подкоманда
  `tausik init --template aidd` копирует три слойных шаблона —
  `idea.md`, `vision.md`, `conventions.md` — из `harness/aidd-templates/`
  в корень текущего проекта. Conflict detection: каждый существующий
  файл триггерит 4-option prompt (overwrite / merge-append / skip /
  abort-all); empty-ввод или unknown-выбор → skip с предупреждением.
  `--force` обходит prompt и перезаписывает каждый конфликт.
  `merge-append` сохраняет существующий контент и дописывает шаблон под
  маркером `<!-- merged from AIDD template -->`. Новый модуль
  `scripts/project_cli_aidd.py` (handler), `scripts/project_parser.py`
  + `scripts/project_cli.py` расширены `--template` / `--force`.
  v1.5 follow-ups записаны как stories в эпике `v15-cross-ide-parity`:
  `v15-aidd-autogen` (autogen `vision.md` из существующего кода) и
  `v15-aidd-ai-validation` (drift detection между AIDD-слоями и
  фактическим кодом). Тесты (`tests/test_aidd_scaffold.py`): 14 кейсов —
  resolve-choice mapping (empty / first-letter / unknown), template-name
  whitelist, scenarios (clean dir, partial conflict, full conflict
  default-skip, `--force` перезаписывает всё без prompt, явные `o` / `m`
  choices, `abort-all` short-circuits оставшиеся файлы), CLI dispatch
  (unknown template → exit 2 + stderr; happy path → exit 0).
  Smoke-tested end-to-end через `python scripts/project.py init --template aidd`
  в чистом tmp-dir. Docs: `docs/en/cli.md` + `docs/ru/cli.md` документируют
  новые флаги и семантику conflict-prompt.

- **Скрипт валидации prompt caching + docs (`v14b-token-t13-prompt-caching-docs`).**
  Новый `scripts/validate_prompt_caching.py` парсит транскрипт Claude Code
  (JSONL — `--auto` ищет свежайший, либо передай путь явно) и выдаёт
  `cache_creation_input_tokens`, `cache_read_input_tokens`, hit-rate и
  классификацию: exit 0 = caching активен, 1 = префикс нестабилен
  (creation > 0, reads = 0), 2 = API вообще не вернул cache-поля,
  64 = ошибочный CLI / файл не найден. Новая секция «Prompt caching» в
  `docs/{en,ru}/architecture.md` перечисляет кешируемые поверхности
  (system prompt + tool schemas, CLAUDE.md, описания MCP-инструментов,
  SKILL.md) и инвалидаторы (главный — `tausik_update_claudemd` в середине
  сессии). Новая секция «Prompt caching не активен» в
  `docs/{en,ru}/troubleshooting.md` сопоставляет низкий / нулевой hit-rate
  с причинами (сторонняя оболочка не шлёт `cache_control`, правка
  CLAUDE.md между ходами, правки агентских артефактов в worktree). Жёсткий
  prerequisite для `v14b-baseline-token-metrics` — та задача меряет
  токены, эта — фиксирует, что измерения идут на стабильном кеш-режиме,
  а не на шумном. Тесты: `tests/test_validate_prompt_caching.py` покрывает
  парсер (извлекает оба поля, обработка отсутствующих полей, top-level
  и nested usage, пустые строки, явный 0 в cache-поле всё равно считается),
  классификатор (3 exit-кода), CLI-диспетч (missing file, без аргументов,
  active-cache happy path). 11 тестов зелёные; mypy чисто.

### Изменено

- **Active-time сессии переведено с "exclude" на "clip" semantics
  (`v14b-session-active-time`).** `compute_active_minutes` (и новый
  компаньон `compute_active_seconds`) раньше выбрасывал любой
  inter-tool-call gap ≥ `idle_threshold` из суммы (gap → 0). Bounded-deltas
  intent в SENAR Rule 9.2 всегда был "каждый gap считается максимум
  threshold секунд", иначе многодневная сессия с одним коротким
  всплеском работы в день записывала бы near-zero active и никогда не
  упиралась в лимит 180 мин. v1.4 polish меняет SQL CASE с `THEN 0` на
  `THEN ?` (клипуется до `idle_threshold_seconds`): длинный AFK теперь
  добавляет ровно `idle_threshold` (default 600 с / 10 мин) к active.
  Sub-minute precision выставлен через
  `backend_session_metrics.compute_active_seconds`,
  `service_session_metrics.session_active_seconds`,
  `ProjectService.session_active_seconds`, и новое поле `active_seconds`
  в обоих `tausik_status` MCP-ответах (claude + cursor handlers) рядом
  с существующим `active_minutes`. `recompute_all_sessions` теперь тоже
  возвращает `active_seconds` per-row. **Изменение поведения:** сессии,
  ранее логгировавшие 0-min "long AFK gap", теперь покажут на ~10 мин
  больше active — Rule 9.2 будет корректно энфорсить 180-минутный
  бюджет на сессиях, которые раньше под-считывались. Тесты:
  `test_backend_session_metrics::TestComputeActiveSeconds` добавляет
  9 кейсов на AC-сценарии (a) короткая сессия, (b) 30-min gap клипуется,
  (c) 180 мин триггерит warning, + негативные сценарии (нет событий,
  long AFK держит active низким, non-monotonic timestamps best-effort,
  sub-minute precision, округление wrapper'а минут). Существующий
  `test_gap_above_threshold_excluded` переименован в
  `_clipped_not_excluded` с ассертом 10 → 20 мин. `test_custom_threshold`
  обновлён: gap при threshold даёт threshold (5 мин), не 0. Доки:
  `docs/{en,ru}/session-active-time.md` переписаны вокруг clip-формулы
  `Σ min(Δ, idle_threshold)`; `senar-compliance-matrix.md` +
  `agent-contract.md` (RU) обновлены в строке Rule 9.2. 24
  backend-metric теста + полный fast lane проходят.

- **MCP-инструмент `tausik_task_done_v2` удалён — единый
  `tausik_task_done` возвращает structured JSON
  (`v14b-task-done-rename-drop-v2`).** Промежуточный alias `_v2`,
  добавленный в 1.3.7 (пока обкатывали structured-JSON контракт),
  вызывал постоянную путаницу: скиллы носили fallback-текст ("звони
  v2; если нет — fall back на v1"), в `troubleshooting.md` была
  целая секция "v2 vs v1", PostToolUse-матчер тащил оба имени.
  Консолидация: единственный MCP-инструмент — `tausik_task_done`,
  всегда возвращает structured-response dict (`ok`, `gates`,
  `blocking_failures`, `cache_status`, …). Внутренне: метод
  `service_task.py::task_done_v2` удалён; str-возвращающий
  `task_done()` оставлен для CLI-команды (`scripts/project_cli.py`)
  — там backward compatible. В `agents/{claude,cursor}/mcp/project/
  handlers.py::_do_task_done` теперь напрямую вызывается
  `_task_done_report()` и JSON-encode'ится; `_do_task_done_v2`
  удалён из обоих handlers и `_DISPATCH`; `tools.py` дропает
  дубликат tool definition `tausik_task_done_v2` (счёт project
  tools: 93 → 92, итого с brain: 100 → 99). Матчер PostToolUse в
  `bootstrap_hooks.py`: `tausik_task_done|tausik_task_done_v2` →
  `tausik_task_done`. `scripts/hooks/_common.py::_TASK_DONE_TOOL_NAMES`
  упрощён до двух канонических форм. Тесты:
  `tests/test_task_done_v2_matcher.py` → переименован в
  `test_task_done_matcher.py`, проверяет отсутствие `_v2`;
  `test_project_mcp.py::test_task_done_v2_returns_structured_json` →
  `test_task_done_returns_structured_json` против канонического
  имени; `test_mcp_integration.py` и `test_verify_first_contract.py`
  обновлены. Скиллы (`/task`, `/ship` SKILL.md + variants/{haiku,
  sonnet}.md) убрали гайд "fall back на legacy v1"; доки
  (`mcp.md`, `troubleshooting.md`, `quickstart.md`, `hooks.md` EN+RU
  + AGENTS.md + QWEN.md + READMEs) почищены от `_v2` упоминаний и
  tool counts обновлены (100 → 99, 107 → 106 с codebase-rag).
  **Breaking** для любого агента или сторонней тулзы, вызывающей
  `mcp__tausik-project__tausik_task_done_v2` напрямую — переключайся
  на `mcp__tausik-project__tausik_task_done` (та же input schema,
  тот же structured-JSON return). Тесты: 2741 passed, 7 skipped,
  118 deselected.

### Исправлено

- **Verify-First STRICT vs relaxed асимметрия между `has_fresh_verify_run`
  и `run_gates_with_cache` (`v14b-verify-first-relaxed-symmetry`,
  gotcha #111).**
  `service_verification.run_gates_with_cache` уже принимал односторонний
  relaxed-матч (Sharp edge #2: `tausik verify` запущен с `files=[]`
  manual scope, последующий `task done` приходит с явными
  `relevant_files`), а `verify_cache.has_fresh_verify_run` — функция,
  которую дёргает QG-2 verify-first guard в
  `service_gates._enforce_verify_first` — делал только STRICT lookup.
  Результат: `task done <slug> --relevant-files scripts/foo.py` поверх
  свежего `tausik verify --task <slug>` (без `--relevant-files`)
  возвращал `cache_status='git-mismatch'`, хотя heavy gates только что
  прошли. Натыкались три сессии подряд до структурного фикса. Теперь
  `has_fresh_verify_run` после strict-miss зеркалит relaxed-фолбэк:
  принимает свежий exit-zero verify-trigger row с `files=[]` в
  записанной command, отбрасывает строки с конкретными файлами
  (обратное направление остаётся strict — mtime / gate-signature
  инвалидация продолжает работать) и отбрасывает строки из task-done
  бакета (контракт cache-bucket separation сохранён). Security-чувствительные
  пути коротятся существующей проверкой `is_cache_allowed` — до relaxed
  ветки не доходят.
  `verify_recent_lookup.lookup_any_fresh_run_for_task` получил опциональный
  параметр `command_prefix` — фильтр trigger=verify| применяется в SQL.
  Без него вклинившийся task-done bucket row между `tausik verify` и
  последующим `task done` затенял бы verify row через бо́льший id под
  `ORDER BY id DESC LIMIT 1` (точно этот failure mode словили в
  dogfood-верификации фикса).
  Тесты: `tests/test_verify_cache.py` (9 кейсов —
  manual→explicit принятие в т.ч. multi-file, strict-приоритет-над-relaxed,
  reverse-direction reject, interleaved-bucket-shadowing, security
  short-circuit с strict row, no-row miss, red-row miss). Full pytest
  2889 passed (было 2880, +9 новых, 0 регрессий).

- **Brain `--join-existing` discovery не находил переименованные БД
  (`v14b-defect-brain-enable-no-discovery`).**
  `find_workspace_brain_databases` сматчивал кандидатов в Notion
  только точным сравнением title с `DB_TITLES`
  (`Brain · Decisions / Web Cache / Patterns / Gotchas`). Если 4 BRAIN
  БД существовали под любым другим title — переименование в UI,
  emoji-префикс, перевод, или они были созданы вне wizard'а с
  category-only названиями (`decisions` / `web_cache` / `patterns` /
  `gotchas`) — discovery возвращал `{}`, а wizard выдавал
  misleading-сообщение «integration not shared with the BRAIN page»,
  хотя integration видел БД нормально.
  Теперь discovery в два прохода: сначала title-match (happy path
  не меняется, ноль лишних API-вызовов), потом schema-fallback —
  скан непривязанных visible БД с проверкой что Notion `properties`
  содержат required-набор для категории. Discovery также теперь
  не передаёт `query="Brain"` в `search()` — этот префильтр тихо
  отбрасывал БД без этого слова в title. Ветка A `run_wizard`
  при пустом discovery дёргает новый помощник
  `inspect_workspace_brain_databases()` и выдаёт enriched-ошибку
  со списком visible кандидатов (id, title, parent page) и двумя
  путями (переименовать канонически или передать IDs явно), чтобы
  пользователь мог сам поставить диагноз без чтения исходников.
  Сообщение «integration not shared» сохранено для visible-zero
  случая, где это всё ещё правильный диагноз.
  Discovery вынесен в `scripts/brain_discovery.py`, чтобы
  `brain_init.py` оставался сфокусированным. Тесты: 69 проходят
  в `tests/test_brain_init.py` (10 новых — schema-fallback positive,
  mixed title+schema, schema conflicts, enriched error, регрессия
  share-via-Connections). Live evidence на этом проекте: 4 БД с
  title `decisions` / `web_cache` / `patterns` / `gotchas` (без
  `Brain ·` префикса) сматчены через `via=schema`, ID идентичны
  тем, что были вручную указаны раньше.

- **Token metrics никогда не писались в production
  (`v14b-defect-token-metrics-no-realworld-write`,
  defect_of=`v14b-baseline-token-metrics`).** `.tausik/token_metrics.jsonl`
  тихо оставался пустым во всех реальных сессиях, потому что оригинальный
  PostToolUse-хук (`scripts/hooks/token_metrics.py`) читал
  `tool_response.usage` из harness-payload — поле, которое Claude Code
  никогда не заполняет per-tool-call (token usage существует только на
  уровне message). Хук был юнит-тестирован против синтетических payloads,
  которые подделывали это поле — поэтому CI зелёный, а в production тишина.
  По решению #61 capture перенесён в существующий SessionEnd transcript-
  parser (`scripts/hooks/session_metrics.py`): новый `extract_token_rows`
  проходит по каждой assistant-записи, делит message-level `usage` поровну
  между `tool_use` блоками (последний блок забирает остаток integer-
  деления, чтобы суммы оставались точными), а `append_token_rows` пишет
  ту же схему, которую уже потребляет `service_token_metrics.aggregate()`.
  Сломанный PostToolUse-хук удалён из `bootstrap/bootstrap_hooks.py` +
  `bootstrap/bootstrap_qwen.py`; `scripts/hooks/token_metrics.py` остался
  no-op stub'ом, чтобы живые IDE-инстансы со старым hook-конфигом не
  падали до перезапуска (удалить после рестарта IDE). Тесты: 26 кейсов
  в переписанном `tests/test_token_metrics.py` (aggregator, row
  extractor, appender, session_id resolver, end-to-end). End-to-end
  проверка: прогнали на живом transcript сессии #55 и получили 73
  строки по 22 тулам, `tausik metrics tokens` корректно отрендерил
  таблицу с доминированием cache_read над input_tokens (ожидаемо под
  prompt caching).
- **`tausik_self_check.sibling_mcp_count` хронический +1 false-positive
  на Windows venv (`v14b-defect-mcp-self-check-venv-launcher`,
  defect_of=`v14b-mcp-stale-module-detector`).** Каждый рестарт IDE
  оставлял `sibling_mcp_count=1` даже на чистой машине, постоянно
  подталкивая пользователя к "Restart your IDE" — тот же симптом,
  который мы принимали за реальный в сессиях #49/#50/#51. Корень: на
  Windows `venv\Scripts\python.exe` — это launcher SHIM, который
  re-execs настоящий интерпретатор (`C:\Python311\python.exe`) как
  CHILD-процесс, сохраняя тот же `CommandLine`; родитель поэтому
  совпадает с тем же фильтром `mcp/project/server.py --project <project>`
  что и child и засчитывается как "sibling MCP". POSIX редко показывает
  такую форму (venv обычно отдаёт PID настоящего интерпретатора
  напрямую), но guard унифицирован. Фикс: `_enumerate_sibling_mcps`
  захватывает `os.getppid()` на входе и исключает этот PID на каждом
  introspection backend (wmic, PowerShell `Get-CimInstance`, `/proc`
  walk, `ps -A` fallback). Зеркалится в
  `agents/cursor/mcp/project/self_check.py`. Регрессионный тест:
  `tests/test_mcp_self_check.py::test_enumerate_excludes_parent_pid_venv_launcher`
  мокает PowerShell-ветку тремя строками (parent + self + real sibling)
  и утверждает что считается только настоящий sibling. Существующие 6
  self-check тестов + 2 windows-fallback не меняются. Проектная память:
  gotcha #87 документирует venv-launcher механизм.
- **MCP `task_done_v2` 10-секундный тихий хэнг — корень найден после
  5-дневного расследования (`v14b-defect-mcp-task-done-stdin-hang`).**
  `tausik_task_done_v2` стабильно проводил ~10 секунд в cache-lookup пути
  перед возвратом, наблюдалось в сессиях #47–#51. Предыдущие фиксы
  (диагностика `tausik_self_check` в `v14b-mcp-stale-module-detector`,
  wmic→PowerShell fallback в `v14b-defect-mcp-self-check-windows-fallback`)
  лечили периферийные симптомы — ни один не поймал настоящую причину.
  Корень нашли через timing-пробы внутри MCP-сервера:
  `is_declared_consistent_with_git_diff` в `scripts/verify_git_diff.py`
  вызывает `subprocess.run(["git", "log", "--since=...", ...],
  capture_output=True, timeout=10)` и `git diff --name-only HEAD`.
  `subprocess.run` с `capture_output=True` НЕ редиректит stdin — child
  наследует stdin родителя. Внутри `asyncio.to_thread` воркера MCP-сервера
  stdin = JSON-RPC pipe к IDE. На Windows git блокируется при попытке
  чтения с этого pipe (paginator probe / credential prompt detection /
  общий stdin handling) пока не сработает таймаут 10s; except-ветка
  затем defensively возвращает `None` и
  `is_declared_consistent_with_git_diff` возвращает `True`
  ("git упал → считаем cache OK" fallback), маскируя хэнг как
  successful-but-slow `cache_status=hit`. Фикс: добавить
  `stdin=subprocess.DEVNULL` в проблемные `subprocess.run`-вызовы.
  Эмпирический замер: MCP `task_done_v2` упал с 10031ms до 63ms —
  **ускорение в 159 раз** — в end-to-end JSON-RPC харнесе против
  свежего MCP-сервера. Запатчены: `scripts/verify_git_diff.py` (обе
  git-пробы), `scripts/project_service.py` (session_metrics spawn),
  `scripts/project_cli_extra.py` (git branch detection),
  `scripts/skill_manager.py` (git pull, git clone, pip install). Все
  четыре достижимы из worker-потока MCP project server. Тесты:
  `tests/test_verify_git_diff_stdin.py` (НОВЫЙ) утверждает что
  `subprocess.run` вызывается с `stdin=subprocess.DEVNULL` на обеих
  git-пробах — защита от регрессии. Проектная память: gotcha #88
  документирует правило ("subprocess.run внутри MCP worker ОБЯЗАН
  передавать `stdin=subprocess.DEVNULL`") и рецепт обнаружения
  (grep `subprocess\.(run|Popen)\(` без `stdin=`, триаж по достижимости
  из MCP-хендлеров). Decision #56 закрепляет конвенцию проектно.
  **Урок** (сохранён как gotcha): диагностика может маскировать баги,
  которые выглядят как таймауты — когда подозрителен 10-секундный
  потолок, ищи defensive except-ветки, проглатывающие
  `subprocess.TimeoutExpired`.
- **Brain включён, но не сконфигурирован — тихий fallback
  (`v14b-defect-brain-decisions-empty`).** Когда в `.tausik/config.json`
  стояло `brain.enabled=true`, но `database_ids` были пусты (или env-токен
  не задан), `tausik_decide` тихо сваливался в локальный SQLite с
  невзрачной причиной "brain write failed: config_error:
  brain.database_ids.decisions is empty". Пользователи копили
  local-only решения, которые должны были зеркалиться в Notion, не
  замечая, что brain-конфиг сломан. Корень: `brain_config.validate_brain()`
  существовал и ловил проблему, но в продовом коде его никто не вызывал —
  только тесты. Фикс: (1) `service_knowledge.decide()` теперь вызывает
  `validate_brain()` ДО попытки записи в brain; при ошибках валидации
  всё равно сохраняет решение локально (сохраняем пользовательские
  данные), но возвращает ГРОМКОЕ многострочное предупреждение с
  префиксом `⚠ Decision #N saved LOCALLY ONLY — brain mirror BLOCKED`,
  перечисляет каждую ошибку конфига и даёт явные пути исправления
  (`tausik brain init` ИЛИ `brain.enabled=false`) плюс подсказку
  `tausik brain move --to-brain` для миграции накопленных local-only
  решений. (2) `tausik doctor` получает строку `Brain config`, которая
  поднимает ошибки `validate_brain()` на health-check, так что
  мисконфиг виден ещё до первого decide. Тесты:
  `tests/test_service_knowledge_decide.py` +1 кейс
  (`test_brain_enabled_with_empty_database_ids_returns_loud_warning`);
  три существующих brain-enabled теста теперь тоже патчат
  `validate_brain` на `[]` (тестируют пост-валидационный путь).
  Разовый gap: существующие local-only решения от этого дефекта НЕ
  мигрируются автоматически — сначала исправь конфиг, потом
  `tausik brain move --to-brain` по каждому решению (или по категории)
  для бекфилла в Notion.
- **Self-check sibling enumeration на Windows 11 24H2+ + ложное
  срабатывание remediation при `count=-1`
  (`v14b-defect-mcp-self-check-windows-fallback`,
  defect_of=`v14b-mcp-stale-module-detector`).** Первый живой прогон
  `tausik_self_check` на Win 11 build 26200 вернул
  `sibling_mcp_count=-1` и `wmic introspection failed: WinError 2` —
  Microsoft удалил `wmic.exe` из современного Windows. Логика
  `collect()` к тому же путала `count=-1` (диагностика недоступна) и
  `count>0` (реальная утечка sibling-серверов), поэтому здоровый
  сервер на современном Windows ложно кричал бы "Restart your IDE".
  Два фикса: (1) Windows-ветка `_enumerate_sibling_mcps` сначала
  пробует `wmic` (legacy compat), на `FileNotFoundError` падает к
  PowerShell `Get-CimInstance Win32_Process` через
  `subprocess.run(['powershell', '-NoProfile', '-NonInteractive',
  '-Command', '<query>'])` с парсингом строк `pid|cmdline`; если
  PowerShell тоже отсутствует, ошибка фиксирует именно этот факт.
  (2) Remediation теперь различает три состояния: drift OR `count>0`
  → "Restart IDE"; `count=-1` → "MCP modules in sync (drift check
  passed). Sibling-MCP check unavailable on this host"; чисто → "no
  action needed". Тесты: `tests/test_mcp_self_check.py` +2 кейса
  (`test_remediation_silent_when_count_unknown`,
  `test_remediation_fires_on_real_drift`); существующие 6 кейсов
  не меняются. Зеркалится в
  `agents/cursor/mcp/project/self_check.py`.

### Добавлено

- **Детектор stale MCP-модулей — корневой фикс тихих зависаний
  task_done_v2 / verify (`v14b-mcp-stale-module-detector`).** Новый MCP
  инструмент `tausik_self_check` возвращает время старта MCP project
  сервера, snapshot mtime watched-модулей при загрузке vs текущие
  mtime на диске, флаг `drift_detected`, список stale-модулей
  (с `delta_seconds`) и `sibling_mcp_count` — число других MCP
  project-серверов на этом проекте (сигнал window-leak'а). Watch-list
  покрывает сервис-модули, чьи stale-копии исторически вызывали
  hang'и: `service_verification`, `verify_cache`, `security_pattern`,
  `gate_runner`, `gate_command_runner`, `service_gates`, `service_task`,
  `project_service`, `project_backend`, `handlers`, `handlers_skill`.
  Сама диагностика — в новом
  `agents/claude/mcp/project/self_check.py`; на старте MCP она
  eager-импортирует watch-list, чтобы snapshot отражал именно те
  модули, которые сервер будет звать позже (lazy-импортируемые модули
  иначе совпадали бы с текущим mtime по определению и маскировали
  бы drift). Skill `/start` Phase 1 теперь добавляет
  `tausik_self_check` в параллельный batch; Phase 3 рендерит
  заметный блок `⚠ MCP Health`, когда есть drift или sibling-серверы,
  с remediation `Restart your IDE`. Companion gotchas: #77
  (`tausik_verify` виснет после правки
  `service_verification.py`/`gate_runner.py`), #79 (`task_done_v2`
  виснет на большом evidence), #80 (root cause). Тесты:
  `tests/test_mcp_self_check.py` (NEW, 6 кейсов — snapshot
  заполнен; нет drift'а на нетронутом дереве; drift всплывает при
  advance mtime ≥30 с; пропавшие файлы не валят сборщик;
  sibling-инвентаризация возвращает int (≥-1) без exception; handler
  отдаёт валидный JSON envelope). Документация:
  `docs/{en,ru}/mcp.md` регистрирует инструмент;
  `docs/{en,ru}/troubleshooting.md` получает секцию `Stale MCP
  modules (silent hangs)` с описанием remediation-потока.

- **Skill core cleanup — bootstrap default = 12 + brain conditional
  (`v14b-skill-core-cleanup`).** Раньше bootstrap автоматически
  разворачивал все 13 source-скиллов плюс каждый entry из
  `skills-official/registry.json` (~38 скиллов → ~1,520 токенов в
  system-reminder каждый ход). С v1.4.x default — **12 core
  скиллов** (`/start`, `/end`, `/checkpoint`, `/plan`, `/task`,
  `/ship`, `/commit`, `/review`, `/test`, `/debug`, `/explore`,
  `/interview`) плюс `/brain` *условно* — только когда
  `bootstrap_config.is_brain_enabled(cfg)` возвращает true (т.е. у
  проекта заполнен `brain.notion_db_ids` после `tausik brain init`).
  Эмпирический эффект: **−1,040 токенов/ход (−68%)** на skill-листе
  system-reminder. Два новых bootstrap-флага возвращают v1.3.x
  поведение, когда нужно: `--include-official` (полные registry
  stubs) и `--include-vendor` (alias ради симметрии с vendor-skill
  терминологией). `_profile-demo` остаётся в `agents/skills/` как
  underscore-prefixed reference fixture (уже фильтруется bootstrap).
  `tausik status` теперь печатает однострочное предупреждение, если
  развёрнутый skill-set расходится с флагом (например, 38 развёрнуто
  без `--include-official`) — чтобы случайный bloat не остался
  незамеченным. Negative-тесты фиксируют edge-cases: отсутствующий
  или повреждённый `.tausik/config.json` → brain пропускается без
  crash; entries в `installed_skills` разворачиваются независимо от
  default; underscore-префиксы в `installed_skills` фильтруются.
  Файлы: `bootstrap.py`, `bootstrap_config.is_brain_enabled`,
  `bootstrap_copy.copy_skills` (gated `builtin_names` loop + opt-in
  registry stubs), `project_cli._maybe_print_skill_set_warning`.
  Тесты: `tests/test_bootstrap_skills_coverage.py` (8 кейсов, в т.ч.
  4 negative). Документация: `docs/{en,ru}/skills.md`,
  `docs/{en,ru}/architecture.md`, `README.md` + `README.ru.md`
  (новая секция `## Token Efficiency` перед `## Functionality`).

### Добавлено

- **Закрытие filesize-долга (`v14b-filesize-debt-paydown`).** Четыре
  модуля сверх 400-line cap разделены на фокусные подмодули;
  `gates.filesize.exempt_files` в `.tausik/config.json` теперь пуст.
  Конкретно:
  - `scripts/backend_queries.py` 536→397: методы
    usage_events / session_usage_metrics (`usage_event_append`,
    `session_usage_record`, `usage_events_cost_rollup_by_task`,
    `session_usage_summary`) вынесены в новый
    `scripts/backend_queries_usage.BackendQueriesUsageMixin`;
    `BackendQueriesMixin` наследует от него — публичный surface на
    `SQLiteBackend` не изменился.
  - `scripts/service_verification.py` 464→345: классификатор
    security-паттернов (`is_security_sensitive` +
    `_SECURITY_PATH_TOKENS` / `_SEC_BASE` / `_SECURITY_BASENAMES` /
    `_SECURITY_EXTENSIONS`) вынесен в `scripts/security_pattern.py`;
    cache-хелперы (`is_cache_allowed`, `resolve_gate_signature`,
    `_build_cache_command`, `has_fresh_verify_run`) — в
    `scripts/verify_cache.py`. Оба набора re-export'ятся из
    `service_verification`, существующие импорты не сломаны.
  - `scripts/gate_runner.py` 476→394: `run_command_gate` +
    `_SCOPED_SKIP_SENTINEL` (включая TAUSIK_VERIFY_FULL inject из
    v14b-pytest-fast-lane) вынесены в
    `scripts/gate_command_runner.py`; re-export из `gate_runner` —
    `tests/test_gates.py` и другие callers работают без изменений.
  - `bootstrap/bootstrap_generate.py` 433→223: огромный settings
    hooks-блок вынесен в `bootstrap/bootstrap_hooks.build_hooks_dict(_hook_cmd)`.
    `generate_settings_claude` теперь читается как тот lean config builder,
    которым и должен был быть.
  Smoke-тест фиксирует обратную совместимость:
  `tests/test_filesize_split_smoke.py` импортирует каждый перенесённый
  символ из ОРИГИНАЛЬНОГО модуля и проверяет identity с новым местом
  плюс контракт hooks-shape для settings.json (зеркало существующих
  per-hook coverage assertions).

### Добавлено

- **Pytest fast lane (`v14b-pytest-fast-lane`).** Дефолтная
  конфигурация pytest в `pyproject.toml` теперь пропускает тесты,
  помеченные `@pytest.mark.slow` (`addopts = "-m 'not slow'"`).
  Тяжёлые тесты — bootstrap real/dryrun + skills coverage, MCP
  integration & project server, brain MCP handlers +
  installed-layout, stress (1000 tasks / 100 sessions), bootstrap
  venv, RAG FTS5 benchmarks, Tausik CLI smoke, skill CLI help,
  bootstrap-варианты model-profile, плюс один 7-секундный кейс
  блокировки БД в `posttool_usage_hook` — все получили маркер.
  Эмпирический эффект на репе TAUSIK: полный сьют **с 731 с (12:11)
  до 99 с (1:39)** — **ускорение в 7.4 раза**, 118 тестов deselected
  из fast lane. Три escape-hatch'а для полной батареи:
  `pytest --override-ini='addopts='`, `pytest -m ''` (или `-m 'slow'`
  для CI nightly) и новый env-var `TAUSIK_VERIFY_FULL=1`, который
  `gate_runner.run_command_gate` подхватывает и инжектит
  `--override-ini=addopts=` в команду pytest-гейта. Затрагивает
  только pytest-гейт — ruff, mypy, filesize не задеты. Тесты
  покрывают путь env-var-инъекции, no-op для не-pytest гейтов и
  дефолтный неизменённый cmd (`tests/test_gates.py:TestRunCommandGate`).
  Документация обновлена в `docs/{en,ru}/cli.md`.

### Исправлено

- **Регрессия size-cap CLAUDE.md
  (`claude-md-trim-reference-line-fix-test-claude-md-s`).** Reference-строка
  была расширена в handoff #45 ради трёх drift-тестов T2.2; правка вытолкнула
  статическую часть на 4113 B при cap 4096 B (тест
  `tests/test_claude_md_size.py::test_claude_md_static_under_size_cap`).
  Сократил формулировку, сохранив ссылку на `agent-contract.md` и якоря
  (`estimation`, `SENAR matrix`, `roles`, `custom_stacks`, `QG-2`). Все
  4 теста CLAUDE.md теперь PASS.

- **QG-2 verify-first ложное срабатывание на hook/session-файлах
  (`v14b-defect-qg2-security-substring-too-broad`).**
  `is_security_sensitive` в `scripts/service_verification.py` раньше
  матчил голые подстроки ("session", "login", "signup",
  "scripts/hooks/", …), из-за чего любой hook-файл TAUSIK
  (`scripts/hooks/session_start.py`, `posttool_usage.py`,
  `keyword_detector.py`, ...) и любой hook-тест
  (`tests/test_session_start_hook.py`, `tests/test_session_metrics.py`)
  помечался как security-sensitive. Это давало `is_cache_allowed=False`,
  `has_fresh_verify_run` возвращал `(False, None)`, и
  `_enforce_verify_first` блокировал `task_done` с "no fresh verify run"
  даже сразу после успешного `tausik verify`. Хуки — это инфраструктура,
  а не auth surface. Фикс сужает `_SECURITY_PATH_TOKENS` до строго
  каталогами-окруженных токенов (`/auth/`, `/oauth/`, `/payment/`,
  `/webhook/`, …), убирает голые подстроки, заменяет нечёткие basename'ы
  "session"/"login" на явные (`session_token.py`, `login_handler.py` и
  т.д.). `_SECURITY_BASENAMES` теперь также покрывает `secrets.json`,
  `credentials.json`, `.npmrc`, `id_rsa`, `id_ed25519`. Полный контракт
  задокументирован в docstring `is_security_sensitive`. Новый файл
  `tests/test_security_sensitive.py` (70 кейсов) фиксирует оба набора —
  истинно-положительный и ложно-положительный, плюс регресс-кейс,
  который записывает зелёный verify-прогон на hook-файле и проверяет,
  что `has_fresh_verify_run` возвращает `(True, row)` — именно тот failure
  mode, который заблокировал закрытие `v14b-rag-first-nudges`. Аудит
  `verification_runs` показал, что исторически пострадала только одна
  задача (родительская, на которой баг и всплыл) — повторная верификация
  не требуется.

### Добавлено

- **RAG-first подсказки (`v14b-rag-first-nudges`).** В скиллах `start`,
  `task`, `debug` появился раздел "Code search hierarchy", направляющий
  агента сначала к `mcp__codebase-rag__search_code` для поиска
  символов/паттернов, а `Grep`/`Read` оставляющий только для известных
  путей. Скилл `explore` переписан — шаг 3 теперь начинается с
  `search_code` по ранжированным чанкам, прежде чем читать целые файлы.
  Хук SessionStart (`scripts/hooks/session_start.py`) усиливает
  авто-инжект: RAG summary указывает MCP-инструмент явно
  (`mcp__codebase-rag__search_code`), а блок Reminders получает буллет
  про экономию токенов через `search_code` вместо `Grep/Read`. Stop-хук
  (`scripts/hooks/keyword_detector.py`) расширен вторым детектором: если
  последний user-промпт содержит интент поиска кода ("where is X" / "find
  Y" / "how does Z work" / "где определ…"), а в ответе агента нет
  упоминания `search_code` — хук блокирует stop с рекомендацией перейти
  на RAG. Drift guard сохраняет приоритет; loop-safe сокращение через
  `stop_hook_active` действует на оба детектора. Тесты:
  `tests/test_keyword_detector_hook.py` (+8 кейсов для нового детектора,
  включая приоритет и подавление при уже использованном search_code),
  `tests/test_session_start_hook.py` (+1 кейс на rag-first reminder).
- **Атрибуция токенов по задачам (`v14b-usage-events-auto-write`).**
  Новый PostToolUse-хук `scripts/hooks/posttool_usage.py` пишет одну
  строку `usage_events` за каждый tool call с привязкой к активной
  задаче. Миграция схемы v24 добавляет `usage_events.tool_name` и
  расширяет CHECK по `source` значением `posttool`. Прайсинг моделей
  вынесен в общий модуль `scripts/cost_pricing.py` — единый источник
  правды для нового хука и существующего SessionEnd writer'а
  (`session_metrics.py`). Пять путей graceful-degradation покрыты
  тестами (битый stdin, нет активной задачи, неизвестная модель,
  заблокированная БД, отсутствие `.tausik/tausik.db`). Документация:
  `docs/{en,ru}/cost-telemetry.md`.

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
