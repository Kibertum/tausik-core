<script setup lang="ts">
import { computed } from "vue";
import constants from "../../../../docs/_generated/constants.json";

interface Props {
  lang?: "en" | "ru";
}
const props = withDefaults(defineProps<Props>(), { lang: "en" });

const HOOKS = constants.hooks_count;
const REVIEW_AGENTS = constants.review_agents_count;
const SKILLS_CORE = constants.skills_core_count;
const MCP_TOOLS = constants.mcp_main_tools;
const TESTS = constants.test_count;
const STACKS = constants.stacks_count;
const VERSION = constants.tausik_version;

const copy = {
  en: {
    eyebrow: "Discipline layer for AI coding agents",
    nav: {
      brand: "TAUSIK",
      items: [
        ["Receipts", "#receipts"],
        ["Lifecycle", "#lifecycle"],
        ["Features", "#what-you-get"],
        ["Compare", "#compare"],
        ["Quick start", "#quick-start"],
      ],
      cta: "Get started",
    },
    hero: {
      titleA: "AI agents that can't",
      titleB: "fake 'done'",
      lede:
        "A local Python framework that gates Claude Code, Cursor, Qwen, and Windsurf at the two points where AI agents lie most: starting a task without a goal, and claiming completion without proof. Three messages cover the full cycle.",
      ctaPrimary: "Get started",
      ctaSecondary: "View on GitHub",
      badges: ["ed25519 signed receipts", "Apache 2.0", "Python 3.11+", `${TESTS.toLocaleString("en-US")} tests passing`, "0 core dependencies"],
      termTitle: "~/your-project — claude code",
      annos: [
        { k: "/start", v: "opens session, reloads context" },
        { k: "/task", v: `creates AC · runs tests · ${REVIEW_AGENTS}-agent review` },
        { k: "/ship", v: "verifies → signs a receipt → commits → asks before push" },
      ],
    },
    compare: {
      eyebrow: "The problem · The mechanism",
      title: "Without TAUSIK",
      titleSep: " vs ",
      titleAlt: "With TAUSIK",
      sub: "Enforcement, not suggestion. The agent literally cannot bypass the gate — the hook process blocks Write/Edit before the tool call lands.",
      headL: "Without TAUSIK",
      headR: "With TAUSIK",
      rows: [
        [
          'Agent says "I\'ll quickly refactor this" and edits 30 files.',
          'task_gate.py hook returns: BLOCKED — no active task (SENAR Rule 9.1).',
          "QG-0",
        ],
        [
          'Agent reports "Done — all green" without running tests.',
          'task_done_verify rejects close: AC #2 has no evidence row in verification_runs.',
          "QG-2",
        ],
        [
          "Next session starts blank. The agent re-asks the same questions.",
          "SessionStart hook injects handoff + memory tail. Last decision and dead-end load with CLAUDE.md.",
          "",
        ],
        [
          "Agent re-tries the same broken approach two days later.",
          "tausik dead-end records the failed approach. Search surfaces it before the agent burns more tokens.",
          "",
        ],
        [
          'Agent runs "the obvious tests" — usually none.',
          `tausik verify runs the ${STACKS}-stack matrix (pytest, ruff, tsc, eslint, cargo, go vet, hadolint…) and caches the result.`,
          "",
        ],
        [
          'You ask "what changed?" and read 200 lines of chat.',
          "tausik metrics prints throughput, defect rate, lead time, cost-per-task. Every gate exit is logged in events.",
          "",
        ],
      ],
    },
    receipts: {
      eyebrow: "Verifiable trust · the differentiator",
      title: "When the agent says green,",
      titleAccent: "you get a receipt.",
      sub: "This is what separates TAUSIK from every prompt-based ruleset. The green isn't a claim you take on faith — it's an ed25519-signed receipt bound to the exact gate and the HEAD commit. Forge-proof, replay-proof, verifiable offline.",
      points: [
        ["tausik verify emits a signed receipt", "Format tausik-signed/v1, ed25519, bound to the gate signature and the HEAD commit sha."],
        ["task done validates it before close", "A green that wasn't actually produced — or was produced for a different commit — fails QG-2."],
        ["Receipts are portable", "Export one and verify it offline: no SDK, a stateless HTTP endpoint or the no-SDK example."],
        ["Releases are signed too", "Skill and stack installs verify the signature before writing a byte to disk."],
      ],
      kicker: "When an agent tells you the build is green, you don't have to believe it. You hold a receipt that proves it — or proves it lied.",
      cta: "How signed receipts work",
      ctaHref: "/docs/receipts",
      termTitle: "tausik verify → receipt",
    },
    cycle: {
      eyebrow: "Task lifecycle",
      title: "Three messages. Full lifecycle.",
      sub: "You describe what you want. The framework forces the steps you skip when you trust the agent too much.",
      steps: [
        {
          n: "01",
          label: "session start",
          msg: "message 1 of 3",
          caption: "Opens session, loads handoff from the last one, refreshes the CLAUDE.md memory tail.",
        },
        {
          n: "02",
          label: "task lifecycle",
          msg: "message 2 of 3",
          caption: `Interviews you on edge cases, creates a task with acceptance criteria, writes the code, runs tests + lint + ${REVIEW_AGENTS} parallel review agents, verifies each AC has evidence in the DB.`,
        },
        {
          n: "03",
          label: "ship",
          msg: "message 3 of 3",
          caption: "Runs tausik verify (cached 10 min), passes QG-2, commits, asks before pushing.",
        },
      ],
      footer: "That's it. You describe what you want. The framework forces the steps you skip when you trust the agent too much.",
    },
    features: {
      eyebrow: "What you get",
      title: "Six things, none of them optional.",
      sub: "The framework is small on purpose. Every piece exists to enforce one specific behavior.",
      items: [
        ["Quality gates", "QG-0 blocks task start without goal + AC. QG-2 blocks task done without verify evidence."],
        ["Project memory", "SQLite + FTS5 for patterns, gotchas, decisions, dead-ends. Re-injected at session start."],
        ["Verify-First", "Heavy tests on a separate verify step, cached for 10 minutes; closing a task is millisecond."],
        [`${HOOKS} real-time hooks`, "Task gate, bash firewall, push gate, auto-format, memory audits — block bad actions before they happen."],
        [`${MCP_TOOLS} MCP tools`, "Full programmatic access to the project DB. Works the same in Claude Code, Cursor, Qwen Code, Windsurf."],
        ["Cross-project brain", "Notion-mirrored decisions, patterns, gotchas with privacy-preserving project hashes.", "optional"],
      ],
    },
    quickstart: {
      eyebrow: "Quick start — 10 minutes (after your AI IDE is set up)",
      title: "Four commands, then restart your IDE.",
      sub: "Bootstrap auto-detects your stack (Python, TS, Rust, Go) and enables matching quality gates.",
      copyBtn: "copy",
      copiedBtn: "copied",
      note: "Restart your IDE — done. Bootstrap auto-detects your stack and enables matching quality gates.",
      notes: [
        "Submodule pins the framework version per-project. Update with one git command.",
        "Hooks register with Claude Code and Qwen Code automatically. Cursor + Windsurf wire up via MCP.",
        "Local SQLite DB lives in .tausik/. Never committed. Mirrored to Notion only if you opt in.",
        "First start working creates session #1 and writes the initial CLAUDE.md tail.",
        "Windows: the .tausik/tausik wrapper is bash-only; use .tausik/tausik.cmd from PowerShell or cmd.exe.",
      ],
      fullLink: "Read the full quick-start",
      fullHref: "/docs/quickstart",
    },
    stats: {
      eyebrow: "Dogfooding",
      title: "TAUSIK built TAUSIK.",
      sub: "Every feature, every refactor, every bug fix went through the same gates that ship with the framework. The numbers below are the dogfood project's own state.",
      items: [
        ["800+", "tasks closed — every one with a goal + AC"],
        ["0", "tasks closed without verify evidence", true],
        [`${TESTS.toLocaleString("en-US")}`, "tests passing"],
        ["0", "core dependencies / phone-home calls"],
      ],
      foot: `Snapshot at v${VERSION}. Live numbers via tausik metrics.`,
    },
    ides: {
      eyebrow: "Supported IDEs & agents",
      title: "Six runtimes. One enforcement layer.",
      items: [
        ["VS", "VSCode + Claude Extension", "Officially tested", true],
        ["CR", "Cursor", "Officially tested", true],
        ["CC", "Claude Code (CLI)", "Expected · partial matrix", false],
        ["QC", "Qwen Code", "Expected · partial matrix", false],
        ["WS", "Windsurf", "Expected · partial matrix", false],
        ["OC", "Codex / OpenCode-style agents", "Expected · manual validation", false],
      ],
      foot: `${MCP_TOOLS} MCP tools and the ${SKILLS_CORE} core skills work everywhere. Real-time hooks live in Claude Code and Qwen Code today; Cursor and Windsurf get the same enforcement at QG-0 and QG-2 task transitions.`,
    },
    notSection: {
      eyebrow: "Clarity",
      title: "TAUSIK is not.",
      sub: "Setting expectations before you install.",
      items: [
        ["Not a SaaS.", "Everything runs locally. Your task DB lives in .tausik/ next to your code. No phone-home, no usage telemetry, no required account."],
        ["Not a model.", "TAUSIK does not generate code. It guards an existing coding agent (Claude Code, Cursor, Qwen, Windsurf) and tracks its work."],
        ["Not a replacement for Cursor / Claude Code.", "It runs inside them as MCP tools, hooks, and skills. You keep your existing IDE workflow."],
        ["Not a junior-onboarding tool.", "It enforces practice for engineers who already know what good looks like — it does not teach you what an AC is."],
        ["Not auto-merging.", "QG-0 and QG-2 ask the agent for proof; the agent still asks you to confirm before push."],
      ],
    },
    comparison: {
      eyebrow: "Landscape",
      title: "How TAUSIK differs.",
      sub: "Same row → same capability. Empty cell → the tool does not address it natively.",
      heads: ["Capability", "TAUSIK", "Aider", "Cursor Rules", "Continue", "Claude Skills"],
      rows: [
        ["Enforced task model (goal + AC)", "✓ QG-0 hook blocks edits", "—", "—", "—", "—"],
        ["Signed verify receipts (ed25519)", "✓ tausik-signed/v1", "—", "—", "—", "—"],
        ["Verify cache decoupled from close", "✓ 10-min TTL", "—", "—", "—", "—"],
        ["Tracked decisions / dead-ends", "✓ SQLite + FTS5", "—", "—", "—", "—"],
        ["Cross-project memory (opt-in)", "✓ Notion-backed brain", "—", "—", "—", "—"],
        ["Stack-aware verify suites", `✓ ${STACKS} stacks`, "single-language", "—", "—", "—"],
        ["Multi-IDE same surface", "✓ MCP + skills", "CLI only", "Cursor only", "Continue only", "Claude only"],
        ["Editor-agnostic install", "✓ Python script", "✓", "—", "—", "—"],
      ],
    },
    faq: {
      eyebrow: "Answers",
      title: "Common questions.",
      items: [
        [
          "Do I need an extra API key on top of my AI IDE?",
          "No. TAUSIK never calls any LLM directly. The agent (Claude Code / Cursor / Qwen / Windsurf) uses the API key you already configured for that IDE.",
        ],
        [
          "Does it phone home?",
          "No. Everything is local: SQLite under .tausik/, hooks under .claude/. The optional Shared Brain only writes to your own Notion workspace if you wire it up.",
        ],
        [
          "Can my team share decisions and patterns?",
          "Yes, via the optional Shared Brain. Per-project hashes keep names private; the cross-project content goes through a scrubbing linter before it lands in Notion.",
        ],
        [
          "Does it work on Windows?",
          "Yes. The CLI ships .tausik/tausik.cmd for PowerShell/cmd. A few hooks (pre-commit shell, push gate) prefer Git Bash or WSL; the rest of the pipeline runs natively.",
        ],
        [
          "What about my existing AGENTS.md / CLAUDE.md?",
          "TAUSIK manages a small dynamic block inside CLAUDE.md (session + counts). Your existing instructions in CLAUDE.md or AGENTS.md stay intact; TAUSIK reads them, doesn't overwrite them.",
        ],
      ],
    },
    senar: {
      eyebrow: "Foundation",
      title: "Built on SENAR.",
      bodyHtml:
        'TAUSIK implements <b>SENAR</b> — an open engineering standard for AI-assisted development. Quality gates, session management, metrics, verification checklists — all defined in SENAR. See <a href="https://senar.tech">senar.tech</a> for the spec.',
    },
    footer: {
      tagline: "AI development framework with enforced quality gates for coding agents.",
      cols: [
        { h: "Source", links: [["github.com/Kibertum/tausik-core", "https://github.com/Kibertum/tausik-core"]] },
        { h: "Spec", links: [["senar.tech", "https://senar.tech"], ["Documentation", "/docs/quickstart"]] },
        { h: "License", text: ["Apache 2.0", "Free & open source"] },
      ],
      copyright: "© 2026 · tausik.tech",
      pill: `v${VERSION} — near-stable pre-2.0`,
    },
  },
  ru: {
    eyebrow: "Discipline-слой для AI-кодинг-агентов",
    nav: {
      brand: "TAUSIK",
      items: [
        ["Чеки", "#receipts"],
        ["Цикл", "#lifecycle"],
        ["Возможности", "#what-you-get"],
        ["Сравнение", "#compare"],
        ["Быстрый старт", "#quick-start"],
      ],
      cta: "Начать",
    },
    hero: {
      titleA: "AI-агенты, которые",
      titleB: "не врут «готово»",
      lede:
        "Локальный Python-фреймворк, который перехватывает Claude Code, Cursor, Qwen и Windsurf в двух точках, где AI-агенты врут чаще всего: старт задачи без цели и заявление «готово» без доказательств. Три сообщения покрывают весь цикл.",
      ctaPrimary: "Начать",
      ctaSecondary: "Открыть GitHub",
      badges: ["ed25519 подписанные чеки", "Apache 2.0", "Python 3.11+", `${TESTS.toLocaleString("ru-RU").replace(",", " ")} тестов проходит`, "0 core-зависимостей"],
      termTitle: "~/your-project — claude code",
      annos: [
        { k: "/start", v: "открывает сессию, перезагружает контекст" },
        { k: "/task", v: `создаёт AC · запускает тесты · ${REVIEW_AGENTS}-агентное ревью` },
        { k: "/ship", v: "verify → подписывает чек → коммит → спрашивает перед push" },
      ],
    },
    compare: {
      eyebrow: "Проблема · Механизм",
      title: "Без TAUSIK",
      titleSep: " vs ",
      titleAlt: "С TAUSIK",
      sub: "Принуждение, а не подсказка. Агент физически не может пропустить шаг — хук блокирует Write/Edit до того, как tool call долетит до runtime.",
      headL: "Без TAUSIK",
      headR: "С TAUSIK",
      rows: [
        [
          'Агент говорит "сейчас быстро отрефакторю" и правит 30 файлов.',
          'task_gate.py хук возвращает: BLOCKED — нет активной задачи (SENAR Rule 9.1).',
          "QG-0",
        ],
        [
          'Агент рапортует "Готово, всё зелёное" — без запуска тестов.',
          'task_done_verify блокирует закрытие: у AC #2 нет evidence-строки в verification_runs.',
          "QG-2",
        ],
        [
          "Новая сессия стартует чистой. Агент задаёт те же вопросы заново.",
          "SessionStart хук инжектит handoff + memory tail. Последнее решение и dead-end грузятся вместе с CLAUDE.md.",
          "",
        ],
        [
          "Через два дня агент пытается тот же неработающий подход.",
          "tausik dead-end сохраняет провальные подходы. Search всплывает их до того, как агент сожжёт ещё токены.",
          "",
        ],
        [
          'Агент гоняет "очевидные тесты" — обычно никаких.',
          `tausik verify запускает матрицу из ${STACKS} стеков (pytest, ruff, tsc, eslint, cargo, go vet, hadolint…) и кэширует результат.`,
          "",
        ],
        [
          'Спрашиваешь "что изменилось?" — читаешь 200 строк чата.',
          "tausik metrics печатает throughput, defect rate, lead time, cost-per-task. Каждый gate-exit лежит в events.",
          "",
        ],
      ],
    },
    receipts: {
      eyebrow: "Проверяемое доверие · differentiator",
      title: "Когда агент говорит «зелёно» —",
      titleAccent: "ты получаешь чек.",
      sub: "Именно это отличает TAUSIK от любого prompt-based свода правил. «Зелёно» — не утверждение на веру, а ed25519-подписанный чек, привязанный к конкретному гейту и HEAD-коммиту. Нельзя подделать, нельзя переиграть, проверяется офлайн.",
      points: [
        ["tausik verify выдаёт подписанный чек", "Формат tausik-signed/v1, ed25519, привязан к сигнатуре гейта и sha HEAD-коммита."],
        ["task done проверяет его перед закрытием", "«Зелёно», которого на самом деле не было — или было для другого коммита — валит QG-2."],
        ["Чеки переносимы", "Экспортируй один и проверь офлайн: без SDK, через stateless HTTP-эндпоинт или no-SDK пример."],
        ["Релизы тоже подписаны", "Установка скиллов и стеков проверяет подпись до записи единого байта на диск."],
      ],
      kicker: "Когда агент говорит, что билд зелёный, тебе не нужно верить. У тебя есть чек, который это доказывает — или доказывает, что агент соврал.",
      cta: "Как работают подписанные чеки",
      ctaHref: "/ru/docs/receipts",
      termTitle: "tausik verify → чек",
    },
    cycle: {
      eyebrow: "Жизненный цикл задачи",
      title: "Три сообщения. Полный цикл.",
      sub: "Ты описываешь что хочешь. Фреймворк принуждает к шагам, которые ты пропускаешь, когда слишком доверяешь агенту.",
      steps: [
        {
          n: "01",
          label: "старт сессии",
          msg: "сообщение 1 из 3",
          caption: "Открывает сессию, грузит handoff с прошлой, обновляет memory-tail в CLAUDE.md.",
        },
        {
          n: "02",
          label: "жизненный цикл задачи",
          msg: "сообщение 2 из 3",
          caption: `Опрашивает тебя про edge cases, создаёт задачу с acceptance criteria, пишет код, гоняет тесты + линтеры + ${REVIEW_AGENTS} review-агентов параллельно, проверяет evidence в БД для каждого AC.`,
        },
        {
          n: "03",
          label: "релиз",
          msg: "сообщение 3 из 3",
          caption: "Запускает tausik verify (кэш 10 мин), проходит QG-2, коммитит, спрашивает перед push.",
        },
      ],
      footer: "Вот и всё. Ты описываешь что хочешь. Фреймворк принуждает к шагам, которые ты пропускаешь, когда слишком доверяешь агенту.",
    },
    features: {
      eyebrow: "Что внутри",
      title: "Шесть вещей, ни одна не опциональная.",
      sub: "Фреймворк маленький намеренно. Каждый кусок принуждает к одному конкретному поведению.",
      items: [
        ["Quality gates", "QG-0 блокирует task start без цели и AC. QG-2 блокирует task done без verify-evidence."],
        ["Память проекта", "SQLite + FTS5 для паттернов, gotchas, решений, тупиков. Перезагружается в начале сессии."],
        ["Verify-First", "Тяжёлые тесты на отдельном verify-шаге, кэшируются 10 минут; закрытие задачи — миллисекунды."],
        [`${HOOKS} real-time хуков`, "Task-гейт, bash-firewall, push-гейт, авто-формат, memory-аудиты — блокируют плохие действия до того, как они случатся."],
        [`${MCP_TOOLS} MCP-инструментов`, "Полный программный доступ к БД проекта. Одинаково работает в Claude Code, Cursor, Qwen Code, Windsurf."],
        ["Cross-project brain", "Зеркалирование решений, паттернов, gotchas в Notion с приватными project-хешами.", "опционально"],
      ],
    },
    quickstart: {
      eyebrow: "Быстрый старт — 10 минут (после установки AI IDE)",
      title: "Четыре команды, потом перезапусти IDE.",
      sub: "Bootstrap сам определяет твой стек (Python, TS, Rust, Go) и включает подходящие quality gates.",
      copyBtn: "копировать",
      copiedBtn: "скопировано",
      note: "Перезапусти IDE — готово. Bootstrap сам определяет стек и включает подходящие гейты.",
      notes: [
        "Submodule пинит версию фреймворка для проекта. Обновление — одной git-командой.",
        "Хуки автоматически регистрируются в Claude Code и Qwen Code. Cursor + Windsurf подключаются через MCP.",
        "Локальная SQLite БД лежит в .tausik/. Никогда не коммитится. Зеркалится в Notion только если ты сам подключишь.",
        "Первое «start working» создаёт сессию #1 и пишет начальный CLAUDE.md tail.",
        "Windows: обёртка .tausik/tausik только под bash; из PowerShell/cmd.exe используй .tausik/tausik.cmd.",
      ],
      fullLink: "Полный быстрый старт",
      fullHref: "/ru/docs/quickstart",
    },
    stats: {
      eyebrow: "Dogfooding",
      title: "TAUSIK построил TAUSIK.",
      sub: "Каждая фича, каждый рефакторинг, каждый багфикс прошли через те же gates, которые поставляются с фреймворком. Числа ниже — состояние самого dogfood-проекта.",
      items: [
        ["800+", "задач закрыто — каждая с целью + AC"],
        ["0", "задач закрыто без verify-evidence", true],
        [`${TESTS.toLocaleString("ru-RU").replace(",", " ")}`, "тестов проходит"],
        ["0", "core-зависимостей / phone-home вызовов"],
      ],
      foot: `Снимок на момент v${VERSION}. Живые числа — через tausik metrics.`,
    },
    ides: {
      eyebrow: "Поддерживаемые IDE и агенты",
      title: "Шесть рантаймов. Один слой принуждения.",
      items: [
        ["VS", "VSCode + Claude Extension", "Официально протестировано", true],
        ["CR", "Cursor", "Официально протестировано", true],
        ["CC", "Claude Code (CLI)", "Ожидается · частичная матрица", false],
        ["QC", "Qwen Code", "Ожидается · частичная матрица", false],
        ["WS", "Windsurf", "Ожидается · частичная матрица", false],
        ["OC", "Codex / OpenCode-style агенты", "Ожидается · ручная валидация", false],
      ],
      foot: `${MCP_TOOLS} MCP-инструментов и ${SKILLS_CORE} core-скиллов работают везде. Real-time хуки сегодня живут в Claude Code и Qwen Code; Cursor и Windsurf получают то же принуждение на переходах QG-0 и QG-2.`,
    },
    notSection: {
      eyebrow: "Ясность",
      title: "TAUSIK — это не…",
      sub: "Расставляем ожидания до установки.",
      items: [
        ["Не SaaS.", "Всё работает локально. БД задач лежит в .tausik/ рядом с твоим кодом. Никакой phone-home, телеметрии, обязательного аккаунта."],
        ["Не модель.", "TAUSIK не генерирует код. Он сторожит существующего coding-агента (Claude Code, Cursor, Qwen, Windsurf) и трекает его работу."],
        ["Не замена Cursor / Claude Code.", "Работает внутри них как MCP-инструменты, хуки и скиллы. Твой IDE-workflow сохраняется."],
        ["Не tool для онбординга джунов.", "Принуждает к практике инженеров, которые уже знают как выглядит good — он не объясняет что такое AC."],
        ["Не авто-merge.", "QG-0 и QG-2 требуют у агента доказательств; финальное push агент всё равно подтверждает у тебя."],
      ],
    },
    comparison: {
      eyebrow: "Ландшафт",
      title: "Чем TAUSIK отличается.",
      sub: "Одна строка — одна возможность. Пустая ячейка — инструмент не закрывает её нативно.",
      heads: ["Capability", "TAUSIK", "Aider", "Cursor Rules", "Continue", "Claude Skills"],
      rows: [
        ["Enforced task-модель (goal + AC)", "✓ QG-0 хук блокирует правки", "—", "—", "—", "—"],
        ["Подписанные verify-чеки (ed25519)", "✓ tausik-signed/v1", "—", "—", "—", "—"],
        ["Verify-кеш отделён от close", "✓ 10-мин TTL", "—", "—", "—", "—"],
        ["Tracked decisions / dead-ends", "✓ SQLite + FTS5", "—", "—", "—", "—"],
        ["Cross-project memory (опционально)", "✓ Notion-backed brain", "—", "—", "—", "—"],
        ["Stack-aware verify-сьюты", `✓ ${STACKS} стеков`, "single-language", "—", "—", "—"],
        ["Multi-IDE один surface", "✓ MCP + skills", "только CLI", "только Cursor", "только Continue", "только Claude"],
        ["Editor-agnostic install", "✓ Python-скрипт", "✓", "—", "—", "—"],
      ],
    },
    faq: {
      eyebrow: "Ответы",
      title: "Частые вопросы.",
      items: [
        [
          "Нужен ли отдельный API-ключ помимо AI-IDE?",
          "Нет. TAUSIK никогда не зовёт LLM напрямую. Агент (Claude Code / Cursor / Qwen / Windsurf) использует тот API-ключ, который ты уже настроил для своего IDE.",
        ],
        [
          "Phone home есть?",
          "Нет. Всё локально: SQLite в .tausik/, хуки в .claude/. Опциональный Shared Brain пишет только в твой Notion-workspace, если ты сам его подключишь.",
        ],
        [
          "Можно ли шарить decisions/patterns в команде?",
          "Да, через опциональный Shared Brain. Per-project хеши прячут имена; cross-project контент проходит scrubbing-линтер перед записью в Notion.",
        ],
        [
          "Windows работает?",
          "Да. CLI ставит .tausik/tausik.cmd для PowerShell/cmd. Несколько хуков (pre-commit shell, push gate) предпочитают Git Bash или WSL; остальной pipeline идёт нативно.",
        ],
        [
          "А мой текущий AGENTS.md / CLAUDE.md?",
          "TAUSIK управляет маленьким dynamic-блоком внутри CLAUDE.md (сессия + счётчики). Твои инструкции в CLAUDE.md или AGENTS.md остаются нетронутыми — TAUSIK их читает, но не перезаписывает.",
        ],
      ],
    },
    senar: {
      eyebrow: "Фундамент",
      title: "Построено на SENAR.",
      bodyHtml:
        'TAUSIK реализует <b>SENAR</b> — открытый инженерный стандарт AI-assisted разработки. Quality gates, управление сессиями, метрики, чек-листы верификации — всё определено в SENAR. Спецификация: <a href="https://senar.tech">senar.tech</a>.',
    },
    footer: {
      tagline: "Фреймворк AI-разработки с принудительными quality gates для coding-агентов.",
      cols: [
        { h: "Исходники", links: [["github.com/Kibertum/tausik-core", "https://github.com/Kibertum/tausik-core"]] },
        { h: "Спецификация", links: [["senar.tech", "https://senar.tech"], ["Документация", "/ru/docs/quickstart"]] },
        { h: "Лицензия", text: ["Apache 2.0", "Свободный & open source"] },
      ],
      copyright: "© 2026 · tausik.tech",
      pill: `v${VERSION} — near-stable pre-2.0`,
    },
  },
};

