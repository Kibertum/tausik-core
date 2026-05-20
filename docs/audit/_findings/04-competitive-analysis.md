# 04 — Competitive Analysis: TAUSIK in the AI Coding Landscape

**Дата:** 18 мая 2026
**Автор:** Продуктовый аналитик (research pass)
**Скоуп:** TAUSIK + SENAR + RENAR vs. весь рынок AI coding tools (категории 1-6)
**Слоган-под-аудитом:** "AI agents that can't fake 'done'" / "AI-агенты, которые не врут «готово»"

---

## TL;DR (3 минуты)

1. **Рынок раскалён.** AI coding tools — $12.8B в 2026, удвоился за 2 года. Cursor — $2B ARR, $50B valuation, потенциальная покупка SpaceX за $60B. Claude Code — $2.5B ARR. Cognition (Devin+Windsurf) — $25B valuation. Адопшен 84% разработчиков по Stack Overflow 2025.
2. **TAUSIK играет в правильную сторону тренда.** Главная боль рынка — **trust gap** (96% разработчиков не доверяют AI-коду, 66% жалуются на "almost right but not quite", 46% активно distrust). Tools решают её разными способами: spec-first (Spec Kit, Augment Intent), observability (LangFuse, Maxim), instruction files (AGENTS.md). TAUSIK выбирает редкий путь: **enforced quality gates + verification-as-cache + task journal**. Это близко к нише, но не пусто.
3. **3 самых опасных конкурента: GitHub Spec Kit (90k звёзд, бесплатный, спонсор GitHub/Microsoft), TaskMaster AI (drop-in для всех агентов), AGENTS.md/Claude Skills (де-факто стандарт). Все они подбираются к территории "discipline layer" с разных сторон и имеют дистрибуцию, которой у TAUSIK нет.**
4. **Уникальное окно у TAUSIK:** строгий enforcement (физически не даёт агенту врать «done») + verification cache + dead-end журналирование + open-source CLI без vendor-lock. Никто из 30+ изученных продуктов не закрывает эту комбинацию.
5. **Опасности на 12 месяцев:** Cursor/Claude Code/Codex втягивают «discipline» как нативную фичу (хуки, AGENTS.md, проверка PR); стандарт AGENTS.md + Skills делает custom CLI избыточным; SaaS-наследники Spec Kit (Augment Intent) кэптурят enterprise.
6. **Ниши для роста:** governance-первый enterprise (SOC2/compliance/audit-trail), academic/regulated (legal, fintech, gov), не-Python стэки (TypeScript-first, Go-first), интеграция с CI/CD как контракт между агентом и репозиторием.

---

## 1. Карта рынка (категории и игроки)

### Категория 1 — CLI AI Coding Agents (прямые конкуренты по форме)
- **Aider** (open, free, 41.6k★) — terminal pair-programmer, voice, auto-commit
- **Cline** (Apache 2.0, 61.2k★, 5M+ installs) — VS Code agent, Plan/Act mode
- **Roo Code** (open, fork Cline) — multi-mode (Architect/Code/Debug/Orchestrator)
- **OpenHands** (ex OpenDevin, 66k users) — SDK + CLI + GUI, 53%+ SWE-bench
- **Goose** (Block, Apache 2.0, 27k★) — desktop+CLI, recipes (YAML workflows), MCP-first
- **Continue.dev** (MIT, 32.4k★, 2.5M installs) — autocomplete/chat/agent, "quality control for software factory"
- **Cody** (Sourcegraph, enterprise-only, $19-$59/user/mo) — enterprise repo-context
- **Claude Code** (Anthropic, $2.5B ARR) — terminal-native, CLAUDE.md, Skills, plugins
- **Codex CLI** (OpenAI, Rust, SWE-bench 88.7%) — PR-creating, @mention collab
- **Gemini CLI** (Google) — 1M context, 90+ extensions, smart routing

### Категория 2 — IDE-based agents
- **Cursor** (Anysphere, $2B ARR, 1M+ paid, $50B val) — fork VS Code, Composer
- **Windsurf** (Cognition, 1M+ active users, 59% F500) — Cascade agent, Devin-integrated
- **GitHub Copilot** (Microsoft, $10-$39/mo) — Agent mode + Coding Agent + Workspace
- **JetBrains Junie** (launched Jan 2026) — IntelliJ-native agent, Ask/Code modes
- **Zed** (open core, $10-$30/mo) — Zeta2 model, parallel agents, ACP protocol

### Категория 3 — Cloud / Autonomous SWE
- **Devin 2.0** (Cognition, $20/mo, $25B val) — autonomous, SWE-bench 45.8%
- **SWE-agent** (Princeton, open) — academic, ACI interface, SoTA SWE-bench
- **mini-swe-agent** (100 lines, >74% SWE-bench verified)
- **Sweep AI** — GitHub-issue-to-PR app
- **Augment Code** ($20-$200/mo) — Context Engine (500k files), Intent Workspace
- **Replit Agent 4** — full-stack platform, 30+ integrations
- **Bolt.new** (StackBlitz) — browser full-stack from Figma
- **v0** (Vercel) — UI generation, Supabase/Neon, Vercel-deploy
- **Magic.dev** — менее заметен в 2026 публично, отчётов мало
- **xAI Grok Build** — новый игрок в гонке CLI

