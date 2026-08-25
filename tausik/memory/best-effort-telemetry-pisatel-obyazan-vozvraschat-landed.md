---
slug: best-effort-telemetry-pisatel-obyazan-vozvraschat-landed
title: "Best-effort telemetry-писатель обязан возвращать landed/miss bool — иначе caller ложно утверждает успех, убивая фальсифицируемость"
type: convention
tags:
  - best-effort
  - falsifiability
  - review
  - supervision
  - telemetry
task: s128-review-fixes-supervision-provenance
edges: []
---

Паттерн best-effort (глотать все ошибки, не блокировать) правильный для fire-and-forget вызова из хука. НО если у писателя есть caller, который РАПОРТУЕТ результат (CLI печатает «Recorded», скрипт/CI проверяет), молчаливое проглатывание провала делает неудачную запись неотличимой от успеха — ровно в той точке, где человек/скрипт может проверить. Это убивает тезис фальсифицируемости (release 1.8): «сколько раз надзор обошли» становится непроверяемым, если сама запись обхода могла молча не лечь.

Правило: best-effort писатель ВОЗВРАЩАЕТ bool (landed/miss), не None. Fire-and-forget caller (хук) просто игнорирует bool — поведение не меняется. Рапортующий caller (CLI events emit-supervision) печатает WARNING в stderr + exit≠0 при miss. Так provenance провала сохраняется без принуждения записи.

Пример: hook_supervision.emit_supervision_bypass/degradation/_emit_supervision → bool; project_cli_events.cmd_events_emit_supervision печатает WARNING+SystemExit(1) при False. Найдено адверс-ревью s128 (HIGH-1).

Смежно: [[cross-харнесс-телеметрия-через-CLI-к-Python-оракулу]] — именно эта CLI-команда была единственной точкой проверки для JS-плагина. Урок #268 (адверс-ревью обязателен для security-adjacent) подтверждён снова: ревью поймало 2 HIGH в уже закрытом батче.
