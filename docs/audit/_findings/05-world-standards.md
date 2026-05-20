# 05 — Карта мировых стандартов для SENAR / RENAR

**Дата:** 2026-05-18
**Скоуп:** ландшафт международных и российских стандартов SE / RE / AI governance / supply-chain / safety-critical / emergent AI-native, и позиционирование SENAR (методология AI-нативной разработки) и RENAR (инженерия требований для AI-кода) внутри него.

---

## TL;DR

1. **SENAR/RENAR не конкурируют с ISO/IEC 12207/15288 — они их operationalize для AI-native loop.** Классические life-cycle стандарты substrate-agnostic ("human OR machine") и явно разрешают tailoring. SENAR может быть зарегистрирован как tailored profile.
2. **Самые синергичные стандарты — ISO/IEC 29148 (RE), ISO/IEC 42001 (AI mgmt), ISO/IEC 5338 (AI life cycle).** Все три уже используют hierarchy BR → StR → SyR, что один-к-одному маппится на RENAR BR/SR/TR.
3. **Самые "опасные" соседи — GitHub Spec Kit, IREB AI4RE, AGENTS.md.** Они занимают spec-driven и agent-instructions нишу, но без normative discipline. SENAR/RENAR могут позиционироваться как "Spec Kit + RFC 2119 нормативность + Quality Gates".
4. **Главное белое пятно мирового масштаба:** **substrate-agnostic нормативный standard для AI-native development loop с явными QGs и метриками SENAR-style** не существует. ISO 42001 — про governance системы, не про процесс разработки. ISO 5338 — про life-cycle AI системы, не про human+agent loop. RENAR substrate-agnostic V1-V6 — это honest first-of-kind.
5. **EU AI Act August 2026** делает ISO 42001 де-факто обязательным для high-risk AI. SENAR/RENAR могут стать "implementation reference" под зонтом ISO 42001 — это самый прибыльный позиционирующий ход на 2026-2027.
6. **Рекомендация подачи:** не в ISO TC прямо (1-3 года, дорого) и не в IEEE 7000 (etika scope). Оптимально — **OpenJS Foundation или Linux Foundation (AAIF — Agentic AI Foundation)** где уже сидят AGENTS.md, MCP, A2A. SENAR/RENAR заходит как complementary "process & RE" слой к этим protocol-стандартам.

---

## 1. Карта стандартов: 8 категорий × релевантность

