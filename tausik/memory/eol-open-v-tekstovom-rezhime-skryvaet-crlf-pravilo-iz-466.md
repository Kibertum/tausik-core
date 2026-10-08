---
slug: eol-open-v-tekstovom-rezhime-skryvaet-crlf-pravilo-iz-466
title: "EOL: open() в текстовом режиме СКРЫВАЕТ CRLF — правило из #466 без newline=\"\" вырождено"
type: gotcha
tags:
  - encoding
  - eol
  - python
  - windows
task: our-conformance-claim-rests-on-a-mode-the-standard-removed
edges: []
---

ПАМЯТЬ #466 ПРЕДПИСЫВАЕТ eol = "\r\n" if "\r\n" in s else "\n". ЭТО НЕ РАБОТАЕТ, если s прочитан обычным open(p, encoding="utf-8"): режим universal newlines разворачивает \r\n в \n ПРИ ЧТЕНИИ, поэтому "\r\n" in s ВСЕГДА False. Условие вырождено, ветка CRLF недостижима, и всякий CRLF-файл молча переписывается в LF.
ЗАМЕРЕНО ЖИВЬЁМ В #199, НЕ ВЫВЕДЕНО ИЗ ДОКУМЕНТАЦИИ: в scripts/ на диске 215 файлов CRLF и 105 LF; текстовое чтение заведомо CRLF-файла даёт chr(13) in s == False.
ПРАВИЛЬНО: читать с newline="" — io.open(p, encoding="utf-8", newline="").read(). Тогда перевода нет, "\r\n" in s отвечает по факту, и запись с newline="" сохраняет исходные окончания. Проверка на бинарном уровне: io.open(p,"rb").read() и искать b"\r\n".
ПОЧЕМУ УЩЕРБ БЫЛ МАЛ ИМЕННО ЗДЕСЬ: core.autocrlf=true, git нормализует в обе стороны, поэтому git status остаётся чистым и дифф не раздувается. Это МАСКИРОВКА, а не отсутствие дефекта: файл вне git, файл под .gitattributes с eol=crlf или носитель без нормализации получат тихую порчу. В этом же репозитории .gitattributes уже держит renar/** text eol=lf — то есть места, где EOL значим, тут ЕСТЬ.
