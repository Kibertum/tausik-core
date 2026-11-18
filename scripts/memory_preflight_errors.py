"""Stable exception types for memory preflight.

Kept outside ``memory_preflight`` so ``importlib.reload`` of that module (or tip
helpers) cannot replace the class objects ``pytest.raises`` / ``isinstance``
already bound.
"""

from __future__ import annotations

from tausik_utils import ServiceError


class MemoryPreflightError(ServiceError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(f"{code}: {message}")