const t = computed(() => copy[props.lang]);

function copyInstall(e: MouseEvent) {
  const btn = e.currentTarget as HTMLButtonElement;
  const pre = btn.closest(".codeblock")?.querySelector("pre");
  if (!pre) return;
  const text = (pre.textContent || "").replace(/^\$\s?/gm, "").trim();
  if (!navigator.clipboard) return;
  navigator.clipboard.writeText(text).then(() => {
    const old = btn.textContent;
    btn.textContent = t.value.quickstart.copiedBtn;
    setTimeout(() => {
      btn.textContent = old;
    }, 1400);
  });
}
</script>

<template>
  <div class="landing-root">
    <a id="top"></a>

    <!-- STICKY SECTION NAV -->
    <nav class="section-nav" aria-label="Sections">
      <div class="wrap section-nav-inner">
        <a class="sn-brand" href="#top">
          <span class="sn-mark"></span>{{ t.nav.brand }}
        </a>
        <div class="sn-links">
          <a v-for="(it, i) in t.nav.items" :key="i" :href="it[1]">{{ it[0] }}</a>
        </div>
        <a class="sn-cta" href="#quick-start">{{ t.nav.cta }} <span class="arrow">→</span></a>
      </div>
    </nav>

    <!-- HERO -->
    <section class="hero">
      <div class="hero-grid-bg"></div>
      <div class="wrap">
        <div class="hero-grid">
          <div>
            <p class="eyebrow">{{ t.eyebrow }}</p>
            <h1>
              {{ t.hero.titleA }}<br />{{ t.hero.titleB }}<span class="accent">.</span>
            </h1>
            <p class="lede">{{ t.hero.lede }}</p>
            <div class="cta-row">
              <a class="btn btn-primary" href="#quick-start">
                {{ t.hero.ctaPrimary }} <span class="arrow">→</span>
              </a>
              <a class="btn btn-secondary" href="https://github.com/Kibertum/tausik-core">
                {{ t.hero.ctaSecondary }}
              </a>
            </div>
            <div class="badges">
              <template v-for="(b, i) in t.hero.badges" :key="i">
                <span class="b" :class="{ ok: i === 2 }">{{ b }}</span>
                <span v-if="i < t.hero.badges.length - 1" class="sep">·</span>
              </template>
            </div>
          </div>

          <div class="hero-term-wrap">
            <div class="term">
              <div class="term-head">
                <span class="dots"><i></i><i></i><i></i></span>
                <span class="term-title">{{ t.hero.termTitle }}</span>
              </div>
              <div class="term-body">
                <span class="line"><span class="muted">agent ›</span> <span class="prompt">Edit("src/auth.py", "...")</span></span>
                <span class="line"><span class="dim">tausik ›</span> <span class="bad">BLOCKED</span> — no active task (SENAR Rule 9.1)</span>
                <span class="line">&nbsp;</span>
                <span class="line"><span class="muted">you ›</span> <span class="prompt">start working</span></span>
                <span class="line"><span class="dim">tausik ›</span> session <span class="num">#74</span> opened · handoff loaded · memory tail refreshed</span>
                <span class="line">&nbsp;</span>
                <span class="line"><span class="muted">you ›</span> <span class="prompt">fix the mobile button bug</span></span>
                <span class="line"><span class="dim">tausik ›</span> 4 edge cases collected → task <span class="num">T-219</span> · <span class="num">3</span> AC drafted</span>
                <span class="line">        <span class="kw">QG-0</span> <span class="ok">passed</span> · goal + AC locked</span>
                <span class="line">        pytest · ruff · tsc · <span class="num">6</span> review agents · cached</span>
                <span class="line">        <span class="kw">QG-2</span> <span class="ok">passed</span> · every AC has evidence</span>
                <span class="line">&nbsp;</span>
                <span class="line"><span class="muted">you ›</span> <span class="prompt">ship it</span></span>
                <span class="line"><span class="dim">tausik ›</span> tausik verify · cached <span class="num">10</span>m · committed <span class="kw">a91f3e2</span></span>
                <span class="line">        push? <span class="ok">[y/N]</span> _</span>
              </div>
            </div>
            <div class="annos" aria-hidden="true">
              <div v-for="(a, i) in t.hero.annos" :key="i" class="anno">
                <span class="tick">/</span>
                <span><b style="color: var(--lt-fg)">{{ a.k }}</b> &nbsp; {{ a.v }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- COMPARE -->
    <section id="compare">
      <div class="wrap">
        <p class="eyebrow">{{ t.compare.eyebrow }}</p>
        <h2>
          {{ t.compare.title }}<span style="color: var(--lt-fg-3); font-weight: 500">{{ t.compare.titleSep }}</span>{{ t.compare.titleAlt }}
        </h2>
        <p class="section-sub">{{ t.compare.sub }}</p>

        <div class="compare">
          <div class="compare-head">
            <div>{{ t.compare.headL }}</div>
            <div class="col-r">{{ t.compare.headR }}</div>
          </div>
          <div v-for="(row, i) in t.compare.rows" :key="i" class="compare-row">
            <div class="col-l"><span class="icon icon-x"></span>{{ row[0] }}</div>
            <div class="col-r">
              <span class="icon icon-check"></span>
              <span>{{ row[1] }}<span v-if="row[2]" class="qg-tag">{{ row[2] }}</span></span>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- RECEIPTS — the differentiator -->
    <section id="receipts" class="receipts-section">
      <div class="wrap">
        <p class="eyebrow">{{ t.receipts.eyebrow }}</p>
        <h2>{{ t.receipts.title }}<br /><span class="accent-fg">{{ t.receipts.titleAccent }}</span></h2>
        <p class="section-sub">{{ t.receipts.sub }}</p>

        <div class="receipts-grid">
          <div class="receipts-points">
            <div v-for="(p, i) in t.receipts.points" :key="i" class="rcp">
              <span class="rcp-seal" aria-hidden="true">
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                  <path d="M8 1.5l5 2v3.2c0 3-2 5.4-5 6.6-3-1.2-5-3.6-5-6.6V3.5l5-2z" stroke="currentColor" stroke-width="1.2" stroke-linejoin="round" />
                  <path d="M5.6 8.1L7.2 9.7L10.5 6.2" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round" />
                </svg>
              </span>
              <div>
                <h3>{{ p[0] }}</h3>
                <p>{{ p[1] }}</p>
              </div>
            </div>
          </div>

          <div class="receipts-aside">
            <div class="term">
              <div class="term-head">
                <span class="dots"><i></i><i></i><i></i></span>
                <span class="term-title">{{ t.receipts.termTitle }}</span>
              </div>
              <div class="term-body">
                <span class="line"><span class="muted">you ›</span> <span class="prompt">tausik verify --task T-219</span></span>
                <span class="line">&nbsp;</span>
                <span class="line"><span class="dim">tausik ›</span> pytest · ruff · tsc <span class="ok">passed</span></span>
                <span class="line">        receipt <span class="kw">tausik-signed/v1</span></span>
                <span class="line">        alg   <span class="num">ed25519</span></span>
                <span class="line">        gate  <span class="kw">a1b2c3…</span> · head <span class="kw">a91f3e2</span></span>
                <span class="line">        sig   <span class="num">3045022100…</span> <span class="ok">✓ valid</span></span>
                <span class="line">&nbsp;</span>
                <span class="line"><span class="dim">tausik ›</span> task done · <span class="kw">QG-2</span> reads receipt <span class="ok">✓</span></span>
              </div>
            </div>
            <a class="receipts-link" :href="t.receipts.ctaHref">{{ t.receipts.cta }} <span>→</span></a>
          </div>
        </div>

        <p class="receipts-kicker"><em>{{ t.receipts.kicker }}</em></p>
      </div>
    </section>

    <!-- THREE MESSAGES -->
    <section id="lifecycle">
      <div class="wrap">
        <p class="eyebrow">{{ t.cycle.eyebrow }}</p>
        <h2>{{ t.cycle.title }}</h2>
        <p class="section-sub">{{ t.cycle.sub }}</p>

        <div class="cycle">
          <div v-for="(s, i) in t.cycle.steps" :key="i">
            <div class="step-num"><b>{{ s.n }}</b> <span>{{ s.label }}</span><span class="bar"></span></div>
            <div class="term">
              <div class="term-head">
                <span class="dots"><i></i><i></i><i></i></span>
                <span class="term-title">{{ s.msg }}</span>
              </div>
              <div v-if="i === 0" class="term-body">
                <span class="line"><span class="muted">you ›</span> <span class="prompt">start working</span></span>
                <span class="line">&nbsp;</span>
                <span class="line"><span class="dim">tausik ›</span> session <span class="num">#74</span> opened</span>
                <span class="line">        handoff: <span class="kw">fix(auth): retry on 401</span></span>
                <span class="line">        memory tail: <span class="num">14</span> patterns · <span class="num">3</span> gotchas</span>
                <span class="line">        CLAUDE.md refreshed</span>
                <span class="line">        last commit: <span class="kw">a14c2bf</span> · <span class="num">2</span>h ago</span>
                <span class="line">&nbsp;</span>
                <span class="line"><span class="ok">ready.</span></span>
              </div>
              <div v-else-if="i === 1" class="term-body">
                <span class="line"><span class="muted">you ›</span> <span class="prompt">fix the bug — button</span></span>
                <span class="line"><span class="muted">    ›</span> <span class="prompt">doesn't work on mobile</span></span>
                <span class="line">&nbsp;</span>
                <span class="line"><span class="dim">tausik ›</span> interviewing on edge cases…</span>
                <span class="line">        <span class="num">4</span> edge cases collected</span>
                <span class="line">        task <span class="num">T-219</span> · <span class="num">3</span> AC drafted</span>
                <span class="line">        <span class="kw">QG-0</span> <span class="ok">passed</span></span>
                <span class="line">        writing code → pytest · ruff · tsc</span>
                <span class="line">        <span class="num">5</span> review agents · parallel</span>
                <span class="line">        AC evidence: <span class="ok">3 / 3</span></span>
                <span class="line">        <span class="kw">QG-2</span> <span class="ok">passed</span></span>
              </div>
              <div v-else class="term-body">
                <span class="line"><span class="muted">you ›</span> <span class="prompt">ship it</span></span>
                <span class="line">&nbsp;</span>
                <span class="line"><span class="dim">tausik ›</span> $ tausik verify</span>
                <span class="line">        cache hit · <span class="num">10</span>m TTL</span>
                <span class="line">        <span class="kw">QG-2</span> <span class="ok">passed</span></span>
                <span class="line">        staging <span class="num">7</span> files</span>
                <span class="line">        commit <span class="kw">a91f3e2</span> <span class="muted">"fix(ui): mobile button"</span></span>
                <span class="line">&nbsp;</span>
                <span class="line">        push to <span class="kw">origin/main</span>?</span>
                <span class="line">        <span class="ok">[y/N]</span> _</span>
              </div>
            </div>
            <p class="step-caption">{{ s.caption }}</p>
          </div>
        </div>

        <p class="cycle-footer"><em>{{ t.cycle.footer }}</em></p>
      </div>
    </section>

    <!-- FEATURES -->
    <section id="what-you-get">
      <div class="wrap">
        <p class="eyebrow">{{ t.features.eyebrow }}</p>
        <h2>{{ t.features.title }}</h2>
        <p class="section-sub">{{ t.features.sub }}</p>

        <div class="features">
          <div v-for="(f, i) in t.features.items" :key="i" class="feat">
            <span class="ico">
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <rect x="2.5" y="2.5" width="11" height="11" rx="2" stroke="currentColor" stroke-width="1.2" />
                <path d="M5.5 8L7.2 9.7L10.5 6.5" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round" />
              </svg>
            </span>
            <h3>{{ f[0] }}<span v-if="f[2]" class="optional">{{ f[2] }}</span></h3>
            <p>{{ f[1] }}</p>
          </div>
        </div>
      </div>
    </section>

    <!-- QUICK START -->
    <section id="quick-start">
      <div class="wrap">
        <p class="eyebrow">{{ t.quickstart.eyebrow }}</p>
        <h2>{{ t.quickstart.title }}</h2>
        <p class="section-sub">{{ t.quickstart.sub }}</p>

        <div class="qs">
          <div>
            <div class="codeblock">
              <div class="codeblock-head">
                <span class="label">bash</span>
                <button class="copy" type="button" @click="copyInstall">{{ t.quickstart.copyBtn }}</button>
              </div>
              <pre><code><span class="c"># 1 · go to your project</span>
<span class="p">$</span> cd your-project

<span class="c"># 2 · add tausik-core as a submodule</span>
<span class="p">$</span> git submodule add https://github.com/Kibertum/tausik-core .tausik-lib

<span class="c"># 3 · bootstrap (detects stack, wires hooks)</span>
<span class="p">$</span> python .tausik-lib/bootstrap/bootstrap.py --init

<span class="c"># 4 · ignore local state</span>
<span class="p">$</span> echo ".tausik/" &gt;&gt; .gitignore</code></pre>
            </div>
            <p class="note"><em>{{ t.quickstart.note }}</em></p>
          </div>

          <aside class="qs-side">
            <ul>
              <li v-for="(n, i) in t.quickstart.notes" :key="i">
                <span class="n">{{ String(i + 1).padStart(2, "0") }}</span>
                <span>{{ n }}</span>
              </li>
            </ul>
            <a class="link" :href="t.quickstart.fullHref">{{ t.quickstart.fullLink }} <span>→</span></a>
          </aside>
        </div>
      </div>
    </section>

    <!-- STATS -->
    <section>
      <div class="wrap">
        <p class="eyebrow">{{ t.stats.eyebrow }}</p>
        <h2>{{ t.stats.title }}</h2>
        <p class="section-sub">{{ t.stats.sub }}</p>

        <div class="stats">
          <div v-for="(s, i) in t.stats.items" :key="i" class="stat">
            <div class="num"><span :class="{ accent: s[2] }">{{ s[0] }}</span></div>
            <div class="lbl">{{ s[1] }}</div>
          </div>
        </div>
        <p class="stats-foot">{{ t.stats.foot }}</p>
      </div>
    </section>

    <!-- IDES -->
    <section>
      <div class="wrap">
        <p class="eyebrow">{{ t.ides.eyebrow }}</p>
        <h2>{{ t.ides.title }}</h2>

        <div class="ides">
          <div v-for="(it, i) in t.ides.items" :key="i" class="ide" :class="{ tested: it[3] }">
            <div class="logo">{{ it[0] }}</div>
            <div>
              <div class="name">{{ it[1] }}</div>
              <div class="status">{{ it[2] }}</div>
            </div>
          </div>
        </div>
        <p class="ides-foot">{{ t.ides.foot }}</p>
      </div>
    </section>

    <!-- NOT-SECTION -->
    <section>
      <div class="wrap">
        <p class="eyebrow">{{ t.notSection.eyebrow }}</p>
        <h2>{{ t.notSection.title }}</h2>
        <p class="section-sub">{{ t.notSection.sub }}</p>

        <div class="not-grid">
          <div v-for="(it, i) in t.notSection.items" :key="i" class="not-card">
            <div class="not-head">{{ it[0] }}</div>
            <div class="not-body">{{ it[1] }}</div>
          </div>
        </div>
      </div>
    </section>

    <!-- COMPARISON -->
    <section>
      <div class="wrap">
        <p class="eyebrow">{{ t.comparison.eyebrow }}</p>
        <h2>{{ t.comparison.title }}</h2>
        <p class="section-sub">{{ t.comparison.sub }}</p>

        <div class="comp-table-wrap">
          <table class="comp-table">
            <thead>
              <tr>
                <th v-for="(h, i) in t.comparison.heads" :key="i" :class="{ ours: i === 1 }">{{ h }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, i) in t.comparison.rows" :key="i">
                <td v-for="(cell, j) in row" :key="j" :class="{ feat: j === 0, ours: j === 1 }">{{ cell }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <!-- FAQ -->
    <section>
      <div class="wrap">
        <p class="eyebrow">{{ t.faq.eyebrow }}</p>
        <h2>{{ t.faq.title }}</h2>

        <div class="faq-grid">
          <details v-for="(it, i) in t.faq.items" :key="i" class="faq-item">
            <summary>{{ it[0] }}</summary>
            <p>{{ it[1] }}</p>
          </details>
        </div>
      </div>
    </section>

    <!-- SENAR -->
    <section>
      <div class="wrap">
        <p class="eyebrow">{{ t.senar.eyebrow }}</p>
        <h2>{{ t.senar.title }}</h2>

        <div class="senar">
          <div class="senar-mark">SENAR</div>
          <p v-html="t.senar.bodyHtml"></p>
        </div>
      </div>
    </section>

    <!-- FOOTER -->
    <footer class="lt-footer">
      <div class="wrap">
        <div class="foot-grid">
          <div class="foot-col">
            <p class="brand-line">
              <span class="brand-mark"></span>
              <b>TAUSIK</b>
              <span class="ver">v{{ VERSION }}</span>
            </p>
            <p class="lic">{{ t.footer.tagline }}</p>
          </div>
          <div v-for="(col, i) in t.footer.cols" :key="i" class="foot-col">
            <h4>{{ col.h }}</h4>
            <template v-if="col.links">
              <a v-for="(l, li) in col.links" :key="li" :href="l[1]">{{ l[0] }}</a>
            </template>
            <template v-else-if="col.text">
              <p v-for="(p, pi) in col.text" :key="pi" class="lic">{{ p }}</p>
            </template>
          </div>
        </div>
        <div class="foot-bottom">
          <span>{{ t.footer.copyright }}</span>
          <span class="pill">{{ t.footer.pill }}</span>
        </div>
      </div>
    </footer>
  </div>
</template>

<style scoped>
.landing-root {
  --lt-bg: #0a0a0a;
  --lt-bg-1: #0e0e0e;
  --lt-bg-2: #131313;
  --lt-bg-3: #181818;
  --lt-line: #1f1f1f;
  --lt-line-2: #2a2a2a;
  --lt-fg: #fafafa;
  --lt-fg-1: #d6d6d6;
  --lt-fg-2: #9a9a9a;
  --lt-fg-3: #6b6b6b;
  --lt-fg-4: #4a4a4a;
  --lt-accent: #5e6ad2;
  --lt-accent-2: #7c86e0;
  --lt-accent-3: #3c46a2;
  --lt-good: #4ccb8e;
  --lt-warn: #e8b964;
  --lt-bad: #e26b6b;
  --lt-mono: ui-monospace, "SF Mono", SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
  --lt-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Liberation Sans", sans-serif;
  --lt-maxw: 1180px;
  --lt-pad-x: clamp(20px, 4vw, 56px);

  background: var(--lt-bg);
  color: var(--lt-fg-1);
  font-family: var(--lt-sans);
  font-size: 16px;
  line-height: 1.55;
  -webkit-font-smoothing: antialiased;
  text-rendering: optimizeLegibility;
}
.landing-root :deep(a) {
  color: inherit;
  text-decoration: none;
}
.landing-root :deep(::selection) {
  background: var(--lt-accent);
  color: #fff;
}
.landing-root h1,
.landing-root h2,
.landing-root h3,
.landing-root h4 {
  color: var(--lt-fg);
  font-weight: 600;
  letter-spacing: -0.02em;
  margin: 0;
}
.landing-root code,
.landing-root pre,
.landing-root kbd {
  font-family: var(--lt-mono);
}
.landing-root code {
  font-size: 0.92em;
  background: transparent;
  border: 0;
  padding: 0;
  color: inherit;
}

.wrap {
  max-width: var(--lt-maxw);
  margin: 0 auto;
  padding: 0 var(--lt-pad-x);
}
section {
  padding: clamp(72px, 10vw, 128px) 0;
  border-top: 1px solid var(--lt-line);
  position: relative;
}
section:first-of-type {
  border-top: 0;
}
.eyebrow {
  font-family: var(--lt-mono);
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--lt-fg-3);
  margin: 0 0 18px;
  display: inline-flex;
  align-items: center;
  gap: 10px;
}
.eyebrow::before {
  content: "";
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--lt-accent);
  box-shadow: 0 0 12px rgba(94, 106, 210, 0.7);
}
h2 {
  font-size: clamp(28px, 3.6vw, 44px);
  line-height: 1.1;
  margin-bottom: 14px;
  text-wrap: balance;
}
.section-sub {
  color: var(--lt-fg-2);
  font-size: clamp(15px, 1.4vw, 17px);
  max-width: 62ch;
  margin: 0 0 56px;
  text-wrap: pretty;
}

