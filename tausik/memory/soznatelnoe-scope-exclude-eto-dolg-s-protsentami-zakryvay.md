---
slug: soznatelnoe-scope-exclude-eto-dolg-s-protsentami-zakryvay
title: "Сознательное scope_exclude — это ДОЛГ с процентами: закрывай пломбой по таблице, а не памяткой"
type: pattern
tags:
  - dialects
  - gates
  - senar
task: pwsh-write-gate-does-not-read-script-files-either
edges: []
---

Замер #206. #201 закрыл чтение файла скрипта на канале Bash и положил PowerShell в scope_exclude СОЗНАТЕЛЬНО, чтобы задача не разрослась. Решение было верным, задачу-продолжение завели. Но пока она ждала, ПЕРВИЧНАЯ оболочка платформы пропускала запись вне ACL на ПЯТИ обычных написаниях (python x.py, & python x.py, оба слэша, Start-Process) - гейт возвращал 0. Вывод не 'не откладывать', а 'откладывая, поставь пломбу': тест, перебирающий ТАБЛИЦУ диалектов и требующий одинакового ответа на равнозначную команду. Тогда неравенство каналов краснеет само, а третья оболочка падает в день добавления. Тот же приём закрыл сегодня близнеца write_targets - см. [[soyuz-dvuh-ugadannyh-korney-vse-esche-dogadka-sprashivay]].
