"""Pytest configuration and fixtures."""

import tempfile
from pathlib import Path

import pytest

from clientserverrunner.config_manager import ConfigManager
from clientserverrunner.log_manager import LogManager
from clientserverrunner.models import ServerConfig
from clientserverrunner.port_manager import PortManager
from clientserverrunner.process_manager import ProcessManager
from clientserverrunner.types import create_default_registry


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def server_config(temp_dir: Path) -> ServerConfig:
    """Create a test server configuration."""
    config = ServerConfig(data_dir=temp_dir)
    config.ensure_directories()
    return config


@pytest.fixture
def config_manager(server_config: ServerConfig) -> ConfigManager:
    """Create a configuration manager for testing."""
    return ConfigManager(server_config)


@pytest.fixture
def log_manager(server_config: ServerConfig) -> LogManager:
    """Create a log manager for testing."""
    return LogManager(server_config)


@pytest.fixture
def port_manager() -> PortManager:
    """Create a port manager for testing."""
    return PortManager()


@pytest.fixture
def handler_registry():
    """Create an application handler registry."""
    return create_default_registry()


@pytest.fixture
def process_manager(
    config_manager: ConfigManager,
    log_manager: LogManager,
    port_manager: PortManager,
) -> ProcessManager:
    """Create a process manager for testing."""
    pm = ProcessManager(config_manager, log_manager, port_manager)
    yield pm
    # Cleanup: shutdown all processes
    pm.shutdown_all()


@pytest.fixture
def test_apps_dir() -> Path:
    """Get the test applications directory."""
    return Path(__file__).parent / "fixtures" / "test_apps"


@pytest.fixture
def python_test_app(test_apps_dir: Path) -> Path:
    """Get path to Python test application."""
    return test_apps_dir / "python"


@pytest.fixture
def npm_test_app(test_apps_dir: Path) -> Path:
    """Get path to NPM test application."""
    return test_apps_dir / "npm"
