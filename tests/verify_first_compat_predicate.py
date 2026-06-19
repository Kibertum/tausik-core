"""Logic shared with conftest: when autouse shim may patch GatesMixin.verify-first."""

from __future__ import annotations

from typing import Any


def should_apply_verify_first_autouse_compat_shim(node: Any) -> bool:
    """Return False when the test declares ``@pytest.mark.verify_first``.

    Such tests must run real `_enforce_verify_first`; the autouse fixture must
    not replace it with a no-op.

    Argument: pytest ``request.node`` (implements ``get_closest_marker``).
    """

    return node.get_closest_marker("verify_first") is None


def test_verify_first_marker_turns_off_autouse_compat_shim() -> None:
    """Negative guard: marker present → shim must not deactivate enforcement."""

    class _Node:
        def __init__(self, has_marker: bool) -> None:
            self._has = has_marker

        def get_closest_marker(self, name: str):  # noqa: ANN201
            if name == "verify_first" and self._has:
                return object()
            return None

    assert should_apply_verify_first_autouse_compat_shim(_Node(True)) is False
    assert should_apply_verify_first_autouse_compat_shim(_Node(False)) is True