| Категория | Стандарт | Год / Статус | AI-релевантность | Маппится на SENAR | Маппится на RENAR |
|---|---|---|---|---|---|
| **SE / методологии** | ISO/IEC/IEEE 12207:2017 | Active, обзор 2026 | Косвенная (substrate-agnostic) | Полная (life-cycle processes) | Частичная (RE process) |
| | ISO/IEC/IEEE 15288:2023 | Active | Косвенная | Полная | Частичная |
| | CMMI v3.0 | 2023, only-version с 2024 | Косвенная | Частичная (maturity ≠ practice) | Косвенная |
| | SAFe 6.0 | Active (AI added) | Прямая (AI explicit) | Частичная (PI-level only) | Частичная |
| | ISO 9001:2015 | Active | Нет | Косвенная (PDCA) | Нет |
| | ISO/IEC 25010:2023 | Active (Nov 2023) | Косвенная | Частичная (quality model) | **Полная (NFR taxonomy)** |
| **RE стандарты** | **ISO/IEC/IEEE 29148:2018** | **Active, gold standard** | Косвенная | Частичная | **ПОЛНАЯ (BR/StR/SyR=BR/SR/TR)** |
| | IEEE 830-1998 | Deprecated, used | Нет | Нет | Частичная (SRS) |
| | IIBA BABOK v3 | Active, 2026 cert | Косвенная (AI as topic) | Частичная (BA process) | Полная (requirements lifecycle) |
| | IREB CPRE + AI4RE | Active 2025 | Прямая (AI4RE micro-cred) | Частичная | **Прямая (RE for AI)** |
| | INCOSE SE Handbook v5 | 2023 | Косвенная | Полная | Частичная |
| | Volere Template | Active community | Нет | Нет | Частичная (template) |
| **AI Governance** | **EU AI Act** | In force 2024-08, full 2026-08-02 | **Прямая (нормативная)** | Частичная (process gate) | **Прямая (tech doc)** |
| | NIST AI RMF 1.0 + GenAI Profile | 2023 + 2024 GenAI | Прямая | Полная (risk/govern functions) | Частичная |
| | **ISO/IEC 42001:2023** | **Active, certifiable** | **Прямая (AIMS)** | **Полная (AI mgmt system)** | Частичная (system-level) |
| | ISO/IEC 23894:2023 | Active | Прямая (risk) | Частичная | Косвенная |
| | ISO/IEC 5338:2023 | Active | **Прямая (AI life cycle)** | **Полная** | **Полная** |
| | ISO/IEC TR 24028:2020 | Active TR | Прямая (trust) | Косвенная | Частичная |
| | OECD AI Principles (2024 upd) | Active (47 adherents) | Прямая | Косвенная (values) | Косвенная |
| | IEEE 7000 series | Active (2021+) | Прямая (ethics) | Частичная (ethical concerns) | Косвенная |
| **Supply Chain** | SLSA v1.0 | Active | Косвенная | Частичная (provenance) | Нет |
| | SBOM (CycloneDX / SPDX = ISO 5962) | Active | Косвенная | Частичная | Нет |
| | in-toto / Sigstore / Cosign | Active | Косвенная | Частичная | Нет |
| | ISO/IEC 5230 (OpenChain) | Active 2020, 2025 upd | Нет | Нет | Нет |
| **Safety-critical** | MISRA C/C++ | Active | Косвенная | Нет | Нет |
| | DO-178C (avionics) | Active | Прямая (V-model + AI) | Частичная (gates) | **Частичная (req traceability)** |
| | IEC 62304 (medical) | Active | Прямая | Частичная | Частичная |
| | ISO 26262 (auto) | Active | Прямая | Частичная | Частичная |
| | IEC 61508 (functional safety) | Active | Косвенная | Частичная | Частичная |
| | ISO/IEC 15408 (Common Criteria) | Active | Нет | Нет | Нет |
| **Российские** | ГОСТ 34.601-90 | Active (legacy) | Нет | Косвенная | Частичная |
| | **ГОСТ 34.602-2020** | **Active с 2022-01-01** | Нет | Частичная | **Полная (ТЗ structure)** |
| | **ГОСТ Р 56939-2024** | **Active с 2024-12** | Нет | Частичная (secure dev) | Косвенная |
| | ГОСТ Р 71476-2024 (=ISO 22989) | Active с 2025 | Прямая (AI termin.) | Косвенная | Косвенная |
| | ГОСТ Р 70462.1-2022 (=ISO 24029) | Active | Прямая (NN robustness) | Косвенная | Косвенная |
| | ГОСТ Р 59792-2021 | Active (АС испытания) | Нет | Частичная (test gates) | Частичная |
| | Приказ ФСТЭК №240 (от 30.06.25) | Active | Косвенная | Частичная | Косвенная |
| **Эмерджентные AI-native** | **AGENTS.md** | De-facto 2026, AAIF/Linux Found. | **Прямая (agent instructions)** | **Частичная (CLAUDE.md analog)** | Нет |
| | **MCP (Anthropic)** | De-facto std 2025-2026 | **Прямая (context protocol)** | Полная (tool/context) | Косвенная |
| | A2A (Google → Linux Found.) | v1.0, 150+ orgs 2026 | Прямая (multi-agent) | Косвенная | Нет |
| | ACP (IBM) | Merged into A2A 2025 | Прямая | Косвенная | Нет |
| | llms.txt | Limited adoption (10%) | Прямая (LLM nav) | Нет | Нет |
| | **GitHub Spec Kit** | OSS Sept-2025, growing | **Прямая (spec-driven)** | **Частичная (4 gates)** | **Частичная (spec layer)** |
| **Benchmarks** | SWE-bench Verified | Contaminated (2026) | Прямая | Метрика | Нет |
| | SWE-bench Pro | Recommended replacement | Прямая | Метрика | Нет |
| | LiveCodeBench v6 | Active (contamination-free) | Прямая | Метрика | Нет |
| | BigCodeBench | Active (1140 tasks) | Прямая | Метрика | Нет |
| | TerminalBench | Active | Прямая | Метрика | Нет |
| | METR Time-Horizon | Active (doubling 4 мес 2025-26) | Прямая | Метрика SENAR-2 | Нет |

---

## 2. Топ-15 наиболее релевантных стандартов — детальные карточки

### 2.1. ISO/IEC/IEEE 29148:2018 — Requirements Engineering (Gold Standard)

- **Скоуп:** Life-cycle RE для systems & software, complement to 12207/15288.
- **Hierarchy:** Stakeholder Requirements (StRS) → System Requirements (SyRS) → Software Requirements (SRS). Это **прямой аналог RENAR BR → SR → TR**.
- **Совместимость с RENAR:** **ПОЛНАЯ.** RENAR можно позиционировать как 29148-tailored profile для AI-native.
- **Compliance gap:** 29148 не предполагает "agent as stakeholder", не описывает drift detectors, не имеет substrate-agnostic V1-V6 verification levels, не использует RFC 2119 в нормативной форме. RENAR заполняет каждый из этих gaps.
- **Сертификация:** не сам стандарт, но используется как reference в audit (TÜV, BSI).

