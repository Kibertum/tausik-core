---
slug: ratchet-pro-geyt-kladi-v-lanu-kotoruyu-etot-geyt-gonyaet
title: "Ратчет про гейт клади в лану, которую этот гейт гоняет"
type: convention
tags: []
task: ci-does-not-run-on-the-release-branch
edges: []
---

test_ci_lanes_are_honest.py помечен pytest.mark.slow на уровне МОДУЛЯ, а GitLab гоняет быструю ленту -m 'not slow'. Храповик про триггер GitLab, положенный туда, никогда не выполнился бы там, где стоит гейт — повторил бы ошибку, ради которой заведён. Проверяй markers модуля ПЕРЕД тем как дописать тест в существующий файл.