### Категория 4 — Agent Frameworks
- **LangChain/LangGraph** (LangGraph 0.4, state+HITL) — production graph
- **LlamaIndex** — data-centric agents
- **AutoGen 1.0 GA** (Microsoft) — conversational multi-agent
- **CrewAI** — role-based, 20 lines to start, enterprise observability
- **Claude Agent SDK** (Anthropic) — programmable Claude Code core
- **OpenAI Agents SDK** — minimal primitives, Python-first
- **Google ADK 1.0** (Apache 2.0, A2A protocol) — Gemini-optimised, multi-language
- **Semantic Kernel** (Microsoft) — .NET/Python enterprise

### Категория 5 — Rule/Instruction Systems
- **Cursor Rules** (`.cursorrules`) — proprietary, Cursor-only
- **CLAUDE.md** — Claude-specific session context
- **AGENTS.md** — open standard (Linux Foundation), 60k+ repos, ridden by Codex/Claude/Cursor/Aider/Devin/Copilot/Gemini/Windsurf/Amazon Q
- **Claude Skills** (Anthropic Marketplace, 55+ official + 72+ community, opened spec adopted by OpenAI)
- **Aider CONVENTIONS.md** (старая конвенция, теперь чаще AGENTS.md)
- **Spec Kit** (GitHub, 90k★) — spec-driven dev toolkit, 29+ агентов

### Категория 6 — Quality / Governance Layers
- **DSPy** (Stanford, 28k★) — programming-not-prompting, compilation, signatures
- **Guardrails AI** — input/output validation, toxicity, PII, format
- **LangSmith** (LangChain) — tracing/eval for LangChain
- **LangFuse** (MIT, $29/mo) — opensource observability + eval
- **Helicone** ($79/mo) — proxy-style observability
- **Arize AX, Galileo, Opik (Apache 2.0)** — eval/observability
- **Maxim AI** — eval+observability+simulation в одном
- **Codacy / CodeScene / Qodo** — AI code quality gates (PR-уровень)
- **TaskMaster AI** (eyaltoledano) — task management drop-in для Cursor/Lovable/Windsurf/Roo/Claude Code

---

## 2. Подробные карточки топ-15 конкурентов

### 2.1 Cursor (Anysphere) — главный «слон» рынка
- URL: cursor.sh, anysphere.inc
- Value prop: AI-native fork VS Code с агентами, автокомплитом и параллельным background-агентом.
- Лицензия/цена: commercial. Hobby free; Pro $20; Pro+ $60; Ultra $200; Teams $40/seat.
- Модели: Claude, GPT, Gemini, Grok — mix-and-match.
- Killer: Composer/Agent + Background Agents, мультимодель + кредиты.
- Аудитория: solo devs → F500 (>50% Fortune 500 used Cursor по состоянию на Series C 2025).
- Traction: $2B ARR (Feb 2026), 2M users, 1M paid, 1M DAU. Возможный exit SpaceX $60B.
- vs TAUSIK по 7 осям:
  - Quality gates: **слабо** (.cursorrules только)
  - Verification-as-code: **отсутствует**
  - Task tracking: **отсутствует** (есть Composer history, не tasks)
  - Multi-agent: **да** (background agents)
  - Memory: **да** (rules + skills через AGENTS.md)
  - Skills/plugins: **умеренно** (MCP, rules)
  - Language-agnostic: **да**
  - Итог: Cursor играет в editor+agent, не в discipline. TAUSIK комплементарен.

### 2.2 Claude Code (Anthropic) — самый близкий по форме к TAUSIK
- URL: anthropic.com/product/claude-code
- Value prop: terminal-native agent с CLAUDE.md, Skills, plugins, hooks.
- Цена: API-driven, $20/$200/mo подписки + Agent SDK credits с 15 июня 2026.
- Killer: 128K output context, CLAUDE.md, Hooks, Skills marketplace, Plugins, Agent SDK.
- Traction: $2.5B ARR run rate; 300k бизнес-клиентов; рост среди профи.
- vs TAUSIK:
  - Quality gates: **частично** (Hooks, Stop hooks)
  - Verification-as-code: **слабо** (нет cache, нет enforced verify-first)
  - Task tracking: **отсутствует нативно** (есть TodoWrite tool, но не персистентный journal)
  - Multi-agent: **да**, через Agent SDK
  - Memory: **CLAUDE.md + Skills**
  - Skills/plugins: **сильнейший marketplace**
  - Language-agnostic: **да**
- Угроза: **высокая**. Claude Code втягивает дисциплину как нативную фичу. TAUSIK строится **поверх** Claude Code как раз ради недостающих частей.