### 2.2. ISO/IEC 42001:2023 — AI Management System (AIMS)

- **Скоуп:** Plan-Do-Check-Act для responsible AI lifecycle. Mirrors ISO 9001 / 27001.
- **Релевантность:** **критическая.** Покрывает ~70% документации EU AI Act high-risk.
- **Совместимость с SENAR:** **ПОЛНАЯ на governance уровне.** SENAR может стать "process implementation reference" под зонтом 42001.
- **Compliance gap:** 42001 — это система менеджмента (политики, роли, аудит). Не описывает **процесс ежедневной разработки** с участием AI-агентов, нет QGs, нет метрик productivity vs. quality. SENAR заполняет process gap.
- **Сертификация:** **есть, certifiable** (BSI, A-LIGN, Schellman, KPMG, TÜV SÜD). К 2026 — de-facto AI governance стандарт для регулируемых рынков.

### 2.3. ISO/IEC 5338:2023 — AI System Life Cycle Processes

- **Скоуп:** AI-specific extension к 12207/15288. Основан на тех же процессах с modifications + AI-specific additions (data lifecycle, model training, evaluation).
- **Релевантность:** **критическая для substrate claim.** Это единственный стандарт, который явно интегрирует AI-system lifecycle с classical SE processes.
- **Совместимость с SENAR/RENAR:** **ПОЛНАЯ.** RENAR substrate-agnostic V1-V6 — естественное расширение 5338.
- **Compliance gap:** 5338 описывает AI **system** lifecycle (ML model training, MLOps), а не AI-augmented **dev** lifecycle (human + coding agent). SENAR/RENAR заполняют development loop side.

### 2.4. EU AI Act (Reg. 2024/1689) — full applicability 2026-08-02

- **Скоуп:** Нормативный (закон), не стандарт. Категории риска (prohibited / high-risk / limited / minimal).
- **Релевантность для SENAR/RENAR:** **прямая для high-risk.** Требует technical documentation, risk management, transparency, quality management system. RENAR ADAPT artefact = candidate для technical documentation.
- **Сертификация:** Conformity assessment + CE marking + EU database registration к 2026-08-02.
- **Позиция:** SENAR/RENAR не сам compliance, но **сильно сокращает effort** для high-risk систем, использующих AI coding agents.

### 2.5. NIST AI RMF 1.0 + GenAI Profile (NIST AI 600-1)

- **Скоуп:** Voluntary risk management framework. 4 функции: Govern / Map / Measure / Manage.
- **GenAI Profile 2024:** 12 GenAI-specific risk areas (confabulation, IP, data privacy, value chain).
- **Совместимость с SENAR:** **ПОЛНАЯ** (RFC 2119 рядом, метрики маппятся на Measure function).
- **Compliance gap:** RMF — высокоуровневая taxonomy, не имеет конкретных QGs / процессных артефактов. SENAR — implementation.
- **Сертификация:** voluntary, но de-facto referenced в US gov procurement.

### 2.6. ISO/IEC 25010:2023 — Software Quality Model

- **Скоуп:** 9 quality characteristics (functional suitability, performance, compatibility, interaction capability, reliability, security, maintainability, flexibility, **safety added 2023**).
- **Совместимость с RENAR:** **ПОЛНАЯ для NFR taxonomy.** RENAR SPEC types для non-functional requirements могут заимствовать 25010.
- **Compliance gap:** 25010 — model, не process. Не отвечает на "как verify в AI-native loop". RENAR V1-V6 — answer.

### 2.7. AGENTS.md (Linux Foundation / AAIF)

- **Скоуп:** Markdown convention для agent instructions в repo root.
- **Adoption 2026:** Claude Code, Codex, Cursor, Aider, Devin, Gemini CLI, Copilot, Windsurf, Q, и др. (15+ tools).
- **Governance:** stewarded by Agentic AI Foundation under Linux Foundation (Dec 2025).
- **Совместимость с SENAR:** SENAR CLAUDE.md / project-instructions можно унифицировать через AGENTS.md format. **Это must-do для distribution.**
- **Compliance gap:** AGENTS.md = static instructions; SENAR = dynamic process + gates + metrics. Они дополняют друг друга.

### 2.8. Model Context Protocol (MCP)

- **Скоуп:** Открытый протокол context/tool exchange между LLM-агентом и системами (data, tools).
- **Adoption 2026:** 78% enterprise AI teams с MCP в production (Apr 2026); 9,400+ servers; нативная поддержка Claude, ChatGPT, Gemini API, Vertex AI, Cursor, Windsurf, JetBrains AI, Vercel AI SDK, OpenAI Agents SDK.
- **Governance:** donated to Agentic AI Foundation (Linux Foundation) Dec 2025.
- **Релевантность:** SENAR-runtime использует MCP-tools (tausik MCP). Это substrate-level dependency.

