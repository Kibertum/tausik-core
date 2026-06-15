**Русский**

# Контракт агента TAUSIK — расширенная справка

Этот документ — продолжение `CLAUDE.md`. CLAUDE.md грузится в контекст агента
**на каждом ходе**, поэтому он держит только enforceable rules и quick reference.
Сюда вынесено всё, что нужно реже: estimation table, SENAR Compliance matrix,
QG-2 механика, Roles, External skills, Custom stacks.

Грузи этот файл по мере надобности через Read — не на каждом ходе.

---

## QG-2 Implementation Gate — механика

`task done --ac-verified` требует evidence в notes + прохождения **scoped**
quality gates. Pytest gate использует `{test_files_for_files}` substitution —
гонит только `tests/test_<basename>.py` для каждого `relevant_files`
(basename heuristic + glob `_*.py` варианты).

- Если `relevant_files` non-empty но ни один тест не маппится → **gate SKIPPED**
  (раньше fallback на полный suite — defect fixed).
- Без `relevant_files` (None/empty) — fallback на полный suite остаётся
  (regression-safe для unscoped вызовов).
- Verify cache (`verification_runs` table): зелёный run за последние 10 минут с
  тем же `files_hash` → cache hit, gate skipped.
- Security-sensitive файлы (`scripts/hooks/`, `/auth/`, `/payment/`, `/billing/`)
  обходят cache — всегда re-verify.

Залогируй проверку AC через `task log` перед закрытием.

### Структурированный evidence (`--evidence-json`, v1.4 polish)

Альтернатива prose-форме — JSON-аргумент, который конвертится в каноническую
prose-форму внутри сервиса:

```bash
.tausik/tausik task done my-task --ac-verified --evidence-json '{
  "ac_evidence": [
    {"n": 1, "status": "pass", "evidence": "tests/test_foo.py::test_bar"},
    {"n": 2, "status": "pass", "evidence": "smoke run", "manual": true},
    {"n": 3, "status": "pass", "evidence": "401 на bad creds", "negative": true},
    {"n": 4, "status": "pass", "evidence": "сумма заказа неотрицательна для реальных входов", "domain": true}
  ]
}'
```

Опциональные per-item флаги `manual` / `negative` / `domain` пробрасываются как
маркеры в prose, чтобы `service_ac_evidence` парсер проставил
`has_manual` / `has_negative_evidence` / `has_domain_evidence` в отчёте.
`--evidence` и `--evidence-json` взаимоисключающие (argparse + сервис). Та же
семантика у MCP-tool `tausik_task_done` через аргумент `evidence_json`.

**SENAR Rule 4 — domain challenge (v15s-rule4-domain-challenge).** QG-2 checklist
для всех тиров кроме planning-tier `trivial` требует ответа на доменный вопрос:
*имеет ли результат смысл ВНЕ тестов?* (arXiv 2605.30353 — агент проходит тесты
с физически бессмысленным выводом). Достаточно строки `Domain:` в notes/evidence,
например `Domain: выход семантически валиден для реальных входов`. Парсер
распознаёт `domain` / `sanity` / `makes sense` / `имеет смысл` / `доменн` /
`real-world`. Пропускается только для `trivial`.

---

## Agent-native estimation

Задачи измеряются в **tool calls**, а не в часах.

| Tier | call_budget | Когда подходит |
|------|-------------|----------------|
| `trivial` | ≤10 | мелкий fix, единственный флаг, doc-правка |
| `light` | ≤25 | миграция + helpers + тесты на одной поверхности |
| `moderate` | ≤60 | hook + service + tests, multi-file feature |
| `substantial` | ≤150 | CLI + service + MCP + mirror + tests одновременно |
| `deep` | ≤400 | полный вертикал (новый стэк, end-to-end feature) |

Бюджеты **>400** разрешены — `call_budget` сохраняется как есть, а tier label
cap'ается на `deep`. Warning at-1.5×budget работает для любого N.
Если регулярно превышаешь 400 — это сигнал split task (через subagent или
последовательную сессию).

При создании task через `task add`/`task update` указывай `--call-budget`
(авто-derives tier) или `--tier` напрямую. Пропуск допустим, но **явно** обоснуй
— без budget calibration ломается. На task_done `call_actual` записывается
автоматически (events + PostToolUse hook); если actual > 1.5×budget — TAUSIK
логирует warning для re-calibration.

`tausik task start <slug> --force` — bypass session capacity gate when
overshoot is intentional (audit event + notes line trace it).

---

## SENAR Compliance (v1.3 Core)

