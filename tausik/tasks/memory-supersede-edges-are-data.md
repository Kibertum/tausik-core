---
slug: memory-supersede-edges-are-data
title: "Отменяющие связи в памяти живут в промпте, а не в данных"
status: planning
epic: release-112-knowledge
story: release112-knowledge
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: null
resolution: null
resolution_reason: null
tracker_refs:
  - "github#145"
started_model_id: null
started_model_version: null
done_model_id: null
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

ЗАМЕР #189, И ОН НЕ ОСТАВЛЯЕТ МЕСТА ТОЛКОВАНИЮ. Ребро `supersedes` в memory_edges СУЩЕСТВУЕТ и применено: 425 supersedes 421 («правило подмешивать пять имён ОТМЕНЕНО»). При этом `tausik memory block` — единственный текст, который агент получает в контекст, — печатает #425 и #421 РЯДОМ, как равные действующие конвенции. Ребро не читается там, где оно единственно и имеет значение. СЛЕДСТВИЕ, НАБЛЮДАЕМОЕ ЖИВЬЁМ: владелец вынужден каждый раз писать в рукописном вводном промпте «ПРАВИЛО ПЯТИ ИМЁН УМЕРЛО. Не воскрешай его». Ручная компенсация машинного отказа. МАСШТАБ: рёбер в memory_edges ЧЕТЫРЕ на 426 памяток и 270 решений. Из них supersedes — два. То есть подложка построена и почти не используется, а единственные два применения игнорируются потребителем. ЧТО ДЕЛАЕТСЯ: (1) блок памяти перестаёт втягивать отменённое как действующее — отменённая запись показывается ТОЛЬКО вместе с отменившей и с явной пометкой; (2) ребро становится дешёвым в постановке: `memory add --supersedes N` одним вызовом вместо «добавь, потом свяжи»; (3) РАСШИРЕНИЕ НА РЕШЕНИЯ — memory_edges уже несёт source_type/target_type, значит decision->decision выражается тем же механизмом без новой таблицы (смежная задача decisions-have-no-lifecycle делает командную часть). НЕГАТИВНОЕ, ДВУСТОРОННЕЕ: отменённая запись НЕ УДАЛЯЕТСЯ и остаётся находимой поиском — история опровержений и есть ценность проекта; и она обязана появляться в выдаче поиска С ПОМЕТКОЙ, а не тихо исчезать, иначе следующий агент повторит уже опровергнутый заход. Проверять обеими сторонами: отменённое ушло из блока И осталось в поиске.

## Acceptance Criteria

## Plan

## Rollback

Тип ребра плюс фильтр в сборке блока. Откат — git revert; записи памяти не удаляются ни на каком шаге.

## Journal
