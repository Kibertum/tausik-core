---
slug: pytest-s-neizvestnym-flagom-daet-kod-0-i-lenta-pri-etom-ne
title: "pytest с неизвестным флагом даёт КОД 0, и лента при этом НЕ ЗАПУСКАЕТСЯ"
type: gotcha
tags:
  - measurement
  - pytest
  - windows
task: memory-route-gate-did-not-get-the-base-directory
edges: []
---

Замер #206. Прогон полной ленты с --timeout=600 (плагина pytest-timeout в проекте нет) закончился строкой 'error: unrecognized arguments' и КОДОМ ВОЗВРАТА 0 в обёртке фонового запуска. Уведомление отчиталось 'completed exit code 0'. Если бы я прочитал только код, я бы записал зелёную ленту, которой не было. Это тот же класс, против которого заведена вся история evidence-primitives: 'не смогло выполниться' неотличимо от 'прошло'. Правило: у прогона ленты читай ПОСЛЕДНЮЮ СТРОКУ со счётом passed/failed, а не код возврата; счёт отсутствует - значит лента не шла.
