---
slug: harness-mutatsiy-snachala-rc-0-na-originale-ubitoy-schitat
title: "Харнесс мутаций: сначала rc=0 на оригинале, убитой считать ТОЛЬКО rc=1 — иначе сломанная команда pytest даёт «100% убито»"
type: gotcha
tags:
  - harness
  - mutation
  - pytest
task: ar-existence-is-probed-by-three-guessed-table-names
edges: []
---

В #208 мутации гонялись с -p no:xdist, а pyproject addopts несёт -n: pytest падал с rc=4 (unrecognized arguments) до сбора тестов, и харнесс, считавший «rc != 0» за убийство, отчитался 6/6 при нуле реальных прогонов. Поймано только базовым прогоном той же командой. Правило: (1) прогнать оригинал той же командой и потребовать rc=0 с числом passed; (2) убитой считать только rc=1 (тесты собраны и упали), rc 2-5 — ошибка харнесса; (3) печатать строку итога «N failed» рядом с вердиктом. Дополняет #529 (неизвестный флаг даёт rc=0): pytest врёт в ОБЕ стороны.
