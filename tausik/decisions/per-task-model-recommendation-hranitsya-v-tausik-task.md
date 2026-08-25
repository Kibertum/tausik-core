---
slug: per-task-model-recommendation-hranitsya-v-tausik-task
task: v14c-auto-switch-model
date: "2026-05-07"
edges: []
---

## Decision

Per-task model recommendation хранится в .tausik/.task_recommendation.json — отдельно от .tausik/.session.json (skill_profile_session)

## Rationale

.session.json::model отвечает на вопрос «какой профиль АГРЕГИРОВАН по env > config > auto-detect и используется skill_profile_rebuild». .task_recommendation.json::model отвечает на вопрос «какую модель РЕКОМЕНДУЕТ task complexity для активной задачи». Разные lifetime (rebuild → пока сессия жива; recommendation → пока active task жив), разная природа (АГРЕГИРОВАН vs SUGGESTED). Объединение полей в одном файле потребовало бы расширить save_session_state whitelist (он сейчас отбрасывает extra keys) и риск путаницы при чтении. Отдельный файл — изоляция, проверена в tests/test_model_routing_session.py::test_record_does_not_touch_session_json.
