"""Base application type handler interface."""

from abc import ABC, abstractmethod
from typing import Any

from ..models import ApplicationInstance, CommandResult


class ApplicationHandler(ABC):
    """Base class for application type handlers."""

    @abstractmethod
    def prepare_command(
        self,
        app: ApplicationInstance,
        env: dict[str, str],
    ) -> str:
        """Prepare the start command for the application.

        Args:
            app: Application instance
            env: Environment variables

        Returns:
            Command to execute
        """
        pass

    @abstractmethod
    def run_custom_command(
        self,
        app: ApplicationInstance,
        command: str,
        args: list[str],
        env: dict[str, str],
    ) -> CommandResult:
        """Run a custom command for the application.

        Args:
            app: Application instance
            command: Command name (e.g., 'lint', 'test')
            args: Additional arguments
            env: Environment variables

        Returns:
            Command result
        """
        pass

    @abstractmethod
    def supports_reload(self, app: ApplicationInstance) -> bool:
        """Check if the application supports hot reload.

        Args:
            app: Application instance

        Returns:
            True if reload is supported
        """
        pass

    @abstractmethod
    def trigger_reload(self, app: ApplicationInstance) -> tuple[bool, str]:
        """Trigger a hot reload of the application.

        Args:
            app: Application instance

        Returns:
            Tuple of (success, message)
        """
        pass


class HandlerRegistry:
    """Registry for application type handlers."""

    def __init__(self) -> None:
        """Initialize the handler registry."""
        self._handlers: dict[str, ApplicationHandler] = {}

    def register(self, app_type: str, handler: ApplicationHandler) -> None:
        """Register a handler for an application type.

        Args:
            app_type: Application type name
            handler: Handler instance
        """
        self._handlers[app_type] = handler

    def get_handler(self, app_type: str) -> ApplicationHandler:
        """Get a handler for an application type.

        Args:
            app_type: Application type name

        Returns:
            Handler instance

        Raises:
            KeyError: If handler not found
        """
        if app_type not in self._handlers:
            raise KeyError(f"No handler registered for app type '{app_type}'")
        return self._handlers[app_type]

    def has_handler(self, app_type: str) -> bool:
        """Check if a handler is registered for an application type.

        Args:
            app_type: Application type name

        Returns:
            True if handler is registered
        """
        return app_type in self._handlers
