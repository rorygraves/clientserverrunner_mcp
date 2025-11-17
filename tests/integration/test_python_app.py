"""Integration tests for Python applications."""

import time
from pathlib import Path

import httpx
import pytest

from clientserverrunner.models import AppState


class TestPythonApplication:
    """Integration tests for Python application lifecycle."""

    def test_start_stop_python_app(
        self, config_manager, process_manager, handler_registry, python_test_app: Path
    ):
        """Test starting and stopping a Python application."""
        # Create configuration
        config = config_manager.create_configuration(
            name="Python Test",
            applications=[
                {
                    "id": "server",
                    "name": "Test Server",
                    "app_type": "python",
                    "working_dir": str(python_test_app),
                    "command": "python server.py 8888",
                    "health_check": {
                        "type": "tcp",
                        "port": 8888,
                        "interval": 1,
                        "timeout": 2,
                    },
                }
            ],
        )

        try:
            # Start the application
            result = process_manager.start_application(
                config.id, "server", handler_registry
            )
            assert result.success
            assert result.pid is not None

            # Wait a bit for server to be ready
            time.sleep(2)

            # Check status
            status = process_manager.get_status(config.id, "server")
            assert status.state == AppState.RUNNING
            assert status.pid is not None

            # Try to connect to the server
            try:
                response = httpx.get("http://localhost:8888", timeout=5.0)
                assert response.status_code == 200
                assert b"Hello from test server" in response.content
            except Exception as e:
                pytest.fail(f"Failed to connect to test server: {e}")

            # Stop the application
            stop_result = process_manager.stop_application(config.id, "server")
            assert stop_result.success

            # Verify it's stopped
            time.sleep(1)
            status = process_manager.get_status(config.id, "server")
            assert status.state == AppState.STOPPED

        finally:
            # Cleanup
            process_manager.stop_application(config.id, "server", graceful=False)
            config_manager.delete_configuration(config.id)

    def test_python_app_with_logs(
        self, config_manager, process_manager, log_manager, handler_registry, python_test_app: Path
    ):
        """Test Python application with log capture."""
        # Create configuration
        config = config_manager.create_configuration(
            name="Python Test",
            applications=[
                {
                    "id": "server",
                    "name": "Test Server",
                    "app_type": "python",
                    "working_dir": str(python_test_app),
                    "command": "python server.py 8889",
                }
            ],
        )

        try:
            # Start the application
            result = process_manager.start_application(
                config.id, "server", handler_registry
            )
            assert result.success

            time.sleep(2)

            # Make a request to generate logs
            try:
                httpx.get("http://localhost:8889", timeout=5.0)
            except Exception:
                pass

            time.sleep(1)

            # Check logs
            logs = log_manager.get_logs(config.id, "server", lines=50)
            assert len(logs) > 0

            # Should contain startup message
            log_content = " ".join(log.content for log in logs)
            assert "Test server starting" in log_content

        finally:
            # Cleanup
            process_manager.stop_application(config.id, "server", graceful=False)
            config_manager.delete_configuration(config.id)
