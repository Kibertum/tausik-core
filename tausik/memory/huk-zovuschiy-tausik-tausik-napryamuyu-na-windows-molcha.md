---
slug: huk-zovuschiy-tausik-tausik-napryamuyu-na-windows-molcha
title: "Хук, зовущий .tausik/tausik напрямую, на Windows молча мёртв — обёртку резолвит только _common.tausik_path"
type: gotcha
tags:
  - hooks
  - silent-failure
  - windows
task: ag-incremental-refresh-on-the-write-hook
edges: []
---

НАЙДЕНО В СМЕНЕ #235, жило годами. scripts/hooks/auto_format.py собирал путь как os.path.join(project_dir, '.tausik', 'tausik') и запускал его подпроцессом. Это POSIX-обёртка на bash; на Windows subprocess даёт OSError [WinError 2], и объемлющий except OSError его проглатывал. Итог: пофайловая запись «Modified: путь» в журнал задачи не работала ни разу — 4 задачи из 1565 несут такую строку, все из эпохи до разделения обёрток.

ПОЧЕМУ ЭТО НЕ ЗАМЕТИЛИ. os.path.exists('.tausik/tausik') на Windows возвращает True — файл есть, просто не исполняется. Значит проверка существования НЕ отличает работающую обёртку от неработающей, и весь блок выглядел живым.

КАК ПРАВИЛЬНО. scripts/hooks/_common.py::tausik_path(project_dir) — он на win32 сначала пробует .tausik/tausik.cmd. А если нужен всего лишь слуг активной задачи, есть _common.current_active_task_slug: он читает базу напрямую и подпроцесса не заводит вовсе (один вызов CLI через обёртку замерен в 190 мс).

ГДЕ ИСКАТЬ ТО ЖЕ. Любой хук или скрипт, собирающий путь к обёртке руками. Признак — литерал '.tausik', 'tausik' рядом с subprocess. Проверка существования файла при этом ничего не доказывает; доказывает только код возврата.

СВЯЗАННОЕ: конвенция про то, что команду с вложенными кавычками на Windows пишут файлом, — тот же класс «хост ведёт себя иначе, и молчание об этом дороже ошибки».