### 2.9. GitHub Spec Kit / Spec-Driven Development

- **Скоуп:** OSS toolkit (MIT, Sept 2025) для spec-driven AI workflows. 4 gated phases: Specify → Plan → Tasks → Implement.
- **Релевантность:** **прямой "competitor" RENAR в spec-layer.** Похожий по идее (spec as source of truth).
- **Различие:** Spec Kit = tool + light convention, без нормативного RFC 2119 языка, без drift detectors, без substrate-agnostic claim. RENAR = nor­mative standard + ADAPT + V1-V6.
- **Стратегия:** SENAR/RENAR должны позиционироваться как "normative layer ON TOP of Spec Kit", не replacement.

### 2.10. IREB CPRE-FL + AI4RE Micro-Credential

- **Скоуп:** European RE certification + Generative AI for RE micro-credential.
- **AI4RE:** AI tools для elicitation, documentation, validation, management of requirements.
- **Релевантность для RENAR:** Это самый близкий "education side" к RENAR. RENAR может стать reference reading для AI4RE 2027+.
- **Compliance gap:** AI4RE учит **using AI for RE**; RENAR учит **doing RE for AI-generated code**. Это разные углы — синергия, не конкуренция.

### 2.11. ISO/IEC 23894:2023 — AI Risk Management

- **Скоуп:** Practical playbook для AI risk на базе ISO 31000.
- **Связь с ISO 42001:** 42001 = "what", 23894 = "how". Mandatory companion.
- **Релевантность для SENAR:** SENAR-3 (Verify) metric может включать AI-specific risks из 23894.

### 2.12. ISO/IEC/IEEE 12207:2017 / 15288:2023

- **Скоуп:** Software / Systems life cycle processes. 4 process groups: agreement / org-enabling / technical management / technical.
- **Совместимость с SENAR:** **ПОЛНАЯ.** SENAR — tailored profile.
- **Tailoring clause:** оба стандарта **явно разрешают** tailoring (4.2 в 12207). Это даёт SENAR/RENAR juridical ground для compliance claims.

### 2.13. ГОСТ Р 56939-2024 — Безопасная разработка ПО

- **Скоуп:** Российский эквивалент ISO/IEC 27034 + SDL. Замена 56939-2016. Active с 2024-12.
- **Связь с ФСТЭК:** Приказ №240 (с обновлением №230 от 2025-06-30) — порядок сертификации СЗИ-разработки.
- **Релевантность:** **критическая для RU-аудитории.** SENAR-Verify (QG) можно маппить на 56939 secure development controls.
- **Compliance gap:** 56939 не упоминает AI agents в роли co-developer. SENAR может стать "AI-native extension profile".

### 2.14. ГОСТ 34.602-2020 — ТЗ на АС

- **Скоуп:** Технические задания на автоматизированные системы. Active с 2022-01-01 (заменил 34.602-89).
- **Релевантность для RENAR:** **прямая для RU enterprise + госсектор.** RENAR BR/SR/TR можно представить как 34.602-compatible ТЗ структуру.
- **Новое в 2020:** добавлен раздел "порядок разработки АС" + "общие технические требования".

### 2.15. ISO/IEC 5230 (OpenChain License) + SLSA + SBOM

- **Скоуп:** Open source license compliance + supply chain provenance.
- **Релевантность для SENAR:** косвенная, но **обязательная для AI-generated code provenance.** AI-code часто включает training-data residuals → license risk. SENAR должен включать SBOM gate.
- **Сертификация:** ISO 5230 self-certifiable (free webapp); SLSA — voluntary.

---

## 3. Compliance matrix: SENAR / RENAR концепты × стандарты

| SENAR/RENAR концепт | Стандарт | Статус совместимости |
|---|---|---|
| **5 ценностей SENAR** (Context > Code, Verification > Speed, Knowledge > Experience, …) | OECD AI Principles, NIST RMF Govern, ISO 42001 §5 | **Полная (values сходны)** |
| **15 правил SENAR (RFC 2119)** | ISO 42001 Annex A controls | **Adapter required** (правила → controls mapping) |
| **5 Quality Gates (QG-0…QG-4)** | DO-178C verification objectives; ISO 5338 review/verify processes | **Полная (concept-level)** |
| **SENAR 10 метрик** (delivery, quality, productivity, learning, cost) | NIST RMF Measure; ISO 42001 §9; METR time-horizon | **Полная** |
| **Verify-First (QG-2)** | DO-178C MC/DC; ISO 26262 ASIL verification | **Полная (concept), partial (rigor depth)** |
| **RENAR BR/SR/TR hierarchy** | ISO 29148 StRS/SyRS/SRS; ГОСТ 34.602-2020 | **ПОЛНАЯ (direct 1-to-1)** |
| **RENAR ADAPT artefact** | EU AI Act Annex IV "technical documentation"; ISO 42001 §7.5 | **Высокая (candidate doc)** |
| **9 SPEC types** | ISO 25010:2023 9 quality characteristics; INCOSE SEH v5 | **Полная (NFR), partial (functional)** |
| **Substrate-agnostic V1-V6** | ISO 5338 + ISO 29148 | **Расширение (no precedent)** |
| **Drift detectors** | ISO 23894 AI risk continuous monitoring | **Расширение (RENAR — implementation)** |
| **TAUSIK runtime** (CLI + DB + MCP) | MCP protocol, AGENTS.md | **Полная** |
| **Agent as stakeholder** | ISO 29148 (extended) | **Нужна формальная extension claim** |

