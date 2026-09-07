---
slug: class-surface-baseline-podnyat-pod-podlozhku-grafa
task: null
date: "2026-09-07"
edges: []
---

## Decision

class_surface baseline поднят под подложку графа артефактов: SQLiteBackend 159→168 (+9, GraphCrudMixin), ProjectService 143→148 (+5, ArtifactGraphMixin: graph_index_paths, graph_stale_artifacts, graph_build_cochange, graph_build_declared, neighbours_of). Рост оплачен тем, что подложка ЗАМЕНЯЕТ отсутствующий механизм, а не дублирует существующий: код и документация становятся сущностями в ТОЙ ЖЕ БД, memory_edges не трогается. Приватные помощники слоя 1 (_declared_from_crosscutting, _declared_from_tasks, _edge_to_declared_path) в счёт не входят и намеренно оставлены приватными: наружу отдаются два строителя слоёв и один запрос, а не пятнадцать мелких операций. Модульные classify/fingerprint тоже вне класса — чистые, состояния не требуют, та же экономия, что применена к route_at_tc решением #330.

## Rationale