/* HERO */
.hero {
  padding-top: clamp(40px, 7vw, 96px);
  padding-bottom: clamp(80px, 11vw, 140px);
  border-top: 0;
}
.hero-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.05fr) minmax(0, 1fr);
  gap: clamp(32px, 5vw, 72px);
  align-items: center;
}
@media (max-width: 920px) {
  .hero-grid {
    grid-template-columns: 1fr;
    gap: 48px;
  }
}
.hero h1 {
  font-size: clamp(40px, 6.6vw, 80px);
  line-height: 0.98;
  letter-spacing: -0.035em;
  font-weight: 600;
  color: var(--lt-fg);
  margin: 0 0 22px;
}
.hero h1 .accent {
  color: var(--lt-accent);
}
.hero p.lede {
  font-size: clamp(16px, 1.6vw, 19px);
  color: var(--lt-fg-2);
  margin: 0 0 36px;
  max-width: 38ch;
  text-wrap: pretty;
  line-height: 1.5;
}
.hero .cta-row {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 28px;
}
.btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 11px 16px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  border: 1px solid transparent;
  transition: background 0.15s ease, border-color 0.15s ease, transform 0.15s ease;
  cursor: pointer;
}
.btn-primary {
  background: var(--lt-accent);
  color: #fff;
}
.btn-primary:hover {
  background: var(--lt-accent-2);
}
.btn-secondary {
  background: transparent;
  color: var(--lt-fg);
  border-color: var(--lt-line-2);
}
.btn-secondary:hover {
  border-color: var(--lt-fg-3);
  background: var(--lt-bg-2);
}
.btn .arrow {
  transition: transform 0.15s ease;
}
.btn:hover .arrow {
  transform: translateX(2px);
}
.badges {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 0;
  align-items: center;
  font-family: var(--lt-mono);
  font-size: 12px;
  color: var(--lt-fg-3);
}
.badges .sep {
  color: var(--lt-fg-4);
  margin: 0 10px;
}
.badges .b {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  white-space: nowrap;
}
.badges .b::before {
  content: "";
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: var(--lt-fg-4);
}
.badges .b.ok::before {
  background: var(--lt-good);
}

