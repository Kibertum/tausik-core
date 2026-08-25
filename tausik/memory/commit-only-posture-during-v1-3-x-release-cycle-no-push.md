---
slug: commit-only-posture-during-v1-3-x-release-cycle-no-push
title: "Commit-only posture during v1.3.x release cycle — no push pressure"
type: convention
tags:
  - git
  - release-cycle
  - workflow
task: null
edges: []
---

Don't surface "N commits ahead of origin/main" as a blocker in `/start` dashboards or handoffs, and don't propose `git push` as a next step during feature work. Commit-only is the default posture until the entire version is shipped — "пока всё не доделаем" applies to the whole release, not a specific task list.

User's literal framing: "чего ты так пушить хочешь то что не готово? забудь про пуш, только коммиты пока что — у нас много работы в новой версии".

How to apply: commit incrementally, suggest `end` + `commit` at session wrap, never `push`. Only raise pushing when the user explicitly brings it up or when a release-cut task is active.
