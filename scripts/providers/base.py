"""Base provider protocol for TAUSIK runtime abstraction."""

from __future__ import annotations

from abc import ABC, abstractmethod


class Provider(ABC):
    """Abstract base for IDE/runtime providers.

    Each provider knows how to:
    - Detect the active model running the current session
    - Locate the transcript/session log (if any)
    - Generate IDE-specific settings / config
    """

    @abstractmethod
    def name(self) -> str:
        """Lowercase provider slug (e.g. 'claude', 'kilo', 'qwen')."""
        ...

    @abstractmethod
    def get_active_model(self) -> str | None:
        """Return the current model id, or None when unknown."""
        ...

    @abstractmethod
    def get_transcript_path(self) -> str | None:
        """Return path to the current session transcript, or None."""
        ...

    def generate_settings(self, target_dir: str, project_dir: str, **kwargs) -> None:
        """Write provider-specific settings into target_dir.

        Default: no-op. Concrete providers override as needed.
        """
        return None

    def generate_commands(self, target_dir: str, skills_dir: str, **kwargs) -> None:
        """Write slash-command stubs into target_dir/commands/.

        Default: no-op. Kilo overrides to emit .kilo/command/*.md.
        """
        return None
