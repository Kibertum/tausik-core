---
title: "Аудит TAUSIK + SENAR + RENAR — независимый профессиональный отчёт"
date: 2026-05-18
version: 1.0
authors: ["Multi-agent synthesis (6 parallel agents) + Andrey Yumashev orchestration"]
audience: ["Authors", "Potential partners", "Standards bodies", "Early adopters"]
classification: "Internal — может быть опубликован с согласия авторов"
---

# Аудит TAUSIK + SENAR + RENAR
## Профессиональный независимый аудит экосистемы AI-нативной разработки
*Дата отчёта: 18 мая 2026 | Версии: TAUSIK 1.4.2, SENAR 1.3, RENAR 0.1-draft*

---

## TL;DR (читать в первую очередь)

1. **Это не маркетинговая методология, а пред-стандарт.** SENAR v1.3 + RENAR v0.1-draft + TAUSIK v1.4.2 — самая зрелая публичная попытка нормировать AI-нативную разработку. По дисциплине нормативного текста (RFC 2119, closed lists, mandatory clauses, dated references, negative proof) комплект уровня **раннего CMMI v1.2 (2006) и SAFe 1.0 (2011)** — то есть на 4–6 лет впереди типового рынка «AI playbook’ов».

2. **Главная техническая инновация — Verification-as-Cache contract.** TAUSIK `task done --ac-verified` физически читает кэш `verify --task <slug>` (10-минутное окно). Никто другой в индустрии не делает так: ни Cursor, ни Claude Code, ни Spec Kit, ни TaskMaster AI. Это объективное конкурентное преимущество в момент trust-кризиса (96% разработчиков не доверяют AI-коду по Sonar 2026).

3. **Главные системные риски — три:** (а) implementation gap — RENAR-CONFORMANCE.yaml в `kai/` зафиксирован уровнем RENAR-0 даже у автора стандарта, 7 из 8 drift detectors не реализованы; (б) N=1 эмпирическая база у SENAR (552 задачи, одна модель, одна команда) — критичный блокер для ISO TC; (в) market-timing — Anthropic Skills + AGENTS.md + GitHub Spec Kit поглощают соседние ниши быстрее, чем мы получаем дистрибуцию.

4. **VC-готовность сейчас — нет.** Russian residency блокирует ~80% US/EU institutional capital, telemetry отсутствует (нет метрик для pitch’а), нет design partner / LOI / paid pilot. Earliest VC-окно: **Q1 2027** при условии re-domiciliation (Сербия/UAE/Кипр/Эстония) ИЛИ российский PE/grant-track (Сколково/РФРИТ).

5. **Реалистичный путь продвижения — community-led OSS PLG, не sales-led.** В ближайшие 8 недель нужны 5 вещей: SWE-bench-бенчмарк TAUSIK vs Cursor (без чисел ни один канал не конвертит), Show HN + Habr парный launch, заявка в Linux Foundation AAIF, CFP в HighLoad SPb + AI Engineer Summit Europe, telemetry-opt-in build + Discord/TG.

6. **Не подавать в ISO TC.** ISO TC 22989 / JTC1 SC42 — 18–36 месяцев и политика. Оптимальный дом — **Linux Foundation AAIF** (Agentic AI Foundation, Dec 2025): там уже AGENTS.md, MCP, A2A. SENAR/RENAR заходит как process+RE-слой к этим protocol-стандартам, что закрывает белое пятно AAIF.

7. **Один абзац-вердикт.** Это работа уровня **8/10 как методологическая разработка, 5.5/10 как продукт, 4/10 как бизнес**. Если ничего не делать — через 12 месяцев SENAR/RENAR останутся ценным академическим артефактом, TAUSIK — нишевым CLI на ~500–1000 GitHub stars. Если выполнить топ-5 рекомендаций ниже — есть реалистичный шанс к Q4 2027 закрепиться как «open-source ISO 42001 implementation reference» для AI-native dev loop.

---

## Оглавление

