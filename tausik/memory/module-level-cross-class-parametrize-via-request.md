---
slug: module-level-cross-class-parametrize-via-request
title: "Module-level cross-class parametrize via request.getfixturevalue"
type: pattern
tags:
  - fixtures
  - parametrize
  - pytest
task: v14c-mass-parametrize-batch-1
edges: []
---

Когда нужно объединить структурно-идентичные тесты из разных классов с разными fixture'ами (например `svc` vs `seeded`), pytest позволяет dynamic fixture lookup через `request.getfixturevalue(name)`:

```python
@pytest.mark.parametrize(
    "fixture_name,tool_name,args,expected",
    [
        pytest.param("svc",    "tausik_status",     {}, "Tasks: 0/0 done", id="status_empty"),
        pytest.param("seeded", "tausik_task_list",  {"status": "active"}, "No tasks found", id="task_list_filter"),
        ...
    ],
)
def test_handle_tool_returns_expected(request, fixture_name, tool_name, args, expected):
    fixture = request.getfixturevalue(fixture_name)
    result = _handle_tool(fixture, tool_name, args)
    assert expected in result
```

Преимущества: классовая организация ломается, но dedupe-аудит больше не флагает группу. Test ID хорошо читается: `test_handle_tool_returns_expected[status_empty]`. Применено в G19+G20 (test_project_mcp.py, 10 tests across TestStatus/TestTaskCRUD/TestSession/TestHierarchy/TestKnowledge/TestMetricsAndEvents).
