---
slug: tekstovyy-stdin-subprocess-na-windows-perevodit-n-v-r-n
title: "Текстовый stdin subprocess на Windows переводит \\n в \\r\\n — строковые протоколы git кормить bytes"
type: gotcha
tags:
  - crlf
  - git
  - subprocess
  - windows
task: next-version-reads-the-journal-tip-not-its-history
edges: []
---

subprocess.run(input="abc\n", text=True) на Windows открывает трубу через TextIOWrapper с newline=None, и ребёнок получает "abc\r\n". Замер: git hash-object --stdin, накормленный строкой "abc\n", дал НЕ 8baef1b4 (хэш блоба abc\n), а другой хэш; bytes b"abc\n" под binary=True дали ожидаемый. Для cat-file --batch и любого построчного протокола git — только bytes и binary=True; в git_exec.run это записано в докстринге параметра input.
