---
slug: caveman-chto-eto-iz-nego-nichego-ne-brali-nasha-podderzhka
title: "caveman: что это, из него ничего не брали, наша поддержка — свой output-режим"
type: context
tags:
  - caveman
  - interop
  - output_mode
  - token-economy
task: caveman-output-build-full-body-interop
edges: []
---

Вопрос «брали ли мы что-то от caveman» — проверено во всех источниках (git-дерево, git-история по содержимому и сообщениям всех веток, база TAUSIK): НЕТ, ничего не брали до v1.7.0-unreleased.

Что такое caveman (github.com/JuliusBrussee/caveman, ~85k★): Claude-Code скилл, жмёт ВЫВОД агента ~65% телеграфным «caveman-speak», код/команды/ошибки байт-в-байт. Архитектура зеркалит нашу: hooks для Claude Code (+ merge settings.json + .caveman-active флаг), rule-файлы для Cursor/Windsurf/Cline (.cursor/rules/caveman.mdc, .windsurf/rules/caveman.md, .clinerules/caveman.md), skills-реестр для 30+ остальных.

КАК МЫ ВНЕДРИЛИ (задача caveman-output-build-full-body-interop, выбор пользователя — «свой output-режим + interop», линза = токен-экономия): НЕ вендорим caveman и НЕ ставим его инсталлятор — его SessionStart-hook + merge settings.json подрались бы с нашим session_start.py и владением settings.json. Вместо этого свой knob output_mode: off|caveman (по умолчанию off) в .tausik/config.json; при caveman build_full_body дописывает короткую директиву (потолок 700 симв — она инжектится каждую сессию, длина = токен-статья). Ортогонален context_tier (tier жмёт вход, output_mode — выход). Карв-ауты: код/команды/ошибки байт-в-байт, AC-evidence/decisions/SPEC/ADAPT/логи полными (agent-first). Interop: service_doctor_caveman.py детектит реальный caveman и предупреждает о коллизии в settings.json.

ГРАНИЦА: 65% — цифра caveman, у нас НЕ измерена, не заявлять как нашу. Отдельная НЕ сделанная идея (задел): сжимать реинжектируемые артефакты (memory tail/handoff) — компаундируется по сессиям, но риск для agent-first; сначала измерить, потом строить.