/* TERMINAL */
.term {
  background: var(--lt-bg-1);
  border: 1px solid var(--lt-line);
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 1px 0 rgba(255, 255, 255, 0.03) inset, 0 30px 60px -30px rgba(0, 0, 0, 0.6);
}
.term-head {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  border-bottom: 1px solid var(--lt-line);
  background: linear-gradient(180deg, #131313 0%, #101010 100%);
}
.dots {
  display: inline-flex;
  gap: 6px;
}
.dots i {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--lt-line-2);
  display: block;
}
.term-title {
  font-family: var(--lt-mono);
  font-size: 12px;
  color: var(--lt-fg-3);
  margin-left: 6px;
}
.term-body {
  padding: 18px 20px;
  font-family: var(--lt-mono);
  font-size: 13px;
  line-height: 1.7;
  color: var(--lt-fg-1);
  overflow-x: auto;
}
.term-body .line {
  display: block;
  white-space: pre;
}
.prompt {
  color: var(--lt-accent);
}
.muted {
  color: var(--lt-fg-3);
}
.dim {
  color: var(--lt-fg-4);
}
.ok {
  color: var(--lt-good);
}
.bad {
  color: var(--lt-bad);
  font-weight: 600;
}
.kw {
  color: #c0c8ff;
}
.num {
  color: #e0c088;
}

