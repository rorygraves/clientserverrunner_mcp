"""NPM/Node.js application type handler."""

import subprocess
import time

from ..models import ApplicationInstance, CommandResult
from ..utils.logging import setup_logger
from .base import ApplicationHandler

logger = setup_logger(__name__)


class NpmHandler(ApplicationHandler):
    """Handler for NPM/Node.js applications."""

    def prepare_command(
        self,
        app: ApplicationInstance,
        env: dict[str, str],
    ) -> str:
        """Prepare the start command for an NPM application.

        Args:
            app: Application instance
            env: Environment variables

        Returns:
            Command to execute
        """
        # Return the command as-is
        # e.g., "npm run dev" or "npm start"
        return app.command

    def run_custom_command(
        self,
        app: ApplicationInstance,
        command: str,
        args: list[str],
        env: dict[str, str],
    ) -> CommandResult:
        """Run a custom command for an NPM application.

        Supported commands:
        - lint: Run npm run lint
        - format: Run npm run format
        - test: Run npm test
        - build: Run npm run build

        Args:
            app: Application instance
            command: Command name
            args: Additional arguments
            env: Environment variables

        Returns:
            Command result
        """
        start_time = time.time()

        # Map command to npm script
        command_map = {
            "lint": ["npm", "run", "lint"],
            "format": ["npm", "run", "format"],
            "test": ["npm", "test"],
            "build": ["npm", "run", "build"],
            "typecheck": ["npm", "run", "typecheck"],
        }

        if command not in command_map:
            # Try to run as npm script
            cmd_parts = ["npm", "run", command] + args
        else:
            cmd_parts = command_map[command] + args

        try:
            result = subprocess.run(
                cmd_parts,
                cwd=app.working_dir,
                env=env,
                capture_output=True,
                text=True,
                timeout=600,  # 10 minute timeout for builds
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
                stderr="Command timeout (10 minutes)",
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
        """Check if the NPM application supports hot reload.

        Most modern dev servers support HMR (Hot Module Replacement):
        - Vite
        - webpack-dev-server
        - Next.js dev
        - Create React App
        - Parcel

        Args:
            app: Application instance

        Returns:
            True if command suggests dev server with HMR
        """
        dev_server_indicators = [
            "npm run dev",
            "npm start",
            "vite",
            "next dev",
            "react-scripts start",
            "parcel",
            "webpack-dev-server",
        ]
        command_lower = app.command.lower()
        return any(indicator in command_lower for indicator in dev_server_indicators)

    def trigger_reload(self, app: ApplicationInstance) -> tuple[bool, str]:
        """Trigger a hot reload of an NPM application.

        Most modern dev servers watch for file changes automatically.
        We can trigger a reload by touching a source file.

        Args:
            app: Application instance

        Returns:
            Tuple of (success, message)
        """
        if not self.supports_reload(app):
            return False, "Application does not support hot reload"

        # Common entry point files for different frameworks
        entry_points = [
            "src/main.tsx",
            "src/main.ts",
            "src/main.jsx",
            "src/main.js",
            "src/index.tsx",
            "src/index.ts",
            "src/index.jsx",
            "src/index.js",
            "src/App.tsx",
            "src/App.ts",
            "src/App.jsx",
            "src/App.js",
            "pages/index.tsx",  # Next.js
            "pages/index.jsx",  # Next.js
        ]

        for entry_point in entry_points:
            entry_file = app.working_dir / entry_point
            if entry_file.exists():
                try:
                    # Touch the file to trigger HMR
                    entry_file.touch()
                    logger.info(f"Triggered HMR by touching {entry_file}")
                    return True, f"Reload triggered by touching {entry_point}"
                except Exception as e:
                    return False, f"Failed to touch {entry_point}: {e}"

        # If no specific entry point found, try package.json
        package_json = app.working_dir / "package.json"
        if package_json.exists():
            return (
                True,
                "HMR should be automatic for this dev server, no manual trigger needed",
            )

        return False, "Could not find entry point file to trigger reload"
