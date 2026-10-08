---
slug: glab-api-skleivaet-neskolko-json-v-odnom-otvete-rezh-ne-po
title: "glab api склеивает несколько JSON в одном ответе — режь не по ](?=[, а разбирай циклом raw_decode"
type: gotcha
tags:
  - gitlab
  - glab
  - json
  - tooling
task: doc-values-of-closed-lists-have-no-guard
edges: []
---

Правило из прежних передач «режь по ](?=[» в #213 не сработало: склейка была другой формы (после ] шёл не [), и json.loads упал «Extra data: char 669». Устойчивый разбор: json.JSONDecoder().raw_decode в цикле — пропускаем всё до ближайшего '[' или '{', декодируем один объект, продолжаем с конца. Собираем список из всех кусков. Одна форма читает и один объект, и склейку любого числа массивов, независимо от того, чем они разделены.