---

## 4. Маппинг к EU AI Act / NIST AI RMF / ISO 42001

### 4.1. EU AI Act high-risk requirements (Annex IV) ↔ SENAR/RENAR

| EU AI Act требование | SENAR/RENAR покрытие |
|---|---|
| Technical documentation (Art. 11 + Annex IV) | RENAR ADAPT artefact + SENAR project DB exports |
| Risk management system (Art. 9) | SENAR QG-3 verify + ISO 23894 mapping |
| Data governance (Art. 10) | Out of scope (handled by ISO 42001) |
| Transparency (Art. 13, 50) | RENAR SPEC types include traceability + ADAPT |
| Human oversight (Art. 14) | SENAR QG-0 Context Gate + role= required |
| Accuracy, robustness, cybersecurity (Art. 15) | SENAR Verify-First + ISO 56939 (RU) |
| Quality management system (Art. 17) | ISO 42001 / 9001 — **SENAR sits inside QMS** |
| Conformity assessment (Art. 43) | SENAR audit trail (task DB + events log) supports |

### 4.2. NIST AI RMF functions ↔ SENAR/RENAR

| NIST function | SENAR/RENAR |
|---|---|
| **Govern** | SENAR roles + custom_stacks + ценности |
| **Map** | RENAR BR/SR/TR + ADAPT |
| **Measure** | SENAR 10 метрик + METR time-horizon |
| **Manage** | SENAR QGs + drift detectors |

### 4.3. ISO 42001 implementation ↔ SENAR

| ISO 42001 clause | SENAR artefact |
|---|---|
| §4 Context of organization | CLAUDE.md project context |
| §5 Leadership / AI policy | SENAR ценности + правила |
| §6 Planning / AI risks & impacts | RENAR impact analysis |
| §7 Support (resources, awareness, documented info) | tausik runtime + DB |
| §8 Operation / AI system lifecycle | SENAR loop + QGs |
| §9 Performance evaluation / metrics | SENAR 10 метрик |
| §10 Improvement | dead-ends + retrospective via metrics |

**Вывод:** SENAR — это **operational reference implementation для ISO 42001 §8** для команд, использующих coding agents.

---

## 5. РФ-стандарты (отдельная глава)

| Стандарт | Год | Заменяет | Релевантность для SENAR/RENAR |
|---|---|---|---|
| ГОСТ 34.601-90 | 1990 | — | Legacy, всё ещё обязателен для госзаказа. Stages of AS creation. |
| ГОСТ 34.602-2020 | 2022-01-01 in force | 34.602-89 | **ТЗ структура — direct mapping для RENAR ADAPT.** |
| РД 50-34.698-90 | 1990 | — | Содержание документов АС. Legacy, used in gov. |
| ГОСТ Р 59792-2021 | 2021 | — | Виды испытаний АС. Маппится на SENAR QG-3 (verify). |
| ГОСТ Р 56939-2024 | 2024-12 | 56939-2016 | **Secure dev — обязателен для СЗИ.** Маппится на SENAR Verify + Security gates. |
| ГОСТ Р 71476-2024 (=ISO 22989) | 2025-01-01 | — | AI terminology. SENAR/RENAR должен использовать его термины. |
| ГОСТ Р 70462.1-2022 (=ISO 24029-1) | 2022 | — | NN robustness assessment. Optional для RENAR robustness SPEC. |
| ГОСТ Р 70462.2-2024 (=ISO 24029-2) | 2024 | — | NN robustness formal methods. Косвенная. |
| ГОСТ Р 59277-2020 | 2020 | — | AI systems classification. Терминология. |
| ФСТЭК Приказ №240 (с изм. №230 от 2025-06-30) | 2023 → 2025 | — | Сертификация процессов БРПО на базе ГОСТ 56939-2024. **Обязательно для СЗИ.** |
| ГОСТ Р "ИИ в КИИ" (проект) | в разработке | — | AI в критической инфраструктуре. Future-proof реверанс. |