- [Метаданные аудита](#метаданные-аудита)
- [0. Executive Summary](#0-executive-summary)
- [Часть I. Анатомия экосистемы](#часть-i-анатомия-экосистемы)
  - [1. Контекст: проблема AI-нативной разработки 2026](#1-контекст-проблема-ai-нативной-разработки-2026)
  - [2. SENAR v1.3 — анализ нормативного стандарта](#2-senar-v13--анализ-нормативного-стандарта)
  - [3. RENAR v0.1-draft — анализ AI-нативного RE-стандарта](#3-renar-v01-draft--анализ-ai-нативного-re-стандарта)
  - [4. TAUSIK — аудит референсной реализации](#4-tausik--аудит-референсной-реализации)
- [Часть II. Конкурентная среда и стандарты](#часть-ii-конкурентная-среда-и-стандарты)
  - [5. Карта рынка AI coding tools 2026](#5-карта-рынка-ai-coding-tools-2026)
  - [6. SENAR/RENAR в ландшафте мировых стандартов](#6-senarrenar-в-ландшафте-мировых-стандартов)
- [Часть III. Honest assessment](#часть-iii-honest-assessment)
  - [7. Что мы сделали хорошо](#7-что-мы-сделали-хорошо)
  - [8. Что мы сделали плохо или сомнительно](#8-что-мы-сделали-плохо-или-сомнительно)
  - [9. Риски (top-10 ранжированных)](#9-риски-top-10-ранжированных)
  - [10. Уникальное позиционирование](#10-уникальное-позиционирование)
- [Часть IV. Куда дальше](#часть-iv-куда-дальше)
  - [11. Технический roadmap (24 месяца)](#11-технический-roadmap-24-месяца)
  - [12. Go-to-market план (24 месяца)](#12-go-to-market-план-24-месяца)
  - [13. Top-10 рекомендаций (приоритизированных)](#13-top-10-рекомендаций-приоритизированных)
  - [14. Заключение](#14-заключение)
- [Что делать на этой неделе / в этом месяце / в этом квартале](#что-делать-на-этой-неделе--в-этом-месяце--в-этом-квартале)
- [Приложения](#приложения)

---

## Метаданные аудита

**Заказчик и цель.** Аудит запрошен Андреем Юмашевым — соавтором стандартов SENAR/RENAR и автором фреймворка TAUSIK. Формулировка задачи (verbatim): «оцените, насколько здраво, актуально и полезно то, что мы сделали; аналоги, отличия, преимущества и недостатки; рекомендации, куда дальше стремиться и как продвигать». Аудитория отчёта: автор + потенциальные партнёры, инвесторы, standards bodies, евангелисты.

**Методология.** Шесть параллельных независимых агентов работали ~3 часа каждый по строго разнесённым скоупам:

| Агент | Скоуп | Объём вывода | Источник |
|---|---|---|---|
| A | SENAR v1.3 (нормативный стандарт) | ~7 600 слов | `_findings/01-senar-analysis.md` |
| B | RENAR v0.1-draft (RE-стандарт) | ~8 700 слов | `_findings/02-renar-analysis.md` |
| C | TAUSIK v1.4.2 (референс-реализация) | ~4 600 слов | `_findings/03-tausik-audit.md` |
| D | Конкурентный анализ (30+ продуктов) | ~4 300 слов | `_findings/04-competitive-analysis.md` |
| E | Мировые стандарты (40+ стандартов) | ~4 200 слов | `_findings/05-world-standards.md` |
| F | Market + GTM (sizing, ICP, каналы, бюджет) | ~6 500 слов | `_findings/06-market-and-gtm.md` |

**Источники.** 90+ файлов внутренней документации трёх продуктов (`D:\Work\Kibertum\senar\`, `D:\Work\Kibertum\renar-public\` + `req-standart\`, `tausik` репозиторий), ~80 внешних URL (рынок, конкуренты, стандарты, регуляторы), боевые манифесты (`kai/RENAR-CONFORMANCE.yaml`, `kai/CLAUDE.md`).

**Скоуп и ограничения.** В скоуп НЕ входило:
- финансовый аудит компаний/продуктов,
- юридический аудит лицензий и IP,
- security pentest TAUSIK (только статический code review),
- независимые pilot studies (внешние replications эмпирики SENAR),
- интервью с пользователями (telemetry отсутствует).

**Conflict of interest disclosure.** Исходный аудит запрошен соавтором стандартов. Каждый из шести агентов работал по explicit instruction «писать как независимый внешний аналитик, не подхалимаж, конкретные слабости с цитатами». Финальный синтез сохранён в репозитории `D:\Work\Personal\claude\docs\audit\` и может быть опубликован с согласия авторов.

**Дата выпуска:** 2026-05-18. **Автор синтеза:** main editorial pass over six parallel-agent findings.

---

## 0. Executive Summary

### 0.1 Ключевое сообщение (один абзац)

TAUSIK + SENAR + RENAR — серьёзная работа уровня раннего CMMI или SAFe 1.0, делающая в 2026 году ровно то, чего рынку не хватает: **нормативный слой над AI-нативной разработкой**, где AI-агент производит код, а человек — Супервайзер. Авторы избежали типовых ловушек «AI methodology» жанра (маркетинговые принципы без операционализации, vendor lock-in, отсутствие conformance механизма): SENAR пишется на RFC 2119, RENAR содержит 16 closed lists и 7 mandatory clauses, TAUSIK реально enforced хуками и не позволяет агенту врать `done`. Главные проблемы — **не методологические, а адаптационные**: эмпирическая база N=1, реализация RENAR на 20–25% даже у автора, нет публичной telemetry, нет distribution. Окно для занятия ниши «процессного слоя» открыто, но закрывается быстро — Linux Foundation AAIF (AGENTS.md/MCP/A2A) и GitHub Spec Kit (90k★) растут со скоростью, на которой одинокий founder-проект не выдерживает гонку. Ближайшие 6 месяцев решающие.

### 0.2 Топ-5 находок

1. **TAUSIK Verification-as-Cache contract — техническая инновация мирового уровня.** `task done --ac-verified` физически читает кэш `verify --task <slug>` (10-min TTL, files_hash, git-diff cross-check, security-sensitive bypass). Аналогов нет ни в одном из 30+ изученных продуктов. Это и есть «AI agents that can't fake done» — не слоган, а runtime-контракт.

2. **SENAR — первый формальный нормативный стандарт для AI-native dev.** 7.5/10 как нормативный документ (`01-senar-analysis.md`). Уникальные инновации: Adversarial Detection Rate с формулой и таргетом, Agent Profiles с separation of duties между AI (Reviewer SHALL NOT have write access), Agent Dispatch isolation, AI Model = External Supplier с governance. Главный блокер — N=1 эмпирика (552 задачи, одна модель).

3. **RENAR — первый формальный SDD-стандарт в индустрии.** 7.7/10 как методологическая работа (`02-renar-analysis.md`). Уникальные инновации: ADAPT artefact с dual signature и delta workflow, 9 закрытых SPEC types, substrate-agnostic V1-V6 capabilities с **negative proof** (academic-grade reasoning, отсутствует в IEEE 42010 / arc42), TC pos/neg парность + judge ≠ production isolation. Главный блокер — implementation gap: `kai/RENAR-CONFORMANCE.yaml` зафиксирован уровнем RENAR-0, 7 из 8 drift detectors не реализованы, JSON Schema файлы помечены TODO Phase 8.

4. **TAUSIK — самая полная open-source реализация SENAR на сегодня.** SENAR conformance 88–92% (`03-tausik-audit.md`), но Rules 4 (External Validation) и 6 (Rollback Planning) не имплементированы, Rule 5 — warning, не hard. RENAR readiness 20–25%: инфраструктура (decisions table, dead-ends, exploration time-boxing) есть, но провenance chain и reasoning trace не выделены как явная фича. Главный технический долг — doc/code drift (один внутренний аудит нашёл 58 defects в v1.4.1).

5. **Главная угроза от рынка — Linux Foundation AAIF + GitHub Spec Kit.** AAIF (Anthropic + OpenAI + Block, founded Dec 2025) уже хранит AGENTS.md, MCP, A2A. Если они добавят process/governance layer как 4-й primitive — это закроет именно ту нишу, где живёт SENAR. GitHub Spec Kit (90k★, 8k forks) покрывает ~60–70% TAUSIK use cases с дистрибуцией GitHub/Microsoft. Окно для подачи SENAR/RENAR через AAIF — следующие 6 месяцев.

### 0.3 Топ-5 рекомендаций (приоритизированных)

| # | Action | Impact | Effort | Time-to-value |
|---|---|---|---|---|
| **R1** | Запустить SWE-bench Verified бенчмарк (50 задач) **TAUSIK vs Cursor Background Agents vs Claude Code baseline**, опубликовать как Show HN + Habr парный launch | **Critical** — без чисел ни один канал не конвертит; trust gap 96% даёт maximum amplification | Med (1–2 недели founder-time) | 2–4 недели до публикации |
| **R2** | Submit заявку в **Linux Foundation AAIF** как «process profile for AGENTS.md» — co-existence, не collision | **Critical** — закрывает риск поглощения ниши; единственный реалистичный standardization путь | Med ($5–15K membership + applications) | 6–9 месяцев до working group acceptance |
| **R3** | Включить **telemetry-opt-in** в v1.5 build (privacy notice + Plausible-style anonymized metrics) | **High** — без telemetry никаких «10K installs in 6 months» credibility у инвесторов и медиа | Med (4–6 недель разработки) | 3 месяца до первых defensible metrics |
| **R4** | Добавить **глобальную R-ID нумерацию SENAR (`SENAR-STD-R-NNN`) + JSON Schema файлы RENAR + 4 из 8 drift detectors** к v1.5/v0.2 | **High** — разблокирует serious conformance audit; закрывает implementation gap, который public будут сразу замечать | High (1.5–2 квартала разработки) | Q4 2026 — v0.2-draft RENAR public |
| **R5** | Открыть **paid consulting trajectory**: 5 free 1-hour консультаций → 1 paid pilot ($20–40K) → 1 case study → 3 paid pilots. Цель — $80–150K revenue к Q4 2026 | **High** — единственный способ избежать founder burnout без VC и без revenue-ready Pro tier | Low-Med (founder-time + personal network) | 8–12 недель до первого paid pilot |

### 0.4 Сводный scoreboard (3 продукта × 10 осей)

Оценка по 10-балльной шкале; обоснование — в Части I (детальный анализ) и Приложении A.

| Ось | SENAR v1.3 | RENAR v0.1-draft | TAUSIK v1.4.2 |
|---|---|---|---|
| **Формальность** (RFC 2119, IDs, нормативный язык) | 7 | 9 | 7.5 |
| **Полнота** (covers всё необходимое) | 8 | 8 | 8 (SENAR) / 2 (RENAR) |
| **Инновационность** (новое vs derivative) | 9 | 9 | 9 |
| **Прагматичность** (можно ли применить завтра) | 8 | 6 | 7.5 |
| **Измеримость** (SHALL → testable evidence) | 6 | 7 | 6.5 |
| **Адаптивность** (модель/IDE/язык) | 9 | 7 | 7 |
| **Документация** (читаемость, structure) | 9 | 9 | 8 |
| **Риск принятия** (политич./культ./adoption) | 6 | 5 | 7.5 |
| **Конкурентоспособность** (vs аналоги) | 9 | 8 | 7 |
| **Методологическая глубина** | 8 | 9 | 8.5 |
| **Средняя** | **7.9** | **7.7** | **7.0** |

**Сводно по экосистеме: 7.5 / 10** — это очень высокая оценка для авторского pre-стандарта первой генерации с N=1 эмпирикой. Для сравнения: CMMI v1.0 (1991) был на 7/10, SAFe 1.0 (2011) — на 6/10, Scrum Guide 2010 — на 5/10.

### 0.5 Honest assessment в одном предложении

**Это серьёзная методологическая работа на стыке нормативного стандарта и реализации, которая решает реальную проблему trust gap в AI-native dev, но три вещи, которые надо сделать в ближайшие 6 месяцев — это (1) SWE-bench-бенчмарк с числами, (2) подача в Linux Foundation AAIF, (3) telemetry-opt-in; без них работа останется ценным академическим артефактом, а не продуктом.**

---

# Часть I. Анатомия экосистемы

## 1. Контекст: проблема AI-нативной разработки 2026

### 1.1 Состояние индустрии

Рынок AI coding tools в 2026 году находится в фазе раскалённой консолидации:

- **TAM $16.1B в 2026**, прогноз $79B к 2031 (CAGR 37.4%) — Mordor Intelligence.
- **Cursor**: $2B ARR, $50B pre-money valuation (apr 2026, TechCrunch). В разговорах о покупке SpaceX за $60B.
- **Anthropic / Claude Code**: $2.5B ARR run rate, 300k бизнес-клиентов.
- **Cognition (Devin + Windsurf)**: $25B valuation после consolidation.
- **OpenAI / Codex CLI**: SWE-bench 88.7%, push в credit-based pricing с июня 2026.
- **GitHub Spec Kit**: 90k★ за полгода, 8k forks — одна из самых быстрорастущих devtool-репо в истории.

При этом по данным Stack Overflow 2025 Survey: **84% разработчиков используют AI**, но **96% не доверяют AI-коду** (Sonar State of Code 2026), **42% всего production-кода — AI-generated** (рост до 60% к концу 2026 по Gartner), **AI-generated код имеет в 2.74 раза больше уязвимостей**, чем human-written, и **45% AI-кода проваливают security tests**.

Это формирует **trust gap** — главный продуктовый драйвер для всего пласта «discipline / governance» решений. Karpathy объявил `vibe coding` мёртвым в мае 2026 — «agentic engineering» как новая парадигма требует normative reference, чего рынок пока не предложил.

### 1.2 Что такое «vibe coding» и почему это проблема

«Vibe coding» (Карпатый, январь 2025) — практика, когда разработчик принимает AI-вывод по интуиции («работает — значит правильно»), без формальной проверки. На уровне solo-dev это терпимо для прототипов; на уровне команды/продукта/регулируемой отрасли — главный источник:
- **Hallucination defects** (несуществующие API/dependencies/methods),
- **Silent test fitting** (AI генерирует тесты, которые проходят, но не верифицируют intent),
- **Security drift** (AI охотно пишет хорошо выглядящий, но уязвимый код),
- **Compliance violations** (AI не различает PII/secret/credential контексты).

DORA 2025 Report (Google Cloud) показал **negative correlation** между AI adoption и delivery stability — что прозвучало как звонок к structured discipline.

### 1.3 Гипотеза: discipline layer как новая категория

Категории решений, выросшие в ответ:

| Категория | Что делает | Примеры |
|---|---|---|
| **Capability layer** | AI пишет код быстрее/лучше | Cursor, Claude Code, Devin, Aider, Cline |
| **Spec layer** | Spec становится контрактом перед кодом | Spec Kit, BMAD, Kiro, Augment Intent |
| **Observability layer** | Traces / evals / monitoring | LangFuse, Maxim, Helicone, Arize |
| **Convention layer** | Static instructions для агентов | AGENTS.md, CLAUDE.md, Cursor Rules |
| **Discipline / governance layer** | Enforced gates + audit trail + verification | **TAUSIK**, частично Continue.dev |

TAUSIK/SENAR/RENAR — единственный публичный комплект, который занимает четвёртое + пятое одновременно, причём с **enforcement, а не suggestion**. Это нишевое позиционирование, но ниша реальная: каждый ISO 42001 сертификант на high-risk EU рынке нуждается в process layer, который покрывает §8 Operation. ISO 42001 — это «what», TAUSIK + SENAR — «how».

### 1.4 Где SENAR/RENAR/TAUSIK на эволюционной кривой

Сопоставляя зрелость с классическими аналогами:

| Аналог | Год его «прото-стадии» | Где сейчас наш аналог |
|---|---|---|
| CMMI v1.0 (1991) | 7/10 нормативной зрелости | SENAR v1.3 = аналог CMMI v1.2 (2006) |
| SAFe 1.0 (2011) | 6/10 нормативной зрелости | RENAR v0.1-draft = аналог SAFe 0.7 (pre-1.0) |
| Scrum Guide 2010 | 5/10 | TAUSIK v1.4.2 = аналог Atlassian Jira 1.0 (2002) для своей категории |

То есть мы находимся в стадии, когда **технический и методологический корпус уже зрелый, а индустриальная канонизация — ещё в год-два пути**.

---

## 2. SENAR v1.3 — анализ нормативного стандарта

### 2.1 Что такое SENAR

**SENAR (Supervised Engineering & Normative AI Regulation)** — нормативный стандарт для AI-нативной разработки, где AI-агент является основным производителем кода, а человек — Супервайзером. Структура:

- **5 ценностей** (Context > Code, Verification > Speed, Knowledge > Experience, Quality > Velocity, Enforcement > Agreement)
- **15 нормативных правил** (`10-rules.md` §10.1–10.15) с RFC 2119 keywords
- **5 Quality Gates** (QG-0 Context → QG-1 Requirements → QG-2 Implementation → QG-3 Verification → QG-4 Acceptance)
- **10 метрик** (Throughput, Lead Time, FPSR, Defect Escape Rate, ADR, и др.)
- **4 конфигурации** (Core → Foundation → Team → Enterprise)
- **5 уровней зрелости** (L1 Ad Hoc → L5 Optimizing)
- **44 нормативных термина** (`03-terms.md`)

Дополнительно: 5 ролей (Supervisor, Context Architect, Knowledge Engineer, Flow Manager, Verification Engineer) + 7 церемоний + 13 нормативных глав standard/ + информативный Guide + Reference annexes.

### 2.2 Формальная зрелость

**Сильные стороны (по `01-senar-analysis.md`):**

- **Структурная честность** — нормативные требования собраны в `standard/`, философия в `guide/`, измеримые единицы — в core capability requirements. Это редкое свойство для авторских методологий.
- **RFC 2119 + RFC 8174** корректно нормированы как единственные normative references (`02-normative-refs.md:5-7`).
- **Configuration-зависимая нотация `[Team+: SHALL]`** (`03-terms.md:5`) — разумное расширение для масштабируемого стандарта.
- **Conformance levels** (self-declared, peer-assessed, independently audited) в `13-conformance.md`.
- **Honest disclaimer об N=1 эмпирике** (`00-introduction.md:71-75`): «552 tasks, $989 in AI costs, 38 sessions across 6 microservices. This constitutes a case study, not a controlled experiment».

**Слабые места:**

- **Нет глобальной системы Requirement ID** (типа `SENAR-STD-R-008.1.3`). Conformance-аудитор не может скомпилировать матрицу `requirement_id → applicable configuration → evidence_type`. Это **#1 блокер для serious conformance audit** (`01-senar-analysis.md`).
- **RFC 2119 ключевые слова местами используются разговорно** (`01-scope.md:38`: «Organizations should conduct gap analysis…» — без капитализации). Нужен formal language sanity check.
- **Смешение нормативного и информативного** (`08-quality-gates.md:99-106`: нормативная таблица risk-based review расширяется прозой «security review SHALL be performed at ALL configuration levels» — это нормативное добавление вне пронумерованной структуры).

### 2.3 Ключевые инновации

Из 13 идентифицированных инноваций (`01-senar-analysis.md` §4) выделим топ-5:

1. **Adversarial Detection Rate (ADR) + L3 Adversarial Review** (`10.15`, `9.2`, `3.36`). Обязательная независимая проверка результата cold-агентом для детекции latent defects, плюс метрика плотности скрытых дефектов с явной формулой и target «< 0.5». Нюанс: «ADR=0 indicates either excellent AI quality OR insufficient review rigor» (`09-metrics.md:29`) — зрелое предупреждение против карго-метрики.

2. **Agent Profiles + Separation of Duties между AI** (`5.2`). Принцип «Reviewer SHALL NOT have write access to the artifacts being reviewed» — прямой импорт ISO 27001 SoD, применённый внутри AI-агентов. Никто другой не нормирует SoD между AI-инстансами.

3. **AI Model = External Supplier** (`10.13`). «AI model providers are external suppliers. The AI model is the primary production tool — equivalent to a compiler.» Это методологически очень мощный фрейм — он автоматически подключает к AI-моделям всю аппаратуру supplier risk management из ISO 9001.

4. **Agent Dispatch and Execution Isolation** (`5.7`). Нормирует то, что только-только появилось в продакшене (Claude Code subagents, OpenAI Swarm, AutoGen): isolation (worktrees/containers), scoped boundaries, mandatory L3 review, max parallel dispatch count. Самая опережающая по времени часть стандарта.

5. **Prompt Injection Defense as Normative SHALL** (`5.5`). Единственный известный индустриальный стандарт, который нормативно требует prompt injection protection. (Хотя без verifiable test method — см. §2.4 ниже.)

Дополнительно: First-Pass Success Rate (FPSR) как primary metric — прямой импорт First Pass Yield из бережливого производства, применённый к non-deterministic LLM output. Dead End mandatory documentation (15 min threshold). Quality Gates as Code. Operational Scripts (структура trigger/precond/algo/postcond/output — формальный аналог Design by Contract Мейера).

### 2.4 Внутренние противоречия

`01-senar-analysis.md` §6 нашёл 5 внутренних противоречий, из них критичные:

| # | Противоречие | Локация | Серьёзность |
|---|---|---|---|
| 1 | **Cost Predictability как SHALL для Team+** при том, что авторы признают: «In practice, planned cost estimation for AI-assisted tasks is unreliable» | `09-metrics.md:43` vs метрика 6 как SHALL | **High** — нормативное напряжение |
| 2 | **Maturity Levels 4-5 заявлены, но самопризнаны aspirational** | `12-maturity-model.md:18` | High — верхняя половина модели зрелости гипотетическая |
| 3 | **Sequential vs flexible progression** | `12-maturity-model.md:43-44` — «Organizations SHOULD progress sequentially. ... Organizations MAY focus on weakest dimensions first.» | Med — противоречит само себе в две строки |
| 4 | **Прыжок Foundation → Team слишком резкий** (2.1x по всем измерениям) | `11-configurations.md` | Med — adoption cliff |
| 5 | **Foundation Ceremonies omission vs Section 6.5** | `11-configurations.md:13` vs `06.5` | Low — stylistic fix |

### 2.5 Сравнение с CMMI / SAFe / ISO 12207

Из `01-senar-analysis.md` §7.1, упрощённо:

| Аспект | CMMI v2.0 | SAFe 6.0 | ISO/IEC 12207 | SENAR v1.3 |
|---|---|---|---|---|
| Production unit | проектная команда | Agile Release Train | abstract process | **Supervisor+AI Pair** |
| Process levels | 5 (L1-L5) | 4 configurations | 4 life cycle stages | **5 maturity + 4 config** |
| Quality gates | подразумеваются | DoR/DoD | review/audit | **5 explicit gates** |
| Metrics | process performance | velocity | measurement process | **10 metrics incl. FPSR/ADR** |
| AI as actor | нет | нет | нет | **first-class** |
| Adversarial review | нет | peer review | review | **normative L3** |
| AI Model risk | supplier mgmt | supplier mgmt | acquisition | **`10.13` AI Model Governance** |
| Open license | нет | proprietary | proprietary | **CC BY-SA 4.0** |

**Где SENAR заполняет пробел:** AI Model Provider as Supplier, Agent Profiles + SoD, L3 Adversarial Review с ADR, Operational Scripts с формальной структурой, Prompt Injection Defense, Dead End Documentation. Никто из CMMI/SAFe/ISO/IEEE этой ниши не закрывает.

### 2.6 Оценка по осям

| Ось | Оценка | Обоснование (сжато) |
|---|---|---|
| Формальность | 7 | RFC 2119 used правильно; нет глобальной R-ID системы |
| Полнота | 8 | Покрыт production-loop; недоописан Enterprise, нет hallucination rate metric |
| Инновационность | 9 | ADR, Agent Profiles+SoD, Agent Dispatch isolation, AI Model as Supplier — первое нормативное появление |
| Прагматичность | 8 | Core применим за час; cliff Foundation→Team снижает оценку |
| Измеримость | 6 | FPSR/DER/ADR measurable; Cost Predictability soft; QG-2 «no security vulns» — не measurable без specifying scanner |
| Адаптивность | 9 | `10.13` AI Model Governance, `5.9` Portability, language-agnostic — designed for evolution |
| Документация | 9 | 4-уровневое расслоение (Standard + Guide + Reference + Core); cross-references густые |
| Риск принятия | 6 | CC BY-SA 4.0, двуязычность; малая публичная видимость, N=1 reference impl |
| Конкурентоспособность | 9 | Единственный нормативный стандарт для AI-native dev |
| Методологическая глубина | 8 | Понимание: контекст важнее кода, hallucination — главный risk, AI model — supplier |

**Средняя: 7.9 / 10.** Согласно `01-senar-analysis.md`, это сравнимо с CMMI v1.2 (2006).

### 2.7 Готовность к публикации

| Назначение | Готовность | Что нужно |
|---|---|---|
| Independent web publication (senar.tech) | **READY** | уже опубликовано |
| Submission в OASIS / OpenChain | **READY** | sync glossary, unify ID format |
| **Informational RFC (IETF Independent Submission)** | **NEARLY READY** | глобальная R-ID, разрешение 2-3 противоречий |
| ISO/IEC PAS | **NOT YET** | second reference implementation; secure dev annex expansion |
| ISO TC 154 / JTC 1 SC 7 | **NOT YET** | independent validation N≥3 orgs; controlled FPSR/DER study; expert panel |

**Рекомендация:** подача как Independent RFC в IETF возможна через 6–9 месяцев после R-ID реформы. Серьёзная подача в ISO TC — 2027+ при условии 2-3 независимых pilot implementations.

---

## 3. RENAR v0.1-draft — анализ AI-нативного RE-стандарта

### 3.1 Что такое RENAR

**RENAR (Requirements Engineering & Normative Adaptive Regulation)** — первый формальный нормативный стандарт инженерии требований для парадигмы, где AI генерирует **сами требования**, а не реализацию по готовым требованиям. Структура:

- **3 типа требований** (BR — Business Requirement, SR — System Requirement, TR — Task Requirement) с closed list policy
- **ADAPT artefact** — bridge между immutable client ТЗ и BR/SR/SPEC с forward + backward + dual signature
- **9 закрытых SPEC types** (ARCH / API / DATA / INT / PROC / UI / AI / SEC / OPS)
- **TC as first-class** (6 типов: acceptance / ux / system / contract / eval / security) с pos/neg парностью + judge ≠ production isolation
- **5 canonical Quality Gates** (3 mandatory + 2 optional)
- **8 классов drift** с detection points
- **5 уровней зрелости RENAR-1..5** (orthogonal to SENAR maturity)
- **Substrate-agnostic V1-V6 capabilities** с negative proof
- **16 closed lists** с master index
- **14 AI risks (AIR) register** с mapping на ISO 23894 + NIST AI RMF
- **7 mandatory clauses (MVR §14.3.1-7)** — Minimal Viable RENAR

### 3.2 Spec-Driven Development inversion — обоснование и критика

`renar-public/standard/05-methodology-positioning.md` §5.3.1 нормативно фиксирует: «Источник истины о поведении системы — иерархия артефактов требований: ТЗ → ADAPT → BR / SR / SPEC → TR → TC. Код является derived артефактом реализации этой иерархии. При расхождении между кодом и вышестоящим требованием — нормативно побеждает требование.»

Это **первая нормативная формулировка SDD** в индустрии. Существующие vendor implementations (GitHub Spec Kit, Anthropic spec-first agents, Amazon Kiro, BMAD-Method) — это **tools и templates**, не **standards**. RENAR делает SDD conformance clause.

**Обоснование** (по `02-renar-analysis.md` §3.2): когда AI способен декомпозировать формальную спецификацию в код за минуты, **корректность спецификации становится критическим ограничением**, а не корректность кода. ISO/IEC 5338:2023 §6.2.1 явно говорит то же самое для AI-систем, но не нормирует механики SoT inversion.

**Критика (важная):**

1. **SoT inversion не работает для bug-fix циклов.** §5.3.3 (1) сам признаёт: «Reverse-engineering допустим только при создании bug-fix задачи». Но граница между bug-fix и «молчаливой адаптацией SR под код» нечёткая. Это — judgement call архитектора, что в AI-driven контексте без human-in-the-loop **может стать loophole**.

2. **SoT inversion плохо ложится на data-driven продукты.** Для ML/AI продукта «требование» формулируется как metric threshold (recall ≥ 0.95), а не как наблюдаемое поведение. SPEC-AI пытается адресовать через `eval-strategy` + `metric-thresholds`, но фактически признаёт, что SoT для AI-компонент — это пара (spec, eval-dataset). Без версионирования eval-dataset (V5 cross-substrate version pin) SoT decay неизбежен.

3. **Source citation как нормативный механизм работает только если ТЗ структурировано.** Принцип 3 (`09-metrics.md`: Hallucination Rate) предполагает, что AI вставляет inline citation `[TZ-XXX §Y line Z]`. Но **большинство ТЗ — polished prose, не нумерованные параграфы**. Для unstructured ТЗ (typical pre-sale брифы, transcripts видеоинтервью) source citation не имеет надёжного якоря. Это **слабое место**: без normative требования к ТЗ-структуре Hallucination Rate ≤ 1% на RENAR-5 (§13.3.3) недостижим на типичных enterprise проектах.

### 3.3 ADAPT artefact — главная инновация

ADAPT — обязательный bridge artefact между immutable ТЗ и BR/SR/SPEC. Содержит:
- **Forward**: инженерная интерпретация по разделам ТЗ + term mapping + достроенные сценарии + scope clarification
- **Backward**: 7 закрытых категорий findings (contradiction / gap / hidden-assumption / feasibility / regulatory / terminology / scope) с sub-state machine (open → asked-to-client → answered → resolved → frozen)
- **Двойная подпись** (client-signature + architect-signature) для перехода в `approved`
- **Delta-ADAPT** цепочка строго ordered (защита от drift class 6 Order/provenance drift)
- **Errata-ADAPT** для post-approval ошибок

Похожие artefacts существуют в RUP (Use-Case Realization), BABOK §6, SAFe (Solution Intent fixed+variable). Но **никто не нормирует это так формально**: closed list 7 категорий findings, sub-state machine для каждой записи, mandatory double-signature, errata workflow. RENAR — первый.

Особенно ценны (`02-renar-analysis.md` §4.2):
- **§7.10.3 «Клиент не общается с AI напрямую»** — архитектор агрегирует backward вопросы в человеческий формат. Структурная защита от AIR-02 (prompt injection через клиента).
- **§7.6 Delta-ADAPT строго ordered** — закрывает drift class 6.
- **§7.6.3 Errata vs delta-ADAPT** — два разных артефакта в зависимости от типа ошибки (ambiguity ТЗ vs ошибка интерпретации инженера).

**Реалистичность практически — большие вопросы:**

- **Двойная подпись требует identifiable Client representative.** В госконтрактах подпись «представитель клиента» — отдельный человек, который не участвовал в формулировании ТЗ. В стартап-консалтинге PM клиента сам не знает ответы на backward вопросы. RENAR честно объявляет lean startup / hackathon / pure discovery non-conformant (`01-scope.md` §1.5), но это **сужает применимость значительно**.
- **7 категорий backward findings — closed list слишком rigid.** Multi-category findings (например, «hosting в РФ + EU-only tech + EU-market») будут вынуждать архитектора выбирать категорию arbitrary.
- **ADAPT lifecycle 6 состояний — много для маленьких проектов.** Full lifecycle + double signature = 2–3 рабочих дня overhead для проекта на 5 SR. Даже в `kai/RENAR-CONFORMANCE.yaml` ADAPT-lite advisory wired, а `dual-signature hard-block` запланирован «на team-tier» в Phase 6 — то есть **сам автор стандарта не запускает full ADAPT lifecycle на core-tier**.

**Вывод по ADAPT:** настоящая инновация уровня ISO TC. Но primary scope (§1.4.1) — узкий sliver реальных проектов (~20–30% enterprise consulting, ~80% regulated industries). Core-mode (`core/renar-core.md`) — explicit acknowledgment, что full RENAR не для всех.

### 3.4 9 SPEC types — анализ closed list

§8.3 фиксирует 9 типов: `SPEC-ARCH / API / DATA / INT / PROC / UI / AI / SEC / OPS`. §8.3.1 явно перечисляет, что **не вошло** в v1.0: SPEC-EVENT, SPEC-CONFIG, SPEC-PERF, SPEC-TEST-ENV, SPEC-DOMAIN, SPEC-MIGRATION, SPEC-COMPLIANCE — с обоснованием каждого исключения.

**Сильные стороны:**
- Closed list с явным forbidden — best practice ISO TC discipline. Открытые наборы artifact types в enterprise превращаются в 30–50 типов через 2–3 года.
- Обоснование исключений — academic-grade (каждое решение с rationale).
- Параллельная ось SPEC (`§8.2.2`) с typed edges через `constrained-by[]` — больше дисциплины, чем у arc42.

**Где границы спорные (`02-renar-analysis.md` §5.3):**
- **SPEC-API vs SPEC-INT** для outbound webhooks / async event-driven internal communication — эвристика «есть ли counterparty» не всегда чёткая.
- **SPEC-AI vs SPEC-SEC** для adversarial concerns (prompt injection — AI или SEC?). §8.5.7+§8.5.8 признают overlap.
- **SPEC-PROC vs SPEC-API** для saga/workflow orchestration. Граница на бумаге работает, в практике PROC и API становятся mutual references.

**Что не покрыто (gaps):**
- **SPEC-CONTENT** для CMS/контент-систем.
- **SPEC-EVT** для event-sourcing систем — event schema versioning, replay semantics. RENAR говорит «events — раздел SPEC-API», но event-sourced система — не API, а cumulative log.
- **SPEC-ML-DATA** для ML-проектов — training set lineage, label provenance, fairness audit datasets.

### 3.5 Substrate-agnostic V1-V6 — лучшая часть стандарта

Любой substrate, реализующий RENAR, обязан обеспечить 6 capabilities:
- **V1** Immutable history
- **V2** Atomic change unit
- **V3** Diff & review
- **V4** Branching / change-set
- **V5** Cross-substrate version pin
- **V6** Author + timestamp

§11.2 даёт **negative proof** для каждой capability — «что без V_i невозможно», ссылаясь на конкретные секции других глав. Это **academic-grade reasoning**: capability не «nice to have», а structurally necessary для других нормативных утверждений. Substrate-agnostic нормативный язык («atomic change unit», «version pin», «author + timestamp» вместо «commit», «PR», «merge») — best practice ISO TC 7.

**Где V1-V6 покрывают всё, но с натяжкой.** Mapping таблица (§11.4) перечисляет только git/Mercurial/SVN/Perforce/CouchDB. Современные analytical/streaming substrates:

| Substrate | V1 | V2 | V3 | V4 | V5 | V6 |
|---|---|---|---|---|---|---|
| ClickHouse | ✓ | partial | ✗ | ✗ | partial | ✓ |
| Delta Live Tables | ✓ | ✓ | partial | partial | ✓ | ✓ |
| Snowflake Time Travel | ✓ | ✓ | partial | partial | ✓ | ✓ |
| Kafka + KSQL | ✓ | partial | ✗ | partial | partial | ✓ |
| Iceberg | ✓ | ✓ | partial | ✓ | ✓ | ✓ |
| DVC | ✓ | ✓ | через git | через git | ✓ | через git |

**V3 (diff & review) и V4 (branching) — не first-class в analytical/streaming substrates.** RENAR формально объявляет такие конфигурации non-conformant (§11.5), но **compensating layer для ClickHouse — это внешний git с schema migrations, не сам substrate**. Это hidden assumption: V1-V6 хорошо ложатся на document/code, плохо на analytical/streaming. Для **AI-критических продуктов** (RENAR явно targets на RENAR-5), где eval-dataset + model weights + RAG corpus — это analytical substrate, V3/V4 implementation остаётся open question.

**V5 (cross-substrate version pin) — лучшая идея во всём стандарте.** Pair `(artifact-id, version-id)` resolvable cross-substrate решает: `verifies[].version` в TC, TC freshness metric, delta-ADAPT base point, audit trail. Боевой манифест `kai/RENAR-CONFORMANCE.yaml` использует CouchDB `_revs` для V5 — это работает.

### 3.6 Drift detectors — реализуемость

8 классов drift с detection points:

| # | Класс | Detection point | Реализуемость |
|---|---|---|---|
| 1 | Schema drift | Substrate hook на change-set | **Высокая** — JSON Schema validator |
| 2 | Lifecycle drift | Substrate hook на promote | **Высокая** — state machine check |
| 3 | Source-of-truth drift | Reconciliation hook RENAR-4+ | **Средняя** — diff между substrate и derived |
| 4 | Implementation drift | Auto-invalidate `verified` при `version` increment | **Высокая** — V5 pin check |
| 5 | Terminological drift | Substrate hook | **Средняя** — regex/AST, false positives |
| 6 | Order/provenance drift | Substrate hook | **Высокая** — `created-by-order` check |
| 7 | TC ↔ requirement drift | Runner-managed | **Высокая** — `last-run.requirement-version` |
| 8 | Test-fitting drift | Substrate hook через `[test-spec-change]` | **Средняя** — ACL constraint |

**Только drift-8 реализован на боевом примере `kai/RENAR-CONFORMANCE.yaml` (строки 33–44).** Остальные 7 — «planned Phase 8 (gerda-drift-1-7 story, LLM-based)». Это значит, что **на момент v0.1-draft нет полной reference implementation** ни одного из drift detectors 1-7. Для v1.0 RENAR-3+ conformance это **критический gap**: без работающих drift detectors §10.11.1 (substrate-нативные hooks обязаны блокировать) **остаётся декларативным**.

### 3.7 Сравнение с ISO 29148 / IEEE 830 / BABOK / IREB / SAFe

Из `02-renar-analysis.md` §9.1, упрощённо:

| Аспект | ISO/IEC/IEEE 29148:2018 | BABOK v3 | SAFe 6.0 | RENAR v0.1-draft |
|---|---|---|---|---|
| Requirements taxonomy | Business/System/Software/Stakeholder | Business/Stakeholder/Solution/Transition | Epic/Capability/Feature/Story | **BR/SR/TR (closed list)** |
| Lifecycle states | Listed, not normative | Knowledge area | Workflow (per tracker) | **Canonical state machines** |
| Spec types | Design Description (one) | Solution Components | Enabler Epic | **9 closed types** |
| Test cases | Verification activity | Verification artifact | Story acceptance | **First-class artifact** |
| AI provenance | Not addressed | Not addressed | Not addressed | **Mandatory at RENAR-4+** |
| Bidirectional client adaptation | Mentioned (validation) | Elicitation | Solution Intent | **ADAPT artefact** |
| Substrate-agnostic | Tool-agnostic implicit | Tool-agnostic | Tool-agnostic | **V1-V6 explicit + negative proof** |
| Conformance procedure | None | None | Certification | **RENAR-CONFORMANCE.yaml** |
| Closed lists | None | None | None | **16 closed lists** |
| Drift detection | Mentioned (config mgmt) | Continuous improvement | Continuous reconciliation | **8 classes formal** |

**Где RENAR заимствует, переименовывает, игнорирует:**

Заимствует напрямую — ISO/IEC 29148 (BR/SR/TR ≈ StRS/SyRS/SRS), ISO/IEC 25010 (NFR), SAFe hierarchy (mapping table §3.13.1), ISTQB test design, CMMI capability levels (как orthogonal RENAR-M).

Адаптирует — ISO/IEC 29148 18 attributes → 7-8 mandatory + auto-derived; ISO/IEC 5338:2023 → ai-provenance + judge isolation; ISO/IEC 23894:2023 → 14 AIR.

Игнорирует принципиально — IEEE 1028 inspections (заменены adversarial AI-review), CMMI organisational standard processes (заменены принципами + автоматический enforcement), heavy formal methods (B-method, Z-notation, TLA+), document-heavy practices (RUP, SWEBOK inspections).

### 3.8 Маппинг на EU AI Act / NIST AI RMF / ISO 42001

`guide/06-compliance.md` §5 даёт mapping RENAR-артефактов на high-risk requirements EU AI Act:

| EU AI Act требование | RENAR покрытие |
|---|---|
| Technical documentation (Art. 11 + Annex IV) | ADAPT artefact + project DB exports |
| Risk management system (Art. 9) | SPEC-AI + AI risk register (14 AIR) |
| Transparency (Art. 13, 50) | SPEC types include traceability + ADAPT |
| Human oversight (Art. 14) | One-click approval + spot-check |
| Accuracy/robustness (Art. 15) | eval-tests (tc-type: eval) + adversarial review |
| Quality management system (Art. 17) | RENAR sits inside ISO 42001 QMS |
| Conformity assessment (Art. 43) | RENAR audit trail supports |
| GPAI obligations (Art. 51-55) | `ai-provenance` mandatory + model card в SPEC-AI |

**Это сильное mapping**, но без third-party assessor accreditation (§14.6 gap) формальный AI Act conformity assessment через RENAR **невозможен**. EU AI Act требует CE marking + accredited notified body; RENAR — infrastructure layer, не certification body.

### 3.9 Implementation gap

Самая критическая часть аудита. Боевой манифест `kai/RENAR-CONFORMANCE.yaml` фиксирует уровень **RENAR-0 (pre-adoption)** даже на референсной команде Kibertum, где RENAR разрабатывался. Это значит:
- 7 из 8 drift detectors не реализованы
- `dual-signature hard-block` планируется в Phase 6
- JSON Schema файлы помечены TODO Phase 8

**Подтверждение из аудита TAUSIK (`03-tausik-audit.md` §"RENAR-readiness"):** RENAR-готовность 20–25%. Инфраструктура на 50% (`task_logs`, `decisions`, `memory_edges`, `verification_runs.files_hash`), но нет structured reasoning steps, нет model-version-pinning per task, нет `task replay`.

**Это критический сигнал** о реалистичной длительности adoption: **1–2+ года для RENAR-3, ещё 1–2 квартала для RENAR-4**. Claim conformance к RENAR-4 на момент v0.1-draft физически невозможен без 1–2 кварталов substrate-engineering работы.

### 3.10 Оценка по осям

| Ось | Оценка | Обоснование |
|---|---|---|
| Формальность | 9 | Closed lists, mandatory clauses, MVR, dated references, immutable manifest, master index — ISO TC-grade |
| Полнота | 8 | 15 normative + 5 reference + 8 guide покрывают 95% сценариев; минус JSON schemas + analytical substrates |
| Инновационность | 9 | ADAPT, judge isolation, V1-V6 negative proof, SoT inversion as conformance clause, 16 closed lists |
| Прагматичность | 6 | Heavy для малых команд; ADAPT overhead; mandatory pos/neg; source citation per утверждение = enterprise level |
| Измеримость | 7 | 10 метрик с формулами; целевые значения теоретические, field data missing |
| Адаптивность | 7 | RENAR-1..5 + declared-stricter + delta-ADAPT + multi-substrate; heavy `formal change procedure` снижает |
| Документация | 9 | ~80-100k слов с cross-references; «Связь с другими главами»; canonical-only; anti-patterns guide |
| Риск принятия | 5 | Высокий barrier; substrate V1-V6 + ADAPT + AI provenance — enterprise+regulated only |
| Конкурентоспособность | 8 | **Единственный** публичный normative SDD стандарт в 2026 |
| Методологическая глубина | 9 | Корпус уровня CMMI v2 / ISO 9001 |

**Средняя: 7.7 / 10.** Если бы это был v1.0 с закрытыми Top-10 findings (JSON Schema, drift detector reference impl, 3+ pilot benchmarks, third-party assessor accreditation, research↔public reference reconciliation) — **8.5–9 / 10**.

### 3.11 Что нужно для v1.0

Из `02-renar-analysis.md` §12, 7 пунктов:

1. JSON Schema файлы для машинной валидации (`reference/schemas/` — sub-folder помечен TODO Phase 8)
2. Реализация 4+ drift detectors из 8 (сейчас 1 из 8)
3. 3+ independent pilot adoptions с публикуемыми case studies
4. Substrate-specific tool guides для analytical/streaming (расширение §11.4 mapping таблицы)
5. Third-party assessor accreditation model (§14.6 gap)
6. Field data benchmarks для целевых значений метрик (Hallucination ≤ 1%, RDLT < 4h, DRA ≤ 2%)
7. Reconciliation public↔research cross-references (§11.3) — нормативные ссылки на `research/*.md` broken для public аудитории

Реалистичный timeline для v1.0: **9–12 месяцев при наличии 2–3 pilot adoptions**.

---

## 4. TAUSIK — аудит референсной реализации

### 4.1 Что такое TAUSIK

TAUSIK v1.4.2 (commit `a127d45`, branch `main`) — open-source CLI/runtime, реализующий SENAR. Снимок:
- **138 source files** (Python stdlib), средний файл ≈ 217 строк
- **3378 заявленных тестов** (badge: «3400 passing»), 183 test-файла
- **103 MCP tools** (96 project + 7 brain)
- **25 quality gates** (5 universal + 20 stack-scoped)
- **20+1 hooks** (PreToolUse/PostToolUse/SessionStart/UserPromptSubmit/Stop/SessionEnd/pre-commit shell)
- **11 review agents** (6-agent `/review` parallel + 2 named subagents + 3 vendor)
- **12 core skills auto-deployed + 25 vendor opt-in**
- **9 stacks** в маркетинге vs 25 в `DEFAULT_STACKS` коде (см. §4.10 тех. долг)
- **Schema v27**
- **2 MCP-сервера** (`tausik-project` + `tausik-brain`) + опциональный `codebase-rag`

### 4.2 Архитектура

Чистая трёхслойная архитектура **CLI → Service → Backend**:
- `scripts/project.py` (152 строки) — точка входа
- `scripts/project_parser*.py` (×7) — argparse дерево
- `scripts/project_cli*.py` (×11) — handlers per-domain
- `scripts/project_service.py` + 12 mixins — бизнес-логика
- `scripts/project_backend.py` + 11 backend модулей — SQLite CRUD + миграции + FTS5

**Сильные стороны (`03-tausik-audit.md`):**
- File-size gate 400 строк работает (18 файлов прижались к 350–400)
- Циклов зависимостей не обнаружено
- `default_gates.py` корректно делегирует stack-scoped gates в `stack_registry` (single source of truth)
- Mixin-композиция `TaskMixin(TaskDoneReportMixin, GatesMixin, CascadeMixin)` облегчает разрезание задач

**Что вызывает сомнения:**
- **13 mixin'ов** — потенциально хрупкая MRO (method resolution order)
- **Daemon-thread envelope timeout** в `run_gates_with_cache` (service_verification.py:266) — корректное решение для «гейт повис», но «daemon thread leaves the lingering subprocess unwound» — subprocess может зависнуть осиротевшим до перезапуска IDE

**Архитектурный рейтинг: 4.2/5.** Сильно, но местами over-engineered.

### 4.3 SENAR conformance — Rule-by-Rule

Из `03-tausik-audit.md` §SENAR-conformance:

| Элемент | Авто-оценка | Реальная (1-5) | Комментарий |
|---|---|---|---|
| QG-0 Goal / AC обязательны | ✅ Hard | 5 / 5 | `gate_qg0_check.check_qg0_start()` блокирует |
| QG-0 Негативный сценарий | ✅ Hard | 5 | 30+ en+ru keywords |
| QG-2 AC evidence | ✅ Hard | 5 | `verify_ac()` — нет `--force` |
| QG-2 Verify cache | ✅ Skip-on-hit | 5 | 10-min TTL + files_hash + security bypass + git-diff |
| QG-2 Quality gates | ✅ Hard | 5 | 25 gates, stack-aware |
| **Rule 1 — No code without task** | ✅ Hard (hook) | **5** | `task_gate.py` блокирует Write/Edit. **Killer feature** |
| Rule 2 — Scope boundaries | ✅ Warning | 3 | Warning-only |
| Rule 3 — Verify against criteria | ✅ Hard | 5 | QG-0 + QG-2 |
| **Rule 4 — External validation** | ❌ Не упомянуто | **1.5** | **NOT IMPLEMENTED**. `/review` — внутренний 6-агентный pipeline; «external» в SENAR-смысле покрывается только `tausik-reviewer` opt-in |
| Rule 5 — Verification checklist | ✅ Warning | 3.5 | 4-tier auto-detect, не enforce |
| **Rule 6 — Rollback planning** | ❌ Не упомянуто | **1** | **NOT IMPLEMENTED**. В `docs/ru/senar.md` явно: «Правила 4–6 существуют в спецификации, но пока не применяются» |
| Rule 7 — Root cause for defects | ✅ Warning | 3.5 | Keyword-detection ограничен |
| Rule 8 — Knowledge capture | ✅ Warning | 4 | `tausik decide`, `memory add`, `dead-end` |
| Rule 9.2 — Session limit (180 min) | ✅ Hard | 5 | Gap-based active time, clip AFK до 10 min — единственная индустрия, кто это делает правильно |

**Суммарный SENAR rating: 4.10/5.0 ≈ 82%.** Расхождение с моей экспертной оценкой полноты 88–92% — я считаю Rules 4/6 критичными, а матрица выводит их за пределы Core.

### 4.4 RENAR readiness 20-25%

Тот же gap analysis из `03-tausik-audit.md`:

| RENAR concept | TAUSIK инфраструктура | Готовность |
|---|---|---|
| Reasoning trace per task | `task_logs` + FTS5 | 60% — есть, но нет structured (intent → premise → action → verification) |
| Provenance chain | `decisions` + `memory_edges` (supersedes/caused_by/contradicts) | 50% — graph есть, нет «research → decision → code → test» |
| Reproducibility | `verification_runs.files_hash`, prompt-caching validator | 40% — нет prompt-snapshot / model-version pinning per task |
| Audit log | `events` table | 70% — лог есть, нет immutability (hash-chain / append-only) |
| Model version tracking | `sessions.model_id` | 50% — есть колонки, weak link с `usage_events` |
| Cost reproducibility | `usage_events` + `cost_pricing.py` | 65% — работает, не привязано к decision provenance |

**Что блокирует RENAR-релиз:**
1. Нет formal reasoning trace API (`/reason start` skill + `reasoning_steps` table)
2. Нет model-version-pinning per task (текущий `usage_events.model_id` — best-effort)
3. Нет `task replay` команды

### 4.5 Killer feature: Verification-as-Cache contract

Из `03-tausik-audit.md` и `04-competitive-analysis.md` §4.1:

«Никто другой не реализует "verify запускает heavy gates, кэшируется 10 минут, task done читает кэш". В индустрии есть Stop Hooks (Claude Code), pre-commit hooks, CI-уровень PR-checks — но не сквозной кэш-контракт между verify и done в одном CLI. Это **технически уникальная** часть TAUSIK.»

Механизм:
1. Агент вызывает `tausik verify --task <slug>` — heavy gates запускаются (pytest scope, mypy, secret_scan, FTS5 checks, gate runner)
2. Результат + `files_hash` + `git-diff cross-check` + security bypass for security paths кэшируется в `verification_runs` table с 10-min TTL
3. Агент вызывает `tausik task done <slug> --ac-verified`
4. `task_done` физически читает кэш. Если cache miss / expired / files_hash mismatch — task done **отказывается** закрыть
5. Нет `--force` у `task done` (есть `--force` у `task start` с audit trail)

Это превращает agent loop в **физически невозможный для "fake done"**. Это и есть «AI agents that can't fake done» в техническом смысле, а не маркетинговом.

### 4.6 DX (Developer Experience)

**Сильные стороны:**
- Onboarding <15 минут (submodule + bootstrap + restart IDE — три команды)
- «Tell your agent» pattern (README) — установку делает сам агент
- Token efficiency: с 38 skills (~1520 tok/turn) → 12 + brain conditional (~480 tok/turn) — экономия **68% per turn**
- `tausik doctor` — 4-group health check с remediation hints
- 49 RU + 47 EN doc файлов с regular translation-drift audits
- Verify-First Contract: «task done в миллисекунды» — действительно меняет UX

**Слабые стороны:**
- CLI surface ≥80 команд — учить не нужно (skills wrap), но debugging требует
- Memory 4-tier (TAUSIK / Claude auto / Brain / CLAUDE.md) — onboarding-документация недостаточно объясняет «зачем 4, а не 1»
- Windows-friction: `.tausik/tausik` — bash wrapper, на cmd.exe не работает (есть `.tausik/tausik.cmd`, но quickstart рекомендует Git Bash / WSL)
- `tausik` нет в PATH — после bootstrap агент должен звать через `.tausik/tausik` (намеренно, per-project venv, но визуально шумно)
- MCP server timeout (VS Code Claude Extension ≈ 60s) — gotcha; Verify-First Contract пришлось ввести **специально** под этот баг хоста

**DX rating: 4.0/5.**

### 4.7 Performance / scaling concerns

**SQLite + FTS5 — реальные риски:**
- **WAL mode + concurrent agents** — документированы как working, но `run_gates_with_cache` docstring явно признаёт: «two simultaneous `task done` calls for the same slug both miss cache, both run gates, both `record_run`. SQLite WAL keeps this safe (no corruption); the cost is duplicate `verification_runs` rows and redundant gate work.»
- **fts_* triggers** на каждое INSERT/UPDATE/DELETE для `tasks`, `memory`, `decisions`, `task_logs` — на 10k+ задач становится заметно
- **`backend_queries.get_metrics()`** — combined query с `julianday()`, `GROUP BY complexity` — на 10k tasks миллисекунды, но не line
- **Per-PostToolUse hook overhead**: 6 хуков на каждый tool call. Каждый — отдельный Python subprocess (cold start ~50–80 ms). Это **300–480 ms latency на каждый Read/Write/Edit**. На 200-call сессии = 60–96 секунд накладных расходов. **Не задокументировано как perf cost.**

**Scaling estimate (`03-tausik-audit.md`):**
- До 5k tasks — комфортно
- 5k–20k — потребуется `fts optimize` + partition по `archived_at`
- 20k+ — SQLite перестанет быть оптимальным. **Schema_v27 это не задумывала** — это hidden scaling cliff

**Performance rating: 3.5/5.**

### 4.8 Security audit

**Что реализовано (сильно):**
- `bash_firewall.py` — regex с word boundaries (fix v1.3.4 — раньше substring match ловил false-positives на `echo "git push --force"`)
- `secret_scan.py` — AWS/GitHub/Slack/Stripe/OpenAI/Anthropic/JWT/private-key/generic. Warning по умолчанию, `TAUSIK_SECRET_SCAN_STRICT=1` блокирует
- `git_push_gate.py` — single-use ticket с TTL 60s + HEAD SHA bind. v1.4 удалила broken env-bypass
- `memory_pretool_block.py` — блокирует cross-project leak в `~/.claude/`
- `brain_scrubbing.py` — scrubbing linter
- SHA256 project hashes в Brain для приватности
- `is_security_sensitive()` — security paths (auth/payment/billing/hooks/) bypass verify cache

**Риски:**
- **`shell=True` в `gate_command_runner.py:75`** при наличии `|`, `&&`, `>>`, `2>&1`. Команды берутся из `default_gates.py` + `stack_registry` + custom stacks в `.tausik/config.json`. Если кто-то правит custom stack — может попасть command injection. **Не критично** (это файл, который пишет владелец проекта), но шероховатость.
- **`bandit` gate `enabled: False`** по умолчанию. Включить руками — не делается автоматически
- **No supply chain proof** — нет SBOM, нет signed releases. Vendor skill auto-install (`tausik skill install`) скачивает code из GitHub, проверяется только URL/origin, контент не верифицируется
- **Hook subprocess'ы получают stdin tool_input** — это user-controlled. Хуки в основном parse JSON, но если кто-то добавит `os.system(tool_input.get('command'))` в кастомный хук — game over. Контракт hook'ов — read-only — конвенция, не enforcement

**Security rating: 3.8/5.**

### 4.9 Memory / skill / hook 4-tier architecture

| Tier | Где | Что | Когда |
|---|---|---|---|
| 1. TAUSIK memory | `.tausik/tausik.db` | Project-scoped patterns/gotchas/conventions/dead_ends/decisions | Каждая задача, hot path |
| 2. Claude auto-memory | `~/.claude/projects/<dir>/memory/MEMORY.md` | Cross-project user habits | Implicit, IDE-managed |
| 3. Shared Brain | Notion (4 DBs) + local mirror `~/.tausik-brain/brain.db` | Cross-project artifacts/patterns/web cache | Opt-in после `brain init` |
| 4. CLAUDE.md | Repo root | Static rules + dynamic block | Каждый turn (re-injected) |

**Проблема:** пользователю объяснили, что у нас 4 уровня, но `memory_pretool_block.py` блокирует запись project-инфо в `~/.claude/` — то есть **граница между tier 1 и tier 2 enforced**. Между tier 1 (local) и tier 3 (brain) — есть scrubbing, classifier, universality detector. Tier 4 (CLAUDE.md) обновляется отдельной командой `tausik update-claudemd`.

Это **не путаница, это многослойная защита**. Но onboarding-документация недостаточно объясняет **зачем** четыре уровня. Agent с непустой auto-memory путается между tier 1 и tier 2 — лечится дисциплиной «Знания фреймворка остаются здесь» (CLAUDE.md).

**Memory rating: 4.0/5.** Архитектурно сильно, UX-документация слабая.

**Skills:** 12 core auto-deployed + 25 vendor opt-in, **2-axis variants** (`variants/ide/{claude,cursor,qwen,codex}.md` + `variants/model/{opus,sonnet,haiku,gpt-4,gpt-5,gpt-5-5,qwen}.md`), bundles (`integrations`, `data-formats`, `quality-pro`, `automation`, `workflow-helpers`, `ru-locale`), marketplace (`tausik skill repo add <url>`). Это **best-in-class** среди открытых систем. **Skills rating: 4.7/5.**

**Hooks:** 6 PostToolUse + 6 PreToolUse + 1 SessionStart + 1 UserPromptSubmit + 2 Stop + 1 SessionEnd + 1 git pre-commit. **Hooks rating: 4.2/5.** Полезный набор, perf cost скрыт (см. §4.7).

### 4.10 Vendor lock-in: Claude Code 100% vs Cursor 60%

Заявлено: Multi-IDE (Claude Code, Cursor, Qwen Code, Windsurf, Codex), multi-model (Opus/Sonnet/Haiku/GPT-4/5/5-5/Qwen).

**Реальность:**
| Capability | Claude Code | Cursor | Qwen | Codex | GPT-любой |
|---|---|---|---|---|---|
| MCP tools | ✅ | ✅ | ✅ | partial | ✅ |
| 20 Python hooks | ✅ | ❌ (no API) | partial | ❌ | ❌ |
| Slash skills | ✅ native | ❌ (read SKILL.md) | partial | ❌ | ❌ |
| `~/.claude/...` memory | ✅ | ❌ | read-only | ❌ | ❌ |

**Вывод:** TAUSIK **архитектурно multi-IDE**, но enforcement-разница между Claude Code (full hooks + skills) и Cursor/Qwen (только MCP + self-serve) — огромная. Если ваш агент не Claude и не Cursor — вы получаете ~60% от обещанной дисциплины. **Vendor-neutrality rating: 3.5/5.** Architecturally honest, enforcement is Claude-first.

### 4.11 Сравнение с базой

| Сценарий | Что есть | Что теряется без TAUSIK |
|---|---|---|
| Vanilla Claude Code, нет CLAUDE.md | Только агент + tools | Всё: нет goal/AC, нет session continuity, нет verify, нет dead ends, нет metrics |
| Claude Code + AGENTS.md only | Письменные рекомендации | Enforcement = 0 |
| Cursor Rules | Static rules в `.cursorrules` | Нет lifecycle, нет metrics, нет hooks API |
| Claude Skills (Anthropic native) | 8-10 встроенных skills | Нет project DB, нет dead-end tracking, нет multi-IDE |
| **TAUSIK** | Все вышеперечисленные + enforcement + project memory + metrics | — |

**Ключевая дельта: Enforcement vs Suggestion.** AGENTS.md/Cursor Rules — рекомендации. TAUSIK — `task_gate.py exit 2` + Verify-First refuse-to-close.

### 4.12 Технический долг (top-10)

Из `03-tausik-audit.md` §«Технический долг»:

1. `/notify_on_done` hook удалён в 1.3.6 как orphan — до сих пор не восстановлено
2. Outline как alt-backend для Shared Brain (TODO 2026-04-22) — нет MVP
3. **Cursor MCP rework для v1.5** (CHANGELOG Unreleased) — composer/workspace MCP filesystem mirror не публикует stdio servers; патча нет
4. **README/docs drift:** «13 stacks» в маркетинге vs 25 в `DEFAULT_STACKS` (не исправлено в v1.4.2)
5. `tdd_order` enabled=False по умолчанию, рекламируется в functionality table
6. `bandit` enabled=False по умолчанию
7. **Coverage % не публикуется** — badge «3400 tests passing» не отражает реальное покрытие
8. **`shell=True` в gate_command_runner** для команд с `|`/`&&` — потенциальный command injection через custom stacks
9. **Daemon-thread envelope timeout** — subprocess может остаться осиротевшим
10. `v14c-defect-mcp-tool-handler-drift` — `test_every_tool_name_has_handler` падает; не закрыто в v1.4.0
11. **MCP tool descriptions** — каждая правка переписывает prompt prefix → cache bust. Нет CI-gate, который ловил бы accidental rewording
12. **6 PostToolUse hooks per tool call** = 300-480 ms latency, не документировано
13. Manual `fts optimize` — без cron / scheduled задачи
14. **No SBOM / signed releases**
15. **Vendor skill auto-install** скачивает arbitrary code без content verification
16. **«0 dependencies» badge** игнорирует MCP venv deps (`mcp` package)
17. README количества: «5-agent» → «6-agent» (CHANGELOG v1.4.1) — drift регулярный, исправляется ad-hoc
18. **`tausik task done` без `--force`** (правильно), но **`tausik task start --force` есть** — асимметрия может быть exploit'ом

### 4.13 Оценка по осям

| Ось | Оценка | Обоснование |
|---|---|---|
| SENAR полнота | 8.5/10 | 33/33 core элементов, но Rules 4/6 partial; Rule 5 = warning |
| RENAR готовность | 2/10 | Не имплементирован; инфраструктура на 50% |
| DX | 7.5/10 | Отличный onboarding, тяжёлый CLI surface, Windows friction |
| Performance | 6.5/10 | SQLite до 5k tasks OK, hook latency скрыт |
| Security | 7/10 | Хорошие основы, нет supply chain story |
| Tests | 7.5/10 | 3378 высокий count, но coverage % не публикуется |
| Документация | 8/10 | 49+47 файлов, RU/EN sync; периодический drift |
| Расширяемость | 8.5/10 | Custom stacks, skill marketplace, MCP-first дизайн |
| Vendor-neutrality | 6.5/10 | Multi-IDE задумано, enforcement Claude-first |
| Adoption-readiness | 7.5/10 | Production-grade core, marketing-honesty work-in-progress |

**Средняя: 6.95/10.** Сильный pre-2.0 кандидат, не релизный 1.5. Релиз 1.5 близок (Cursor MCP + coverage + doc/code drift baseline — три блокера разрешимы за 1-2 sprint'а). 2.0 потребует RENAR-roadmap + multi-IDE matrix-completion.

---

# Часть II. Конкурентная среда и стандарты

## 5. Карта рынка AI coding tools 2026

### 5.1 6 категорий конкурентов

Из `04-competitive-analysis.md` §1, агрегированно:

**Категория 1 — CLI AI Coding Agents** (прямые конкуренты по форме): Aider (41.6k★), Cline (61.2k★, 5M+ installs), Roo Code, OpenHands (66k users, 53%+ SWE-bench), Goose (Block, 27k★), Continue.dev (32.4k★, 2.5M installs), Cody (Sourcegraph, enterprise-only), Claude Code ($2.5B ARR), Codex CLI (OpenAI, SWE-bench 88.7%), Gemini CLI.

**Категория 2 — IDE-based agents**: Cursor ($2B ARR, $50B val), Windsurf (Cognition, 1M+ active), GitHub Copilot ($10-$39/mo), JetBrains Junie, Zed.

**Категория 3 — Cloud / Autonomous SWE**: Devin 2.0 ($20/mo, $25B val), SWE-agent (Princeton), mini-swe-agent (>74% SWE-bench verified), Sweep AI, Augment Code (Context Engine 500k файлов + Intent Workspace, $20-$200/mo), Replit Agent 4, Bolt.new, v0 (Vercel), Magic.dev, xAI Grok Build.

**Категория 4 — Agent Frameworks**: LangChain/LangGraph, LlamaIndex, AutoGen 1.0 GA, CrewAI, Claude Agent SDK, OpenAI Agents SDK, Google ADK 1.0 (A2A protocol), Semantic Kernel.

**Категория 5 — Rule/Instruction Systems**: Cursor Rules, CLAUDE.md, **AGENTS.md (60k+ репо)**, Claude Skills (55+ official + 72+ community), Aider CONVENTIONS.md, **GitHub Spec Kit (90k★)**.

**Категория 6 — Quality / Governance Layers**: DSPy (28k★), Guardrails AI, LangSmith, LangFuse (MIT + $29/mo), Helicone, Arize AX / Galileo / Opik, Maxim AI, Codacy / CodeScene / Qodo, **TaskMaster AI**.

### 5.2 Топ-15 конкурентов: краткие карточки

Извлекаю самое существенное из 15 карточек `04-competitive-analysis.md` §2 (детали и URL — в Приложении B и в оригинальном файле):

| Продукт | Killer | Threat для TAUSIK |
|---|---|---|
| **Cursor** | Composer + Background Agents, мультимодель, 1M paid | Втягивает discipline как нативную фичу |
| **Claude Code** | CLAUDE.md, Skills marketplace, Hooks, Agent SDK | **Высокая** — самый близкий по форме; если добавит enforced verify + journal — TAUSIK избыточен |
| **GitHub Spec Kit** | Structured spec → tech plan → tasks → AI implementation; 29+ агентов | **Высочайшая** — покрывает 60-70% TAUSIK use cases с дистрибуцией GitHub |
| **Cline** | Plan/Act, 30+ providers | Не пересекается по слою, но пожирает mindshare CLI-ниши |
| **OpenHands** | open generalist, 53%+ SWE-bench, academic credibility | Капабилити layer, не дисциплина |
| **Devin 2.0** | Автономный AI-инженер, $25B val | Антагонист по позиции (hands-off vs hands-on) |
| **Augment Code (Intent)** | Context Engine 500k файлов + Intent Workspace | **Прямой концептуальный конкурент** в enterprise |
| **AGENTS.md** | Универсальный README, 60k+ репо, Linux Foundation | TAUSIK должен **писать AGENTS.md**, не конкурировать |
| **Claude Skills + Plugins** | 55+ official, 72+ community, marketplace | TAUSIK уже использует; угроза — если Skills добавят task tracking |
| **TaskMaster AI** | drop-in PM для всех агентов | **Высокая** — занял ту же поверхность («задачи для агентов»), но без гейтов и verification |
| **DSPy** | Declarative signatures + compiler | Не пересекается (ML framework vs process framework) |
| **LangFuse** | Traces, eval, datasets | Ортогональны (observability vs discipline) |
| **Maxim AI** | Eval + observability + simulation | Ортогональны, но enterprise может хотеть оба |
| **Goose** | Recipes (YAML), MCP-first, 70+ extensions | Если добавит quality gates — прямой OSS конкурент |
| **Continue.dev** | **«Quality control for your software factory»** (буквально слоган), 2.5M installs, MIT | **Позиционирование почти идентично** — нужна тонкая дифференциация |

### 5.3 Сводная heatmap (TAUSIK vs 15 конкурентов)

Из `04-competitive-analysis.md` §3, упрощённо (●●● сильно, ●● присутствует, ● слабо, ○ нет):

| Продукт | QG enforced | Verify-as-code | Task journal | Multi-agent | Memory | Lang-agnostic | Open source | Cost/mo |
|---|---|---|---|---|---|---|---|---|
| **TAUSIK** | ●●● | ●●● | ●●● | ●● | ●●● | ●●● | ●●● | $0 (BYO LLM) |
| Cursor | ○ | ○ | ○ | ●● | ●● | ●●● | ○ | $20-200 |
| Claude Code | ●● | ● | ● | ●● | ●●● | ●●● | ○ | $20-200 |
| Cline | ○ | ○ | ○ | ● | ● | ●●● | ●●● | LLM only |
| Goose | ● | ● | ●● (recipes) | ●● | ● | ●●● | ●●● | LLM only |
| Continue.dev | ●● | ●● | ● | ●● | ●● | ●●● | ●●● | $0-10 |
| Aider | ○ | ● | ○ | ○ | ● | ●●● | ●●● | LLM only |
| Spec Kit | ●● | ●●● | ●●● | agent-agnostic | ●● | ●●● | ●●● | $0 |
| TaskMaster AI | ○ | ○ | ●●● | drop-in | ●● | ●●● | ●●● | $0 |
| AGENTS.md | ○ | ○ | ○ | ●●● | ●●● | ●●● | ●●● | $0 |
| Claude Skills | ● | ● | ○ | ●● | ●●● | ●●● | partial | $0 |
| Maxim AI | ●●● (eval) | ●●● | ○ | observability | ●● | ●●● | ○ | enterprise |

**Чтение таблицы:** TAUSIK — **единственный продукт с тройной сильной позицией (QG enforced + Verify-as-code + Task journal) одновременно**. Spec Kit подбирается ближе всего (●●/●●●/●●●), но не enforced. Это объективная конкурентная позиция, не маркетинг.

### 5.4 Где TAUSIK лидирует

1. **Verify-First Cache + AC-Verified Done** — никто иной не делает сквозной кэш-контракт между verify и done в одном CLI.
2. **SENAR + RENAR как открытые нормативные стандарты** — открытая methodology может стать «AGENTS.md для процесса», как AGENTS.md стал для контекста.
3. **Task lifecycle с journal + dead-end documentation** — TaskMaster даёт задачи, но не журнал шагов; TAUSIK единственный требует логировать каждый шаг.
4. **Open-source + self-host + zero-vendor-lock** — в когорте «discipline»-инструментов (Continue.dev, Augment Intent, Maxim) только Continue.dev открытый и self-host. Continue идёт в IDE — TAUSIK идёт в CLI.
5. **Instrumented agent + cross-tool (MCP-first)** — TAUSIK работает с любым агентом через MCP, может «оборачивать» Claude Code, Cursor (через MCP), Codex, Gemini CLI.

### 5.5 Где TAUSIK отстаёт

1. **Дистрибуция и mindshare** — 0★ публично vs 90k★ Spec Kit, 41k★ Aider, 61k★ Cline.
2. **Ecosystem & integrations** — TaskMaster drop-in для Cursor/Lovable/Windsurf/Roo/Claude Code; TAUSIK преимущественно Claude Code.
3. **Eval/observability native** — Maxim/LangFuse/Galileo дают eval, traces, simulation. TAUSIK — metrics + verify, но не сравним eval-pipeline.
4. **Не-Python экосистема** — Python stdlib — потолок. TS/Go-команды воспринимают «Python CLI» как чужеродный.
5. **Spec-driven не нативный** — Spec Kit прямо называет «spec-driven». TAUSIK имеет goal + AC, но не позиционируется как spec-driven.
6. **Cloud/team-уровень отсутствует** — Multi-developer flows (Roo Code Cloud, Cursor Teams, Augment Enterprise) — у TAUSIK нет.

### 5.6 Топ-3 угрозы обнуления (`04-competitive-analysis.md` §10)

1. **GitHub Spec Kit (90k★, бесплатный, GitHub-спонсорство).** Покрывает ~70% сценариев TAUSIK с гораздо большей дистрибуцией. Главное отличие — Spec Kit описывает _что_ делать, TAUSIK навязывает _как_ + verify. **Но если Spec Kit добавит enforced gates — это сделает TAUSIK маргинальным.**

2. **Claude Skills + Hooks + AGENTS.md (Anthropic ecosystem).** Втягивают discipline в нативный слой Claude Code; если добавят enforced verify + journal — TAUSIK становится избыточным. Уже намечается (Stop hooks, plugin marketplace, Agent SDK credits с 15 июня 2026).

3. **TaskMaster AI (drop-in для всех агентов).** Самый прямой конкурент по форме (CLI + tasks + AI-agent friendly). Не даёт гейтов и verification, но занял ту же поверхность.

### 5.7 Тренды Q1-Q2 2026

1. **Аккумуляция власти у двух exits:** Cognition+Windsurf+Devin ($25B) и Anthropic+Claude Code ($2.5B ARR).
2. **OpenAI vs Cognition vs Anthropic vs Cursor — 4-way war.** xAI Grok Build добавился весной 2026.
3. **AGENTS.md = новый стандарт.** Donated to Linux Foundation Dec 2025; adopted by 60k+ репо.
4. **Skills как формат.** Anthropic Skills spec открыт; OpenAI приняла его для Codex CLI/ChatGPT.
5. **Spec-Driven Development резко поднимается.** Spec Kit 90k★ за полгода; Augment Intent.
6. **Hooks/Stop hooks как способ принудительной проверки.** Тренд внутри Claude Code и других.
7. **Trust crisis.** Stack Overflow 2025: 84% используют AI, 96% не доверяют. Sonar 2026: 42% кода AI, рост до 65% к 2027. Это формирует спрос на discipline layer.
8. **MCP стал нормой.** Все CLI-агенты поддерживают MCP-серверы.
9. **Background/parallel agents** — Cursor, Zed 1.0, Roo Cloud — новая граница UX.

### 5.8 Белые пятна на рынке

1. **Compliance-grade audit trail для AI-кода.** SOC2/HIPAA/PCI требуют evidence-trail. TAUSIK journal + dead-end docs + verify cache — естественный фундамент. Никто open-source этого не закрывает.
2. **Cross-agent governance.** Команда использует Cursor + Claude Code + Copilot одновременно — кто гарантирует, что все играют по одним правилам? AGENTS.md даёт контекст, но не enforcement.
3. **Verification-как-первоклассный-артефакт.** Все хотят verify, но никто не делает её гранулярной и кэшируемой между задачами.
4. **Open-source enterprise discipline.** Augment Intent — SaaS-only. Continue.dev — open IDE, но не CLI. TAUSIK может занять «open-source Augment Intent».
5. **Не-Python first-class CLI** — TypeScript/Go.

---

## 6. SENAR/RENAR в ландшафте мировых стандартов

### 6.1 Карта стандартов: 8 категорий

Из `05-world-standards.md` §1, упрощённо (полная таблица — Приложение C):

| Категория | Ключевые стандарты |
|---|---|
| **SE / методологии** | ISO/IEC/IEEE 12207:2017, 15288:2023, CMMI v3.0, SAFe 6.0, ISO 9001:2015, ISO/IEC 25010:2023 |
| **RE стандарты** | **ISO/IEC/IEEE 29148:2018** (gold standard), IEEE 830-1998 (deprecated), IIBA BABOK v3, **IREB CPRE + AI4RE**, INCOSE SE Handbook v5, Volere Template |
| **AI Governance** | **EU AI Act** (full 2026-08-02), NIST AI RMF 1.0 + GenAI Profile, **ISO/IEC 42001:2023** (AIMS, certifiable), ISO/IEC 23894:2023, **ISO/IEC 5338:2023** (AI life cycle), ISO/IEC TR 24028:2020, OECD AI Principles, IEEE 7000 series |
| **Supply Chain** | SLSA v1.0, SBOM (CycloneDX / SPDX = ISO 5962), in-toto / Sigstore / Cosign, ISO/IEC 5230 (OpenChain) |
| **Safety-critical** | MISRA C/C++, **DO-178C** (avionics), **IEC 62304** (medical), **ISO 26262** (auto), IEC 61508, ISO/IEC 15408 |
| **Российские** | ГОСТ 34.601-90 (legacy), **ГОСТ 34.602-2020**, **ГОСТ Р 56939-2024**, ГОСТ Р 71476-2024 (=ISO 22989), ГОСТ Р 70462.1-2022 (=ISO 24029), Приказ ФСТЭК №240 |
| **Эмерджентные AI-native** | **AGENTS.md** (de-facto, AAIF), **MCP** (Anthropic → AAIF), A2A (Google → LF, 150+ orgs), ACP (IBM, merged в A2A), llms.txt, **GitHub Spec Kit** |
| **Benchmarks** | SWE-bench Verified (contaminated 2026), SWE-bench Pro, LiveCodeBench v6, BigCodeBench, TerminalBench, METR Time-Horizon |

### 6.2 3 главных моста

#### 6.2.1 ISO/IEC/IEEE 29148:2018 — Requirements Engineering (Gold Standard)

- **Скоуп:** Life-cycle RE для systems & software, complement to 12207/15288.
- **Hierarchy:** Stakeholder Requirements (StRS) → System Requirements (SyRS) → Software Requirements (SRS). Это **прямой аналог RENAR BR → SR → TR (1-to-1)**.
- **Совместимость с RENAR:** **ПОЛНАЯ.** RENAR можно позиционировать как 29148-tailored profile для AI-native.
- **Compliance gap:** 29148 не предполагает «agent as stakeholder», не описывает drift detectors, не имеет substrate-agnostic V1-V6 verification levels, не использует RFC 2119 в нормативной форме. RENAR заполняет каждый из этих gaps.
- **Стратегический ход:** опубликовать RENAR ↔ 29148 crosswalk — это бесплатное credibility-bridging для крупных enterprise.

#### 6.2.2 ISO/IEC 42001:2023 — AI Management System (AIMS)

- **Скоуп:** Plan-Do-Check-Act для responsible AI lifecycle. Mirrors ISO 9001 / 27001.
- **Релевантность:** **критическая.** Покрывает ~70% документации EU AI Act high-risk.
- **Совместимость с SENAR:** **ПОЛНАЯ на governance уровне.** SENAR может стать «process implementation reference» под зонтом 42001.
- **Compliance gap:** 42001 — это система менеджмента (политики, роли, аудит). Не описывает **процесс ежедневной разработки** с участием AI-агентов. SENAR заполняет process gap.
- **Сертификация:** certifiable через BSI, A-LIGN, Schellman, KPMG, TÜV SÜD. К 2026 — de-facto AI governance стандарт.

Mapping SENAR на 42001:

| ISO 42001 clause | SENAR artefact |
|---|---|
| §4 Context of organization | CLAUDE.md project context |
| §5 Leadership / AI policy | SENAR ценности + правила |
| §6 Planning / AI risks & impacts | RENAR impact analysis |
| §7 Support (resources, awareness, documented info) | tausik runtime + DB |
| **§8 Operation / AI system lifecycle** | **SENAR loop + QGs (главный угол позиционирования)** |
| §9 Performance evaluation / metrics | SENAR 10 метрик |
| §10 Improvement | dead-ends + retrospective via metrics |

**Вывод:** SENAR — это **operational reference implementation для ISO 42001 §8** для команд, использующих coding agents. Это **самый прибыльный позиционирующий ход на 2026-2027**.

#### 6.2.3 ISO/IEC 5338:2023 — AI System Life Cycle Processes

- **Скоуп:** AI-specific extension к 12207/15288. Интегрирует AI-system lifecycle с classical SE processes (data lifecycle, model training, evaluation).
- **Релевантность:** **критическая для substrate claim.** Единственный стандарт, который явно интегрирует AI-system lifecycle с classical SE.
- **Совместимость с SENAR/RENAR:** **ПОЛНАЯ.** RENAR substrate-agnostic V1-V6 — естественное расширение 5338.
- **Compliance gap:** 5338 описывает AI **system** lifecycle (ML model training, MLOps), а не AI-augmented **dev** lifecycle (human + coding agent). SENAR/RENAR заполняют development loop side.

### 6.3 3 эмерджентных для синхронизации

#### 6.3.1 AGENTS.md

- **Статус:** de-facto convention 2026; AAIF / Linux Foundation governance.
- **Adoption:** 60k+ репо, native parse в Claude Code/Codex/Cursor/Aider/Devin/Copilot/Gemini/Windsurf/Amazon Q.
- **Риск:** если SENAR использует другой формат project-instructions, теряется compatibility с 15+ tools.
- **Рекомендация:** SENAR CLAUDE.md должен быть валидным AGENTS.md либо публиковать AGENTS.md как mirror. **Это must-do для distribution.**

#### 6.3.2 MCP (Model Context Protocol)

- **Статус:** de-facto industry standard 2026; AAIF governance.
- **Adoption:** 78% enterprise AI teams с MCP в production (Apr 2026), 9,400+ servers; нативная поддержка Claude, ChatGPT, Gemini API, Vertex AI, Cursor, Windsurf, JetBrains AI, Vercel AI SDK, OpenAI Agents SDK.
- **Релевантность:** TAUSIK уже использует MCP. **Continue MCP-first, publish TAUSIK MCP server spec.**

#### 6.3.3 GitHub Spec Kit

- **Статус:** OSS Sept 2025, активный рост; 30+ AI tools.
- **Риск:** **средний** — overlap со spec-driven частью RENAR.
- **Различие:** Spec Kit = tool + light convention, без RFC 2119, без drift detectors, без substrate-agnostic. RENAR = normative standard + ADAPT + V1-V6.
- **Рекомендация:** позиционировать RENAR как «normative layer ON TOP of Spec Kit», не replacement.

### 6.4 РФ-стандарты — отдельная глава

Из `05-world-standards.md` §5:

| Стандарт | Год | Релевантность для SENAR/RENAR |
|---|---|---|
| ГОСТ 34.601-90 | 1990 | Legacy, обязателен для госзаказа |
| **ГОСТ 34.602-2020** | 2022-01-01 in force | **ТЗ структура — direct mapping для RENAR ADAPT** |
| РД 50-34.698-90 | 1990 | Содержание документов АС. Legacy, used in gov |
| ГОСТ Р 59792-2021 | 2021 | Виды испытаний АС. Маппится на SENAR QG-3 |
| **ГОСТ Р 56939-2024** | 2024-12 | **Secure dev — обязателен для СЗИ.** Маппится на SENAR Verify + Security gates |
| ГОСТ Р 71476-2024 (=ISO 22989) | 2025-01-01 | AI terminology. SENAR/RENAR должен использовать его термины |
| ГОСТ Р 70462.1-2022 (=ISO 24029-1) | 2022 | NN robustness assessment. Optional для RENAR robustness SPEC |
| ГОСТ Р 59277-2020 | 2020 | AI systems classification |
| **ФСТЭК Приказ №240** (с изм. №230 от 2025-06-30) | 2023 → 2025 | Сертификация процессов БРПО на базе ГОСТ 56939-2024. **Обязательно для СЗИ** |

**Стратегическая рекомендация:** позиционировать SENAR как «AI-native процесс разработки, совместимый с ГОСТ Р 56939-2024 и ГОСТ 34.602-2020». Это открывает enterprise + госсектор рынок без альтернатив.

### 6.5 EU AI Act / NIST AI RMF / ISO 42001 compliance mapping

#### 6.5.1 EU AI Act high-risk requirements (Annex IV) ↔ SENAR/RENAR

| EU AI Act требование | SENAR/RENAR покрытие |
|---|---|
| Technical documentation (Art. 11 + Annex IV) | RENAR ADAPT + SENAR project DB exports |
| Risk management system (Art. 9) | SENAR QG-3 + ISO 23894 mapping |
| Data governance (Art. 10) | Out of scope (ISO 42001) |
| Transparency (Art. 13, 50) | RENAR SPEC types include traceability + ADAPT |
| Human oversight (Art. 14) | SENAR QG-0 Context Gate + role= required |
| Accuracy/robustness/cybersecurity (Art. 15) | SENAR Verify-First + ISO 56939 (RU) |
| Quality management system (Art. 17) | ISO 42001 / 9001 — **SENAR sits inside QMS** |
| Conformity assessment (Art. 43) | SENAR audit trail (task DB + events log) supports |

#### 6.5.2 NIST AI RMF functions ↔ SENAR/RENAR

| NIST function | SENAR/RENAR |
|---|---|
| Govern | SENAR roles + custom_stacks + ценности |
| Map | RENAR BR/SR/TR + ADAPT |
| Measure | SENAR 10 метрик + METR time-horizon |
| Manage | SENAR QGs + drift detectors |

### 6.6 Compliance matrix (полная таблица)

| SENAR/RENAR концепт | Стандарт | Статус совместимости |
|---|---|---|
| 5 ценностей SENAR | OECD AI Principles, NIST RMF Govern, ISO 42001 §5 | **Полная (values сходны)** |
| 15 правил SENAR (RFC 2119) | ISO 42001 Annex A controls | Adapter required |
| 5 QGs (QG-0…QG-4) | DO-178C verification objectives; ISO 5338 review/verify | **Полная (concept-level)** |
| SENAR 10 метрик | NIST RMF Measure; ISO 42001 §9; METR time-horizon | **Полная** |
| Verify-First (QG-2) | DO-178C MC/DC; ISO 26262 ASIL verification | **Полная (concept), partial (rigor)** |
| RENAR BR/SR/TR | ISO 29148 StRS/SyRS/SRS; ГОСТ 34.602-2020 | **ПОЛНАЯ (direct 1-to-1)** |
| RENAR ADAPT artefact | EU AI Act Annex IV «technical documentation»; ISO 42001 §7.5 | **Высокая (candidate doc)** |
| 9 SPEC types | ISO 25010:2023 9 quality characteristics; INCOSE SEH v5 | **Полная (NFR), partial (functional)** |
| Substrate-agnostic V1-V6 | ISO 5338 + ISO 29148 | **Расширение (no precedent)** |
| Drift detectors | ISO 23894 AI risk continuous monitoring | **Расширение (RENAR — implementation)** |
| TAUSIK runtime | MCP protocol, AGENTS.md | **Полная** |
| Agent as stakeholder | ISO 29148 (extended) | Нужна формальная extension claim |

### 6.7 Главное белое пятно

**Substrate-agnostic нормативный стандарт для AI-native development loop с явными QGs и метриками SENAR-style — не существует.** 

- ISO 42001 — про governance системы, не про процесс разработки.
- ISO 5338 — про life-cycle AI системы, не про human+agent loop.
- GitHub Spec Kit — tool, не standard.
- AGENTS.md / MCP / A2A — protocols, не process.
- IREB CPRE / BABOK — human-native RE, не AI-native.

RENAR substrate-agnostic V1-V6 — это **honest first-of-kind**. SENAR + RENAR заполняют четыре gap’а одновременно: process discipline + AI-native RE + substrate-agnostic + RFC 2119 normativity.

### 6.8 Тренды стандартизации 2024-2026

1. **Конвергенция AI governance под зонтом ISO 42001 + EU AI Act.** К 2026-08 это de-facto обязательный стек для high-risk AI на EU рынке.
2. **Linux Foundation как dominant governance body для AI-native protocols** (AGENTS.md, MCP, A2A, AAIF created Dec 2025).
3. **Spec-driven development стал mainstream.**
4. **Бенчмарки потеряли доверие из-за contamination** (SWE-bench Verified deprecated by OpenAI Q1 2026). Сдвиг к contamination-free (LiveCodeBench v6, SWE-bench Pro).
5. **METR time-horizon doubling accelerated** (4 месяца в 2025-26 vs 7 в 2019-25).
6. **ISO/IEC 5338 + 29148 + 42001 = «the AI development trinity»** к 2026.
7. **Российские стандарты AI оформляются как identical adoption ISO** (ГОСТ Р 71476 = ISO 22989, 70462 = ISO 24029). Это снижает барьер для cross-jurisdiction compliance.
8. **DORA report 2025 показал negative correlation AI adoption ↔ delivery stability.**
9. **«AI-native SDLC» как явная категория** (EPAM, Intetics, Xebia публикации 2026).
10. **CMMI и SAFe мигрируют в AI direction**, но без normative AI-native discipline. Gap для SENAR.

### 6.9 Рекомендация: Linux Foundation AAIF

Из `05-world-standards.md` §8, главный вывод:

**Не подавать в ISO TC прямо** (1-3 года, дорого) и **не в IEEE 7000** (ethics scope). Оптимально — **Linux Foundation AAIF (Agentic AI Foundation)**, где уже сидят AGENTS.md, MCP, A2A. SENAR/RENAR заходит как complementary «process & RE» слой к этим protocol-стандартам.

**Альтернатива** — **OpenJS Foundation** (если SENAR/RENAR сделают JS/TS implementation первой). OpenJS даёт быстрее governance структуру + dev-friendly community. Решение зависит от первичной аудитории (multi-language → AAIF; JS-first → OpenJS).

**Финальный совет:** AAIF — оптимальный путь. Опционально продублировать в W3C Community Group для веб-видимости (RENAR especially).

---

# Часть III. Honest assessment

## 7. Что мы сделали хорошо

### 7.1 5 уникальных мировых инноваций (только наши)

1. **Verification-as-Cache contract в TAUSIK.** `task done --ac-verified` физически читает кэш `verify --task <slug>` (10-min TTL + files_hash + git-diff cross-check + security bypass). Ни Cursor, ни Claude Code, ни Spec Kit, ни TaskMaster — никто другой не делает сквозной кэш-контракт между verify и done в одном CLI (`03-tausik-audit.md` §"Killer feature", `04-competitive-analysis.md` §4.1).

2. **ADAPT artefact в RENAR.** Bridge artefact между immutable ТЗ и BR/SR/SPEC с forward + backward + dual signature + delta workflow + errata. Похожие artefacts есть в RUP/BABOK/SAFe, но никто не нормирует с closed list 7 категорий findings + sub-state machine + mandatory double-signature (`02-renar-analysis.md` §4.2).

3. **Substrate-agnostic V1-V6 с negative proof.** Capability list для versioning systems с математическим обоснованием «без V_i невозможно X». Academic-grade reasoning, отсутствующее в IEEE 42010 / arc42 / CMMI CM SG2 (`02-renar-analysis.md` §7.2).

4. **Adversarial Detection Rate (ADR) + L3 Adversarial Review в SENAR.** Обязательная независимая проверка cold-агентом + метрика плотности скрытых дефектов с формулой и таргетом. Первая нормативная operationalization adversarial AI review (`01-senar-analysis.md` §4).

5. **Agent Profiles + Separation of Duties между AI-агентами.** «Reviewer SHALL NOT have write access to the artifacts being reviewed» — прямой импорт ISO 27001 SoD, применённый внутри AI-агентов. Никто другой не нормирует SoD между AI (`01-senar-analysis.md` §2.3).

### 7.2 5 хороших но не уникальных решений

6. **AI Model = External Supplier (ISO 9001 framing) в SENAR `10.13`.** Не уникально концептуально (supplier risk mgmt — классика ISO 9001), но **первое применение к AI-модели**. Это даёт organizations языковую основу для управления риском смены модели.

7. **First-Pass Success Rate (FPSR) как primary metric.** Прямой импорт First Pass Yield из бережливого производства, адаптированный к non-deterministic LLM output. Не уникально как concept, но как «primary metric для AI dev» — да.

8. **Quality Gates as Code (TAUSIK + SENAR `8.6(a)`, `5.4.3`).** DoR/DoD из Scrum существуют, но они **manual**. TAUSIK реализует quality gates as executable code с hard enforcement.

9. **Dead End mandatory documentation (15 min threshold).** Идея сохранения отрицательных результатов — классика lessons learned, но **обязательность с конкретным threshold** — нормативная инновация.

10. **2-axis skill variants в TAUSIK** (IDE × model). Никто из открытых систем (Cursor Rules, Claude Skills, Continue Rules) так не делает.

### 7.3 5 вторичных преимуществ

11. **Gap-based active time для session limit (TAUSIK).** Не наивный wall-clock, а clip AFK до 10 min — единственная индустрия, кто это делает правильно.

12. **Project memory с FTS5 + graph edges + re-injection в каждую сессию.** Архитектурно сильнее, чем CLAUDE.md / Cursor Rules.

13. **16 closed lists с master index (RENAR §1.7.5).** Структурно сильная защита от расползания artifact types. Единственный стандарт в индустрии, где closed list policy применяется системно.

14. **9 SPEC types closed list с явным обоснованием 7 исключений (`§8.3.1`).** Best practice ISO TC discipline, отсутствующая в arc42.

15. **TC pos/neg парность + judge ≠ production isolation + защита от test-fitting через `[test-spec-change]`** — три механизма, отсутствующие в ISO/IEC/IEEE 29119, формирующие первую normative защиту от AI-driven test fitting.

---

## 8. Что мы сделали плохо или сомнительно

### 8.1 Методологические провалы

1. **N=1 эмпирическая база (SENAR).** Все количественные ориентиры (180 мин session, 15 мин dead end, 3 parallel agents, FPSR 50-65% → 80-90%, ADR < 0.5) выведены из одной организации, одного семейства моделей, 552 задач (`00-introduction.md:71-75`). Авторы это признают, но это критичный блокер для ISO TC.

2. **Метрики «с потолка» (RENAR).** Hallucination Rate ≤ 1% на RENAR-5, RDLT < 4h, DRA ≤ 2% — взяты теоретически (`research/04-metrics-and-outcomes.md` §8 явно признаёт: «бенчмарк по индустрии нужен»). Multi-model Disagreement Rate threshold 15% — open question в research/02 §4.

3. **L4-L5 maturity aspirational (SENAR `12-maturity-model.md:18`).** Верхняя половина модели зрелости — гипотетическая, не валидированная. Это либо неосознанная калька CMMI L4-L5, либо сознательное наследование без resolution.

4. **Cost Predictability как SHALL противоречит признанию авторов о ненадёжности** (`09-metrics.md:43`: «planned cost estimation for AI-assisted tasks is unreliable»).

5. **Hallucination Rate не выделена в отдельную метрику SENAR.** При том, что это **главный** failure mode AI-кода, в SENAR упоминается только как pattern check в QG-3 AI Output Review.

### 8.2 Implementation gap

6. **RENAR-0 implementation на самом kai.** Боевой манифест `kai/RENAR-CONFORMANCE.yaml` фиксирует уровень RENAR-0 (pre-adoption) даже на референсной команде Kibertum. 7 из 8 drift detectors не реализованы (`02-renar-analysis.md` §1.4, `03-tausik-audit.md`). Claim conformance к RENAR-4 на момент v0.1-draft физически невозможен.

7. **TAUSIK SENAR Rules 4 и 6 не имплементированы.** В `docs/ru/senar.md` явно: «Правила 4-6 существуют в спецификации, но пока не применяются». `/review` — внутренний 6-агентный pipeline, но «external» в SENAR-смысле (другой агент с другим контекстом) покрывается только `tausik-reviewer` opt-in.

8. **JSON Schema файлы RENAR отсутствуют.** `reference/02-schemas.md` §12 имеет single fragment example, но sub-folder `reference/schemas/` помечен TODO Phase 8. Без них валидатор frontmatter невозможен, RENAR-3 enforcement остаётся декларативным.

### 8.3 Терминологические проблемы

9. **«ТЗ» (Task Requirement) в русской редакции SENAR конфликтует с «техническое задание».** В русской инженерной культуре «ТЗ» — это документ верхнего уровня. Здесь же ТЗ обозначает атомарное Task-уровневое требование. Может вводить в заблуждение.

10. **Forbidden terms (`RENAR §3.14`)** — «User Story», «Use Case», «Feature», «Эпик» все запрещены. SAFe-команды привыкли называть свои SR «Features», и принуждение к ребрендингу — organizational overhead, барьер adoption.

11. **«Adversarial Detection Rate» конкурирует с «Anomaly Detection Rate».** Возможна путаница; рекомендую переименовать в LDR (Latent Defect Rate) или AdvRR.

12. **Reference glossary не sync с normative terms.** `reference/01-glossary.md` дублирует часть `standard/03-terms.md`, но не все 44 normative термина есть в глоссарии. Типовая ISO-аудит-проблема.

### 8.4 Технический долг TAUSIK

13. **Doc/code drift baseline.** Один внутренний аудит нашёл 58 defects (32 WRONG + 22 DRIFT) по schema/gates/hooks/cli/mcp в v1.4.1. Сам факт того, что 4-агентный аудит был необходим — индикатор, что dogfooding не покрывает doc consistency полностью. v1.4.2 ввёл `gen_doc_constants.py --check`, но это компенсирующий контроль.

14. **PostToolUse latency 300-480 ms не задокументирована.** 6 хуков на каждый tool call, каждый — отдельный subprocess (cold start 50-80 ms). На 200-call сессии = 60-96 секунд накладных расходов.

15. **`shell=True` в `gate_command_runner.py:75`** для команд с `|`/`&&`/`>>`/`2>&1`. Потенциальный command injection через custom stacks (`.tausik/config.json`).

16. **Coverage % не публикуется.** Badge «3400 tests passing» не отражает реальное покрытие. После v14c-mass-parametrize-batch-1 удалено ~125 дубликатных тестов; реальная behavior coverage ниже raw count.

17. **«13 stacks» в маркетинге vs 25 в `DEFAULT_STACKS`.** README drift регулярный.

18. **No SBOM / signed releases.** Vendor skill auto-install скачивает arbitrary code без content verification.

19. **SQLite scaling cliff на 20k+ задач.** Schema_v27 это не задумывала. fts_* triggers на 10k+ становятся заметны.

20. **Asymmetric `--force`.** `task done` без `--force` (правильно), но `task start --force` есть — может быть exploit'ом если агент через scope bypass обходит QG-0.

### 8.5 Marketing проблемы

21. **Нет telemetry.** Без telemetry нет defensible metrics. «10K installs в 6 months» — невозможно подтвердить.

22. **Нет community.** 0 публичных GitHub stars vs 90k у Spec Kit, 41k у Aider, 61k у Cline.

23. **RU residency блокирует US/EU institutional capital** (CFIUS, regulatory concerns).

24. **Naming.** «TAUSIK» не запоминаемо; cyrillic backronym («Технический Агент Унифицированного Сопровождения, Инспекции и Контроля») видим только в RU-доках. Для EN-аудитории нет meaning.

### 8.6 Спорные архитектурные решения

25. **13 mixin'ов в TaskMixin (TAUSIK).** Потенциально хрупкая MRO. Если завтра нужно добавить hook между QG-2 и cache-write — придётся искать, в каком из 13 mixin'ов.

26. **Memory 4-tier UX.** Архитектурно сильно, но onboarding-документация недостаточно объясняет «зачем 4». Agent с непустой auto-memory путается.

27. **ADAPT 6 состояний + dual signature — много для маленьких проектов.** 2-3 рабочих дня overhead на 5 SR. Даже автор не запускает full ADAPT lifecycle на core-tier.

28. **RENAR `core/renar-core.md`** — explicit acknowledgment, что full RENAR не для всех. Сужает применимость значительно.

29. **Prompt Injection Defense (SENAR `5.5`)** содержит SHALL без verifiable test method. Нет референс-датасета (HackAPrompt, GenAI Red Team taxonomy).

30. **Security tools в QG-2 не нормированы** — «no security vulnerabilities detected by scanning tools» без specifying scanner. Gate-bypass-готовое место.

---

## 9. Риски (top-10 ранжированных)

| # | Риск | Likelihood | Impact | Категория | Mitigation |
|---|---|---|---|---|---|
| **1** | **Linux Foundation AAIF (Anthropic+OpenAI+Block) добавит process layer как 4-й primitive до того, как мы получим distribution** | Med | **Critical** | Стандартизационный | Apply for AAIF working group ASAP (Q3 2026); position SENAR как complementary, не competing |
| **2** | **AGENTS.md / Skills становятся универсальным стандартом разметки** — если в стандарт зашьют `verify:` и `gates:` — кастомный CLI окажется не нужен | High | High | Рыночный | Differentiate hard: AGENTS.md = static; TAUSIK = runtime gates. «AGENTS.md compatible» badge |
| **3** | **GitHub Spec Kit (90k★) добавит enforced gates** — это сделает TAUSIK маргинальным | Med | High | Рыночный | Build relationship; co-existence statement; позиционировать как «runtime для Spec Kit specs» |
| **4** | **Russian residency блокирует US/EU enterprise procurement** (CFIUS, regulatory) | High | High | Юридический | Re-domicile EU/UAE/Cyprus к Q1 2027; ИЛИ partner via white-label; ИЛИ Russian PE/grant route |
| **5** | **Open-source-without-revenue founder burnout 12-18 months** (86% OSS maintainers unpaid; Tailwind reported -80% revenue из-за AI eating docs traffic) | High | **Critical** | Финансовый | Paid consulting с месяца 1; никогда >6 месяцев без paying engagement; GitHub Sponsors + Open Source Endowment ($750K committed) |
| **6** | **Cursor/Claude/Cognition нативно реализуют quality gates + journaling** в своих IDE | Med | High | Рыночный | Stay tool-agnostic; emphasize open + audit-grade (vendor-neutral logs); их gates не будут vendor-neutral |
| **7** | **SQLite scaling cliff на 20k+ задач** — schema_v27 это не задумывала | Low (12-mo), Med (24-mo) | Med | Технический | Migration plan: partition by archived_at; partial index optimization; eventually PostgreSQL backend |
| **8** | **Supply-chain через vendor skills без SBOM/signed releases** — содержит arbitrary code | Low | High | Технический/Security | Sign releases (Sigstore); CycloneDX SBOM; content-hash для vendor skill auto-install |
| **9** | **EU AI Act / NIST RMF создают competing normative language**, заменяющий нашу терминологию в C-suite vocab | Med | High | Стандартизационный | Map SENAR/RENAR controls 1-to-1 to ISO 42001 + EU AI Act Annex IV + NIST RMF; никогда не конкурировать, всегда overlay |
| **10** | **Standard fatigue** — девелоперы roll eyes на «yet another framework/standard» | Med | Med | Маркетинговый | Lead with measurable evidence (SWE-bench delta, defect-density delta); never lead with «our methodology»; ride DORA 2025 reference framing |

**Honorable mentions:** (11) Russian sanctions tightening блокируют GitHub/Stripe/Discord access; (12) Anthropic acquires Spec Kit или похожее и bundle'ит free; (13) AI bubble correction режет dev-tools spend H2 2026; (14) GDPR / data residency проблемы для cloud features.

---

## 10. Уникальное позиционирование

### 10.1 Что TAUSIK/SENAR/RENAR могут сказать про себя ЧЕСТНО

1. **«Первый формальный нормативный стандарт SDD для AI-native dev».** RENAR — единственный publish’ed normative SDD стандарт в 2026. GitHub Spec Kit / Augment Intent / Kiro / BMAD — это vendor tools, не стандарты.

2. **«Verification-as-Cache contract — единственный продукт, где AI агент физически не может врать done».** Объективная техническая позиция, не маркетинг.

3. **«Substrate-agnostic с negative proof».** RENAR §11.2 даёт математическое обоснование «без V_i невозможно X». Academic-grade reasoning, отсутствующее у всех конкурентов.

4. **«RFC 2119 в эпоху AGENTS.md tutorials».** SENAR/RENAR — единственный комплект, который пишется как ISO TC документ, а не как blog post.

5. **«Open-source, BYO-LLM, zero vendor lock».** В когорте discipline-инструментов (Continue.dev, Augment Intent, Maxim) только Continue.dev открытый и self-host. Continue идёт в IDE — TAUSIK идёт в CLI. TAUSIK уникален как «open-source CLI discipline layer».

### 10.2 One-liner positioning statements

- **SENAR** — *«The IEEE/ISO of AI-native software development — versioned, normative, citable.»*
- **RENAR** — *«Requirements engineering when the implementer is an agent, not a human.»*
- **TAUSIK** — *«AI agents that can't fake done. Open-source enforcement gates for Claude Code, Cursor, and beyond.»*

### 10.3 Anti-positioning (что мы НЕ)

- Мы **не Cursor killer.** Cursor — IDE; мы — discipline layer поверх.
- Мы **не autonomous AGI orchestrator** (Devin / Magic). Мы keep human-in-the-loop.
- Мы **не no-code платформа.** Мы предполагаем professional devs.
- Мы **не yet another AI framework** (LangChain/LangGraph). Мы над framework — мы process.
- Мы **не AGENTS.md replacement.** Мы process-profile, который использует AGENTS.md как context contract.
- Мы **не SAFe конкурент.** SAFe — human-team scaling; мы — AI-native dev loop. Комплементарны.
- Мы **не IREB CPRE замена.** RENAR — AI-native RE; IREB — human-native RE. Комплементарны.
- Мы **не ISO 42001 замена.** TAUSIK = implementation evidence; SENAR/RENAR = methodology layer; ISO = governance layer. Stackable.

---

# Часть IV. Куда дальше

## 11. Технический roadmap (24 месяца)

### Q3 2026 (июнь-август) — Foundation + first signal

**Цель:** 500 GH stars, 50 telemetry-active installs, 3 conf talks accepted, 1 paid pilot signed.

| Продукт | Ключевые поставки |
|---|---|
| **SENAR** | Глобальные R-ID (`SENAR-STD-R-NNN`); resolution 2-3 противоречий (sequential vs flexible, Foundation Ceremonies vs §6.5, Cost Predictability SHALL→SHOULD); sync глоссария с normative terms; формальная language sanity check |
| **RENAR** | JSON Schema файлы для всех артефактов (`reference/schemas/`); 2 из 8 drift detectors реализованы (drift-1 schema, drift-7 TC↔req provenance); v0.2-draft с changelog; research↔public cross-reference reconciliation |
| **TAUSIK** | **Cursor MCP rework** (composer/workspace MCP filesystem mirror); coverage badge через pytest-cov; doc/code drift cross-file scanner (расширить `gen_doc_constants.py --check` на stack/hook/subagent counts); **telemetry-opt-in build** (privacy notice + Plausible-style metrics); **v1.5 release** |

### Q4 2026 (сентябрь-ноябрь) — Distribution + monetization seed

**Цель:** 2K GH stars, 300 active installs, 3 paid pilots running, $80K revenue.

| Продукт | Ключевые поставки |
|---|---|
| **SENAR** | v1.4 с R-IDs published; IREB workshop submission; hallucination rate как 11-я метрика; Maturity L4-L5 в Informative Annex; Foundation Plus (промежуточная конфигурация) |
| **RENAR** | 3+ pilot adoptions started (через TAUSIK consulting engagements); v0.3-draft; 4 из 8 drift detectors; substrate-specific tool guides для Iceberg / DVC (расширение §11.4) |
| **TAUSIK** | SQLite migration plan (partition by archived_at; partial indexes); supply-chain signing (Sigstore); SBOM (CycloneDX); secondary IDE support (Continue.dev MCP bridge); SENAR Rule 4 (named subagent `tausik-external-reviewer` на другой модели); JetBrains AI Assistant integration spike |

### Q1 2027 — Pro tier launch + entity move

**Цель:** 5K GH stars, 800 active installs, Pro tier soft-launch ($15K MRR), legal entity decision.

| Продукт | Ключевые поставки |
|---|---|
| **SENAR** | v2.0 RC с N≥3 validation (через pilot data из 3 RENAR adoptions); AAIF application accepted; ISO 29148 crosswalk опубликован |
| **RENAR** | v1.0 release; assessor accreditation модель (§14.6); 6 из 8 drift detectors; SPEC-EVT для event-sourcing добавлен |
| **TAUSIK** | 2.0 release с RENAR primitives (reasoning_steps table, `tausik_reason_step` MCP tool, `/reason` skill, `task replay` команда, model-version-pinning per task); multi-agent dispatch isolation; SENAR Rule 6 (Rollback Planning); Pro tier launch |

### Q2 2027 (март-май) — Enterprise pilot wave

**Цель:** 10K GH stars, 2K active installs, 3 enterprise pilots ($150K+ each).

| Продукт | Ключевые поставки |
|---|---|
| **SENAR** | Informational RFC submitted в IETF Independent Submission; SENAR Practitioner Level 2 cert |
| **RENAR** | v1.1 с расширенной substrate matrix (ClickHouse / Delta Live Tables / Snowflake / Kafka); ML-DATA SPEC |
| **TAUSIK** | 2.1 multi-IDE polish (Cursor parity 90%+); SaaS Pro tier (Tausik Cloud lite); Drata/Vanta/Lorikeet integration listing; ISO 42001 evidence pack для compliance; first enterprise deployment ready (on-prem, SOC2-aligned, RU sovereign + EU sovereign variants) |

---

## 12. Go-to-market план (24 месяца)

### 12.1 Market sizing

| Layer | 2026 |
|---|---|
| TAM AI coding tools total | $16.1B revenue 2026 → $79B by 2031 (Mordor Intelligence) |
| TAM narrow (AI code assistants) | $4.5-5.5B (Gartner) |
| SAM (AI agent discipline/governance) | $400-600M |
| SAM RU | $60-90M |
| **SOM TAUSIK 24-mo target** | **$1.5-3M ARR-equivalent** (consulting + training + open-core) |

### 12.2 ICP — 12 карточек (3 продукта × 4 размера)

#### TAUSIK
| Сегмент | Pain | Buying | TAUSIK fit | LTV/CAC |
|---|---|---|---|---|
| **A1. Solo dev** | «AI пишет 80% кода, 30% дня re-reading и fixing» | $0-20/mo | Free OSS, community engine | ~$0 revenue, attention LTV high |
| **A2. Small team 2-10** | Agent quality uneven across teammates | $20-100/seat | Free OSS + **Team Tier $15-25/seat/mo** | **8-15×** — highest |
| **A3. Mid-market 10-100** | EU AI Act Art. 50 audit | $5K-50K/yr | **Enterprise Tier $25-75K/yr** + paid impl $30-80K | 4-6× |
| **A4. Enterprise 100+** | Cannot mass-deploy Cursor без governance | $100K-1M+ | Compliance Pack + Audit Services $150K-500K/yr | 2-3× (через partner) |

#### SENAR
| Сегмент | Pain | Buying | Fit |
|---|---|---|---|
| **B1. Tech-lead / senior IC** | Already convinced of SDD | $0 → cert $300-500 | Free spec + paid certification |
| **B2. Eng manager (small)** | Trying to standardize AI use across 5-15 people | $500-5K (workshop) | SENAR workshop + TAUSIK setup |
| **B3. CIO/CTO mid-market** | «AI transformation methodology» | $20-100K (consulting) | **License SENAR to integrator $20-50K/yr + train-the-trainer $30-80K** — **6-10×** |
| **B4. Big consultancy (Accenture/Deloitte/EPAM, ЛАНИТ/Croc)** | OEM license + co-branded training | $100K-1M | OEM partnership |

#### RENAR
| Сегмент | Pain | Buying | Fit |
|---|---|---|---|
| **C1. BA / PM individual** | No normative framework | $0 → cert $300 | Free draft + RENAR Foundation cert |
| **C2. BA team / product team** | BABOK-trained, struggling to integrate AI | $5-15K | RENAR templates + TAUSIK MCP for spec gates |
| **C3. Enterprise architect** | Owns AI architecture council | $30-100K | Substrate-agnostic capability framework |
| **C4. Government РФ** | ГОСТ-aligned methodology | ₽5-30M (grant/контракт) | Co-author ГОСТ Р based on SENAR/RENAR (Минцифры/ТК164) |

### 12.3 Каналы — приоритизированная таблица

| Канал | Effort | Cost | 1-mo | 3-mo | 12-mo | Priority |
|---|---|---|---|---|---|---|
| **Show HN** (с SWE-bench delta) | Med | Low | high | med | low | **P0** |
| **Habr deep article** (с числами) | Med | Low | high | high | high | **P0** |
| **Awesome-lists PRs** (5-8 lists) | Low | None | high | med | low | **P0** |
| **Claude Code Marketplace** (160K MAU) | Med | None | high | high | high | **P0** |
| **HighLoad++ SPb CFP** | Med | Med (travel) | none | high (talk) | high | **P0** (urgent) |
| **AI Engineer Summit Europe CFP** | Med | Med | none | high | high | **P0** |
| **Linux Foundation AAIF** | Med | $5-15K | low | med | very high | **P0** |
| **Discord + ru-TG** | High (founder time) | Low | high | high | high | **P0** |
| **Reddit** (r/ClaudeAI, r/cursor, r/programming) | Med | Low | low | med | high | P1 |
| **Dev.to / Medium / Substack** | Med | Low | low | med | high | P1 |
| **X (Twitter)** + tag @karpathy | Med | Low | low | med | med-high | P1 |
| **LinkedIn** (C-level case studies) | Med | Low | low | low | med | P1 |
| **TAdviser SUMMIT** (RU C-level) | Med | Med-High | med | high | high | P1 |
| **Latent Space / Practical AI / SE Daily podcasts** | Med | Low | low | med | med-high | P2 |
| **YouTube** (5-min demo + long-form quarterly) | High | Low-Med | low | low | med | P2 |
| **Product Hunt** | Med | Low | spike | residual | low | P2 (save for v2.0) |

### 12.4 Контент-план первых 6 месяцев

| Month | Pillar 1 (technical) | Pillar 2 (cultural) | Pillar 3 (enterprise) |
|---|---|---|---|
| **Jun 2026** | TAUSIK vs Spec Kit vs BMAD: 50 SWE-bench tasks measured | Why vibe coding can't be fixed with prompts (it needs gates) | Mapping TAUSIK gates to ISO 42001 Annex A controls |
| **Jul 2026** | Claude Code + TAUSIK: how QG-2 cache works under the hood | What Karpathy got right about agentic engineering | EU AI Act Art. 50 for code repos: a checklist |
| **Aug 2026** | MCP server for TAUSIK: every gate as a tool | Open-source standards vs vendor standards: why SENAR matters | DORA 2025 7 capabilities ↔ SENAR practices, mapped |
| **Sep 2026** | RENAR draft 0.2: substrate-agnostic capabilities walkthrough | Why AGENTS.md is necessary but not sufficient | The audit log every CISO needs for AI-generated code |
| **Oct 2026** | Building your own QG profile (custom verification gates) | What we got wrong: 6 dead-ends from 1500 dogfood tasks | Pilot results from [partner] — 6 weeks before/after |
| **Nov 2026** | TAUSIK + Continue + Cline: composing 3 tools | Standard fatigue is real — how SENAR avoids it | NIST AI RMF Agentic Profile (Q4 2026) and TAUSIK |

### 12.5 Партнёрства — 5 lateral attacks

1. **Linux Foundation AAIF.** Apply Q3 2026 для process profile WG. Ask: «Process Profile WG для AGENTS.md». Give: spec contribution + neutral governance. Time: 9-12 mo.
2. **Drata / Vanta / Lorikeet (compliance vendors).** TAUSIK audit-log → Drata-compatible export. Ask: listing. Give: ISO 42001 evidence pipe для их customers.
3. **ЛАНИТ / Croc / AT-Consulting (RU consultancies).** OEM SENAR + co-branded training. Give: 30% rev-share. Time: 6-12 mo.
4. **IREB AI4RE workshop.** RENAR становится reference reading для AI4RE 2027 micro-credential. Academic credibility, не revenue.
5. **Cursor partnership (MCP integration).** «TAUSIK MCP server как default optional gates plugin». Give: distribution. Ask: free Pro tier.

### 12.6 Монетизация — 4 сценария

| Scenario | Year 1 rev | Year 2 rev | Verdict |
|---|---|---|---|
| **A. 100% open-source + consulting/training** (Sourcegraph/HashiCorp early days) | $80-150K | $400-700K | **Default start** для M1-12 |
| **B. Open core + Pro features** (GitLab/Sentry) — Core free, Pro $15-25/seat/mo, Enterprise $75-500K/yr | $20-60K | $300-900K | **Target для M9-12 transition** при telemetry >2K active orgs |
| **C. SaaS layer** (LangFuse/Helicone) | — | — | **Skip for now** (Helicone went into maintenance mode Mar 2026 — cautionary tale) |
| **D. Certification / Education** (IREB/SAFe model) — €310/exam × 1000/yr = €310K | $20-40K | $150-300K | **Parallel track from M6** |
| **E. Audit/compliance services** | — | — | M12+ via partner co-marketing |

**Recommended blend:**

| Период | Mix |
|---|---|
| M1-M6 | 100% A — get to $30-60K revenue |
| M7-M12 | 70% A + 20% B + 10% D — $100-200K |
| M13-M18 | 40% A + 35% B + 15% D + 10% E — $300-600K |
| M19-M24 | 25% A + 45% B + 15% D + 15% E — $700K-1.5M |

### 12.7 Конкурентное позиционирование (head-to-head)

| Competitor | Their game | Our differentiator | Don't-compete-on |
|---|---|---|---|
| **Cursor / Anysphere** ($50B) | IDE + UX + speed | Audit layer они не шипят | UX, model price |
| **Cognition / Devin** ($25B) | Autonomous SWE-bench | Human-in-loop; для teams, не replacing devs | full autonomy |
| **Claude Code** | Reference agent runtime | Комплементарны — harness на top | model quality |
| **GitHub Spec Kit** (90k★) | Spec-driven template CLI | Spec Kit = template; SENAR = normative spec; TAUSIK = enforced | template count |
| **AWS Kiro** | All-in-one SDD IDE | Tool-agnostic, не fork VS Code | IDE features |
| **BMAD-METHOD** (46.7k★) | Multi-agent specialization | TAUSIK enforces quality; BMAD — role separation. Integrate | multi-agent orchestration |
| **Aider** (40k★) | Terminal-native, mature | TAUSIK работает alongside — gate Aider commits | reliability legend |
| **Cline** (5M installs, 61k★) | IDE-extension AI agent | TAUSIK добавляет gates; Cline — executor | install base |
| **Continue** (pivot 2026) | CI quality control | Overlap; differentiate на agent-time vs CI-time enforcement | CI integrations |
| **Claude Skills** (4200+) | Tutorials | Skills = micro-instructions; SENAR = macro-process | skill count |
| **AGENTS.md** | Context convention | Мы consume AGENTS.md; SENAR — process layer на top | convention adoption |
| **SAFe** | Enterprise process methodology | AI-native vs human-team-native; не competing в scaling | training revenue base |
| **IREB CPRE** (€310/exam) | RE certification | RENAR = AI-native RE; IREB = human-native RE. **Комплемент, не replacement** | certification body authority |
| **ISO/IEC 42001** | AIMS | TAUSIK = implementation evidence; SENAR/RENAR = methodology layer | regulatory authority |
| **DORA AI Capabilities Model** | Research framework | DORA = measurement; SENAR = prescription. **Cite DORA в каждом doc** | research authority |

### 12.8 KPI dashboard — quarterly numbers

| Metric | Q3 2026 | Q4 2026 | Q1 2027 | Q2 2027 | Q3 2027 | Q4 2027 |
|---|---|---|---|---|---|---|
| **GitHub stars** (TAUSIK) | 500 | 2,000 | 5,000 | 10,000 | 15,000 | 20,000 |
| **Telemetry-active installs** | 50 | 300 | 800 | 2,000 | 5,000 | 8,000 |
| **Discord members** | 100 | 500 | 1,500 | 3,500 | 6,000 | 10,000 |
| **TG-channel subs (RU)** | 200 | 800 | 2,000 | 4,000 | 7,000 | 11,000 |
| **Blog uniques / month** | 2K | 8K | 20K | 45K | 80K | 120K |
| **Inbound consulting leads / quarter** | 1 | 5 | 12 | 25 | 40 | 60 |
| **Paid pilots signed** | 1 | 3 | 5 | 8 | 12 | 16 |
| **Revenue (USD)** | $20K | $60K | $120K | $250K | $400K | $650K |
| **Pro tier MRR** | $0 | $0 | $15K | $40K | $80K | $130K |
| **Conf talks delivered** | 1 | 3 | 4 | 5 | 6 | 7 |
| **Media mentions (EN)** | 2 | 8 | 18 | 30 | 50 | 80 |
| **Media mentions (RU)** | 4 | 12 | 25 | 40 | 60 | 90 |
| **AAIF / ISO milestones** | apply AAIF | AAIF intake | TC164 contact | NIST mapping done | AAIF profile draft | ГОСТ Р init |
| **Certified users (SENAR Foundation)** | 0 | 0 | 30 | 100 | 250 | 500 |

### 12.9 Бюджет и команда (минимальный без VC)

**Team additions (in order of urgency):**

| Role | When | Type | Monthly cost (USD) |
|---|---|---|---|
| DevRel / Community Lead (bilingual EN/RU) | Month 2 | Contractor → FT by M9 | $4-7K |
| Technical Writer / Content | Month 3 | Contractor (½ FTE) | $2-4K |
| Designer / Brand | Month 1-6 ad hoc | Contractor | $0.5-1.5K |
| GTM Lead / Partnerships | Month 7 | FT | $6-10K |
| Sales / BD (EU/UAE entity) | Month 13 | FT | $8-15K |

**6-month bootstrap budget (M1-M6):**

| Item | USD |
|---|---|
| DevRel contractor (5 mo) | $30K |
| Technical writer (4 mo) | $12K |
| Designer ad hoc | $4K |
| Legal (re-domicile prep + contracts) | $10K |
| Hosting (docs, Discord, telemetry backend) | $1.2K |
| Travel (HighLoad++ SPb, AI Eng Summit Europe, TAdviser) | $8K |
| Conference sponsorships (1 small) | $5K |
| Awesome-list / paid TG integrations | $4K |
| ISO 42001 / NIST training material | $3K |
| Buffer 15% | $11.5K |
| **Total 6 mo** | **~$88.7K** |

### 12.10 «Что делать, если денег нет» — sustainable model на консалтинге

Realistic zero-budget GTM для 90 дней:

1. **Founder time = the only resource.** 60% на code/spec, 40% на distribution.
2. **One artifact per week** — alternating: 1 Habr article → 1 EN blog → 1 video/demo → 1 conf CFP submission.
3. **Free distribution stack:** GitHub Pages, Discord, TG, X, LinkedIn, dev.to, Habr, Medium. Zero cost.
4. **Trade time for credibility:** offer 5 free 1-hour консультаций любому willing to be a case study.
5. **Awesome-list PRs** (free, high-leverage): at least 8 in 30 days.
6. **Apply to GitHub Sponsors + Open Source Endowment ($750K committed Feb 2026) + НИОКР гранты (Сколково / РФРИТ).**
7. **Bundle first paid consulting** с someone в personal network — даже $5K даёт reference.
8. **One paid TG-channel integration** (~$1K) only если personal-network discount available.
9. **Skip travel** для 90 days. Talk online (AI Engineer Summit accepts remote).
10. **At month 4 — re-evaluate.** Если no paid pilot signed — run «consulting ladder»: 5 free intros → 1 paid pilot → 1 case study → 3 paid pilots.

**The single highest-ROI thing on zero budget: a credible benchmark with numbers.** SWE-bench delta with/without TAUSIK на маленьком subset достижим в 1-2 недели founder-time и даёт каждому каналу выше его hook.

---

## 13. Top-10 рекомендаций (приоритизированных)

| # | Action | Owner | Time | Impact | Effort | Dependencies | Acceptance criteria |
|---|---|---|---|---|---|---|---|
| **R1** | **SWE-bench Verified бенчмарк (50 задач) TAUSIK vs Cursor Background Agents vs Claude Code baseline** | Founder | 2-4 недели | **Critical** | Med (founder-time) | — | Опубликован JSON-результат + reproducibility README; delta TAUSIK vs baseline ≥5pp |
| **R2** | **Submit заявку в Linux Foundation AAIF** как «process profile for AGENTS.md» | Founder + legal | 6-9 mo до acceptance | **Critical** | Med ($5-15K membership + applications) | Membership purchase, application drafted | AAIF intake confirmed; WG slot allocated |
| **R3** | **Telemetry-opt-in build в v1.5** (privacy notice + anonymized metrics + Plausible-style backend) | Contractor + founder | 4-6 недель | High | Med | Privacy review | v1.5 ships с opt-in flow; первые 50 telemetry-active installs к Q3 2026 end |
| **R4** | **Глобальная R-ID нумерация SENAR (`SENAR-STD-R-NNN`) + JSON Schema файлы RENAR + 4 из 8 drift detectors** к v1.5/v0.2 | Founder | 1.5-2 квартала | High | High | — | SENAR v1.4 + RENAR v0.2-draft published с обновлённой нумерацией и schemas |
| **R5** | **Open paid consulting trajectory:** 5 free 1-hour консультаций → 1 paid pilot ($20-40K) → 1 case study → 3 paid pilots | Founder | 8-12 недель до первого paid pilot | High | Low-Med (founder-time + personal network) | — | $80-150K revenue к Q4 2026; ≥1 case study published |
| **R6** | **AGENTS.md compatibility:** TAUSIK генерирует AGENTS.md и читает его; SENAR CLAUDE.md формат становится валидным AGENTS.md | Founder | 4-8 недель | High | Low | — | `tausik agents-md generate` команда работает; AGENTS.md spec validation passes |
| **R7** | **Cross-agent adapters:** официальная поддержка Cursor (MCP), Codex CLI, Cline через MCP bridge | Founder + contractor | 2-3 квартала | High | High | Cursor MCP rework | Cursor parity ≥80% к Q1 2027; Codex CLI ≥50%; Cline working integration |
| **R8** | **Compliance-grade audit trail для AI-кода:** ISO 42001 Annex A controls mapping (PDF lead magnet + Drata-compatible export) | Founder + contractor | 1 квартал | High | Med | ISO 42001 training material ($3K) | PDF deck published; Drata listing applied; 1 enterprise inbound lead на compliance angle |
| **R9** | **TypeScript SDK или CLI wrapper** для TS/JS экосистемы | Contractor | 2-3 квартала | Med | High | — | `@tausik/sdk` npm package published; minimal API equivalent; ≥10 GH stars от TS-команд |
| **R10** | **Public Discord + ru-TG channel + weekly content cadence** (1 artifact per week alternating Habr/EN blog/video/CFP) | Founder + DevRel contractor (M2) | Continuous | Med | Med (founder time) | DevRel contractor hired | Discord ≥500 members к Q4 2026; ru-TG ≥800 subs; ≥24 content artifacts published за 6 месяцев |

---

## 14. Заключение

### 14.1 Honest one-paragraph verdict

TAUSIK + SENAR + RENAR — серьёзная методологическая работа уровня ранних CMMI (v1.2, 2006) или SAFe (1.0, 2011), решающая реальную проблему trust gap в AI-native dev (96% разработчиков не доверяют AI-коду по Sonar 2026). Авторы прошли путь, на который у большинства «AI playbook» проектов уходит несколько лет — нормативный язык RFC 2119, closed lists, mandatory clauses, substrate-agnostic capabilities с negative proof, реально enforced quality gates вместо «AGENTS.md рекомендаций». Главные риски — не методологические (методология сильна), а **адаптационные**: N=1 эмпирика, implementation gap RENAR-0 даже у автора, отсутствие telemetry/community/distribution, market timing (Linux Foundation AAIF и GitHub Spec Kit растут быстрее, чем мы получаем mindshare). Окно для занятия ниши «процессного слоя для AI-native dev» открыто, но закрывается — следующие 6 месяцев решают, останется ли это ценным академическим артефактом или станет open-source ISO 42001 implementation reference.

### 14.2 Что произойдёт, если ничего не делать (status quo 12 months)

- TAUSIK останется dogfood-инструментом автора и узкого круга single-digit пользователей.
- SENAR/RENAR останутся ценным академическим артефактом, цитируемым в отдельных blog posts.
- Linux Foundation AAIF добавит process layer как 4-й primitive (Anthropic + OpenAI + Block имеют ресурсы) — нишу займёт другой game.
- GitHub Spec Kit добавит enforced gates в Q4 2026 / Q1 2027 (вероятность ~40%) — TAUSIK станет маргинальным.
- Founder burnout через 12-18 месяцев из-за отсутствия revenue и infinite-effort OSS.

### 14.3 Что произойдёт, если выполнить top-5 рекомендаций (12 months projection)

- SWE-bench delta + Show HN + Habr launch + Claude Marketplace listing → **500-2000 GitHub stars к Q4 2026**.
- Telemetry-opt-in → **300+ telemetry-active installs** = defensible metric.
- AAIF intake к Q1 2027 → standardization credibility + protection от threat #1.
- 3 paid pilots × $40-80K → **$80-150K revenue к Q4 2026** = founder sustainability.
- v0.2 RENAR + R-IDs SENAR + 4 drift detectors → **conformance audit possible** = enterprise sales unlocked.
- AGENTS.md compatibility + Cursor MCP rework → addressable market растёт x3-5.
- К Q4 2027 — realistic 10-15K GH stars, $500-700K ARR-equivalent, 8 enterprise customers, AAIF process profile draft.

### 14.4 Final score

- **8/10 как методологическая работа** — нормативная зрелость SENAR + RENAR уровень CMMI v1.2 / SAFe 1.0.
- **5.5/10 как продукт** — TAUSIK production-grade core, но doc/code drift, no telemetry, no SBOM, no coverage badge, Claude-first enforcement.
- **4/10 как бизнес** — нет revenue, нет community, нет paying customers, нет distribution, нет VC-readiness.

### 14.5 Призыв к действию (одно предложение)

**В ближайшие 30 дней — запустить SWE-bench бенчмарк, опубликовать его на Hacker News и Habr, подать заявку в Linux Foundation AAIF, и начать paid consulting trajectory; всё остальное может ждать, но эти четыре действия не могут.**

---

## Что делать на этой неделе / в этом месяце / в этом квартале

Ниже — prioritized список конкретных действий для Андрея Юмашева.

### На этой неделе (18-24 мая 2026)

1. **Прочитать этот отчёт целиком + 6 input-файлов** — 4-6 часов чтения. Маркировать пункты, с которыми не согласен → ответить в `_findings/00-author-response.md`.
2. **Принять решение по R1 (SWE-bench бенчмарк)** — да/нет. Если да — выбрать 50 задач (suggest: SWE-bench Verified subset с балансом по trivial/simple/moderate/complex).
3. **Зарегистрировать домен `tausik.dev`** (если ещё нет) + обновить landing с TL;DR этого отчёта.
4. **Послать 5 cold outreach** в personal network с предложением free 1-hour консультации в обмен на case study consent.
5. **Open public Discord** (free tier sufficient) + анонс в `tausik` README.

### В этом месяце (май-июнь 2026)

1. **Запустить SWE-bench бенчмарк** (R1) — 50 задач, TAUSIK vs Cursor Background Agents vs Claude Code baseline. Опубликовать JSON-результат + reproducibility README. **Это unlocks всё дальнейшее distribution.**
2. **Подготовить Show HN launch** — нужны: SWE-bench delta number, ASCII demo gif, link к 1-pager «AI agents that can't fake done».
3. **Подать CFP в HighLoad++ SPb 2026** (15 мая deadline — если пропущен, в следующий round осенью), AI Engineer Summit Europe, TAdviser SUMMIT.
4. **Submit заявку в Linux Foundation AAIF** (R2) — изучить membership tiers, подготовить application.
5. **Начать v1.5 development cycle:** Cursor MCP rework, coverage badge, telemetry-opt-in (R3), doc/code drift cross-file scanner.
6. **Hire DevRel contractor** (bilingual EN/RU) — $4-7K/mo. Personal network outreach или LinkedIn search.

### В этом квартале (Q3 2026, июнь-август)

1. **Ship v1.5** (Cursor MCP + telemetry + coverage + doc-drift scanner).
2. **Ship SENAR v1.4** (R-IDs + 2-3 противоречий resolved + L4-L5 в Informative Annex).
3. **Ship RENAR v0.2-draft** (JSON Schemas + 2 drift detectors + research↔public reconciliation).
4. **Land 1 paid pilot** ($20-40K) — preferably через current dogfood projects' commercial spinoffs (finka/kai/laplandka).
5. **Publish 6 контент-артефактов:** SWE-bench results post (EN + RU), TAUSIK vs Spec Kit deep dive, EU AI Act Art. 50 checklist, MCP server post, AGENTS.md compatibility post, dead-end stories post.
6. **List на 5+ awesome-lists** + Claude Marketplace + agents.md ecosystem.
7. **Open ru-TG channel** + начать weekly content cadence.
8. **Deliver 1 conference talk** (HighLoad++ SPb или AI Engineer Summit Europe или TAdviser).
9. **Map SENAR controls → ISO 42001 Annex A** — публиковать как downloadable PDF lead magnet.
10. **Hire technical writer** (½ FTE contractor, $2-4K/mo).

К концу Q3 2026 цель — **500 GH stars, 50 telemetry-active installs, 3 conf talks accepted, 1 paid pilot signed, $20K revenue**.

---

# Приложения

## Приложение A. Полная таблица оценок по осям

| Ось | SENAR v1.3 | RENAR v0.1-draft | TAUSIK v1.4.2 | Среднее |
|---|---|---|---|---|
| Формальность (RFC 2119, IDs, нормативный язык) | 7 | 9 | 7.5 | 7.8 |
| Полнота (covers всё необходимое) | 8 | 8 | 8.0 | 8.0 |
| Инновационность (новое vs derivative) | 9 | 9 | 9.0 | 9.0 |
| Прагматичность (можно применить завтра) | 8 | 6 | 7.5 | 7.2 |
| Измеримость (SHALL → testable evidence) | 6 | 7 | 6.5 | 6.5 |
| Адаптивность (модель/IDE/язык) | 9 | 7 | 7.0 | 7.7 |
| Документация (читаемость, structure) | 9 | 9 | 8.0 | 8.7 |
| Риск принятия (политич./культ./adoption) | 6 | 5 | 7.5 | 6.2 |
| Конкурентоспособность (vs аналоги) | 9 | 8 | 7.0 | 8.0 |
| Методологическая глубина | 8 | 9 | 8.5 | 8.5 |
| **Средняя** | **7.9** | **7.7** | **7.0** | **7.5** |

Дополнительные оси для TAUSIK (специфичные для реализации):

| Ось | Оценка |
|---|---|
| SENAR полнота | 8.5/10 |
| RENAR готовность | 2/10 |
| DX (Developer Experience) | 7.5/10 |
| Performance | 6.5/10 |
| Security | 7/10 |
| Tests | 7.5/10 |
| Расширяемость | 8.5/10 |
| Vendor-neutrality | 6.5/10 |
| Adoption-readiness | 7.5/10 |

---

## Приложение B. Сравнительная таблица: TAUSIK vs 15 конкурентов

Расширенная heatmap (●●● сильно, ●● присутствует, ● слабо, ○ нет):

| Продукт | QG enforced | Verify-as-code | Task journal | Multi-agent | Memory | Skills/plugins | Lang-agnostic | Open source | Self-host | Cost/mo |
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

---

## Приложение C. Сравнительная таблица: SENAR/RENAR concepts × мировые стандарты

(Сжатая версия — полная — в `_findings/05-world-standards.md` §1)

| Стандарт | Год | AI-релевантность | SENAR | RENAR |
|---|---|---|---|---|
| ISO/IEC/IEEE 12207:2017 | 2017 | Косвенная | Полная | Частичная |
| ISO/IEC/IEEE 15288:2023 | 2023 | Косвенная | Полная | Частичная |
| CMMI v3.0 | 2023 | Косвенная | Частичная | Косвенная |
| SAFe 6.0 | Active | Прямая (AI explicit) | Частичная (PI-only) | Частичная |
| ISO/IEC 25010:2023 | 2023 | Косвенная | Частичная | **Полная (NFR taxonomy)** |
| **ISO/IEC/IEEE 29148:2018** | 2018 | Косвенная | Частичная | **ПОЛНАЯ (BR/SR/TR direct 1-to-1)** |
| IEEE 830-1998 | Deprecated | — | — | Частичная (SRS) |
| IIBA BABOK v3 | Active | Косвенная | Частичная | Полная |
| IREB CPRE + AI4RE | 2025 | Прямая | Частичная | **Прямая** |
| **EU AI Act** | 2024-08, full 2026-08 | **Прямая (нормативная)** | Частичная | **Прямая (tech doc)** |
| NIST AI RMF 1.0 + GenAI | 2023 + 2024 | Прямая | Полная | Частичная |
| **ISO/IEC 42001:2023** | 2023 | **Прямая (AIMS)** | **Полная** | Частичная |
| ISO/IEC 23894:2023 | 2023 | Прямая (risk) | Частичная | Косвенная |
| **ISO/IEC 5338:2023** | 2023 | **Прямая (AI life cycle)** | **Полная** | **Полная** |
| ГОСТ 34.602-2020 | 2022 | Нет | Частичная | **Полная (ТЗ structure)** |
| ГОСТ Р 56939-2024 | 2024-12 | Нет | Частичная (secure dev) | Косвенная |
| **AGENTS.md** | 2026 | **Прямая** | Частичная | Нет |
| **MCP (Anthropic)** | 2025-26 | **Прямая** | Полная | Косвенная |
| **GitHub Spec Kit** | 2025 | **Прямая (SDD)** | Частичная (4 gates) | Частичная (spec layer) |

---

## Приложение D. Список источников

**Файлы аудита (90+):**
- `D:\Work\Kibertum\senar\standard\` (главы 00-13, RU/EN)
- `D:\Work\Kibertum\senar\core\`, `guide\`, `reference\`, `SENAR-SUMMARY*.md`
- `D:\Work\Kibertum\renar-public\standard\` (15 глав)
- `D:\Work\Kibertum\renar-public\reference\` (5 файлов)
- `D:\Work\Kibertum\renar-public\guide\` (8 файлов)
- `D:\Work\Kibertum\req-standart\research\` (19 приватных research drafts)
- `D:\Work\Kibertum\kai\RENAR-CONFORMANCE.yaml`, `CLAUDE.md`
- TAUSIK repo: 138 source files, CHANGELOG, README, docs/ru/, docs/en/

**Внешние URL (~80, полный список — в каждом из `_findings/0X-*.md` source files):**
- Стандарты: ISO/IEC 12207/15288/29148/42001/5338/23894/25010, EU AI Act, NIST AI RMF, IEEE 7000, ГОСТ Р 56939/34.602, AGENTS.md, MCP, A2A
- Конкуренты: Aider, Cline, Roo Code, OpenHands, Goose, Continue.dev, Cody, Claude Code, Codex CLI, Gemini CLI, Cursor, Windsurf, Copilot, Junie, Zed, Devin, SWE-agent, Augment Code, Replit, Bolt, v0, Magic.dev, xAI Grok Build, LangChain, AutoGen, CrewAI, DSPy, LangFuse, Maxim, Codacy, TaskMaster, Spec Kit, BMAD, Kiro, OpenSpec, Tessl, Antigravity
- Рынок: Mordor Intelligence, Gartner, Stack Overflow 2025, Sonar 2026, DORA 2025, Anthropic 2026 Agentic Coding Trends, TechCrunch, Bloomberg, Crunchbase
- Регуляторы: EC AI Act guidelines, NIST docs, Linux Foundation AAIF press, OECD AI Principles

Полный list URL — в `_findings/04-competitive-analysis.md` §11 (Sources), `_findings/05-world-standards.md` §9, `_findings/06-market-and-gtm.md` Sources.

---

## Приложение E. Глоссарий ключевых терминов

- **ADAPT** — RENAR bridge artefact между immutable client ТЗ и BR/SR/SPEC с forward + backward + dual signature + delta workflow + errata.
- **ADR (Adversarial Detection Rate)** — SENAR метрика плотности скрытых дефектов, обнаруженных adversarial review (формула: latent_defects_found / total_artifacts_reviewed; target < 0.5; nuance: ADR=0 indicates either excellent quality OR insufficient review rigor).
- **AGENTS.md** — Markdown convention для agent instructions в repo root, stewarded by Linux Foundation Agentic AI Foundation. 60k+ репо.
- **AAIF (Agentic AI Foundation)** — Linux Foundation sub-foundation, founded Dec 2025 (Anthropic + OpenAI + Block). Hosts AGENTS.md, MCP, A2A.
- **BR / SR / TR** — RENAR closed list 3 types of requirements (Business / System / Task). 1-to-1 mapping на ISO 29148 StRS / SyRS / SRS.
- **FPSR (First-Pass Success Rate)** — SENAR primary metric, измеряющая % задач, которые проходят QG-3 с первой попытки. Импорт First Pass Yield из бережливого производства.
- **MCP (Model Context Protocol)** — открытый протокол context/tool exchange между LLM-агентом и системами. 78% enterprise AI teams с MCP в production (Apr 2026); 9400+ servers.
- **MVR (Minimal Viable RENAR)** — 7 mandatory clauses §14.3.1-7, минимум для conformance.
- **QG (Quality Gate)** — SENAR 5 gates (QG-0 Context → QG-1 Requirements → QG-2 Implementation → QG-3 Verification → QG-4 Acceptance). RENAR 5 canonical QG (3 mandatory + 2 optional).
- **RENAR-CONFORMANCE.yaml** — обязательный артефакт RENAR-1+, фиксирует уровень conformance + drift detectors + assessment mode.
- **SDD (Spec-Driven Development)** — парадигма, где spec становится source of truth для AI-агентов. RENAR — первая formal normative formulation SDD.
- **SoT (Source of Truth) inversion** — нормативное утверждение RENAR §5.3.1: «требования > код», при расхождении побеждает требование.
- **Substrate** — система хранения артефактов (git, Mercurial, CouchDB, Iceberg, и т.д.). RENAR substrate-agnostic требует V1-V6 capabilities.
- **TC (Test Case)** — RENAR first-class artifact с 6 types (acceptance / ux / system / contract / eval / security), pos/neg парность mandatory, judge ≠ production isolation.
- **V1-V6** — RENAR substrate capabilities (V1 Immutable history, V2 Atomic change unit, V3 Diff & review, V4 Branching, V5 Cross-substrate version pin, V6 Author + timestamp). §11.2 даёт negative proof для каждой.
- **Verify-First Contract** — TAUSIK killer feature: `task done --ac-verified` физически читает кэш `verify --task <slug>` (10-min TTL, files_hash, git-diff cross-check, security bypass).

---

## Приложение F. Атрибуция: 6 агентов

| Агент | Скоуп | Объём | Длительность | Источник |
|---|---|---|---|---|
| **Агент A** (SENAR) | Независимый методолог-аналитик с перспективой CMMI / SAFe / ISO 12207 / IEEE 42010 / SLSA / ISO 9001 | ~7 600 слов | ~3 часа | `_findings/01-senar-analysis.md` |
| **Агент B** (RENAR) | Независимый методолог-аналитик, специализация Requirements Engineering (IREB CPRE / ISO/IEC/IEEE 29148 / IIBA BABOK / SAFe) | ~8 700 слов | ~3 часа | `_findings/02-renar-analysis.md` |
| **Агент C** (TAUSIK) | Independent code reviewer (Claude Opus 4.7, 1M context, single-pass review) | ~4 600 слов | ~3 часа | `_findings/03-tausik-audit.md` |
| **Агент D** (Competitive) | Продуктовый аналитик (research pass) — 30+ продуктов, 6 категорий | ~4 300 слов | ~3 часа | `_findings/04-competitive-analysis.md` |
| **Агент E** (Standards) | Independent standards researcher — 8 категорий × 40+ стандартов | ~4 200 слов | ~3 часа | `_findings/05-world-standards.md` |
| **Агент F** (GTM) | Strategy synthesis (market sizing + ICP + positioning + channels + monetization + roadmap + KPIs + budget) | ~6 500 слов | ~3 часа | `_findings/06-market-and-gtm.md` |
| **Editorial synthesis** | Main editorial pass over six parallel findings, deduplication, prioritization, scorecards | этот документ ~25k слов | ~3 часа | `audit-report-2026-05-18.md` |

**Итого:** ~36 000 слов независимой аналитики + ~25 000 слов synthesis = ~61 000 слов аудитного материала, опирающегося на 90+ файлов внутренней документации и ~80 внешних URL.

---

*Конец отчёта. Все цитаты из source files проверяемы по line-ref. Все внешние данные имеют URL в Приложении D. Этот отчёт сохранён в `D:\Work\Personal\claude\docs\audit\audit-report-2026-05-18.md` и может быть опубликован с согласия авторов.*