### 2.3 GitHub Spec Kit — самый прямой идейный конкурент
- URL: github.com/github/spec-kit
- Value prop: Spec-Driven Development toolkit — specs становятся источником истины для AI-агентов.
- Цена: open, free.
- Killer: structured spec → tech plan → tasks → AI implementation; 29+ интегрированных агентов.
- Traction: **90k★, 8k forks** — одна из самых быстрорастущих devtool-репо в истории.
- vs TAUSIK:
  - Quality gates: **частично** (через spec validation)
  - Verification-as-code: **частично** (specs как контракт)
  - Task tracking: **да, центральная фича**
  - Multi-agent: **agent-agnostic**
  - Memory: через specs
  - Skills/plugins: нет
  - Language-agnostic: **да**
- Угроза: **высочайшая**. Spec Kit покрывает 60-70% сценариев TAUSIK с дистрибуцией GitHub и стилем "spec-driven". Главное отличие — Spec Kit описывает _что_ делать, TAUSIK навязывает _как_ + verify. Но если Spec Kit добавит enforced gates — это сделает TAUSIK маргинальным.

### 2.4 Cline — самый успешный open-source CLI/IDE-agent
- URL: cline.bot
- Value prop: autonomous coding agent, Plan/Act, 30+ providers, controllable.
- Лицензия/цена: Apache 2.0; платится за токены LLM.
- Killer: Plan/Act mode, 5M+ installs, JetBrains/Cursor/Zed/Neovim/CLI preview.
- Traction: 61.2k★, 4M VS Code installs, spend limits UI с v3.78.
- vs TAUSIK: Cline — это _agent_, TAUSIK — _discipline вокруг агента_. Не пересекаются по слою, но Cline пожирает mindshare CLI-ниши.

### 2.5 OpenHands — open-source autonomous SWE
- URL: openhands.dev
- Value prop: open generalist software agent, бесплатный self-host, 53%+ SWE-bench.
- Killer: micro-agents, sandboxes, OpenHands Index leaderboard.
- Traction: 66k users в продакшене, академически известен (NeurIPS 2024 paper).
- vs TAUSIK: близкий по open-source ethos, но фокус на capability, не дисциплине.

### 2.6 Devin 2.0 (Cognition) — главный autonomous SWE
- URL: devin.ai
- Value prop: автономный AI-инженер, ассайнишь как сотрудника.
- Цена: $20/mo entry (раньше $500), enterprise по запросу.
- Killer: 24/7 autonomous, теперь интегрирован в Windsurf 2.0.
- Traction: $25B valuation, ARR удвоилась после поглощения Windsurf.
- vs TAUSIK: Devin — _hands-off_, TAUSIK — _hands-on supervision_. Антагонисты по позиции.

### 2.7 Augment Code (Intent Workspace) — корпоративный аналог по идее
- URL: augmentcode.com
- Value prop: Context Engine 500k файлов + Intent Workspace (Mac app, multi-agent + living spec).
- Цена: $20 / $60 / $200 / Enterprise.
- Killer: monorepo-scale context, multi-agent около spec.
- vs TAUSIK: **прямой концептуальный конкурент** в enterprise-сегменте. Intent делает «spec-as-contract + multi-agent coordination» как раз то, что хочет SENAR.

### 2.8 AGENTS.md — стандарт, а не продукт
- URL: agents.md
- Value prop: универсальный README для AI-агентов.
- Adoption: 60k+ репо, native parse в Claude Code/Codex/Cursor/Aider/Devin/Copilot/Gemini/Windsurf/Amazon Q. Steward — Linux Foundation Agentic AI Foundation.
- vs TAUSIK: TAUSIK должен **писать AGENTS.md**, не конкурировать с ним. Если TAUSIK игнорирует AGENTS.md — он отрезает себя от 60k уже-настроенных проектов.

### 2.9 Claude Skills + Plugins
- Value prop: динамически загружаемые папки инструкций+скриптов; теперь стандарт.
- Adoption: 55+ official, 72+ community, 1M+ contributions индексировано в marketplaces.
- vs TAUSIK: TAUSIK уже использует skills внутри. Угроза — если Skills сами добавят task tracking (текущий статус: легковесно есть в анонсах 2026).

### 2.10 TaskMaster AI — самый прямой task-tracking конкурент
- URL: github.com/eyaltoledano/claude-task-master
- Value prop: drop-in PM для AI-агентов; работает с Cursor, Lovable, Windsurf, Roo, Claude Code.
- Killer: parse_prd, expand_task, 7/15/36 tool tiers, codebase analysis перед task gen.
- vs TAUSIK:
  - Quality gates: **нет**
  - Verification: **нет**
  - Task tracking: **да, главная фича**
  - Memory: умеренно
- Угроза: **высокая**. TaskMaster занял ту же поверхность ("задачи для агентов"), но без жёстких гейтов и без verification cache. TAUSIK должен подчёркивать enforcement + verification, иначе будет восприниматься как «ещё один TaskMaster».

