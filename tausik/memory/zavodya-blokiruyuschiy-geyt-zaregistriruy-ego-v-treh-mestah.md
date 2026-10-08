---
slug: zavodya-blokiruyuschiy-geyt-zaregistriruy-ego-v-treh-mestah
title: "Заводя БЛОКИРУЮЩИЙ гейт, зарегистрируй его в ТРЁХ местах, иначе полный прогон краснеет тремя тестами сразу"
type: convention
tags:
  - degeneracy
  - gates
  - registry
task: test-proliferation-has-a-report-but-no-gate
edges: []
---

Мало написать scripts/gate_<имя>.py и добавить GateSpec в gate_registry. Полный прогон потребовал ещё двух записей: (1) tausik/gates.json → red_proofs.<имя> = {test, violation} — тест, который вручает гейту НАРУШЕНИЕ и требует красного; без него gate_degeneracy краснеет «a blocking gate is in force with no red_proofs entry» (это наш перенос ADR-021: контроль, разучившийся падать, проходит весь свой счастливый путь); (2) tests/test_gates_catch_their_violation.py → COVERED или EXCUSED, причём EXCUSED требует НАЗВАТЬ модуль и оба имени тестов (красный и зелёный), и они сверяются по AST. Плюс mypy строг к результату collect_duplicates: sum(len(g["members"])) требует явной аннотации list[dict[str, Any]]. Порядок такой: гейт → GateSpec → red_proofs → классификация → полный прогон.
