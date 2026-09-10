---
slug: write-gate-is-blind-to-pathlib-writes
title: "Гейт записи не видит pathlib: Rule 2 обеспечен только для перечисленных форм, а репозиторий написан неперечисленной"
status: blocked
epic: release-19-renar-conformance
story: release19-proof-integrity
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 60
defect_of: null
scope: null
scope_exclude: "Do not broaden beyond literal Python AST paths or alter unrelated host hook registries; no changes to user data, hook policy semantics outside recognized write forms, or CI."
relevant_files:
  - "scripts/hooks/python_source_writes.py"
  - "scripts/hooks/python_invocation.py"
  - "scripts/hooks/bash_write_parse.py"
  - "scripts/hooks/shell_statements.py"
  - "scripts/hooks/bash_write_gate.py"
  - "tests/test_write_gate_reads_code_not_text.py"
  - "tests/test_bash_write_gate_hook.py"
  - "tests/test_powershell_channel.py"
  - "tests/test_shell_statements.py"
  - "docs/en/enforcement-coverage.md"
  - "docs/ru/enforcement-coverage.md"
  - "docs/en/model-providers.md"
  - "docs/ru/model-providers.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "scripts/hooks/python_source_writes.py"
  - "scripts/hooks/python_invocation.py"
  - "scripts/hooks/bash_write_parse.py"
  - "scripts/hooks/shell_statements.py"
  - "scripts/hooks/bash_write_gate.py"
  - "tests/test_write_gate_reads_code_not_text.py"
  - "tests/test_bash_write_gate_hook.py"
  - "tests/test_powershell_channel.py"
  - "tests/test_shell_statements.py"
  - "docs/en/enforcement-coverage.md"
  - "docs/ru/enforcement-coverage.md"
  - "docs/en/model-providers.md"
  - "docs/ru/model-providers.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

ЗАМЕР, смена #241, найдено догфудингом на себе. Детектор записи python_source_writes.writes_in_inline_code возвращает ПУСТО на pathlib.Path("путь").write_text(...) — и на литеральной форме, и на форме через переменную. Проверено прямым вызовом: обе дают []. При этом open("путь","w") он ловит. Следствие измерено на живой смене: правки файлов scripts/backend_migrations_v43.py и других, сделанные через python - <<PY с pathlib, прошли мимо ACL области активной задачи без единого возражения, тогда как та же запись через cat >> была заблокирована немедленно. То есть Rule 2 обеспечен только для тех форм записи, которые кто-то перечислил, а pathlib в перечень не попал — при том что этим самым pathlib написан весь репозиторий. Это не теория: гейт объявлен write-enforced и в этом качестве описан в docs/ru/enforcement-coverage.md.

## Acceptance Criteria

AC-1 pathlib.Path(x).write_text/write_bytes/open('w') распознаются как запись в x — и когда путь литерал в самом вызове, и когда он связан переменной строкой выше. AC-2 Покрыты соседние формы того же семейства: Path(x).unlink, Path(x).rename, Path(x).mkdir, shutil.copy/move в x, os.replace. AC-3 НЕГАТИВ: чтение не считается записью — Path(x).read_text и open(x) без режима записи не дают срабатывания, иначе гейт заблокирует собственный разбор. AC-4 Перечень распознаваемых форм ОБЪЯВЛЕН в одном месте и назван в docs/ru/enforcement-coverage.md, а не спрятан в регулярном выражении: проверка, молча прощающая целые формы записи, показывает более строгий гейт, чем измерила. AC-5 Замер до и после: тот же python - <<PY с pathlib, записывающий вне области, ДО правки проходит, ПОСЛЕ блокируется.

## Plan

[{"step": "Reproduce every stated pathlib and neighbouring write/read form through the current inline-Python write detector; record the exact false-negative boundary.", "done": true}, {"step": "Find the single declaration point for recognized Python write operations and extend it without duplicating parser logic.", "done": true}, {"step": "Add parametrized behavioral tests for Path write/mutation and negative read-only forms, plus the controlled outside-ACL command regression.", "done": true}, {"step": "Update enforcement documentation and Codex support claim so it names the corrected coverage rather than a broader promise.", "done": true}, {"step": "Run focused hook/parser tests, dedupe, bootstrap/profile checks and signed verify; only then unblock the live Codex acceptance task.", "done": false}]

## Rollback

Расширение перечня распознаваемых форм записи в python_source_writes; откат — git revert. Гейт при откате возвращается к сегодняшнему поведению, ничего не ломая: он и сейчас пропускает эти формы.

## Journal

- 2026-09-10T07:10:06Z [implementation] — Шаг 1: воспроизведён исходный разрез и найдены реальные каналы. Общий AST-детектор читает только open; Bash и PowerShell оба доходят до него через write_targets. Ошибочный путь tests/test_pwsh_write_gate_hook.py отсутствует; ACL исправлен на существующий tests/test_powershell_channel.py до любой правки.
- 2026-09-10T07:12:57Z [implementation] — Уточнение после воспроизведения AC-5: exact форма python - <<PY требует безопасно извлечь только heredoc, который Python реально получает на stdin; добавлены общие python_invocation, bash_write_parse и shell_statements с существующими тестами. Не сканировать тело heredoc как shell: это прежний источник ложных срабатываний.
- 2026-09-10T07:17:44Z [implementation] — Шаги 2–4: единый каталог RECOGNISED_PYTHON_WRITE_FORMS введён в AST-читателе; добавлены Path, shutil, os и простая прямолинейная строковая привязка. Для exact python - <<PY heredoc извлекается отдельно и читается только при python_stdin, поэтому не превращает его прозу в shell. EN/RU граница и Codex Rule 2 теперь говорят о каталоге, а не о всеядном анализе. Focused cross-channel и Codex-profile suite: 583 passed; ruff clean; audit_pytest_dedupe без новой дублирующей структуры.
- 2026-09-10T12:13:26Z [implementation] — Step 5 verification: scoped critical verify #2389 executed ruff PASS and mapped 63 tests, but receipt status is git-mismatch. The worktree contains prior, separately-scoped Codex/release-composition changes from before this task started; they are not included in this task's ACL, so verify correctly refuses a presentable handle. Do not inflate this task's scope to make the receipt green. Focused manual evidence remains 583 passed, ruff clean, dedupe audit run.
