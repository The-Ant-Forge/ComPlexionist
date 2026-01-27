"""Base screen class for ComPlexionist GUI."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

import flet as ft

if TYPE_CHECKING:
    from complexionist.gui.state import AppState


class BaseScreen(ABC):
    """Base class for all screens."""

    def __init__(self, page: ft.Page, state: AppState) -> None:
        """Initialize the screen.

        Args:
            page: Flet page instance.
            state: Application state.
        """
        self.page = page
        self.state = state

    @abstractmethod
    def build(self) -> ft.Control:
        """Build the screen UI.

        Returns:
            The root control for this screen.
        """
        pass

    def update(self) -> None:
        """Update the page."""
        self.page.update()