### 2.11 DSPy (Stanford) — программирование вместо промптинга
- URL: dspy.ai
- Value prop: declarative signatures + compiler optimises pipelines.
- Traction: 28k★, 160k+ monthly downloads.
- vs TAUSIK: DSPy — Pythonic ML framework для LM-программ, TAUSIK — process framework для агента. Не пересекаются.

### 2.12 LangFuse — open-source observability
- URL: langfuse.com
- Лицензия/цена: MIT + $29/mo cloud.
- Killer: traces, eval, datasets, prompts management; самый «developer-favourite».
- vs TAUSIK: ортогональны (observability vs discipline), но enterprise клиенты часто захотят оба + интеграцию.

### 2.13 Maxim AI — eval + observability + simulation
- URL: getmaxim.ai
- Value prop: lifecycle quality для AI продуктов с no-code UI.
- vs TAUSIK: ортогональны, но Maxim уверенно идёт к enterprise + AI-agent QA, что косвенно перекрывается с TAUSIK.

### 2.14 Goose (Block) — open MCP-first general agent
- URL: block.github.io/goose
- Killer: Recipes (YAML reusable workflows), 70+ extensions, 15+ providers.
- Traction: 27k★, free.
- vs TAUSIK: Recipes — это «лайт-версия» TAUSIK-задач. Если Goose добавит quality gates — будет прямым конкурентом open-source.

### 2.15 Continue.dev — quality control positioning
- URL: continue.dev
- Value prop: «quality control for your software factory» — буквально слоган.
- Cost: MIT free + $10/mo hosted.
- Killer: source-controlled AI checks, enforceable in CI.
- vs TAUSIK: **позиционирование почти идентично**. Continue.dev уже захватил слоган про "quality control" и имеет 2.5M installs. Это означает, что нужно тонко дифференцироваться: TAUSIK = enforced verification cache + task journal + open SENAR methodology; Continue = CI-enforceable AI checks в IDE.

---

## 3. Сводная таблица сравнения (heatmap)

Легенда: ●●● сильная сторона, ●● присутствует, ● слабо/частично, ○ отсутствует.

| Продукт | QG enforced | Verify-as-code | Task journal | Multi-agent | Memory persist | Skills/plugins | Lang-agnostic | Open source | Self-host | Cost/mo |
|---|---|---|---|---|---|---|---|---|---|---|
| **TAUSIK** | ●●● | ●●● | ●●● | ●● | ●●● | ●●● | ●●● | ●●● | ●●● | $0 (BYO LLM) |
| Cursor | ○ | ○ | ○ | ●● | ●● | ●● | ●●● | ○ | ○ | $20-200 |
| Claude Code | ●● | ● | ● | ●● | ●●● | ●●● | ●●● | ○ | ○ | $20-200 |
| Cline | ○ | ○ | ○ | ● | ● | ●● | ●●● | ●●● | ●●● | LLM only |
| Roo Code | ● | ○ | ○ | ●● | ● | ●● | ●●● | ●●● | ●●● | LLM only |
| OpenHands | ● | ● | ● | ●● | ●● | ●● | ●●● | ●●● | ●●● | LLM only |
| Goose | ● | ● | ●● (recipes) | ●● | ● | ●●● | ●●● | ●●● | ●●● | LLM only |
| Continue.dev | ●● | ●● | ● | ●● | ●● | ●● | ●●● | ●●● | ●●● | $0-10 |
| Cody | ●● | ○ | ○ | ● | ●● | ● | ●●● | ○ | partial | $9-59 |
| Aider | ○ | ● | ○ | ○ | ● | ● | ●●● | ●●● | ●●● | LLM only |
| Codex CLI | ●● | ● | ● | ●● | ●● | ●● | ●●● | ○ | ○ | API |
| Gemini CLI | ● | ● | ○ | ●● | ●● | ●● | ●●● | partial | ○ | API |
| Windsurf | ● | ○ | ○ | ●● | ●● | ●● | ●●● | ○ | ○ | $15-60 |
| Copilot | ●● | ● | ● | ●● | ●● | ●● | ●●● | ○ | ○ | $10-39 |
| Junie | ●● | ● | ● | ●● | ●● | ● | ●●● | ○ | ○ | bundle |
| Zed | ● | ● | ○ | ●●● | ● | ●● | ●●● | ●●● | ●●● | $0-30 |
| Devin 2.0 | ●● | ●● | ●● | ●●● | ●● | ●● | ●●● | ○ | ○ | $20+ |
| Augment Code | ●● | ●● (Intent) | ●● | ●●● | ●●● | ●● | ●●● | ○ | partial | $20-200 |
| Spec Kit | ●● | ●●● | ●●● | agent-agnostic | ●● | ● | ●●● | ●●● | ●●● | $0 |
| TaskMaster AI | ○ | ○ | ●●● | drop-in | ●● | ● | ●●● | ●●● | ●●● | $0 |
| AGENTS.md | ○ | ○ | ○ | ●●● | ●●● | ○ | ●●● | ●●● | ●●● | $0 |
| Claude Skills | ● | ● | ○ | ●● | ●●● | ●●● | ●●● | partial | partial | $0 |
| DSPy | ○ | ●● (sigs) | ○ | ●● | ● | ● | ●● (Py) | ●●● | ●●● | $0 |
| LangFuse | ●● (eval) | ●● | ○ | observability | ● | ● | ●●● | ●●● | ●●● | $0-29 |
| Maxim AI | ●●● (eval) | ●●● | ○ | observability | ●● | ●● | ●●● | ○ | partial | enterprise |