.hero-term-wrap {
  position: relative;
}
.annos {
  position: relative;
  margin-top: 14px;
  display: grid;
  gap: 8px;
}
.anno {
  display: grid;
  grid-template-columns: 18px 1fr;
  gap: 10px;
  font-family: var(--lt-mono);
  font-size: 12px;
  color: var(--lt-fg-2);
}
.anno .tick {
  color: var(--lt-accent);
  font-weight: 600;
  text-align: right;
  line-height: 1.6;
}

/* COMPARE */
.compare {
  border: 1px solid var(--lt-line);
  border-radius: 12px;
  overflow: hidden;
  background: var(--lt-bg-1);
}
.compare-head,
.compare-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
}
.compare-head > div {
  padding: 14px 22px;
  font-family: var(--lt-mono);
  font-size: 11px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--lt-fg-3);
  background: var(--lt-bg-2);
  border-bottom: 1px solid var(--lt-line);
}
.compare-head .col-r {
  color: var(--lt-accent-2);
}
.compare-row > div {
  padding: 18px 22px;
  border-bottom: 1px solid var(--lt-line);
  font-size: 15px;
  color: var(--lt-fg-1);
  display: flex;
  gap: 12px;
  align-items: flex-start;
}
.compare-row:last-child > div {
  border-bottom: 0;
}
.compare-row .col-l {
  color: var(--lt-fg-2);
  border-right: 1px solid var(--lt-line);
}
.compare-row .col-r {
  color: var(--lt-fg);
}
.icon-x,
.icon-check {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  display: inline-block;
  position: relative;
  flex: 0 0 16px;
  margin-top: 4px;
}
.icon-x {
  background: rgba(226, 107, 107, 0.12);
}
.icon-x::before,
.icon-x::after {
  content: "";
  position: absolute;
  left: 4px;
  top: 7.5px;
  width: 8px;
  height: 1.5px;
  background: var(--lt-bad);
}
.icon-x::before {
  transform: rotate(45deg);
}
.icon-x::after {
  transform: rotate(-45deg);
}
.icon-check {
  background: rgba(94, 106, 210, 0.15);
}
.icon-check::after {
  content: "";
  position: absolute;
  left: 4px;
  top: 4px;
  width: 5px;
  height: 8px;
  border: solid var(--lt-accent-2);
  border-width: 0 1.5px 1.5px 0;
  transform: rotate(45deg);
}
.qg-tag {
  font-family: var(--lt-mono);
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 4px;
  background: rgba(94, 106, 210, 0.1);
  color: var(--lt-accent-2);
  border: 1px solid rgba(94, 106, 210, 0.25);
  margin-left: 6px;
  white-space: nowrap;
}
@media (max-width: 760px) {
  .compare-head {
    display: none;
  }
  .compare-row {
    grid-template-columns: 1fr;
  }
  .compare-row .col-l {
    border-right: 0;
    padding-bottom: 10px;
  }
  .compare-row .col-r {
    padding-top: 10px;
    background: var(--lt-bg-2);
  }
}

