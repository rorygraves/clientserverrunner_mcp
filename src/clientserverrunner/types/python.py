"""Python application type handler."""

import subprocess
import time
from pathlib import Path

from ..models import ApplicationInstance, CommandResult
from ..utils.logging import setup_logger
from .base import ApplicationHandler

logger = setup_logger(__name__)


class PythonHandler(ApplicationHandler):
    """Handler for Python applications."""

    def prepare_command(
        self,
        app: ApplicationInstance,
        env: dict[str, str],
    ) -> str:
        """Prepare the start command for a Python application.

        Args:
            app: Application instance
            env: Environment variables

        Returns:
            Command to execute
        """
        # Return the command as-is, user should specify full command
        # e.g., "uvicorn main:app --reload --port 8000"
        return app.command

    def run_custom_command(
        self,
        app: ApplicationInstance,
        command: str,
        args: list[str],
        env: dict[str, str],
    ) -> CommandResult:
        """Run a custom command for a Python application.

        Supported commands:
        - lint: Run ruff check
        - format: Run ruff format
        - typecheck: Run mypy
        - test: Run pytest

        Args:
            app: Application instance
            command: Command name
            args: Additional arguments
            env: Environment variables

        Returns:
            Command result
        """
        start_time = time.time()

        # Map command to actual tool
        command_map = {
            "lint": ["ruff", "check", "."],
            "format": ["ruff", "format", "."],
            "typecheck": ["mypy", "."],
            "test": ["pytest"],
        }

        if command not in command_map:
            # Try to run as custom command
            cmd_parts = [command] + args
        else:
            cmd_parts = command_map[command] + args

        try:
            result = subprocess.run(
                cmd_parts,
                cwd=app.working_dir,
                env=env,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
                check=False,
            )

            duration = time.time() - start_time

            return CommandResult(
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                duration_seconds=duration,
            )

        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            return CommandResult(
                exit_code=-1,
                stdout="",
                stderr="Command timeout (5 minutes)",
                duration_seconds=duration,
            )
        except Exception as e:
            duration = time.time() - start_time
            return CommandResult(
                exit_code=-1,
                stdout="",
                stderr=f"Error running command: {e}",
                duration_seconds=duration,
            )

    def supports_reload(self, app: ApplicationInstance) -> bool:
        """Check if the Python application supports hot reload.

        Common frameworks with auto-reload:
        - uvicorn --reload
        - flask --debug
        - django runserver

        Args:
            app: Application instance

        Returns:
            True if command suggests reload support
        """
        reload_indicators = [
            "--reload",
            "--debug",
            "runserver",
            "watchfiles",
        ]
        return any(indicator in app.command.lower() for indicator in reload_indicators)

    def trigger_reload(self, app: ApplicationInstance) -> tuple[bool, str]:
        """Trigger a hot reload of a Python application.

        For most Python frameworks with auto-reload, touching a file
        triggers reload. We touch the main application file if found.

        Args:
            app: Application instance

        Returns:
            Tuple of (success, message)
        """
        if not self.supports_reload(app):
            return False, "Application does not support hot reload"

        # Common Python application entry point files
        entry_points = [
            "main.py",
            "app.py",
            "server.py",
            "wsgi.py",
            "asgi.py",
            "manage.py",
        ]

        for entry_point in entry_points:
            entry_file = app.working_dir / entry_point
            if entry_file.exists():
                try:
                    # Touch the file to trigger reload
                    entry_file.touch()
                    logger.info(f"Triggered reload by touching {entry_file}")
                    return True, f"Reload triggered by touching {entry_file.name}"
                except Exception as e:
                    return False, f"Failed to touch {entry_file.name}: {e}"

        return False, "Could not find entry point file to trigger reload"
