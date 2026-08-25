---
slug: perenesti-is-tausik-project-vyshe-skip-telemetry-v-task
title: "Перенести is_tausik_project() выше skip-telemetry в task_gate.py, scope_write_gate.py, memory_pretoo"
type: dead_end
tags: []
task: hook-skip-emit-before-jurisdiction-check
edges: []
---

Approach: Перенести is_tausik_project() выше skip-telemetry в task_gate.py, scope_write_gate.py, memory_pretool_block.py, чтобы каталог вне юрисдикции не получал supervision-строку (находка ревью s128, LOW)
Reason: Посылка находки невозможна по построению, проверено эмпирически. is_tausik_project = isdir('.tausik'), а _emit_supervision требует '.tausik/tausik.db'. Существование БД ВЛЕЧЁТ существование каталога, поэтому предикат юрисдикции строго СЛАБЕЕ предусловия записи: каталог со стрэй tausik.db всегда возвращает is_tausik_project=True, то есть он в юрисдикции, и строка законна. Каталог без .tausik/ даёт emit landed=False. Сценарий «вне юрисдикции, но строка приземлилась» недостижим ни при каком состоянии диска.

Перестановка была бы поведенчески нейтральной правкой в трёх security-хуках, ломающей установленный в suite порядок, ради нуля. Не делаем.

Побочный результат ценнее самой находки: асимметрия существует, но в ОБРАТНУЮ сторону — '.tausik/' есть, БД нет (окно bootstrap→init, а также заблокированная/битая БД в любой момент) ⇒ юрисдикция ЕСТЬ, TAUSIK_SKIP_HOOKS сработал, а bypass-строка НЕ приземлилась. emit_supervision_bypass честно возвращает False, но все три хука этот bool игнорируют — то есть счёт выключений заявлен фальсифицируемым, а по факту имеет неучтённые потери. Выведено в задачу hook-bypass-telemetry-silent-miss.