/* CYCLE */
.cycle {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 20px;
}
@media (max-width: 980px) {
  .cycle {
    grid-template-columns: 1fr;
  }
}
.cycle .step-num {
  font-family: var(--lt-mono);
  font-size: 12px;
  color: var(--lt-fg-3);
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 10px;
}
.cycle .step-num b {
  color: var(--lt-accent);
  font-weight: 600;
}
.cycle .step-num .bar {
  flex: 1;
  height: 1px;
  background: var(--lt-line);
}
.cycle .term-body {
  min-height: 220px;
}
.cycle .step-caption {
  font-size: 14px;
  color: var(--lt-fg-2);
  margin-top: 14px;
  line-height: 1.55;
}
.cycle-footer {
  margin-top: 40px;
  font-size: 17px;
  color: var(--lt-fg-2);
  text-align: center;
  text-wrap: balance;
}
.cycle-footer em {
  color: var(--lt-fg);
  font-style: normal;
}

/* FEATURES */
.features {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 1px;
  background: var(--lt-line);
  border: 1px solid var(--lt-line);
  border-radius: 12px;
  overflow: hidden;
}
@media (max-width: 900px) {
  .features {
    grid-template-columns: repeat(2, 1fr);
  }
}
@media (max-width: 560px) {
  .features {
    grid-template-columns: 1fr;
  }
}
.feat {
  background: var(--lt-bg-1);
  padding: 28px 26px 30px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 200px;
}
.feat .ico {
  width: 32px;
  height: 32px;
  border-radius: 7px;
  background: var(--lt-bg-3);
  border: 1px solid var(--lt-line-2);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: var(--lt-accent-2);
}
.feat h3 {
  font-size: 16px;
  color: var(--lt-fg);
  margin: 6px 0 0;
}
.feat p {
  margin: 0;
  color: var(--lt-fg-2);
  font-size: 14px;
  line-height: 1.55;
}
.feat .optional {
  font-family: var(--lt-mono);
  font-size: 11px;
  color: var(--lt-fg-3);
  margin-left: 8px;
  font-weight: 400;
}