**Чтение таблицы:** TAUSIK — единственный продукт с тройной сильной позицией по **(quality gates + verification-as-code + task journal)** одновременно. Spec Kit подбирается ближе всего (●●/●●●/●●●), но не enforced. Claude Code + Skills сильны по Memory/Plugins. Maxim/LangFuse сильны по eval, но не интегрируются с агентом как process layer.

---

## 4. Где TAUSIK лидирует — ниши и преимущества

### 4.1 Verify-First Cache + AC-Verified Done
Никто другой не реализует «verify запускает heavy gates, кэшируется 10 минут, task done читает кэш». В индустрии есть Stop Hooks (Claude Code), pre-commit hooks, CI-уровень PR-checks — но не сквозной кэш-контракт между verify и done в одном CLI. Это **технически уникальная** часть TAUSIK.

### 4.2 SENAR + RENAR как открытые нормативные стандарты
SENAR (15 правил, 5 QG, 10 метрик) + RENAR (requirements engineering) — открытая methodology, которая может стать «AGENTS.md для процесса», как AGENTS.md стал для контекста. Если разогнать adoption — это превращается в нормативный слой над любым агентом.

### 4.3 Task lifecycle с journal + dead-end documentation
TaskMaster даёт задачи, но не журнал шагов и не dead-end — только `set_task_status`. TAUSIK единственный требует логировать каждый шаг и документировать тупики. Это важно для compliance/audit-trail сценариев (legal, fintech, gov).

### 4.4 Open-source + self-host + zero-vendor-lock
В когорте «discipline»-инструментов (Continue.dev, Augment Intent, Maxim) только Continue.dev открытый и self-host. Continue идёт в IDE — TAUSIK идёт в CLI. Это уникальный угол.

### 4.5 Instrumented agent + cross-tool (MCP-first)
TAUSIK уже работает с любым агентом через MCP — то есть может «оборачивать» Claude Code, Cursor (через MCP), Codex, Gemini CLI. Никто из chain-of-thought competitors не позиционирует себя как agent-agnostic discipline layer.

---

## 5. Где TAUSIK отстаёт

### 5.1 Дистрибуция и mindshare
0★ публично vs 90k★ Spec Kit, 41k★ Aider, 61k★ Cline. Без дистрибуции — даже идеальный продукт не виден. AGENTS.md за один год набрал 60k репо благодаря OpenAI/Google/Cursor/Anthropic совместной донации в Linux Foundation; SENAR/TAUSIK играют в одиночку.

### 5.2 Ecosystem & integrations
TaskMaster: drop-in для Cursor/Lovable/Windsurf/Roo/Claude Code. TAUSIK: преимущественно Claude Code. Не хватает явных адаптеров для Cursor, Codex, Cline, Roo.

### 5.3 Eval/observability nativ
Maxim/LangFuse/Galileo дают eval, traces, simulation. TAUSIK — metrics + verify, но не сравним eval-pipeline. Enterprise будет требовать.

### 5.4 Не-Python экосистема
Python 3.11+ stdlib — это и плюс, и потолок. TS/Go-команды воспринимают «Python CLI» как чужеродный. Spec Kit — agent-agnostic, TaskMaster — TS-friendly.

### 5.5 Spec-driven не нативный
Spec Kit прямо называет «spec-driven». TAUSIK имеет goal + AC, но не позиционируется как spec-driven. Это упускает запрос рынка.

### 5.6 Cloud/team-уровень отсутствует
Multi-developer flows (Roo Code Cloud, Cursor Teams, Augment Enterprise) — у TAUSIK нет.

---

## 6. Head-to-head сценарии

| Сценарий | Winner | Почему |
|---|---|---|
| Solo dev, terminal, Claude API, mission-critical proj | **TAUSIK + Claude Code** | TAUSIK даёт дисциплину, Claude Code — мощность |
| Solo dev, want one tool, just want chat IDE | **Cursor / Cline** | TAUSIK overhead-у |
| Enterprise, compliance-heavy, audit trail | **TAUSIK или Augment Intent** | TAUSIK если open-source preferred; Augment если SaaS|
| Startup MVP / vibe coding | **Bolt / v0 / Replit** | TAUSIK слишком серьёзный |
| Autonomous PR machine | **Devin / OpenHands / Copilot Coding Agent** | TAUSIK не про автономность |
| Monorepo 500k файлов | **Augment Code / Cursor** | TAUSIK не индексирует |
| Spec-first greenfield | **Spec Kit** | прямой матч |
| LangChain/LangGraph multi-agent | **DSPy / LangGraph** | разные сценарии |
| AI agent governance & metrics | **Maxim / LangFuse + TAUSIK** | комплементарны |

