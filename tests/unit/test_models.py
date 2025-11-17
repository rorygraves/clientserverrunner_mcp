"""Tests for data models."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from clientserverrunner.models import (
    ApplicationInstance,
    Configuration,
    HealthCheck,
    HealthCheckType,
)


class TestHealthCheck:
    """Tests for HealthCheck model."""

    def test_http_health_check_valid(self):
        """Test valid HTTP health check."""
        hc = HealthCheck(
            type=HealthCheckType.HTTP,
            url="http://localhost:8000/health",
            interval=5,
            timeout=3,
        )
        assert hc.type == HealthCheckType.HTTP
        assert hc.url == "http://localhost:8000/health"

    def test_http_health_check_missing_url(self):
        """Test HTTP health check without URL fails validation."""
        with pytest.raises(ValidationError, match="HTTP health check requires url"):
            HealthCheck(type=HealthCheckType.HTTP)

    def test_tcp_health_check_valid(self):
        """Test valid TCP health check."""
        hc = HealthCheck(type=HealthCheckType.TCP, port=8000)
        assert hc.type == HealthCheckType.TCP
        assert hc.port == 8000

    def test_tcp_health_check_missing_port(self):
        """Test TCP health check without port fails validation."""
        with pytest.raises(ValidationError, match="TCP health check requires port"):
            HealthCheck(type=HealthCheckType.TCP)


class TestApplicationInstance:
    """Tests for ApplicationInstance model."""

    def test_valid_application(self, temp_dir: Path):
        """Test creating a valid application instance."""
        app = ApplicationInstance(
            id="test-app",
            name="Test App",
            app_type="python",
            working_dir=temp_dir,
            command="python server.py",
        )
        assert app.id == "test-app"
        assert app.app_type == "python"
        assert app.working_dir == temp_dir

    def test_invalid_app_type(self, temp_dir: Path):
        """Test that invalid app types are rejected."""
        with pytest.raises(ValidationError, match="Unsupported app type"):
            ApplicationInstance(
                id="test-app",
                name="Test App",
                app_type="invalid",
                working_dir=temp_dir,
                command="python server.py",
            )

    def test_port_validation(self, temp_dir: Path):
        """Test port validation."""
        # Valid ports
        app = ApplicationInstance(
            id="test-app",
            name="Test App",
            app_type="python",
            working_dir=temp_dir,
            command="python server.py",
            port=8000,
        )
        assert app.port == 8000

        # Port 0 (dynamic) is valid
        app = ApplicationInstance(
            id="test-app",
            name="Test App",
            app_type="python",
            working_dir=temp_dir,
            command="python server.py",
            port=0,
        )
        assert app.port == 0

        # Invalid port
        with pytest.raises(ValidationError):
            ApplicationInstance(
                id="test-app",
                name="Test App",
                app_type="python",
                working_dir=temp_dir,
                command="python server.py",
                port=99999,
            )

    def test_working_dir_absolute_path(self, temp_dir: Path):
        """Test that working_dir is converted to absolute path."""
        app = ApplicationInstance(
            id="test-app",
            name="Test App",
            app_type="python",
            working_dir=temp_dir,
            command="python server.py",
        )
        assert app.working_dir.is_absolute()


class TestConfiguration:
    """Tests for Configuration model."""

    def test_valid_configuration(self, temp_dir: Path):
        """Test creating a valid configuration."""
        config = Configuration(
            id="test-config",
            name="Test Config",
            applications=[
                ApplicationInstance(
                    id="app1",
                    name="App 1",
                    app_type="python",
                    working_dir=temp_dir,
                    command="python server.py",
                )
            ],
        )
        assert config.id == "test-config"
        assert len(config.applications) == 1

    def test_duplicate_app_ids(self, temp_dir: Path):
        """Test that duplicate app IDs are rejected."""
        with pytest.raises(ValidationError, match="Duplicate application IDs"):
            Configuration(
                id="test-config",
                name="Test Config",
                applications=[
                    ApplicationInstance(
                        id="app1",
                        name="App 1",
                        app_type="python",
                        working_dir=temp_dir,
                        command="python server.py",
                    ),
                    ApplicationInstance(
                        id="app1",
                        name="App 1 Duplicate",
                        app_type="python",
                        working_dir=temp_dir,
                        command="python server.py",
                    ),
                ],
            )

    def test_invalid_dependency(self, temp_dir: Path):
        """Test that non-existent dependencies are rejected."""
        with pytest.raises(ValidationError, match="depends on non-existent app"):
            Configuration(
                id="test-config",
                name="Test Config",
                applications=[
                    ApplicationInstance(
                        id="app1",
                        name="App 1",
                        app_type="python",
                        working_dir=temp_dir,
                        command="python server.py",
                        depends_on=["nonexistent"],
                    )
                ],
            )

    def test_circular_dependency(self, temp_dir: Path):
        """Test that circular dependencies are rejected."""
        with pytest.raises(ValidationError, match="Circular dependency detected"):
            Configuration(
                id="test-config",
                name="Test Config",
                applications=[
                    ApplicationInstance(
                        id="app1",
                        name="App 1",
                        app_type="python",
                        working_dir=temp_dir,
                        command="python server.py",
                        depends_on=["app2"],
                    ),
                    ApplicationInstance(
                        id="app2",
                        name="App 2",
                        app_type="python",
                        working_dir=temp_dir,
                        command="python server.py",
                        depends_on=["app1"],
                    ),
                ],
            )

    def test_valid_dependencies(self, temp_dir: Path):
        """Test valid dependency chain."""
        config = Configuration(
            id="test-config",
            name="Test Config",
            applications=[
                ApplicationInstance(
                    id="backend",
                    name="Backend",
                    app_type="python",
                    working_dir=temp_dir,
                    command="python server.py",
                ),
                ApplicationInstance(
                    id="frontend",
                    name="Frontend",
                    app_type="npm",
                    working_dir=temp_dir,
                    command="npm start",
                    depends_on=["backend"],
                ),
            ],
        )
        assert len(config.applications) == 2
        assert "backend" in config.applications[1].depends_on
