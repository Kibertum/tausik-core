---
slug: sostav-reliza-1-9-pereskazan-odnoy-strokoy-potomu-chto
task: roadmap-reads-an-additive-decision-as-the-whole-composition
date: "2026-09-13"
edges: []
---

## Decision

Состав релиза 1.9 пересказан ОДНОЙ строкой, потому что генератор ROADMAP.md читал дополняющее решение #363 как полный состав и объявил десять историй #360 «не входящими». Пересказ ничего не меняет по существу: он объединяет решения владельца #360 (десять историй релиза), #361 (release19-proof-integrity и release19-effective-context), #362 (1.9 ограничена #358, #360, #361 — уход от Notion входит), #363 (kb-docs — 1.9) и #366 (три тикета GitLab под release19-proof-integrity). Устав: #360. Состав: agent-output-discipline, context-carries-over-between-sessions, guarantees-are-not-claude-only, verification-off-the-critical-path, the-loop-closes-outward, evidence-primitives, gates-declare-what-they-prevent, renar-contract-contour, test-evidence-not-test-volume, codex-first-class-19, release19-proof-integrity, release19-effective-context, knowledge-sheds-notion-and-its-hygiene, kb-docs. Впредь состав меняется только решением, несущим строку «Состав:»; решение, лишь упоминающее истории, состав не переопределяет.

## Rationale

Замер смены #251: ROADMAP.md в разделе «Вопрос версии» цитировал #360 с десятью историями релиза, а разделом ниже перечислял те же десять как «в релиз НЕ входит» — `doc roadmap --check` при этом зелёный, потому что проверяет свежесть, а не правду. Состав — объявление владельца, и читаться он должен из строки, написанной как объявление, а не выводиться из любых двух слагов в прозе.
