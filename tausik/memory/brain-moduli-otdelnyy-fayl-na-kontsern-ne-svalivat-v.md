---
slug: brain-moduli-otdelnyy-fayl-na-kontsern-ne-svalivat-v
title: "Brain-модули: отдельный файл на концерн, не сваливать в project_config.py"
type: convention
tags:
  - architecture
  - brain
  - convention
  - filesize
task: brain-config-schema
edges: []
---

Brain-логика живёт в отдельных модулях `scripts/brain_*.py` (brain_schema.py, brain_config.py, будущие brain_client.py/brain_service.py/brain_mcp.py). project_config.py отвечает только за TAUSIK-конфиг и gates. Причина: (1) 400-строчный filesize-gate — любой «просто добавить секцию brain в существующий файл» быстро превышает лимит (проверено: попытка положить в project_config.py → 471 строка, вынос в brain_config.py → 357 + 126); (2) разный concern: brain — опциональная cross-project фича, не должна проникать в core TAUSIK.
