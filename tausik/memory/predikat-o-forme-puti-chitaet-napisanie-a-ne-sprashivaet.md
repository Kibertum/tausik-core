---
slug: predikat-o-forme-puti-chitaet-napisanie-a-ne-sprashivaet
title: "Предикат о ФОРМЕ пути читает написание, а не спрашивает платформу"
type: convention
tags:
  - paths
  - platform
  - release-18
task: null
edges: []
---

Абсолютность, UNC, буква диска, разделитель — свойства СТРОКИ. Спрашивать о них os.path.isabs / os.path.normpath значит получить ответ, который меняется от ОС и от минорной версии Python, тогда как путь приходит текстом: из конфига, переменной окружения, payload хука, написанного другой машиной.

Сессия #165 нашла ЧЕТЫРЕ места этой формы за один релиз:
- path_glob.normalize схлопывал `..` через os.path.normpath — обратный слэш разделитель только на Windows
- memory_sinks._tree_relative спрашивал os.path.isabs — d:/proj на Linux относительный
- knowledge_home_guard проверял UNC ПОСЛЕ abspath — на Linux проверка не срабатывала вовсе
- knowledge_origin.relative_source_file спрашивал os.path.isabs — Python 3.13 сменил ntpath.isabs, и редактирование раскладки каталогов молча выключилось на Windows

Правило: path_glob.is_absolute либо локальный _ABSOLUTE_RE; для схлопывания — posixpath.normpath ПОСЛЕ замены разделителя.

Тест на ту же болезнь: если утверждение звучит «на любой платформе», проверь, ИСТИННО ли оно на другой. «Путь со слэшами Windows редактируется одинаково везде» — ложно: POSIX-хост не умеет разбить его на сегменты. Такое утверждение делят надвое — кросс-платформенное про ПРЕДИКАТ и сквозное в написании текущей платформы.
