---
slug: bootstrap-bez-ide-all-razvorachivaet-tolko-claude-a-geyt
title: "bootstrap без --ide all разворачивает только .claude, а гейт bootstrap_drift считает ВСЕ профили"
type: gotcha
tags: []
task: tausik-cli-cmd-wrapper-eats-redirect-chars
edges: []
---

В #209 закрытие задачи дважды упало на bootstrap_drift: 8 развёрнутых файлов не совпали с исходником. Причина: python bootstrap/bootstrap.py по умолчанию --ide claude, и НОВЫЙ модуль scripts/cmdline_fidelity.py не попал в .cursor, .kilo, .opencode, .qwen — там его просто не было. Гейт же сверяет все профили, присутствующие в дереве. Лечение: python bootstrap/bootstrap.py --ide all, затем python bootstrap/bootstrap.py --check (печатает CHECK — no bootstrap drift) и только потом verify + done. Особенно важно, когда задача ДОБАВЛЯЕТ файл в scripts/: правка существующего файла в чужом профиле тоже разъедется, но новый файл разъезжается гарантированно. Ставь --check ПЕРЕД verify — он дешевле, чем цикл verify/done/провал.