| Элемент SENAR | Реализация в TAUSIK | Enforcement |
|---|---|---|
| QG-0 Context Gate | `task start` проверяет goal + AC + negative scenario + scope warning | Hard (CLI + MCP блокирует) |
| QG-0 Security Surface | Предупреждает для auth/payment/PII задач без security AC | Warning |
| QG-2 Implementation Gate | `task done` = evidence + --ac-verified + **scoped** gates + verify cache (no bypass) | Hard (CLI + MCP, --force удалён) |
| Rule 1 Задача перед кодом | CLAUDE.md + skills + `/plan` для старта | Instruction |
| Rule 2 Scope Boundaries | Поля `scope` + `scope_exclude` в задачах, QG-0 предупреждает | Warning |
| Rule 3 Verify Against Criteria | Per-criterion AC evidence парсинг | Hard + Warning |
| Rule 4 External Validation | Субагент `tausik-external-reviewer` на ДРУГОЙ модели (separation of duties, read-only); требуется при measured-high closure через L3-триггер | Hard (при high-risk) |
| Rule 5 Verification Checklist | 28-item checklist, 4 тира; **pytest gate scoped по relevant_files**, verify cache reuse в окне 10 мин; v1.4 — структурированный AC-evidence parser (`service_ac_evidence`) сообщает про gaps и отсутствующие test-refs/негативные сценарии | Warning + Hard scope |
| Rule 7 Root Cause | Defect-задачи: keyword floor **блокирует** done без root cause; structured-форма (category+description+prevention) — advisory escalating nudge + coverage в `metrics` | Hard (floor) + Warning (structured) |
| Rule 8 Knowledge Capture | Warning при task_done + `--no-knowledge` для confirm-none | Warning |
| Rule 9.2 Лимит сессии | `task start` блокируется при >180 мин **active time** (bounded sum: каждый gap = `min(Δ, 10 мин)`, длинный AFK клипуется). `session extend` продлевает; `session recompute` retro. | Hard (CLI + MCP блокирует) |
| Rule 9.3 Checkpoint | `/checkpoint` + auto-reminder в `/task` | Instruction |
| Rule 9.4 Dead Ends | `tausik_dead_end` MCP + CLI + skills напоминают | Instruction |
| Rule 9.5 Periodic Audit | `tausik_audit_check/mark` MCP + CLI | Warning |
| Rule 9.15 AI Output QA | `/review` с 5 параллельными агентами + iterative loop | Instruction |
| Метрика: Throughput | tasks_done / sessions | Hard (auto) |
| Метрика: Lead Time | avg(completed_at - created_at) | Hard (auto) |
| Метрика: FPSR | tasks(attempts=1) / done * 100% | Hard (auto) |
| Метрика: DER | DISTINCT(defect_of) / non-defect done * 100% | Hard (auto) |
| Метрика: Dead End Rate | dead_ends / total_tasks * 100% | Hard (auto) |
| Метрика: Cost per Task | avg hours by complexity | Hard (auto) |
| Section 5.1 Explorations | `tausik_explore_*` MCP + CLI | Hard |
| Multi-lang Gates | Auto-enable по стеку (TS, Go, Rust, PHP, Java) | Hard (auto) |
| MCP Coverage | 124 инструмента (117 project + 7 brain); agent-loop verbs полностью покрыты, CLI-only — только намеренные maintenance/operator verbs (список в mcp.md) | Hard |
| Batch Execution | `/run plan.md` — автономное выполнение планов | Instruction |
| Structured Logs | `task_logs` таблица с phase + FTS5 | Hard (auto) |
| Fake Test Detection | 10 паттернов в testing review agent | Warning |

---

## Rule 4 — External Validation (separation of duties)

Закрытие задачи с **measured-high** риском требует независимого adversarial-ревью
ДРУГОЙ моделью — модель не может валидировать собственный код. Реализация:

- **Субагент** `tausik-external-reviewer` (`harness/claude/subagents/`) — read-only
  tools (`Read, Grep, Bash`, без `Write`/`Edit`: SENAR «Reviewer SHALL NOT have
  write access»), `model: opus`. Возвращает structured-вердикт
  (`approved | changes_requested | blocked`) и точную команду `tausik review record`.
- **Different model.** `scripts/external_reviewer.py::recommend_reviewer_model(author)`
  выбирает семейство, отличное от автора (порядок opus → fable → sonnet → haiku);
  `is_separate_duty()` отвергает совпадение семейств и неизвестного ревьюера.
  Если автор уже на opus — ревьюер фолбэчится на fable.
- **Триггер.** `risk_l3_trigger.check_l3_required` при measured-high closure
  блокирует `task done` и в remediation называет `@tausik-external-reviewer`
  с рекомендованной моделью. Записанный `tausik review record --type L3`
  снимает блок. Opt-out: `config risk.l3_block_on_high=false` (→ warning).
