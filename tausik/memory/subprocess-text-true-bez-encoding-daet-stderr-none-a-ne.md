---
slug: subprocess-text-true-bez-encoding-daet-stderr-none-a-ne
title: "subprocess text=True без encoding даёт stderr=None, а не мусор: ошибка тонет в потоке-читателе"
type: gotcha
tags:
  - encoding
  - subprocess
  - testing
  - windows
task: subprocess-run-in-a-string-literal-has-text-true-no-encoding
edges:
  - relation: relates_to
    target_type: memory
    target: windows-tausik-tausik-iz-subprocess-ne-zapuskaetsya-nuzhen
---

subprocess.run(..., text=True) БЕЗ encoding= на Windows не «портит строку» — он делает ХУЖЕ. UnicodeDecodeError поднимается ВНУТРИ потока-читателя subprocess (subprocess.py::_readerthread), туда же и проглатывается, а вызывающий получает stderr = None. Замерено в #199: preferred encoding cp1252, кириллица в stderr, r.stderr is None; с encoding='utf-8' та же строка приходит целой.
ПОЧЕМУ ЭТО ОСОБЕННО ЗЛО В ТЕСТАХ: типовая строка assert p.returncode == 0, p.stderr при таком отказе печатает None. Причина падения стирается ровно тем механизмом, который должен был её показать.
ДЕТЕКТОР, ИЩУЩИЙ encoding= В ОКНЕ ВОКРУГ subprocess.run, НЕНАДЁЖЕН — и это доказано, а не предположено. tests/test_claudemd_audit_hook.py стр.232 пережил ШЕСТЬ смен именно потому, что двумя строками выше стоит encoding='utf-8' у ВЛОЖЕННОГО pathlib.Path.write_text. Окно видит подстроку, вердикт получается ложно-зелёный. Негативная ветвь замера: на заведомо голом вызове тот же сканер отвечает «не нашёл» верно — значит ломается привязка к окну, а не сканер.
ПРАВИЛО: находку encoding= привязывай к КОНКРЕТНОМУ вызову (разбор AST, а не окно строк). Проверяя чужой код глазами — читай, ЧЬЁЙ функции принадлежит найденный encoding=.
