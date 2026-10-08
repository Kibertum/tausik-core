---
slug: payload-pretooluse-neset-cwd-i-on-otslezhivaet-cd
title: "Payload PreToolUse НЕСЁТ cwd, и он отслеживает cd предыдущего вызова"
type: gotcha
tags: []
task: write-gate-resolves-relative-paths-against-the-wrong-directory
edges: []
---

Замерено в #205 инструментовкой живого хука: поля суть session_id, transcript_path, cwd, prompt_id, permission_mode, effort, hook_event_name, tool_name, tool_input, tool_use_id. После cd d:/tmp поле показало D:\tmp, а не корень проекта. Значит хуку НЕ НУЖНО выводить рабочий каталог из CLAUDE_PROJECT_DIR — источник есть в событии. Прежде три хука приклеивали относительные цели к project_dir и объявляли файл чужой выгрузки записью в главный репозиторий.