- **Evidence.** Вердикт ревьюера фиксируется в таблице `reviews` (run_type=L3) и
  попадает в метрики ADR (`tausik review metrics`).

---

## Rule 7 — Structured Root Cause (defect-задачи)

Два уровня (decision #96):

- **Keyword floor (Hard).** `task done` для defect-задачи (`defect_of` задан) блокируется,
  если в notes нет упоминания причины (`root cause` / `причина` / `caused by` / `из-за` / …).
  Opt-out: `config task_done.root_cause_hard=false` → warning.
- **Structured layer (Advisory).** Поверх floor: если причина есть, но не в канонической
  форме — escalating nudge (silent→hint→warning→strong), НЕ блокирует. Compliance сбрасывает счётчик.

**Канонический формат** (одна строка `task log`):

```
Root cause (<category>): <описание>. Prevention: <как не допустить>.
```

Bilingual: `Причина (<category>): <описание>. Профилактика: <…>.`

**Closed-list категорий** (`scripts/root_cause.py::ROOT_CAUSE_CATEGORIES`):
`logic-error`, `missing-validation`, `race-condition`, `config-error`,
`integration-mismatch`, `regression`, `edge-case`, `performance`,
`dependency`, `documentation`, `other`.

Неизвестная категория или отсутствие `Prevention:` → форма не структурная (без исключения).
Coverage (% done defect-задач со структурой) выводится в `tausik metrics` (секция *Root Cause Coverage*).

Пример:

```
.tausik/tausik task log fix-pager "Root cause (logic-error): off-by-one в пагинаторе при пустой странице. Prevention: добавить bounds-тест на last page."
```

---

## Workflow и команды (полный список)

**Граф workflow:** `start → plan → task → [review, test] → commit → end`
**Batch workflow:** `run plan.md → [task start → subagent → validate → commit] × N → summary`

**Полный CLI:** `epic | story | task | session | gates | skill | brain | stack | role | memory | doctor | hud | metrics | roadmap | events | search | decide | dead-end | explore | audit | run | doc | verify | suggest-model | team | update-claudemd | fts | init`. Подробности — `docs/ru/cli.md`.

**Знания:** решение → `decide`. dead end → `dead-end`. паттерн → `memory add`. конец сессии → `session handoff`.

---

## Роли

Свободный текст (любая строка). Частые: `developer`, `architect`, `qa`, `tech-writer`. Профили в `harness/roles/{role}.md`.

---

## Внешние скиллы

Репозитории: `.tausik/tausik skill repo add <url>`. Установка: `.tausik/tausik skill install <name>`.
Активация: `.tausik/tausik skill activate {name}`. Деактивация: `.tausik/tausik skill deactivate {name}`.
Формат: `tausik-skills.json` в корне совместимого репо. Legacy: `skills.json` + bootstrap для обратной совместимости.

---

## Стеки

**DEFAULT_STACKS** (25): python, fastapi, django, flask, react, next, vue, nuxt, svelte, typescript, javascript, go, rust, java, kotlin, swift, flutter, laravel, php, blade, ansible, terraform, helm, kubernetes, docker.

**Custom stacks.** Список открыт для расширения — добавь свой стэк в `.tausik/config.json`:

```json
{ "custom_stacks": ["ruby", "elixir", "scala", "csharp"] }
```

После этого `task add --stack ruby` принимается. Stack-scoped gates (pytest, go-test и т.д.) автоматически НЕ применяются к custom стэкам — для них нужно зарегистрировать custom gate в `gates` секции `config.json`. Universal gates (filesize, tdd_order) работают для всех стэков. `tausik stack list` показывает custom стэки с пометкой `(custom)`.

Гайды в `harness/stacks/{stack}.md`.

---

## Зачем разделили (история)

`CLAUDE.md` грузится в контекст агента **на каждом ходе** — даже когда агент
просто пишет "ok". До v1.4 trim файл был ~15.5KB ≈ 4000 токенов; на 100-turn
сессии — 400K токенов налога только с CLAUDE.md.

Trim до ≤4KB убирает не-enforceable справку (этот файл) из горячего пути.
Регрессионный тест `tests/test_claude_md_size.py` фиксит границу — текущий
предел вынесен в константу теста и сейчас составляет ~4500 байт после v1.4
правок CLAUDE.md; если файл вырастает выше неё, CI блокируется.

См. также: `docs/ru/architecture.md` (3-слойная архитектура), `docs/ru/cli.md`
(полная CLI-справка), `docs/ru/quickstart.md` (быстрый старт).