**Стратегическая рекомендация для РФ:** позиционировать SENAR как "AI-native процесс разработки, совместимый с ГОСТ Р 56939-2024 и ГОСТ 34.602-2020". Это открывает enterprise + госсектор рынок.

---

## 6. Эмерджентные AI-native стандарты — состояние и риски

### 6.1. AGENTS.md
- **Статус:** de-facto convention 2026; AAIF / Linux Foundation governance.
- **Покрытие:** static project instructions (commands, structure, conventions).
- **Риск для SENAR:** если SENAR использует **другой** формат project-instructions, теряется compatibility с 15+ tools. **Recommendation: SENAR CLAUDE.md должен быть валидным AGENTS.md либо публиковать AGENTS.md как mirror.**

### 6.2. MCP (Model Context Protocol)
- **Статус:** de-facto industry standard 2026; AAIF governance.
- **Покрытие:** runtime context/tool exchange protocol.
- **Риск:** низкий — TAUSIK уже использует MCP. **Recommendation: continue MCP-first; publish TAUSIK MCP server spec.**

### 6.3. A2A (Agent-to-Agent)
- **Статус:** v1.0, 150+ orgs, Linux Foundation, ACP merged in.
- **Покрытие:** multi-agent communication / coordination.
- **Релевантность для SENAR:** будущее (когда SENAR loop станет multi-agent). Сейчас — observe.

### 6.4. GitHub Spec Kit
- **Статус:** OSS Sept 2025, активный рост; 30+ AI tools.
- **Риск:** **средний — overlap со spec-driven частью RENAR.** Recommendation: позиционировать RENAR как "normative + substrate-agnostic + drift-aware Spec Kit extension".

### 6.5. llms.txt
- **Статус:** 10% adoption (May 2026), без major AI vendor commitment; используется агентами (Cursor, Claude Code, Copilot) для doc routing.
- **Релевантность:** low-priority. Optional для SENAR доков.

### 6.6. UNESCO AI Ethics Recommendations
- **Статус:** Active, globally adopted normative framework.
- **Релевантность:** values-level only.

---

## 7. Тренды стандартизации 2024-2026

1. **Конвергенция AI governance под зонтом ISO 42001 + EU AI Act.** К 2026-08 это de-facto обязательный стек для high-risk AI на EU рынке.
2. **Linux Foundation как dominant governance body для AI-native protocols** (AGENTS.md, MCP, A2A, AAIF created Dec 2025).
3. **Spec-driven development стал mainstream** (GitHub Spec Kit, OpenSpec, плюс community).
4. **Бенчмарки потеряли доверие из-за contamination** (SWE-bench Verified deprecated by OpenAI Q1 2026). Сдвиг к contamination-free (LiveCodeBench v6, SWE-bench Pro).
5. **METR time-horizon doubling accelerated** (4 месяца в 2025-26 vs 7 в 2019-25). Implication: SENAR-метрики долговечности гипотетических тесок становятся ключевыми.
6. **ISO/IEC 5338 + 29148 + 42001 = "the AI development trinity"** к 2026.
7. **Российские стандарты AI оформляются как identical adoption ISO** (ГОСТ Р 71476 = ISO 22989, 70462 = ISO 24029). Это **снижает барьер** для cross-jurisdiction compliance.
8. **DORA report 2025 показал negative correlation AI adoption ↔ delivery stability**, что усилило интерес к V-model + executable specs (см. ISO 26262/DO-178C ressurgence в AI debate).
9. **Появление "AI-native SDLC" как явной категории** (EPAM, Intetics, Xebia публикации 2026). Это та ниша, которую SENAR может занять как normative reference.
10. **CMMI и SAFe мигрируют в AI direction** (SAFe 6.0 AI spanning palette, CMMI v3 Performance Solutions), но без normative AI-native discipline. Gap для SENAR.

---

## 8. Топ-10 рекомендаций по позиционированию SENAR / RENAR

1. **Позиционировать SENAR как "operational implementation reference для ISO/IEC 42001 §8 в командах с coding-agents".** Это самый прибыльный angle на 2026-2027 — каждый ISO 42001 сертификант на high-risk EU рынке нуждается в process layer.

2. **Позиционировать RENAR как "ISO/IEC/IEEE 29148-compatible AI-native RE profile".** BR/SR/TR ↔ StRS/SyRS/SRS — это бесплатное credibility-bridging для крупных enterprise.

3. **Опубликовать SENAR/RENAR ↔ EU AI Act Annex IV crosswalk** — это превращает SENAR из "ещё одной методологии" в "AI Act compliance accelerator".

4. **Подать SENAR/RENAR через Agentic AI Foundation (Linux Foundation), НЕ через ISO TC.** ISO TC 22989/JTC1/SC42 — 18-36 мес и €€€. AAIF уже содержит AGENTS.md, MCP, A2A — это естественный дом для process+RE слоя.