/* QUICK START */
.qs {
  display: grid;
  grid-template-columns: 1.2fr 1fr;
  gap: clamp(28px, 4vw, 56px);
  align-items: start;
}
@media (max-width: 900px) {
  .qs {
    grid-template-columns: 1fr;
  }
}
.codeblock {
  background: var(--lt-bg-1);
  border: 1px solid var(--lt-line);
  border-radius: 12px;
  overflow: hidden;
}
.codeblock-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px 10px 16px;
  border-bottom: 1px solid var(--lt-line);
  font-family: var(--lt-mono);
  font-size: 12px;
  color: var(--lt-fg-3);
  background: var(--lt-bg-2);
}
.codeblock-head .label::before {
  content: "$";
  color: var(--lt-accent);
  margin-right: 8px;
}
.copy {
  font-family: var(--lt-mono);
  font-size: 11px;
  color: var(--lt-fg-3);
  background: transparent;
  border: 1px solid var(--lt-line-2);
  border-radius: 6px;
  padding: 4px 8px;
  cursor: pointer;
  transition: color 0.15s, border-color 0.15s;
}
.copy:hover {
  color: var(--lt-fg);
  border-color: var(--lt-fg-3);
}
.codeblock pre {
  margin: 0;
  padding: 20px 22px;
  font-family: var(--lt-mono);
  font-size: 13.5px;
  line-height: 1.75;
  color: var(--lt-fg-1);
  overflow-x: auto;
  white-space: pre;
  background: transparent;
}
.codeblock pre .p {
  color: var(--lt-accent);
  user-select: none;
}
.codeblock pre .c {
  color: var(--lt-fg-4);
}
.qs .note {
  color: var(--lt-fg-2);
  font-size: 14px;
  margin-top: 16px;
  line-height: 1.55;
}
.qs .note em {
  color: var(--lt-fg);
  font-style: normal;
}
.qs-side ul {
  list-style: none;
  padding: 0;
  margin: 0 0 24px;
  border-top: 1px solid var(--lt-line);
}
.qs-side ul li {
  display: grid;
  grid-template-columns: 28px 1fr;
  gap: 12px;
  padding: 14px 0;
  border-bottom: 1px solid var(--lt-line);
  color: var(--lt-fg-1);
  font-size: 14px;
}
.qs-side ul li .n {
  font-family: var(--lt-mono);
  color: var(--lt-accent);
  font-size: 12px;
  padding-top: 2px;
}
.qs-side .link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--lt-accent-2);
  font-size: 14px;
  border-bottom: 1px solid transparent;
}
.qs-side .link:hover {
  border-bottom-color: var(--lt-accent-2);
}

/* STATS */
.stats {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 1px;
  background: var(--lt-line);
  border: 1px solid var(--lt-line);
  border-radius: 12px;
  overflow: hidden;
}
@media (max-width: 760px) {
  .stats {
    grid-template-columns: repeat(2, 1fr);
  }
}
.stat {
  background: var(--lt-bg-1);
  padding: 32px 28px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.stat .num {
  font-family: var(--lt-mono);
  font-size: clamp(40px, 5vw, 56px);
  color: var(--lt-fg);
  letter-spacing: -0.03em;
  line-height: 1;
  font-weight: 500;
  font-variant-numeric: tabular-nums;
}
.stat .num .accent {
  color: var(--lt-accent);
}
.stat .lbl {
  font-size: 13px;
  color: var(--lt-fg-2);
  margin-top: 8px;
}
.stats-foot {
  margin-top: 28px;
  color: var(--lt-fg-2);
  text-align: center;
  font-size: 15px;
  max-width: 64ch;
  margin-left: auto;
  margin-right: auto;
}

/* IDES */
.ides {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1px;
  background: var(--lt-line);
  border: 1px solid var(--lt-line);
  border-radius: 12px;
  overflow: hidden;
}
@media (max-width: 760px) {
  .ides {
    grid-template-columns: 1fr 1fr;
  }
}
@media (max-width: 480px) {
  .ides {
    grid-template-columns: 1fr;
  }
}
.ide {
  background: var(--lt-bg-1);
  padding: 22px 22px;
  display: flex;
  align-items: center;
  gap: 14px;
}
.ide .logo {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  background: var(--lt-bg-3);
  border: 1px solid var(--lt-line-2);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: var(--lt-fg-2);
  font-family: var(--lt-mono);
  font-size: 14px;
  font-weight: 600;
  flex-shrink: 0;
}
.ide .name {
  font-size: 14px;
  color: var(--lt-fg);
  font-weight: 500;
  line-height: 1.2;
}
.ide .status {
  font-family: var(--lt-mono);
  font-size: 11px;
  color: var(--lt-fg-3);
  margin-top: 4px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.ide .status::before {
  content: "";
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--lt-fg-4);
}
.ide.tested .status::before {
  background: var(--lt-good);
}
.ide.tested .status {
  color: var(--lt-good);
}
.ides-foot {
  margin-top: 24px;
  color: var(--lt-fg-2);
  font-size: 14px;
  max-width: 80ch;
  line-height: 1.6;
}

/* SENAR */
.senar {
  border: 1px solid var(--lt-line);
  background:
    radial-gradient(800px 200px at 0% 0%, rgba(94, 106, 210, 0.07), transparent 60%),
    var(--lt-bg-1);
  border-radius: 12px;
  padding: clamp(28px, 4vw, 48px);
  display: grid;
  grid-template-columns: 120px 1fr;
  gap: 32px;
  align-items: center;
}
@media (max-width: 700px) {
  .senar {
    grid-template-columns: 1fr;
    gap: 20px;
  }
}
.senar-mark {
  width: 96px;
  height: 96px;
  border-radius: 18px;
  border: 1px solid var(--lt-line-2);
  background:
    conic-gradient(from 140deg at 50% 50%, rgba(94, 106, 210, 0.25), transparent 60%),
    var(--lt-bg-2);
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--lt-mono);
  font-size: 16px;
  letter-spacing: 0.1em;
  color: var(--lt-fg);
}
.senar p {
  margin: 0;
  font-size: 16px;
  color: var(--lt-fg-2);
  line-height: 1.65;
  max-width: 70ch;
}
.landing-root .senar p :deep(b) {
  color: var(--lt-fg);
  font-weight: 600;
}
.landing-root .senar p :deep(a) {
  color: var(--lt-accent-2);
  border-bottom: 1px solid rgba(124, 134, 224, 0.4);
}
.landing-root .senar p :deep(a:hover) {
  color: var(--lt-fg);
  border-bottom-color: var(--lt-fg);
}

.hero-grid-bg {
  position: absolute;
  inset: 0;
  pointer-events: none;
  background:
    linear-gradient(to bottom, transparent 60%, var(--lt-bg) 100%),
    radial-gradient(1000px 400px at 50% 0%, rgba(94, 106, 210, 0.08), transparent 60%);
  z-index: 0;
}
.hero > .wrap {
  position: relative;
  z-index: 1;
}

