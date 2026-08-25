---
slug: flagi-vneshnih-binarey-proveryat-protiv-binarya-cargo
title: "Флаги внешних бинарей проверять против бинаря; cargo clippy имел '—' вместо '--'"
type: gotcha
tags:
  - cargo
  - external-binaries
  - flags
  - git
  - meta-testing
  - testing
task: verify-external-flags-against-real-binaries
edges: []
---

Класс, породивший релиз 1.6.0 (--no-config, флаг которого нет ни в одной версии pip): мы собираем argv для чужого бинаря руками, а тест мокает subprocess и закрепляет наше ПРЕДСТАВЛЕНИЕ о контракте, а не сам контракт.

Конкретный улов при обобщении пробы: stacks/rust/stack.json содержал 'cargo clippy — -D warnings' с длинным тире U+2014 вместо '--'. shlex.split даёт ['cargo','clippy','—','-D','warnings'] — тире уходит позиционным аргументом в clippy, а '-D warnings' не доходит до драйвера rustc. Никто не ловил: cargo не стоит ни на dev-машине, ни на CI. Исправлено на '--'.

Проба, обобщённая в tests/test_external_flags_are_real.py:
- git: валидирующая подкоманда (ls-files, cat-file, pull, config, diff, log, branch) даёт rc=129 'unknown option' на выдуманном флаге; реальный флаг — тот, что НЕ даёт. rev-parse «мягкий» (пропускает неизвестные флаги, rc=0) — его флаги проверять поведением (--is-inside-work-tree -> 'true', --show-prefix -> 'sub/'). '-c key=val' git принимает любой — что core.autocrlf/core.eol РАБОТАЮТ, доказывают CRLF-тесты поведением.
- прочие бинари: флаг-токен должен быть в выводе '<tool> [subcmd] --help'. Нет бинаря -> skip, не зелёный.
- каждая проба стережётся known-bogus кейсом (иначе бесполезна как мок).
- дешёвый статический тест поверх: ни одна gate-команда не содержит unicode-тире и все shlex-токенизируются без ошибки — ловит em-dash без всякого бинаря.

Поверхность флагов живёт в stacks/*/stack.json (gate command), default_gates.UNIVERSAL_GATES, auto_format.FORMATTERS. Центральный исполнитель — gate_command_runner (shlex, без shell; хвост '2>&1 | head -N' срезается _TRUNCATION_PIPE_RE и не является флагом).
