"""Application type handlers."""

from .base import ApplicationHandler, HandlerRegistry
from .npm import NpmHandler
from .python import PythonHandler
from .scala import ScalaHandler

__all__ = [
    "ApplicationHandler",
    "HandlerRegistry",
    "PythonHandler",
    "NpmHandler",
    "ScalaHandler",
    "create_default_registry",
]


def create_default_registry() -> HandlerRegistry:
    """Create a handler registry with default handlers.

    Returns:
        Handler registry with Python, NPM, and Scala handlers
    """
    registry = HandlerRegistry()
    registry.register("python", PythonHandler())
    registry.register("npm", NpmHandler())
    registry.register("scala", ScalaHandler())
    return registry
