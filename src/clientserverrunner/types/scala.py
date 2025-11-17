"""Scala/SBT application type handler."""

import subprocess
import time

import httpx

from ..models import ApplicationInstance, CommandResult
from ..utils.logging import setup_logger
from .base import ApplicationHandler

logger = setup_logger(__name__)


class ScalaHandler(ApplicationHandler):
    """Handler for Scala/SBT applications."""

    def prepare_command(
        self,
        app: ApplicationInstance,
        env: dict[str, str],
    ) -> str:
        """Prepare the start command for a Scala application.

        Args:
            app: Application instance
            env: Environment variables

        Returns:
            Command to execute
        """
        # Return the command as-is
        # e.g., "sbt run" or "sbt ~run" (continuous compilation)
        return app.command

    def run_custom_command(
        self,
        app: ApplicationInstance,
        command: str,
        args: list[str],
        env: dict[str, str],
    ) -> CommandResult:
        """Run a custom command for a Scala application.

        Supported commands:
        - compile: Run sbt compile
        - test: Run sbt test
        - format: Run scalafmt
        - clean: Run sbt clean

        Args:
            app: Application instance
            command: Command name
            args: Additional arguments
            env: Environment variables

        Returns:
            Command result
        """
        start_time = time.time()

        # Map command to sbt task
        command_map = {
            "compile": ["sbt", "compile"],
            "test": ["sbt", "test"],
            "format": ["sbt", "scalafmt"],
            "clean": ["sbt", "clean"],
            "package": ["sbt", "package"],
        }

        if command not in command_map:
            # Try to run as sbt task
            cmd_parts = ["sbt", command] + args
        else:
            cmd_parts = command_map[command] + args

        try:
            result = subprocess.run(
                cmd_parts,
                cwd=app.working_dir,
                env=env,
                capture_output=True,
                text=True,
                timeout=900,  # 15 minute timeout for compilation
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
                stderr="Command timeout (15 minutes)",
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
        """Check if the Scala application supports hot reload.

        SBT supports continuous compilation with ~run.
        Play Framework supports auto-reload.

        Args:
            app: Application instance

        Returns:
            True if command suggests reload support
        """
        reload_indicators = [
            "~run",  # SBT continuous compilation
            "play",  # Play Framework
        ]
        command_lower = app.command.lower()
        return any(indicator in command_lower for indicator in reload_indicators)

    def trigger_reload(self, app: ApplicationInstance) -> tuple[bool, str]:
        """Trigger a hot reload of a Scala application.

        For Play Framework, we can trigger reload via HTTP request.
        For SBT ~run, reload is automatic on file changes.

        Args:
            app: Application instance

        Returns:
            Tuple of (success, message)
        """
        if not self.supports_reload(app):
            return False, "Application does not support hot reload"

        # Check if this is a Play Framework app
        if self._is_play_app(app):
            # Try to trigger reload via HTTP
            reload_url = app.env.get("PLAY_RELOAD_URL")
            if reload_url:
                try:
                    response = httpx.get(reload_url, timeout=10.0)
                    if response.status_code == 200:
                        logger.info(f"Triggered Play reload via {reload_url}")
                        return True, "Play Framework reload triggered via HTTP"
                except Exception as e:
                    logger.warning(f"Failed to trigger Play reload via HTTP: {e}")

        # For SBT ~run, touching a source file should trigger recompilation
        scala_files = list(app.working_dir.glob("app/**/*.scala"))
        if not scala_files:
            scala_files = list(app.working_dir.glob("src/**/*.scala"))

        if scala_files:
            try:
                # Touch the first Scala file found
                scala_files[0].touch()
                logger.info(f"Triggered reload by touching {scala_files[0]}")
                return True, f"Reload triggered by touching {scala_files[0].name}"
            except Exception as e:
                return False, f"Failed to touch Scala file: {e}"

        # If using ~run, reload should be automatic
        if "~run" in app.command:
            return True, "SBT continuous compilation should reload automatically"

        return False, "Could not trigger reload"

    def _is_play_app(self, app: ApplicationInstance) -> bool:
        """Check if the application is a Play Framework app.

        Args:
            app: Application instance

        Returns:
            True if this appears to be a Play app
        """
        # Check for Play-specific files
        play_indicators = [
            app.working_dir / "conf" / "application.conf",
            app.working_dir / "conf" / "routes",
        ]

        return any(path.exists() for path in play_indicators)
