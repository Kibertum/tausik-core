---
slug: subprocess-run-timeout-ne-zaschischaet-ot-vnuka-s-pipe-na
title: "subprocess.run timeout не защищает от внука с pipe на Windows"
type: gotcha
tags:
  - hang
  - subprocess
  - windows
task: v15p-fix-rag-reindex-hang
edges: []
---

subprocess.run(timeout=N) НЕ защищает от зависания, если потомок породил долгоживущего внука с унаследованным stdout-pipe (git fsmonitor--daemon, credential helper, git.exe-шим): после kill() CPython вызывает второй communicate() БЕЗ таймаута → вечная блокировка. Решение: Popen + ручной TimeoutExpired-handling без второго communicate — kill, wait(1), abandon daemon reader threads. Паттерн: rag_indexer._run_git (v15p-fix-rag-reindex-hang).
