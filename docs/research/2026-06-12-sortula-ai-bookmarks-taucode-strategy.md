# Исследование: AI-закладки Sortula → улучшения TAUSIK + стратегия TauCode

**Дата:** 2026-06-12 | **Задача:** `research-sortula-ai-bookmarks-analysis-taucode-str` | **Сессия:** #77

**Источники:**
- Prod БД Sortula (root@172.50.0.19): 331 закладка пользователя andrey.jumashev@gmail.com, из них 169 AI-связанных (категория «AI / ML» или AI-теги), период янв–июнь 2026. Выгрузка: `d:/tmp/sortula_ai_bookmarks.jsonl` (read-only SQL, COPY TO STDOUT).
- Веб-исследование ландшафта агентских харнессов (июнь 2026): OpenCode, Claude Agent SDK, pi, Goose, Aider, Crush, Codex CLI, Cline/Roo/Kilo, Spec Kit, Kiro, Conductor.
- Внутренний контекст: `docs/audit/audit-report-2026-05-18.md`, память фреймворка (#24 классификация багов), handoff сессии #76 (план v1.5 evidence-attestation).

---

## Часть 1. Что я наоткладывал и что это значит для TAUSIK

### 1.1 Профиль интересов (169 закладок, 15 кластеров)

| Кластер | Кол-во | Суть |
|---|---|---|
| Claude Code: конфигурация, skills, hooks | 26 | Самый плотный кластер — harness engineering |
| Локальный инференс + uncensored модели | 18 | Qwen/Gemma GGUF, квантизация, VRAM-бюджеты |
| Мультиагентная оркестрация | 16 | A2A, AgentScope, DeerFlow, oh-my-claudecode, Kimi K2.6 |
| Спец-применения AI (SRE, legal, CAD, OSINT) | 12 | HolmesGPT, claude-for-legal, CADAM, GeoIntel |
| Инфраструктура и модели (новости) | 12 | DeepSeek V4, Nemotron 550B, GLM-5, cloud GPU |
| Генерация изображений/видео | 11 | Qwen-Image, VOID, LTX-2, Kling 3.0 |
| AI coding assistants / IDE | 10 | Cursor 3, opencode, openclaude, Opilot |
| Prompt engineering / token economy | 10 | Cave-man prompts (−75% токенов), GPT-5.5 guide |
| Self-hosting AI | 10 | Local Deep Research, Odysseus, Hermes Desktop |
| MCP-экосистема | 9 | docs-mcp-server, iai-mcp, OpenRAG, Chrome MCP |
| RAG, память, знания | 8 | turbovec, PaddleOCR, Karpathy second brain |
| AI security / adversarial | 8 | MicroClaw, Deepsec, Moltbook breach, supply chain |
| Vibe-coding критика | 8 | Провалы делегирования архитектуры LLM |
| Философия/социология AI | 6 | Hallucinations-as-compression, relational economy |
| TTS / voice | 5 | Voxtral, Voicebox, MisoTTS |

**Повторяющиеся одержимости** (3+ раза за полгода):
1. Claude Code harness engineering (15+) — hooks > промпты, слоистые архитектуры контроля.
2. Локальные uncensored/distilled модели (10+) — систематический трекинг Qwen/Gemma релизов.
3. Мультиагентная координация (10+) — от одиночных тулов к fleet management и A2A.
4. SKILL.md как примитив расширения (8+) — маркетплейсы, коллекции, кросс-harness наборы.
5. Token economy и контроль через промпт (6+).
6. Эпистемический реализм о пределах LLM (5+) — «тесты проходят, физика бессмысленна».

**Динамика по времени:** янв–фев — широкая разведка; март — кристаллизация на Claude Code (момент рождения TAUSIK-одержимости); апрель — пик напряжения «энтузиазм vs скепсис» (лучшие аналитические статьи); май–июнь — продакшн-зрелость: эффективность инференса, предотвращение галлюцинаций, персистентная память, безопасность.

> Вывод-зеркало: закладки показывают траекторию «что может AI → как запускать это надёжно, приватно и в масштабе». TAUSIK — ровно ответ на эту траекторию, и закладки подтверждают рыночность ниши discipline layer.

### 1.2 Маппинг закладок на улучшения TAUSIK

Десять конкретных идей, отсортированы по соотношению ценность/усилие:

**T1. «Самокорректирующийся CLI» — лечим «агент гадает аргументы» (источник: docs-mcp-server, идея grounding)**
Корневая причина боли — агент угадывает API из устаревших весов. Решение docs-mcp-server: подавать актуальную документацию в момент ошибки. Для TAUSIK: при любой ошибке парсинга аргументов CLI/MCP возвращать в тексте ошибки машиночитаемый usage-блок (`--help` соответствующей подкоманды + 1–2 примера). Агент восстанавливается за одну итерацию вместо цикла догадок. Усилие: дни. **Quick win для v1.5.**

**T2. Эскалирующие nudges вместо тотальных hard gates (источник: barkain/claude-code-workflow-orchestration)**
Прецедент: hook-фреймворк отказался от жёстких блокировок везде в пользу эскалации silent→hint→warning→strong. UX-урок для TAUSIK: жёсткость точечно (commit, `task done`, push), мягкая эскалация в потоке (journaling, checkpoint). Снижает раздражение и «обходные манёвры» агента. Усилие: 1–2 недели, ложится на существующие хуки.

**T3. `tausik tune` — ночная самооптимизация харнесса (источник: AutoAgent, SOTA на SpreadsheetBench 96.5%)**
Ключевая находка AutoAgent: «traces matter more than metrics», и одна модель как мета- и worker-агент работает лучше пар. TAUSIK уже пишет usage events и task logs — это готовые traces. Команда `tausik tune`: мета-агент читает трейсы неудачных tool calls / gate failures за N сессий и предлагает диффы к CLAUDE.md/hooks/skills. Связка с telemetry-opt-in из R3 аудита. Усилие: 3–4 недели. **Кандидат в v1.6 — потенциально killer feature №2 после Verification-as-Cache.**

**T4. Граф зависимостей в codebase-rag (источник: CodeCompass, arXiv 2602.20048)**
Эмпирика: больший контекст НЕ решает навигацию по большим кодовым базам, граф зависимостей даёт +23.2% на архитектурных задачах. Добавить в codebase-rag слой import/call-графа (Python stdlib ast — в духе стека). Усилие: 2–3 недели.

**T5. Memory lint — LLM-проверка противоречий в памяти (источник: Karpathy second brain)**
Подход Карпатти: лёгкий LLM-линтинг wiki на противоречия вместо тяжёлого RAG. У TAUSIK есть `memory dedupe` — добавить `memory lint`: поиск противоречий и устаревших фактов между memory-записями (граф связей уже есть). Усилие: 1–2 недели.

**T6. Deny-by-default toolkit-профили (источник: MicroClaw)**
Принцип MicroClaw: креды не попадают в контекст модели, тулы сгруппированы в toolkits, доступ только по allowlist. Для TAUSIK: permission-профили per-role (Reviewer SHALL NOT have write — SENAR уже требует, но не enforced) + секреты через env-injection в хуках, никогда в контекст. Синергия с v1.5 evidence-attestation. Усилие: входит в v1.5 story.

**T7. Judge-пайплайн для недетерминированных AC (источник: LLM-as-a-Judge в тестировании)**
Гибрид vector-similarity + LLM-judge для верификации acceptance criteria, где вывод недетерминирован (генерация текста, отчёты). Judge ≠ production model — уже требование RENAR (TC isolation). Закрывает дыру QG-2 «no security vulnerabilities … без specifying scanner» (аудит §8.6.30). Усилие: 3–4 недели.

**T8. «Domain challenge» шаг в QG-2 (источник: arXiv 2605.30353, астрофизика)**
57 сессий: агент нашёл «работающий» поправочный коэффициент, прошедший все тесты, но физически бессмысленный — и сам этого не увидел. Правило: тесты не заменяют domain expertise. В QG-2 checklist добавить пункт «задай себе 1 доменный вопрос: имеет ли результат смысл вне тестов?» + поле в evidence. Дешёвый частичный ответ на SENAR Rule 4 (External Validation — сейчас не имплементирован). Усилие: дни.

**T9. cq-интеграция / federation tausik-brain (источник: cq Mozilla — «Stack Overflow для агентов»)**
Уже в памяти как план (#31), закладки подтверждают актуальность. Кросс-проектные知 dead ends — естественный экспорт-формат TAUSIK в cq. Низкий приоритет до появления у cq трекшена.

**T10. AGENTS.md-совместимость как badge (источник: рост AGENTS.md-экосистемы в закладках)**
Риск №2 аудита: AGENTS.md становится универсальной разметкой. Генерировать AGENTS.md из bootstrap наравне с CLAUDE.md/QWEN.md («AGENTS.md compatible» позиционирование: AGENTS.md = static contract, TAUSIK = runtime gates). Усилие: дни.

---

## Часть 2. Куда идти дальше: TauCode vs VS Code extension

### 2.1 Диагноз: почему агент «сбивается»

Боль формулируется так: enforcement живёт на уровне промпта (CLAUDE.md) и внешних хуков, а должен жить на уровне рантайма. Подтверждения:
- Память #24: MCP — 33% всех багов фреймворка (hangs, таймауты, stale modules); bootstrap — 25%; Windows — 25%.
- Self_check / drift detection существует именно потому, что MCP-слой ненадёжен.
- Закладка-инсайт («582-line CLAUDE.md»): *правило в промпте — пожелание; hook — гарантия*. TAUSIK уже на 70% hook-enforced, но journaling, checkpoint, выбор инструментов — всё ещё промпт.

### 2.2 Ландшафт (июнь 2026, проверено веб-исследованием)

| Вариант | Состояние | Enforcement | Усилие до MVP | Главный риск |
|---|---|---|---|---|
| **A. OpenCode-плагин** (не форк!) | OpenCode: ~165k★, MIT, client/server, плагины с `tool.execute.before` → **жёсткая блокировка исключением**, permissions allow/ask/deny, 75+ провайдеров | Жёсткий, runtime | **2–4 недели** (плагин), 1–2 мес production | Темп upstream (Anomaly + 900 контрибьюторов), эволюция plugin API |
| **B. Claude Agent SDK** | In-process hooks: `PreToolUse` с `permissionDecision: deny` и **`updatedInput`** (можно переписать аргументы!), `canUseTool` на каждый вызов, подмена вывода | Жёсткий, контроль каждой итерации | **4–8 недель** (policy-слой; loop готов) | Lock-in на Anthropic-модели и биллинг |
| **C. VS Code extension** | BYOK API созрел (LanguageModelChatProvider, апр 2026 — Business/Enterprise); Cline 63k★ Apache 2.0; **Roo Code закрылся 15.05.2026** («IDE — не будущее кодинга») | Средний | Форк Cline: 2–4 мес; с нуля: 6+ мес | Зависимость от политик Copilot/MS; рыночный сигнал против; огромный наследуемый код |
| **D. Свой харнесс с нуля** | Воспроизвести TUI+server+провайдеры+LSP = человеко-годы (Anomaly делала год командой) | Полный | 6–12+ мес | Гонка на содержание вместо развития дифференциатора |
| (опция) **pi (badlogic)** | 62k★, MIT, «анти-фреймворк»: extensions с `block: true`, заменой системного промпта, hot-reload | Жёсткий | 3–6 недель extension | Молодая экосистема, маленькое core |

Прецеденты «discipline layer как продукт»: Spec Kit (~80k★) enforce'ит только промптами/шаблонами; Kiro (AWS) — единственный enforcement-first, но как отдельная IDE; Microsoft Conductor (май 2026) — детерминированная оркестрация. **Никто не совмещает спеки + runtime-гейты + проектную память + сессии — это и есть наша дифференциация.**

### 2.3 Рекомендация: «enforcement-адаптеры, не свой харнесс»

Дифференциатор TAUSIK — policy-ядро (gates, verify-cache, память, сессии), а не харнесс. Харнессы коммодитизируются (OpenCode 165k★ бесплатно, Kimi CLI, Codex). Стратегия — **одно Python policy-ядро + тонкие адаптеры к чужим рантаймам**:

**Фаза 0 — «починить сегодняшний дом» (v1.5, 2–4 недели, параллельно evidence-attestation):**
- T1 самокорректирующийся CLI + T2 эскалирующие nudges.
- Углубить Claude Code хуки: PreToolUse deny на полное покрытие workflow-инвариантов (сейчас часть — в промпте). Claude Code hooks уже поддерживают детерминированный deny — использовать на 100%.
- Эффект: «сбивается на вызовах» лечится в текущей среде без смены платформы.

**Фаза 1 — TauCode = OpenCode-дистрибутив (Q3 2026, MVP 2–4 недели):**
- TAUSIK-плагин для OpenCode: `tool.execute.before` бросает исключение при нарушении gate (нет активной задачи → Write заблокирован — то же, что наш task_gate hook, но runtime-гарантия); кастомные тулы `tausik_*`; permission-конфиг по ролям SENAR.
- «TauCode» как брендированный дистрибутив: `npm create taucode` → OpenCode + плагин + bootstrap. Свой бренд без форка и rebase-налога.
- Бонус: 75+ провайдеров из коробки → закрывает vendor lock-in (аудит §4.10) и открывает локальные Qwen-модели (одержимость №2 в закладках).

**Фаза 2 — Agent SDK адаптер для headless/CI (Q4 2026, 4–8 недель):**
- `taucode run --task <slug>` поверх Claude Agent SDK: PreToolUse `updatedInput` (тихо чинить аргументы CLI!), canUseTool как программный QG, UserPromptSubmit-инъекция контекста задачи.
- Применение: CI-агенты, cloud-раннеры, SENAR Rule 4 external reviewer на другой модели.

**Фаза 3 — VS Code как панель, не как агент (опционально, Q1 2027):**
- НЕ агент-расширение (смерть Roo Code — прямой сигнал). Вместо этого тонкая «TAUSIK Dashboard»-панель: задачи, статус gates, сессия, память — поверх любого агента, работающего в терминале IDE. Усилие: 2–3 недели, нулевая зависимость от Copilot-политик. (Вдохновение: Pixel Agents из закладок — визуализация активности агентов.)
- Полноценный форк Cline — только если рынок развернётся обратно к IDE.

**Почему не свой харнесс и не форк:** гонку рантаймов выигрывают команды с фондированием (Anomaly: раунд, 6.5M MAU); наш узкий ров — «AI agents that can't fake done», и он переносим. Каждый адаптер — недели, а не кварталы, и все три используют одно ядро.

### 2.4 Связь с roadmap аудита

Стратегия адаптеров не противоречит roadmap Q3–Q4 2026 (telemetry, Cursor MCP rework, AAIF, SWE-bench R1) — она его конкретизирует: TauCode-дистрибутив = «distribution» из Q4; SWE-bench бенчмарк (R1) логично гнать уже на TauCode (TAUSIK-плагин vs голый OpenCode — чистый A/B эффекта discipline layer, более честный, чем vs Claude Code).

---

## Приложение: top-источники из закладок для проработки

| Источник | Зачем |
|---|---|
| github.com/kevinrgu/autoagent | T3 — методика self-optimization, «traces > metrics» |
| arxiv.org/html/2602.20048v1 (CodeCompass) | T4 — графовая навигация по коду |
| github.com/arabold/docs-mcp-server | T1 — grounding документации против галлюцинаций API |
| arxiv.org/pdf/2605.30353 (астрофизика) | T8 — пределы агентов, domain challenge |
| u.habr.com/rMxwR (582-line CLAUDE.md) | Фаза 0 — слои Rules/Memory/Handoffs/Hooks/Skills |
| github.com/barkain/claude-code-workflow-orchestration | T2 — эскалирующие nudges |
| opencode.ai/docs/plugins | Фаза 1 — plugin API для TauCode |
| code.claude.com/docs/en/agent-sdk/hooks | Фаза 2 — PreToolUse deny/updatedInput |
| github.com/badlogic/pi-mono (extensions.md) | Опция — самая чистая база, если захотим владеть циклом |
| u.habr.com/0rgFw (MicroClaw) | T6 — deny-by-default, изоляция кредов |
