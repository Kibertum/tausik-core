---
slug: zamer-sessiy-196-265-smena-266-ni-odna-iz-70-smen-ne
title: "Замер сессий #196–#265 (смена #266): ни одна из 70 смен не достигла 180 активных минут; агентов останавливали ёмкость 200 вызовов и ритуал, а не время"
type: context
tags:
  - "1.10"
  - capacity
  - measurement
  - senar
  - session
task: null
edges: []
---

Команда: tausik session recompute --limit 70 (порог простоя 10 мин). Активные минуты: медиана около 60–75, p90 около 145, максимум 246 (смена #241); ни одна смена не пересекла 180 активных; событий session_extend — 0 за всю историю. Wall-clock искажён: #265 висела 12841 мин при 76 активных, #242 — 3908 при 172. Итоги 13 смен упоминают capacity (пример #245: capacity gate exhausted; #244: capacity consumed by closures); смены #252–#260 — девять подряд по 13–82 минуты, перезапущенные ради сброса счётчика, большинство без итога. Вывод для проектирования 1.10 E: ворота, о которые встают агенты, — гейт ёмкости и отказ QG-0 по времени (gate_qg0_check: session_check_duration_fn; service_recording.check_session_capacity), оба не являются Quality Gates по SENAR 1.5 §8.6(a) и не входят в Core; лимит 180 — capability-dependent положение, подлежащее пересмотру по §10.13. Базовая линия метрик до перестройки: Throughput 5.72 задач/сессия, FPSR 91.2%, DER 9.5%, Dead End Rate 2.0%, калибровка 1.03 (n=10).
