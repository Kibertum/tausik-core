---
slug: r18-classifier-drift-in-memory-merge-guidelines
title: "memory-merge-guidelines описывает классификатор как выбирающий local-vs-brain — тот же класс лжи, что чинили, но файл был пропущен"
status: done
epic: landscape-2026-h2
story: l26-narrative
complexity: simple
role: tech-writer
stack: null
tier: moderate
call_budget: 30
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/brain_classifier.py"
  - "docs/en/memory-merge-guidelines.md"
  - "docs/ru/memory-merge-guidelines.md"
  - "docs/en/shared-brain.md"
  - "docs/ru/shared-brain.md"
scope_paths:
  - "docs/en/memory-merge-guidelines.md"
  - "docs/ru/memory-merge-guidelines.md"
  - "docs/en/shared-brain.md"
  - "docs/ru/shared-brain.md"
  - "scripts/brain_classifier.py"
scope_tools: []
depends_on: []
completed_at: "2026-08-03T14:52:17Z"
---

## Goal

Найдено ревью партии. docs/{en,ru}/memory-merge-guidelines.md:7 и :23 утверждают, что classify() определяет, куда пойдёт запись (local или brain) — поведение, снятое решением #221. Там же :25 ссылается на service_knowledge.decide, который переехал в service_decide.py, и :66 цитирует brain_runtime.try_brain_write_decision, у которого в проде ноль вызывающих. Ровно тот класс дефекта, который чинила r18-docs-falsified-by-breaking-changes; файл в неё не попал, потому что я искал по строке про зеркалирование, а не по роли классификатора. Плюс: docstring scripts/brain_classifier.py:1 говорит 'route memory writes to local .tausik or shared brain' — то же неверное описание роли.

## Acceptance Criteria

AC1: ни один из двух файлов не утверждает, что classify() выбирает назначение записи; описана его нынешняя роль — оценка риска ЯВНОЙ публикации.
AC2: ссылка на service_knowledge.decide исправлена на service_decide (проверено по коду, а не по памяти).
AC3: упоминание brain_runtime.try_brain_write_decision либо убрано, либо помечено как не имеющее вызывающих в проде — читатель не должен считать его живым путём.
AC4: docstring scripts/brain_classifier.py приведён к той же правде; ru и en описывают один набор утверждений.
AC5 (негативный): поиск ведётся по РОЛИ ('решает куда', 'routes content', 'local vs brain'), а не по строке, которая уже чинилась. Если найден ещё файл того же класса — заносится в журнал с файлом и строкой. Ноль найденного при непроверенном поиске считается провалом, а не успехом: именно узкий поиск и пропустил этот файл в прошлый раз.

## Plan

## Rollback

Правки в docs/{en,ru}/memory-merge-guidelines.md и в докстринге; git revert одного коммита.

## Journal

- 2026-08-03T14:51:23Z [implementation] — AC5 СРАБОТАЛ — поиск ПО РОЛИ нашёл больше, чем было объявлено, и в файле, который я уже 'починил'. Объявлено было три места в memory-merge-guidelines. Поиск по роли ('routes content', 'picks local vs brain', 'выбирает local vs brain', 'направляет контент', 'route memory writes') дал ещё ДВА — в docs/en/shared-brain.md:281 и docs/ru/shared-brain.md:280, в разделе 'Приватность'. Это тот самый файл, где я в задаче r18-docs-falsified-by-breaking-changes правил пункт 2 списка Enforcement и не заметил, что тот же тезис повторён ниже в другом разделе. Область задачи расширена осознанно, а не обойдена. ТРЕТЬЯ НАХОДКА, попутная: RU-версия shared-brain.md называла brain_scrubbing и brain_classifier 'задача ..., в планах', тогда как EN говорит 'shipped', и оба модуля действительно лежат в scripts/. Русское зеркало отстало на несколько версий. Исправлено вместе с ролью. ЧЕГО НЕ СТАЛ ДЕЛАТЬ. docs/*/research/* содержат старые имена тестов вроде test_content_with_src_file_marker_routes_local — это архив исследований с датами в имени, он описывает состояние на свою дату и переписывать его было бы подделкой записи. audit_stale_docs исключает research/ по глобу намеренно.
- 2026-08-03T14:51:24Z [implementation] — ВЕРИФИКАЦИЯ: AC-1: ✓ повторный поиск по РОЛИ (не по строке) даёт ноль совпадений вне архива research/. Проверено пятью формулировками роли в двух языках. AC-2: ✓ ссылка на service_knowledge.decide заменена на service_decide.record — проверено по коду: scripts/service_decide.py:44 def record, и его докстринг называет три назначения. AC-3: ✓ упоминание brain_runtime.try_brain_write_decision оставлено, но помечено: 'с 1.8 нет ни одного вызывающего в проде'. Проверено grep по scripts/ и harness/ — только определение на brain_runtime.py:157 и упоминание в докстринге соседа. Убирать упоминание совсем было бы хуже: функция жива и умеет писать в Notion, читатель должен знать, что путь мёртв, а не что его нет. AC-4: ✓ докстринг scripts/brain_classifier.py переписан: назван снявший решение (#221), назван единственный вызывающий в проде (brain_publish_flow.assess_publish_risk) и сказано, что поле target сохранило имя, но стало СУЖДЕНИЕМ, а не инструкцией маршрутизации. Сигналы не тронуты — изменился потребитель, а не классификатор. AC-5 (негативный): ✓ см. предыдущую запись — поиск по роли нашёл на два места больше объявленного, оба занесены с файлом и строкой. Гейты: ✓ scripts/docs_lint.py -> clean; scripts/doc_drift_scanners.py -> exit 0; pytest -k 'classifier or brain or doc' -> 1018 passed, 7 skipped. Domain: результат осмыслен вне тестов — читатель, планирующий выгрузку знания наружу, больше не думает, что за него это решит классификатор.
