---
slug: resheniya-vklyuchayutsya-v-geyt-riska-publikatsii-naravne-s
task: brain-decide-publishes-unclassified-rationale
date: "2026-07-28"
edges: []
---

## Decision

Решения ВКЛЮЧАЮТСЯ в гейт риска публикации наравне с patterns/gotchas. Молчаливое исключение снято. Выбор ключей блоба переведён с двухветочного условия на словарь: неизвестная категория теперь ошибка, а не подмена чужими ключами.

## Rationale

Сессия #152, AC2. Гейт вызывается из store_record для ЛЮБОЙ категории, но начинался со строки `if category not in _CLASSIFIER_CATEGORY: return False`, а decisions там не было — между rationale решения и Notion оставался только scrub. Довод «маршрутизация уже отсеет» неполон: решения публикует не только decide. store_record с category=decisions достижим из brain_move (`brain move --to-brain` мигрирует накопленные локальные решения) и из MCP-хендлера brain — эти пути маршрутизацию не проходят, для них гейт единственная защита. Побочно вскрыта латентная ошибка: ключи блоба выбирались как `PATTERNS if category == "patterns" else GOTCHAS`, то есть ЛЮБАЯ третья категория молча читалась ключами gotchas. Для decisions это дало бы блоб из пустых строк -> «empty content» -> local -> high -> блокировку КАЖДОЙ публикации решений. Заменено словарём с явным KeyError.
