---
slug: unicodedecodeerror-v-potoke-chitatele-subprocess
title: "UnicodeDecodeError в потоке-читателе subprocess маскируется под TypeError: NoneType is not iterable"
type: gotcha
tags:
  - debugging
  - encoding
  - hooks
  - subprocess
  - windows
task: hook-stderr-encoding-locale-dependent
edges: []
---

СИМПТОМ: тест падает с «TypeError: argument of type 'NoneType' is not iterable» на строке вроде `assert "текст" in result.stderr`. Про кодировку не сказано ни слова.

ПРИЧИНА: subprocess.run(..., text=True) без encoding= декодирует вывод ребёнка кодировкой РОДИТЕЛЯ. Если не совпало, UnicodeDecodeError падает внутри потока-читателя subprocess, а не в основном. Основной поток получает stdout/stderr равными None. Дальше любая работа со строкой даёт TypeError про NoneType — то есть выглядит как баг вызывающего.

ГДЕ ЛОВИТЬ: расхождение возникает, когда родитель и ребёнок запущены по-разному. Классический случай — `python -X utf8 -m pytest` при том, что тест зовёт ребёнка через голый sys.executable. Тест «то падает, то нет в зависимости от флага запуска» — почти всегда это.

ДИАГНОСТИКА ЗА ОДИН ШАГ: убрать text=True и посмотреть сырые байты. Не-ASCII в кодировке локали виден сразу (b'2\xd7 ... \x97' вместо b'2\xc3\x97 ... \xe2\x80\x94').

ЛЕЧЕНИЕ ОБА КОНЦА: пишущий форсирует UTF-8 у себя (не полагаясь на флаг запуска), читающий передаёт encoding явно. Закреплено гейтом tests/test_hook_encoding.py.

Смежно: [[225]] (машинная правка съедает код), [[236]] (разовую находку закрывать гейтом).