---

## 7. Market trends Q1-Q2 2026

1. **Аккумуляция власти у двух exits:** Cognition+Windsurf+Devin ($25B) и Anthropic+Claude Code ($2.5B ARR, Stainless acquisition, Bun, Vercept). Cursor — потенциально SpaceX $60B.
2. **OpenAI vs Cognition vs Anthropic vs Cursor — 4-way war.** xAI Grok Build добавился весной 2026.
3. **AGENTS.md = новый стандарт.** Donated to Linux Foundation Dec 2025; adopted by 60k+ репо.
4. **Skills как формат.** Anthropic Skills spec открыт; OpenAI приняла его для Codex CLI/ChatGPT.
5. **Spec-Driven Development резко поднимается.** Spec Kit 90k★ за полгода; Augment Intent.
6. **Hooks/Stop hooks как способ принудительной проверки.** Тренд внутри Claude Code и других.
7. **Trust crisis.** Stack Overflow 2025: 84% используют AI, 96% не доверяют. Sonar 2026: 42% кода AI, рост до 65% к 2027 — но 96% не доверяют. Это формирует спрос на discipline layer.
8. **Pricing wars.** Cursor от $20 до $200; Copilot перешёл на credit-based с июня 2026; Claude Code Agent SDK credit с 15 июня 2026.
9. **MCP стал нормой.** Все CLI-агенты поддерживают MCP-серверы; Roo Code — MCP client из коробки.
10. **Background/parallel agents.** Cursor, Zed 1.0, Roo Cloud — новая граница UX.

---

## 8. Белые пятна на рынке

1. **Compliance-grade audit trail для AI-кода.** SOC2/HIPAA/PCI требуют evidence-trail. TAUSIK journal + dead-end docs + verify cache — естественный фундамент. Никто этого open-source не закрывает.
2. **Cross-agent governance.** Команда использует Cursor + Claude Code + Copilot одновременно — кто гарантирует, что все играют по одним правилам? AGENTS.md даёт контекст, но не enforcement.
3. **Verification-как-первоклассный-артефакт.** Все хотят verify, но никто не делает её гранулярной и кэшируемой между задачами.
4. **Open-source enterprise discipline.** Augment Intent — SaaS-only. Continue.dev — open IDE, но не CLI. TAUSIK может занять «open-source Augment Intent».
5. **Не-Python first-class CLI.** TypeScript/Go.

---

## 9. Топ-10 находок и рекомендаций

1. **Слоган удержать, но привязать к данным.** "Can't fake done" работает потому что 96% разработчиков не доверяют AI. Добавить в landing цифры Sonar/SO — это конвертирует.
2. **AGENTS.md-совместимость — критична.** TAUSIK должен генерировать AGENTS.md и читать его. Иначе отрезает 60k+ репо.
3. **Claude Skills-совместимость.** Любая TAUSIK-памятка/конвенция должна экспортироваться в формат Skill — это путь в Anthropic Marketplace и в OpenAI Codex.
4. **Позиционирование: «open-source discipline layer».** Не «yet another agent», не «yet another task tracker». Прямые слова: enforced quality gates + verify-first cache + dead-end journal.
5. **Дифференциация от Spec Kit и TaskMaster.** Spec Kit = что делать; TaskMaster = трекинг шагов; TAUSIK = enforcement + verification cache + journal. Сравнительная таблица на landing обязательна.
6. **Compliance-кейс.** Legal/fintech/gov — рынок premium. Audit trail + journaling + verify cache = почти готовый pitch для SOC2.
7. **Cross-agent adapters.** Поддержка Cursor (MCP), Codex CLI, Cline, Gemini CLI — расширяет ICP в 5-10x.
8. **TypeScript port или wrapper.** Минимум — JS/TS SDK или CLI bridge.
9. **Eval-интеграция.** LangFuse / Maxim экспорт metrics — даст «enterprise tick».
10. **Дистрибуция через AGENTS.md и Spec Kit.** Сделать TAUSIK «runtime» для Spec Kit specs — это piggyback на 90k★.

---

## 10. Ответ на 4 вопроса заказчика

### Топ-3 самых опасных конкурента
1. **GitHub Spec Kit (90k★, бесплатный, GitHub-спонсорство).** Покрывает ~70% сценариев TAUSIK с гораздо большей дистрибуцией.
2. **Claude Skills + Hooks + AGENTS.md (Anthropic ecosystem).** Втягивают discipline в нативный слой Claude Code; если добавят enforced verify + journal — TAUSIK становится избыточным.
3. **TaskMaster AI (drop-in для всех агентов).** Самый прямой конкурент по форме (CLI + tasks + AI-agent friendly).