/* FOOTER */
.lt-footer {
  border-top: 1px solid var(--lt-line);
  padding: 48px 0 56px;
}
.foot-grid {
  display: grid;
  grid-template-columns: 2fr 1fr 1fr 1fr;
  gap: 32px;
}
@media (max-width: 760px) {
  .foot-grid {
    grid-template-columns: 1fr 1fr;
    gap: 28px;
  }
}
.foot-col h4 {
  font-family: var(--lt-mono);
  font-size: 11px;
  color: var(--lt-fg-3);
  text-transform: uppercase;
  letter-spacing: 0.1em;
  font-weight: 500;
  margin: 0 0 12px;
}
.foot-col a,
.foot-col p {
  display: block;
  color: var(--lt-fg-1);
  font-size: 14px;
  margin: 0 0 8px;
}
.foot-col a:hover {
  color: var(--lt-fg);
}
.foot-col .lic {
  color: var(--lt-fg-2);
}
.brand-line {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  font-family: var(--lt-mono);
  font-size: 14px;
  color: var(--lt-fg);
  margin-bottom: 14px;
}
.brand-mark {
  width: 18px;
  height: 18px;
  border-radius: 4px;
  background: linear-gradient(135deg, var(--lt-accent) 0%, var(--lt-accent-3) 100%);
  position: relative;
  box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.06) inset;
  flex-shrink: 0;
}
.brand-mark::after {
  content: "";
  position: absolute;
  inset: 4px;
  border-radius: 2px;
  background: var(--lt-bg);
  clip-path: polygon(0 0, 100% 0, 100% 30%, 30% 30%, 30% 100%, 0 100%);
}
.brand-line b {
  font-weight: 600;
  letter-spacing: 0.04em;
}
.brand-line .ver {
  font-size: 11px;
  color: var(--lt-fg-3);
  padding: 2px 6px;
  border: 1px solid var(--lt-line-2);
  border-radius: 999px;
}
.foot-bottom {
  margin-top: 48px;
  padding-top: 24px;
  border-top: 1px solid var(--lt-line);
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: var(--lt-fg-3);
  font-size: 13px;
  font-family: var(--lt-mono);
}
@media (max-width: 520px) {
  .foot-bottom {
    flex-direction: column;
    gap: 12px;
    align-items: flex-start;
  }
}
.foot-bottom .pill {
  border: 1px solid var(--lt-line-2);
  border-radius: 999px;
  padding: 3px 10px;
  color: var(--lt-fg-2);
}

:target {
  scroll-margin-top: 72px;
}

/* NOT-section */
.not-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1px;
  background: var(--lt-line);
  border: 1px solid var(--lt-line);
  border-radius: 12px;
  overflow: hidden;
}
.not-card {
  background: var(--lt-bg-1);
  padding: 26px 24px 28px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.not-head {
  font-size: 16px;
  color: var(--lt-fg);
  font-weight: 600;
  letter-spacing: -0.01em;
}
.not-head::before {
  content: "✕  ";
  color: var(--lt-bad);
  font-weight: 500;
}
.not-body {
  color: var(--lt-fg-2);
  font-size: 14px;
  line-height: 1.55;
}

/* COMPARISON table */
.comp-table-wrap {
  border: 1px solid var(--lt-line);
  border-radius: 12px;
  overflow-x: auto;
  background: var(--lt-bg-1);
}
.comp-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}
.comp-table thead th {
  text-align: left;
  padding: 14px 18px;
  font-family: var(--lt-mono);
  font-size: 11px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--lt-fg-3);
  background: var(--lt-bg-2);
  border-bottom: 1px solid var(--lt-line);
  white-space: nowrap;
}
.comp-table thead th.ours {
  color: var(--lt-accent-2);
}
.comp-table tbody tr {
  border-bottom: 1px solid var(--lt-line);
}
.comp-table tbody tr:last-child {
  border-bottom: 0;
}
.comp-table tbody td {
  padding: 14px 18px;
  color: var(--lt-fg-2);
  vertical-align: top;
}
.comp-table tbody td.feat {
  color: var(--lt-fg-1);
  font-weight: 500;
}
.comp-table tbody td.ours {
  color: var(--lt-fg);
  background: rgba(94, 106, 210, 0.05);
}

/* FAQ */
.faq-grid {
  border: 1px solid var(--lt-line);
  border-radius: 12px;
  overflow: hidden;
  background: var(--lt-bg-1);
}
.faq-item {
  border-bottom: 1px solid var(--lt-line);
}
.faq-item:last-child {
  border-bottom: 0;
}
.faq-item summary {
  list-style: none;
  cursor: pointer;
  padding: 18px 22px;
  font-size: 16px;
  color: var(--lt-fg);
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 12px;
  position: relative;
}
.faq-item summary::-webkit-details-marker {
  display: none;
}
.faq-item summary::before {
  content: "+";
  font-family: var(--lt-mono);
  color: var(--lt-accent-2);
  font-size: 18px;
  width: 16px;
  display: inline-flex;
  justify-content: center;
  transition: transform 0.2s ease;
}
.faq-item[open] summary::before {
  content: "−";
}
.faq-item summary:hover {
  background: var(--lt-bg-2);
}
.faq-item p {
  margin: 0;
  padding: 0 22px 22px 50px;
  color: var(--lt-fg-2);
  font-size: 14px;
  line-height: 1.6;
  max-width: 80ch;
}

/* STICKY SECTION NAV */
.section-nav {
  position: sticky;
  top: 0;
  z-index: 20;
  background: rgba(10, 10, 10, 0.82);
  backdrop-filter: saturate(140%) blur(10px);
  -webkit-backdrop-filter: saturate(140%) blur(10px);
  border-bottom: 1px solid var(--lt-line);
}
.section-nav-inner {
  display: flex;
  align-items: center;
  gap: 24px;
  height: 52px;
}
.sn-brand {
  display: inline-flex;
  align-items: center;
  gap: 9px;
  font-family: var(--lt-mono);
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.04em;
  color: var(--lt-fg);
  flex-shrink: 0;
}
.sn-mark {
  width: 16px;
  height: 16px;
  border-radius: 4px;
  background: linear-gradient(135deg, var(--lt-accent) 0%, var(--lt-accent-3) 100%);
  box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.06) inset;
}
.sn-links {
  display: flex;
  align-items: center;
  gap: 22px;
  margin-right: auto;
  font-size: 13px;
  color: var(--lt-fg-2);
  overflow-x: auto;
  scrollbar-width: none;
}
.sn-links::-webkit-scrollbar {
  display: none;
}
.sn-links a {
  white-space: nowrap;
  transition: color 0.15s ease;
}
.sn-links a:hover {
  color: var(--lt-fg);
}
.sn-cta {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  flex-shrink: 0;
  padding: 7px 13px;
  border-radius: 7px;
  background: var(--lt-accent);
  color: #fff;
  font-size: 13px;
  font-weight: 500;
  transition: background 0.15s ease;
}
.sn-cta:hover {
  background: var(--lt-accent-2);
}
.sn-cta .arrow {
  transition: transform 0.15s ease;
}
.sn-cta:hover .arrow {
  transform: translateX(2px);
}
@media (max-width: 760px) {
  .sn-links {
    gap: 16px;
  }
  .sn-brand {
    display: none;
  }
}

/* RECEIPTS */
.receipts-section {
  background:
    radial-gradient(900px 300px at 80% 0%, rgba(94, 106, 210, 0.06), transparent 60%),
    var(--lt-bg);
}
.receipts-section h2 .accent-fg {
  color: var(--lt-accent-2);
}
.receipts-grid {
  display: grid;
  grid-template-columns: 1.1fr 1fr;
  gap: clamp(28px, 4vw, 56px);
  align-items: start;
}
@media (max-width: 920px) {
  .receipts-grid {
    grid-template-columns: 1fr;
    gap: 36px;
  }
}
.receipts-points {
  display: grid;
  gap: 22px;
}
.rcp {
  display: grid;
  grid-template-columns: 32px 1fr;
  gap: 14px;
  align-items: start;
}
.rcp-seal {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: rgba(94, 106, 210, 0.1);
  border: 1px solid rgba(94, 106, 210, 0.28);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: var(--lt-accent-2);
  flex-shrink: 0;
}
.rcp h3 {
  font-size: 15px;
  color: var(--lt-fg);
  margin: 4px 0 4px;
}
.rcp p {
  margin: 0;
  font-size: 14px;
  color: var(--lt-fg-2);
  line-height: 1.55;
}
.receipts-aside {
  position: sticky;
  top: 76px;
}
.receipts-link {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  margin-top: 18px;
  color: var(--lt-accent-2);
  font-size: 14px;
  border-bottom: 1px solid transparent;
}
.receipts-link:hover {
  border-bottom-color: var(--lt-accent-2);
}
.receipts-kicker {
  margin: 44px auto 0;
  max-width: 70ch;
  text-align: center;
  font-size: 17px;
  color: var(--lt-fg-2);
  text-wrap: balance;
}
.receipts-kicker em {
  color: var(--lt-fg);
  font-style: normal;
}
@media (max-width: 920px) {
  .receipts-aside {
    position: static;
  }
}
</style>
