---
slug: mcp-doc-adapt-sign-row-still-describes-withdrawn-dual-signature
title: "docs/{en,ru}/mcp.md: строка tausik_adapt_sign всё ещё описывает отозванную двойную подпись клиента"
status: done
epic: release-19-renar-conformance
story: renar-contract-contour
complexity: simple
role: tech-writer
stack: null
tier: trivial
call_budget: 10
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "docs/en/mcp.md"
  - "docs/ru/mcp.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-09-06T20:59:16Z"
resolution: null
resolution_reason: null
---

## Goal

Задача adapt-dual-signature-implements-a-withdrawn-norm обновила описание инструмента в tools_adapt.py и вводные абзацы секции ADAPT в docs/{en,ru}/mcp.md, но не саму строку таблицы для tausik_adapt_sign: docs/en/mcp.md:146 и docs/ru/mcp.md:143 всё ещё гласят "architect signs the body with the project's ed25519 key, client signs with name+timestamp; both roles ⇒ approved" — а client-роль в adapt_sign теперь ОТКАЗЫВАЕТСЯ (ADR-011). Обновить обе строки под фактическое поведение (adapt_sign отвергает role=client, называя причину и ACTZ); свериться с tools_adapt.py как источником истины (правило "нет второй копии"). Найдено побочно при работе над actz-the-contract-contour-artifact-is-missing (правило "чужой дефект не поглощать").

## Acceptance Criteria

AC-1: docs/en/mcp.md строка tausik_adapt_sign (сейчас ~146) переписана под фактическое поведение: architect подписывает тело ed25519-ключом проекта — status→approved (единственная роль, дающая approved, §13.3.3 p.77); role=client ОТКАЗЫВАЕТСЯ методом, называя причину (ADR-011) и указывая на ACTZ как место, куда переехало одобрение клиента.
AC-2: docs/ru/mcp.md строка tausik_adapt_sign (сейчас ~143) переписана эквивалентно на русском, без деклонаций слова "акт" (FORBIDDEN_WORD_RE).
AC-3: текст сверен с tools_adapt.py:109 (описание инструмента) и service_adapts.py::adapt_sign (реальный отказ) как источником истины — не выдумано заново.
AC-4: doc-constants (gen_doc_constants.py --check) и полный прогон тестов зелёные после правки (строка не меняет счётчики инструментов, только описание).

## Plan

## Rollback

## Journal

- 2026-09-06T20:58:16Z [implementation] — AC-1: ✓ docs/en/mcp.md:146 переписана — architect ⇒ approved, role=client REFUSED с указанием ADR-011 и ACTZ; свёрено с service_adapts.py::adapt_sign строки 201-206 дословно (причина отказа). AC-2: ✓ docs/ru/mcp.md:143 переписана эквивалентно; python-проверка FORBIDDEN_WORD_RE на строке — 0 совпадений. AC-3: ✓ текст обеих строк сверен с tools_adapt.py:109 (описание инструмента) как источником истины, не выдуман заново. AC-4: ✓ gen_doc_constants.py --check = OK; tests/test_mcp_doc_tool_counts.py + test_adapts.py = 71 passed; полный прогон python -m pytest -q = 9318 passed, 27 skipped. Domain: строка теперь совпадает с реальным ServiceError текстом adapt_sign(role="client") — не перефразирована мимо смысла, использует те же три факта (ADR-011, отказ, ACTZ), что и живой код.
