---
slug: redeploy-stiraet-fiksy-v-razvernutyh-kopiyah-chini-sloy
title: "Redeploy стирает фиксы в развёрнутых копиях: чини слой границы, не профиль"
type: pattern
tags:
  - bootstrap
  - deploy-boundary
  - kilo
  - redeploy
  - vendor
task: null
edges: []
---

Фикс, применённый к РАЗВЁРНУТЫМ копиям (профили хостов), умирает при каждом bootstrap --ide all, если источник не менялся. Дважды погиб фикс 1.11.2 tools-as-object для .kilo/agents/vendor_seo: вендор — upstream, его нельзя править. Правильный слой — адаптер на границе деплоя (copy_vendor_assets → normalize_agent_tools): граница единственная видит обе схемы. Общий признак: задача называется «Reapply X wiped by redeploy» — значит чинили не тот слой; ищи источник копирования и переноси трансформацию туда.