### Уникальная позиция TAUSIK
**Enforced verification-as-cache contract** — единственный продукт, в котором `task done` физически читает кэш `verify --task <slug>` и блокирует завершение без свежей верификации. Это техническая дисциплина, которую никто иной не делает декларативно.

### 3 рыночных тренда, которые могут «обнулить» TAUSIK через 12 месяцев
1. **Claude Code + Skills + Hooks нативно реализует quality gates и task journaling.** Уже намечается (Stop hooks, plugin marketplace, Agent SDK credits).
2. **AGENTS.md/Skills становятся универсальным стандартом разметки.** Если в стандарт зашьют `verify:` поля и `gates:` — кастомный CLI окажется не нужен.
3. **Spec Kit + Augment Intent + Copilot Coding Agent поглощают «discipline» как фичу SaaS.** Команды выбирают «уже встроено», а не «отдельный фреймворк».

### 3 ниши для роста
1. **Compliance-grade enterprise (SOC2/HIPAA/PCI/Legal/Fintech/Gov).** Audit trail + verify cache + journaling + open-source — почти готовый pitch.
2. **Multi-agent governance plane.** Команда использует 3-4 разных агента; TAUSIK как «один источник правил и логов» для всех (через MCP).
3. **Spec Kit runtime / AGENTS.md extension.** TAUSIK как enforced layer поверх Spec Kit specs или Skills — пиггибэк на 60-90k★ распределения.

---

## 11. Источники (URL для проверяемости)

