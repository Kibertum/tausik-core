---
slug: byte-aware-python-script-merge-dlya-batch-test-parametrize
title: "Byte-aware Python script merge для batch test parametrize"
type: pattern
tags:
  - parametrize
  - python
  - refactor
  - tests
task: v14c-mass-parametrize-batch-1
edges: []
---

Когда Edit tool не справляется с массовой заменой тестов (cross-class restructures, invisible Unicode chars, scattered tests across many classes), используй inline Python script через Bash heredoc:

```python
import re
from pathlib import Path
path = Path("tests/test_X.py")
content = path.read_text(encoding="utf-8")

# 1. Verify each target test exists (bail loud if not).
TESTS = [(name, fixture, ...args), ...]
for name, fixture, *_ in TESTS:
    block_re = re.compile(
        r"    def " + re.escape(name) + r"\(self, " + re.escape(fixture) + r"\):.*?(?=\n    def |\nclass |\Z)",
        flags=re.DOTALL,
    )
    if not block_re.search(content):
        raise RuntimeError(f"NOT FOUND: {name}")

# 2. Build new parametrize block.
# 3. Remove individual tests via re.sub.
# 4. Insert new block at marker location.
# 5. Cleanup: re.sub(r"\n{4,}", "\n\n\n", content) collapses excess blank lines after deletions.
# 6. path.write_text(content, encoding="utf-8")
```

Runtime: pytest sync verify сразу. Применено в batch-1 для G8+G18 unicode (12 tests → 1) и G19+G20 cross-class (10 tests across 6 classes → 1 module-level via request.getfixturevalue для dynamic fixture lookup).

Gotcha: print() с em-dash или Unicode arrow → cp1252 codec error in Windows Python. Skip print или use sys.stdout.write с явным encoding.
