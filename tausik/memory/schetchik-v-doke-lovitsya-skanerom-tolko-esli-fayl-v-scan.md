---
slug: schetchik-v-doke-lovitsya-skanerom-tolko-esli-fayl-v-scan
title: "Счётчик в доке ловится сканером, только если файл в scan-target-списке — иначе дрейф молчит"
type: convention
tags:
  - doc-drift
  - enforcement
  - hooks
  - scanner
task: docs-enforcement-drift-matrix
edges: []
---

doc-drift сканер счётчиков (scan_code_counts/scan_mcp_counts) обходит ТОЛЬКО файлы из явных target-кортежей (CROSS_FILE_SCAN_TARGETS + *_EXTRA_TARGETS). Файл с захардкоженным числом ВНЕ этих списков (как hooks.md с '20 Python hooks') дрейфует молча — gen_doc_constants --check вернёт OK. Правило: любой .md, где число сверяется с constants.json, ОБЯЗАН быть в target-списке. Файлы с историческими version-ссылками (v1.4 и т.п.) клади в *_COUNT_EXTRA_TARGETS (только счётчики, не версии), НЕ в CROSS_FILE_SCAN_TARGETS — иначе version-сканер зафлагает исторические маркеры. Второй слой слепоты: adjacency-паттерн '\\b(\\d+)\\s+hooks\\b' пропускает квалификатор между числом и существительным ('22 Python hooks', '21 активный хук') — квалификатор держи явным allow-list, НЕ \\w+ (иначе поглотит посторонний предлог). Отдельный класс дефекта: доки, заявляющие УРОВЕНЬ enforcement (Warning vs Hard) — опаснее count-drift, свежий агент решает что гейта нет там где он есть. Сверяй с кодом гейта, не с прежним текстом доки.