### Категория 1 — CLI Agents
- [Aider Review 2026](https://toolbrain.net/aider-review-2026/)
- [Aider site](https://aider.chat/)
- [Cline GitHub](https://github.com/cline/cline)
- [Cline.bot](https://cline.bot/)
- [Roo Code GitHub](https://github.com/RooCodeInc/Roo-Code)
- [Roo Code Docs](https://docs.roocode.com/)
- [OpenHands](https://www.openhands.dev/)
- [OpenHands Index Jan 2026](https://www.openhands.dev/blog/openhands-index)
- [Goose docs](https://goose-docs.ai/)
- [Goose Review 2026](https://aitoolanalysis.com/goose-ai-review/)
- [Continue.dev pricing](https://www.continue.dev/pricing)
- [Continue GitHub](https://github.com/continuedev/continue)
- [Cody pricing 2026](https://costbench.com/software/ai-coding-assistants/sourcegraph-cody/)
- [Claude Code product](https://www.anthropic.com/product/claude-code)
- [Claude Code vs Codex vs Gemini 2026](https://www.deployhq.com/blog/comparing-claude-code-openai-codex-and-google-gemini-cli-which-ai-coding-assistant-is-right-for-your-deployment-workflow)
- [Codex CLI in Rust 2026](https://dev.to/rahulxsingh/claude-code-vs-codex-cli-vs-gemini-cli-which-ai-terminal-agent-wins-in-2026-55f5)

### Категория 2 — IDE-based
- [Cursor pricing](https://www.aitooldiscovery.com/guides/cursor-ai-pricing)
- [Cursor statistics 2026](https://www.getpanto.ai/blog/cursor-ai-statistics)
- [Cursor $50B valuation](https://letsdatascience.com/blog/cursor-2-billion-funding-round-50-billion-valuation)
- [SpaceX Cursor $60B](https://thetechmarketer.com/spacex-cursor-deal-60-billion-ai-coding/)
- [Windsurf review 2026](https://www.taskade.com/blog/windsurf-review)
- [Windsurf statistics](https://www.getpanto.ai/blog/windsurf-ai-ide-statistics)
- [Cognition acquires Windsurf TC](https://techcrunch.com/2025/07/14/cognition-maker-of-the-ai-coding-agent-devin-acquires-windsurf/)
- [Cognition $10.2B](https://www.cnbc.com/2025/09/08/cognition-valued-at-10point2-billion-two-months-after-windsurf-.html)
- [Cognition $25B Apr 2026](https://www.idlen.io/news/cognition-devin-25-billion-valuation-windsurf-vibe-coding-april-2026/)
- [Copilot 2026 pricing](https://github.com/features/copilot/plans)
- [Copilot Agent Mode 2026](https://pinklime.io/blog/github-copilot-agent-mode-2026)
- [JetBrains Junie](https://www.jetbrains.com/junie/)
- [Zed pricing](https://zed.dev/pricing)
- [Zed AI Review 2026](https://aitoolshaven.com/ai-tool/zed-ai-editor/)

### Категория 3 — Cloud / Autonomous
- [Devin pricing](https://devin.ai/pricing/)
- [Devin SWE-bench technical report](https://cognition.ai/blog/swe-bench-technical-report)
- [SWE-agent GitHub](https://github.com/SWE-agent/SWE-agent)
- [mini-swe-agent](https://github.com/SWE-agent/mini-swe-agent)
- [Augment Code pricing](https://www.augmentcode.com/pricing)
- [Augment Context Engine](https://www.augmentcode.com/context-engine)
- [Replit vs v0 vs Bolt 2026](https://medium.com/@aftab001x/the-2026-ai-coding-platform-wars-replit-vs-windsurf-vs-bolt-new-f908b9f76325)
- [xAI Grok Build](https://devops.com/xai-enters-the-coding-agent-race-with-grok-build/)

### Категория 4 — Frameworks
- [LangGraph vs CrewAI vs AutoGen 2026](https://pecollective.com/blog/ai-agent-frameworks-compared/)
- [LangGraph vs CrewAI vs AutoGen DataCamp](https://www.datacamp.com/tutorial/crewai-vs-langgraph-vs-autogen)
- [Claude Agent SDK](https://code.claude.com/docs/en/agent-sdk/overview)
- [Anthropic Building Agents](https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk)
- [Google ADK docs](https://google.github.io/adk-docs/)
- [Google ADK 1.0 + A2A](https://explore.n1n.ai/blog/google-adk-1-0-a2a-protocol-multi-agent-standard-2026-05-04)
- [OpenAI vs Google ADK](https://iamulya.one/posts/a-developer-guide-to-ai-agents-openai-agents-sdk-vs-google-adk/)

### Категория 5 — Rules/Instructions
- [AGENTS.md](https://agents.md/)
- [AGENTS.md guide 2026](https://blog.buildbetter.ai/agents-md-complete-guide-for-engineering-teams-in-2026/)
- [AGENTS.md Codex docs](https://developers.openai.com/codex/guides/agents-md)
- [Anthropic Skills](https://www.anthropic.com/news/skills)
- [Claude Code Plugins official](https://github.com/anthropics/claude-plugins-official)
- [Claude marketplaces](https://claudemarketplaces.com/)
- [Cursor Rules vs CLAUDE.md vs AGENTS.md](https://thepromptshelf.dev/blog/cursorrules-vs-claude-md/)
- [SKILL.md vs CLAUDE.md vs .cursorrules](https://www.agensi.io/learn/skill-md-vs-claude-md-vs-cursorrules)
- [Spec Kit GitHub](https://github.com/github/spec-kit)
- [Spec Kit announce](https://github.blog/ai-and-ml/generative-ai/spec-driven-development-with-ai-get-started-with-a-new-open-source-toolkit/)
- [TaskMaster AI](https://github.com/eyaltoledano/claude-task-master)

### Категория 6 — Quality / Governance
- [DSPy](https://dspy.ai/)
- [DSPy GitHub](https://github.com/stanfordnlp/dspy)
- [LangFuse alternatives 2026](https://futureagi.com/blog/langfuse-alternatives-2026)
- [Best LLM observability 2026](https://www.firecrawl.dev/blog/best-llm-observability-tools)
- [Maxim AI top observability 2026](https://www.getmaxim.ai/articles/top-5-llm-observability-platforms-in-2026/)
- [Quality gates for coding agents](https://blog.codacy.com/why-coding-agents-need-independent-quality-gates)
- [Vibe coding quality gate CI](https://getautonoma.com/blog/quality-gate-vibe-coding)
- [Stop hooks quality gates](https://fbakkensen.github.io/ai/devtools/development/2026/03/27/quality-gates-for-coding-agents-how-stop-hooks-make-validation-mandatory.html)
- [Qodo context plane verification](https://www.qodo.ai/blog/context-plane-and-verification/)
- [SENAR](https://senar.tech/en/)
- [SENAR GitHub](https://github.com/Kibertum/SENAR)

### Market trends
- [Stack Overflow 2025 AI](https://survey.stackoverflow.co/2025/ai)
- [Stack Overflow trust gap 2026](https://stackoverflow.blog/2026/02/18/closing-the-developer-ai-trust-gap/)
- [Sonar State of Code 2026 pdf](https://www.sonarsource.com/state-of-code-developer-survey-report.pdf)
- [Sonar State of Code blog](https://www.sonarsource.com/blog/state-of-code-developer-survey-report-the-current-reality-of-ai-coding)
- [42% AI code 96% no trust](https://shiftmag.dev/state-of-code-2025-7978/)
- [AI execution hallucination](https://dev.to/mrlinuncut/ai-execution-hallucination-when-your-agent-says-done-and-does-nothing-586i)
- [Multi-agent validation against hallucination](https://dev.to/aws/how-to-stop-ai-agents-from-hallucinating-silently-with-multi-agent-validation-3f7e)
- [Anthropic acquires Stainless](https://devops.com/cognition-labs-previews-devin-ai-software-engineer/)
- [Cursor $3.4B funding](https://www.buildmvpfast.com/blog/cursor-3b-funding-agentic-coding-fastest-saas-2026)

---

*Конец документа. Объём ~13 страниц. Следующий шаг — внутренняя дискуссия по «top-10 находок» и приоритизация в roadmap.*
