---
slug: geyt-shipyaschiysya-v-chuzhie-proekty-mehanizm-obschiy
title: "Гейт, шипящийся в чужие проекты: механизм общий, политика в конфиге"
type: convention
tags: []
task: changelog-continuous-gate
edges: []
---

Гейт TAUSIK-фреймворка, который поедет в bootstrap-нутые проекты, НЕ имеет права хардкодить проект-специфичную политику (напр. 'оба CHANGELOG.md+CHANGELOG.ru.md обязаны меняться') — иначе он навсегда заблокирует проект без такого артефакта. Паттерн changelog-continuous-gate: требование читается из config.task_done.<gate> {enabled(default False), files[]}, выключено по умолчанию (opt-in); собственный .tausik/config.json включает. Fail-closed при enabled по образцу whole-tree proof (#157). Родственно [[265]] (состояние проекта через tausik_dir, не cwd) и [[266]] (гейт судит реальным производителем).
