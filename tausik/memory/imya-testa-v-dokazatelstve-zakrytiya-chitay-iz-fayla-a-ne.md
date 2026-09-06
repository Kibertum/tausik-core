---
slug: imya-testa-v-dokazatelstve-zakrytiya-chitay-iz-fayla-a-ne
title: "Имя теста в доказательстве закрытия ЧИТАЙ из файла, а не пиши по памяти — и никаких глобов"
type: convention
tags:
  - audit
  - closure
  - evidence
  - renar
task: at-red-with-tc-green-routes-to-interpretation-not-code
edges: []
---

Ссылаясь на тест в AC-доказательстве при закрытии задачи, СНАЧАЛА прочитай имя из файла (grep "def test_" по нужному файлу), только потом пиши. Глоб вида tests/test_at.py::test_route_at_tc_* ссылкой НЕ является — резолвер обрежет его до несуществующего имени.

Почему: в смене #220 при закрытии at-red-with-tc-green-routes-to-interpretation-not-code четыре имени написаны по памяти (test_record_result_appends_not_overwrites, test_diagnose_never_exercised_refuses, test_release_readiness_blocks_on_stale, test_release_readiness_blocks_on_non_green) — ни одного из них в tests/test_at.py нет; реальные имена другие (test_record_result_then_list_history, test_diagnose_without_a_recorded_trial_errors, test_release_readiness_false_when_stale, test_release_readiness_false_when_latest_outcome_is_red). Покрытие было реальным и зелёным — гнилой оказалась ССЫЛКА, то есть закрытие стало непроверяемым для свежего читателя, ровно тот дефект, ради которого существует `tausik audit evidence`.

Как применять: перед task done / task log с AC-доказательством — один grep по файлу теста, имена копируй дословно. Тест написан МИНУТУ назад — это НЕ основание доверять памяти: в том же закрытии ошибочными оказались имена тестов, написанных в этой же сессии. Проверить постфактум: `tausik audit evidence` (read-only, никогда не блокирует) печатает NEVER_EXISTED/ROTTED с указанием задачи-источника.