5. **Сделать SENAR CLAUDE.md формат валидным AGENTS.md.** Это даёт инстант-совместимость с 15+ tools.

6. **Включить SBOM/SLSA gate в SENAR QG-3.** Provenance для AI-generated кода становится regulatory must (CRA EU 2027, US EO supply chain).

7. **Запустить "SENAR for ГОСТ 56939-2024" extension.** РФ enterprise/госсектор — рынок без alternativa. ГОСТ + ФСТЭК сертификация = revenue.

8. **Заключить partnership с IREB AI4RE для academic credibility.** RENAR становится reference reading для AI4RE 2027 микро-credential.

9. **Не подавать в IEEE 7000 series (этика scope) и не в OASIS (formal data std scope).** Они не подходят по mission.

10. **Альтернатива Linux Foundation — OpenJS Foundation** (если SENAR/RENAR сделают JS/TS implementation первой). OpenJS даёт быстрее governance структуру + dev-friendly community. Решение зависит от первичной аудитории (multi-language → AAIF; JS-first → OpenJS).

**Финальный совет по подаче:** **Linux Foundation / Agentic AI Foundation** — оптимальный путь. Опционально продублировать в **W3C Community Group** для веб-видимости (RENAR especially).

---

## 9. Источники

### SE / методологии
- [ISO/IEC/IEEE 12207:2017](https://www.iso.org/standard/63712.html) — Software life cycle processes
- [ISO/IEC/IEEE 15288:2023](https://www.iso.org/standard/81702.html) — Systems engineering life cycle
- [CMMI v3.0 (CMMI Institute)](https://cmmiinstitute.com/products/cmmi/content-release) — Capability Maturity Model Integration
- [SAFe 6.0 Framework](https://framework.scaledagile.com/) — Scaled Agile Framework
- [ISO/IEC 25010:2023](https://www.iso.org/standard/78176.html) — Product quality model
- [arc42 ISO 25010 update](https://quality.arc42.org/articles/iso-25010-update-2023) — quality model changes

### Requirements Engineering
- [ISO/IEC/IEEE 29148:2018](https://www.iso.org/standard/72089.html) — Requirements engineering
- [ISO/IEC/IEEE 29148:2018 (full text iteh sample)](https://cdn.standards.iteh.ai/samples/72089/62bb2ea1ef8b4f33a80d984f826267c1/ISO-IEC-IEEE-29148-2018.pdf)
- [SEBoK — ISO/IEC/IEEE 29148](https://sebokwiki.org/wiki/ISO/IEC/IEEE_29148)
- [IIBA BABOK Guide](https://www.iiba.org/knowledgehub/business-analysis-body-of-knowledge-babok-guide/)
- [IREB CPRE](https://cpre.ireb.org/en) + [AI4RE Micro-Credential](https://cpre.ireb.org/en/concept/ai4re-micro-credential)
- [INCOSE Systems Engineering Handbook v5](https://www.incose.org/resource/incose-systems-engineering-handbook-a-guide-for-system-life-cycle-processes-and-activities-5th-edition/)

### AI Governance
- [EU AI Act — official EC page](https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai)
- [EU AI Act 2026 Updates (Legal Nodes)](https://www.legalnodes.com/article/eu-ai-act-2026-updates-compliance-requirements-and-business-risks)
- [EC Draft Guidelines on AI Transparency (May 2026)](https://www.insideglobaltech.com/2026/05/12/10-takeaways-european-commission-draft-guidelines-on-ai-transparency-under-the-eu-ai-act/)
- [NIST AI RMF](https://www.nist.gov/itl/ai-risk-management-framework)
- [NIST AI 600-1 — GenAI Profile](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf)
- [ISO/IEC 42001:2023](https://www.iso.org/standard/42001)
- [ISO 42001 Certification Guide 2026 (ExamCert)](https://www.examcert.app/blog/iso-42001-ai-management-certification-2026/)
- [ISO/IEC 23894:2023 AI Risk Management](https://www.iso.org/standard/77304.html)
- [ISO/IEC 5338:2023 AI Life Cycle](https://www.iso.org/standard/81118.html)
- [ISO/IEC TR 24028:2020 AI Trustworthiness](https://www.iso.org/standard/77608.html)
- [OECD AI Principles 2024 update](https://oecd.ai/en/ai-principles)
- [OECD AI Principles Update (press release)](https://www.oecd.org/en/about/news/press-releases/2024/05/oecd-updates-ai-principles-to-stay-abreast-of-rapid-technological-developments.html)
- [IEEE 7000 series — OCEANIS](https://ethicsstandards.org/p7000/)
- [IEEE Global Initiative on Ethics of AIS](https://standards.ieee.org/industry-connections/activities/ieee-global-initiative/)

### Supply Chain
- [SLSA framework](https://slsa.dev/)
- [CycloneDX specification](https://cyclonedx.org/specification/overview/)
- [Sbomify 2026 compliance guide](https://sbomify.com/compliance/)
- [OpenChain ISO/IEC 5230](https://openchainproject.org/license-compliance)

### Safety-critical
- [DO-178C, IEC 62304, ISO 26262 (mndwrk overview)](https://www.mndwrk.com/blog/the-role-of-standards-in-safety-critical-qa-navigating-iso-26262-do-178c-and-iec-62304)
- [V-Model with AI coding agents (dev.to)](https://dev.to/ziv_kfir_aa0a372cec2e1e4b/why-the-v-model-is-the-natural-way-to-work-with-ai-coding-agents-17g6)

### Российские стандарты
- [ГОСТ Р 56939-2024 (cntd)](https://docs.cntd.ru/document/1310017763) — Защита информации. Безопасное ПО
- [ГОСТ 34.602-2020 (gostinfo)](https://www.gostinfo.ru/InformationOfStandardization/Details/2906)
- [ГОСТ Р 71476-2024 (cntd)](https://docs.cntd.ru/document/1310068314) — AI терминология
- [ГОСТ Р 70462.1-2022 (cntd)](https://docs.cntd.ru/document/1200193906) — NN robustness
- [Приказ ФСТЭК №230 от 30.06.2025 (garant)](https://www.garant.ru/products/ipo/prime/doc/412607823/)
- [Каталог стандартов AI (rst.gov.ru)](https://www.rst.gov.ru/portal/gost/home/standarts/aistandarts)

### Emergent AI-native
- [AGENTS.md spec](https://agents.md/) + [GitHub repo](https://github.com/agentsmd/agents.md)
- [GitHub Blog — AGENTS.md lessons from 2500 repos](https://github.blog/ai-and-ml/github-copilot/how-to-write-a-great-agents-md-lessons-from-over-2500-repositories/)
- [Anthropic — Model Context Protocol announcement](https://www.anthropic.com/news/model-context-protocol)
- [MCP Wikipedia](https://en.wikipedia.org/wiki/Model_Context_Protocol)
- [MCP adoption statistics 2026 (Digital Applied)](https://www.digitalapplied.com/blog/mcp-adoption-statistics-2026-model-context-protocol)
- [Google A2A Protocol announcement](https://developers.googleblog.com/en/a2a-a-new-era-of-agent-interoperability/)
- [A2A Spec](https://a2a-protocol.org/latest/specification/)
- [Linux Foundation — A2A 1 year](https://www.linuxfoundation.org/press/a2a-protocol-surpasses-150-organizations-lands-in-major-cloud-platforms-and-sees-enterprise-production-use-in-first-year)
- [IBM ACP overview](https://www.ibm.com/think/topics/agent-communication-protocol)
- [GitHub Spec Kit](https://github.com/github/spec-kit) + [GitHub Blog SDD](https://github.blog/ai-and-ml/generative-ai/spec-driven-development-with-ai-get-started-with-a-new-open-source-toolkit/)
- [Visual Studio Magazine — Spec Kit antidote to vibe coding (May 2026)](https://visualstudiomagazine.com/articles/2026/05/12/github-spec-kit-takes-off-as-antidote-to-piecemeal-vibe-coding.aspx)
- [llms.txt state May 2026 (codersera)](https://codersera.com/blog/llms-txt-complete-guide-2026/)
- [SE Ranking llms.txt study](https://seranking.com/blog/llms-txt/)

### Benchmarks
- [SWE-bench main](https://www.swebench.com/)
- [SWE-Bench Pro Leaderboard (Morph)](https://www.morphllm.com/swe-bench-pro)
- [LiveCodeBench leaderboard](https://livecodebench.github.io/leaderboard.html)
- [BigCodeBench](https://bigcode-bench.github.io/)
- [Morph AI Coding Benchmarks 2026](https://www.morphllm.com/ai-coding-benchmarks-2026)
- [METR Time Horizons](https://metr.org/time-horizons/)
- [METR limitations note (Jan 2026)](https://metr.org/notes/2026-01-22-time-horizon-limitations/)
- [Epoch AI METR Time Horizons](https://epoch.ai/benchmarks/metr-time-horizons)

### AI-native SDLC context
- [EPAM — Native AI SDLC 2026](https://www.epam.com/about/newsroom/in-the-news/2026/from-traditional-software-to-a-native-ai-sdlc-how-genai-is-redefining-engineering)
- [Intetics — State of AI-Native SE 2026](https://intetics.com/white-papers/the-state-of-ai-native-software-engineering-2026-industry-analysis/)
- [NIST AI Standards](https://www.nist.gov/artificial-intelligence/ai-standards)
