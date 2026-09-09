---
slug: write-gate-is-blind-to-pathlib-writes
title: "Гейт записи не видит pathlib: Rule 2 обеспечен только для перечисленных форм, а репозиторий написан неперечисленной"
status: planning
epic: release-19-renar-conformance
story: evidence-and-hygiene-debt-paid-in-19
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

ЗАМЕР, смена #241, найдено догфудингом на себе. Детектор записи python_source_writes.writes_in_inline_code возвращает ПУСТО на pathlib.Path("путь").write_text(...) — и на литеральной форме, и на форме через переменную. Проверено прямым вызовом: обе дают []. При этом open("путь","w") он ловит. Следствие измерено на живой смене: правки файлов scripts/backend_migrations_v43.py и других, сделанные через python - <<PY с pathlib, прошли мимо ACL области активной задачи без единого возражения, тогда как та же запись через cat >> была заблокирована немедленно. То есть Rule 2 обеспечен только для тех форм записи, которые кто-то перечислил, а pathlib в перечень не попал — при том что этим самым pathlib написан весь репозиторий. Это не теория: гейт объявлен write-enforced и в этом качестве описан в docs/ru/enforcement-coverage.md.

## Acceptance Criteria

AC-1 pathlib.Path(x).write_text/write_bytes/open('w') распознаются как запись в x — и когда путь литерал в самом вызове, и когда он связан переменной строкой выше. AC-2 Покрыты соседние формы того же семейства: Path(x).unlink, Path(x).rename, Path(x).mkdir, shutil.copy/move в x, os.replace. AC-3 НЕГАТИВ: чтение не считается записью — Path(x).read_text и open(x) без режима записи не дают срабатывания, иначе гейт заблокирует собственный разбор. AC-4 Перечень распознаваемых форм ОБЪЯВЛЕН в одном месте и назван в docs/ru/enforcement-coverage.md, а не спрятан в регулярном выражении: проверка, молча прощающая целые формы записи, показывает более строгий гейт, чем измерила. AC-5 Замер до и после: тот же python - <<PY с pathlib, записывающий вне области, ДО правки проходит, ПОСЛЕ блокируется.

## Plan

## Rollback

Расширение перечня распознаваемых форм записи в python_source_writes; откат — git revert. Гейт при откате возвращается к сегодняшнему поведению, ничего не ломая: он и сейчас пропускает эти формы.

## Journal
