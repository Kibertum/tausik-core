---
slug: test-stabyaschiy-preduslovie-radi-zelenogo-pryachet-dyru
title: "Тест, СТАБЯЩИЙ предусловие ради «зелёного», прячет дыру вместо проверки — адверсариальное ревью обязательно"
type: convention
tags:
  - adversarial-review
  - escape
  - fail-closed
  - gate
  - testing
task: defect-fileless-close-fail-open-no-verify-gates
edges: []
---

Если тест обходит неудобное состояние стабом в ХАРНЕССЕ, он документирует осведомлённость о состоянии, но НЕ проверяет его — дыра остаётся. Реальный кейс (сессия #126): fileless-close git-проверка стояла ПОСЛЕ `if not verify_gates: return`. Тесты родительской задачи (_stub_verify_gates) ВСЕГДА возвращали непустые verify-гейты, комментарий в conftest честно писал «so the fileless branch (after the early return) is reached» — то есть харнесс ОБХОДИЛ ранний возврат, а не тестировал ветку с пустыми гейтами. Fail-open (грязное дерево закрывается + ложный audit-флаг) прошёл scoped verify И полный suite; поймало только адверсариальное ревью (defect-fileless-close-fail-open-no-verify-gates, defect_of qg2-cannot-close-fileless-task).

ПРАВИЛО: когда стабишь предусловие, чтобы дойти до тестируемой ветки, ОБЯЗАТЕЛЬНО добавь второй тест с ПРОТИВОПОЛОЖНЫМ значением предусловия (здесь: get_gates_for_trigger→[]), проверяющий, что инвариант держится и там. Инвариант fail-closed проверяется на КАЖДОМ пути, а не на удобном.

СЛЕДСТВИЕ для процесса: высокорисковые/security-adjacent гейты — под адверсариальное ревью на ОТДЕЛЬНОЙ модели (SENAR Rule 4), а не только под собственные тесты автора: автор стабит вокруг слепого пятна, ревьюер ищет именно его. Это второй escape-через-узкую-верификацию за сессию — усиливает [[267]].
