# rocktalk/components/base.py
from abc import ABC, abstractmethod

from app_context import AppContext


class Component(ABC):
    """Base class for UI components"""

    def __init__(self, ctx: AppContext):
        """
        Initialize the component with application context

        Args:
            ctx: Application context providing access to services
        """
        self.ctx: AppContext = ctx

    @abstractmethod
    def render(self) -> None:
        """Render the component to the UI"""
        pass
