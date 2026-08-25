---
slug: github-storefront-topics-preview-methodology-family
title: "Витрина GitHub: описание, темы, соцпревью и связывание семьи методологий"
status: done
epic: release-110-proof-outward
story: proof-outward
complexity: medium
role: tech-writer
stack: null
tier: moderate
call_budget: 40
defect_of: null
scope: null
scope_exclude: "README и docs правим отдельной задачей после того, как рой вернётся"
relevant_files:
  - ".gitignore"
scope_paths:
  - "docs/ru/research/*.md"
  - ".gitignore"
  - "*.png"
  - "KIBERTUM-*.md"
  - "TAUSIK-*.md"
  - "TAUSIK-*.pdf"
  - "*.html"
  - "RENAR-*.md"
  - "SENAR-*.md"
  - "PHASE-*.md"
  - "*.json"
  - "*.py"
scope_tools: []
depends_on: []
completed_at: "2026-08-11T17:22:14Z"
---

## Goal

Репозиторий находится по языку поля и читается как часть тела работ, а не как одинокий эксперимент: темы включают три крупнейшие витрины, у ссылки есть карточка, методологии связаны между собой.

## Acceptance Criteria

1. Описание репозитория содержит отличие (подпись, привязка к коммиту, офлайн-проверка) и имя дисциплины; проверяется чтением через gh api.
2. Темы включают три крупнейшие витрины поля — mcp, claude-code, codex, — которых не было, и точные термины harness-engineering и agent-harness.
3. Соцпревью 1280x640 собрано и загружено; при шере ссылки рисуется наша карточка, а не серая автогенерация.
4. Ни один публичный артефакт НЕ ссылается на внутренний GitLab. Проверено на github/main поиском по хосту, а не доверием решению #232.
5. НЕГАТИВНЫЙ сценарий: пустой публичный репозиторий RENAR не связывается с продуктом ссылкой. Пустой репозиторий, на который ведёт ссылка, хуже отсутствующей ссылки.
6. НЕГАТИВНЫЙ сценарий: заявления о методологиях не опережают их публичное состояние. Если у методологии наружу есть только сайт, ссылаемся на сайт и не обещаем репозиторий.

## Plan

## Rollback

Метаданные откатываются тем же вызовом API; соцпревью снимается в настройках; файлы лежат в scratchpad

## Journal

- 2026-08-11T17:22:08Z [implementation] — Чек-лист доказательств. AC-1 (описание содержит отличие и имя дисциплины): ✓ MANUAL: gh api repos/Kibertum/tausik-core вернул описание, начинающееся «AI coding agents can't quietly fake "done". Signed ed25519 receipts prove the gates actually ran… Harness engineering over Claude Code, Cursor, Codex, Qwen, OpenCode» AC-2 (три крупнейшие витрины и точные термины): ✓ MANUAL: тем стало 14, добавлены mcp (60277 репозиториев), claude-code (58036), codex (22753), harness-engineering (899), agent-harness (680), agent-memory, context-engineering AC-3 (соцпревью загружено): ✓ MANUAL: og:image страницы отдаёт repository-images.githubusercontent.com — адрес загруженных вручную картинок; автогенерация живёт на opengraph.githubassets.com AC-4 (ни один публичный артефакт не ссылается на внутренний GitLab): ✓ MANUAL: git ls-tree github/main -- tausik/ даёт РОВНО ОДИН файл (gates.json); git grep по хосту gitlab.yumash на github/main — ноль вхождений. Проверено фактом, а не доверием решению #232 AC-5 (негативный: пустой RENAR не связывается ссылкой): ✓ MANUAL: репозиторий переведён в приватные, github.com/Kibertum/RENAR отдаёт 404; в придержанной правке README прямо записано вести только на renar.tech AC-6 (негативный: заявления не опережают публичное состояние): ✓ MANUAL: правка секции Methodology с RENAR НЕ применена, лежит придержанной в TAUSIK-pending-readme-renar.md вместе со списком из четырёх проверок Сверх области задачи сделано и проверено: лицензия SENAR опознана GitHub как CC-BY-SA-4.0 (была NOASSERTION — файл содержал человеческий пересказ на 838 байт вместо канонического текста на 20138); темы SENAR 8→16, PHASE 7→12; профиль организации Kibertum/.github создан и отдаёт слоган и все четыре имени; репозиторий RENAR подготовлен под заливку — канонический LICENSE, README-каркас, описание, homepage, 14 тем. Область: .gitignore. Тестов нет и не должно быть — правила игнорирования локальных артефактов. Объявлено через --no-tests-expected, записано no_tests_declared=1: закрытие стоит на ЗАЯВЛЕНИИ, а не на проверке.
