"""Process management for ClientServerRunner."""

import asyncio
import os
import signal
import subprocess
import threading
import time
from datetime import datetime
from typing import Any, Dict

import httpx
import psutil

from .config_manager import ConfigManager
from .log_manager import LogManager
from .models import (
    AppState,
    ApplicationInstance,
    ApplicationStatus,
    HealthCheckType,
    HealthStatus,
    StartResult,
    StopResult,
)
from .port_manager import PortManager
from .utils.logging import setup_logger

logger = setup_logger(__name__)


class ProcessManager:
    """Manages application process lifecycle."""

    def __init__(
        self,
        config_manager: ConfigManager,
        log_manager: LogManager,
        port_manager: PortManager,
    ) -> None:
        """Initialize the process manager.

        Args:
            config_manager: Configuration manager instance
            log_manager: Log manager instance
            port_manager: Port manager instance
        """
        self.config_manager = config_manager
        self.log_manager = log_manager
        self.port_manager = port_manager
        self._processes: Dict[str, subprocess.Popen[bytes]] = {}
        self._status: Dict[str, ApplicationStatus] = {}
        self._log_threads: Dict[str, threading.Thread] = {}
        self._stop_events: Dict[str, threading.Event] = {}
        self._restart_counts: Dict[str, int] = {}
        self._restart_timestamps: Dict[str, list[float]] = {}

    def start_application(
        self,
        config_id: str,
        app_id: str,
        handler_registry: Any,
    ) -> StartResult:
        """Start an application instance.

        Args:
            config_id: Configuration identifier
            app_id: Application identifier
            handler_registry: Application type handler registry

        Returns:
            Start result
        """
        try:
            config = self.config_manager.get_configuration(config_id)
            app = next((a for a in config.applications if a.id == app_id), None)

            if app is None:
                return StartResult(
                    app_id=app_id,
                    success=False,
                    message=f"Application '{app_id}' not found in configuration",
                )

            # Check if already running
            status_key = f"{config_id}/{app_id}"
            if status_key in self._processes:
                if self._processes[status_key].poll() is None:
                    return StartResult(
                        app_id=app_id,
                        success=False,
                        message=f"Application '{app_id}' is already running",
                    )

            # Check dependencies are running and healthy
            dep_check = self._check_dependencies(config_id, config, app)
            if not dep_check[0]:
                return StartResult(
                    app_id=app_id,
                    success=False,
                    message=dep_check[1] or "Dependency check failed",
                )

            # Get handler for this app type
            handler = handler_registry.get_handler(app.app_type)

            # Prepare environment with dependency ports
            env = self._prepare_environment(config_id, app, config)

            # Allocate port if needed
            allocated_port = None
            if app.port is not None or app.port_env_var is not None:
                allocated_port = self.port_manager.allocate_port(
                    f"{config_id}/{app_id}", app.port
                )
                if app.port_env_var:
                    env[app.port_env_var] = str(allocated_port)

            # Run build command if specified
            if app.build_command:
                build_result = self._run_build(app, env)
                if not build_result[0]:
                    return StartResult(
                        app_id=app_id,
                        success=False,
                        message=f"Build failed: {build_result[1]}",
                    )

            # Start logging
            self.log_manager.start_logging(config_id, app_id)

            # Start the process
            process = self._start_process(app, env, handler)

            if process is None:
                return StartResult(
                    app_id=app_id,
                    success=False,
                    message="Failed to start process",
                )

            # Store process and status
            self._processes[status_key] = process
            self._status[status_key] = ApplicationStatus(
                app_id=app_id,
                state=AppState.STARTING,
                pid=process.pid,
                started_at=datetime.now(),
                allocated_port=allocated_port,
            )

            # Start log capture threads
            self._start_log_capture(config_id, app_id, process)

            # Wait for startup and health check
            startup_success = self._wait_for_startup(config_id, app_id, app)

            if startup_success:
                self._status[status_key].state = AppState.RUNNING
                self._status[status_key].health = HealthStatus.HEALTHY
                logger.info(f"Successfully started {config_id}/{app_id}")
                return StartResult(
                    app_id=app_id,
                    success=True,
                    message="Application started successfully",
                    pid=process.pid,
                    allocated_port=allocated_port,
                )
            else:
                self._status[status_key].state = AppState.FAILED
                self._status[status_key].health = HealthStatus.UNHEALTHY
                self._status[status_key].error_message = "Startup health check failed"
                return StartResult(
                    app_id=app_id,
                    success=False,
                    message="Application started but health check failed",
                    pid=process.pid,
                )

        except Exception as e:
            logger.error(f"Failed to start {config_id}/{app_id}: {e}")
            return StartResult(
                app_id=app_id,
                success=False,
                message=f"Error starting application: {e}",
            )

    def stop_application(
        self,
        config_id: str,
        app_id: str,
        graceful: bool = True,
        timeout: int = 10,
    ) -> StopResult:
        """Stop an application instance.

        Args:
            config_id: Configuration identifier
            app_id: Application identifier
            graceful: Use graceful shutdown (SIGTERM)
            timeout: Timeout for graceful shutdown

        Returns:
            Stop result
        """
        status_key = f"{config_id}/{app_id}"

        if status_key not in self._processes:
            return StopResult(
                app_id=app_id,
                success=False,
                message=f"Application '{app_id}' is not running",
            )

        try:
            process = self._processes[status_key]

            # Update status
            if status_key in self._status:
                self._status[status_key].state = AppState.STOPPING

            # Stop log capture
            if status_key in self._stop_events:
                self._stop_events[status_key].set()

            # Terminate process
            if graceful:
                self._terminate_gracefully(process, timeout)
            else:
                self._terminate_forcefully(process)

            # Wait for log threads to finish
            if status_key in self._log_threads:
                for thread in self._log_threads[status_key]:
                    thread.join(timeout=2)

            # Clean up
            self._cleanup_process(config_id, app_id)

            logger.info(f"Stopped {config_id}/{app_id}")
            return StopResult(
                app_id=app_id,
                success=True,
                message="Application stopped successfully",
            )

        except Exception as e:
            logger.error(f"Failed to stop {config_id}/{app_id}: {e}")
            return StopResult(
                app_id=app_id,
                success=False,
                message=f"Error stopping application: {e}",
            )

    def get_status(self, config_id: str, app_id: str) -> ApplicationStatus:
        """Get the status of an application.

        Args:
            config_id: Configuration identifier
            app_id: Application identifier

        Returns:
            Application status
        """
        status_key = f"{config_id}/{app_id}"

        if status_key not in self._status:
            return ApplicationStatus(
                app_id=app_id,
                state=AppState.STOPPED,
            )

        status = self._status[status_key]

        # Update status based on process state
        if status_key in self._processes:
            process = self._processes[status_key]
            exit_code = process.poll()

            if exit_code is not None and status.state not in [
                AppState.STOPPED,
                AppState.STOPPING,
            ]:
                # Process has exited
                status.state = AppState.FAILED
                status.exit_code = exit_code
                status.error_message = f"Process exited with code {exit_code}"
                status.health = HealthStatus.UNHEALTHY

                # Handle auto-restart
                if status_key in self._status:
                    config = self.config_manager.get_configuration(config_id)
                    app = next((a for a in config.applications if a.id == app_id), None)
                    if app and app.auto_restart:
                        self._handle_auto_restart(config_id, app_id, app)

        return status

    def _check_dependencies(
        self,
        config_id: str,
        config: Any,
        app: ApplicationInstance,
    ) -> tuple[bool, str | None]:
        """Check if all dependencies are running and healthy.

        Args:
            config_id: Configuration identifier
            config: Configuration instance
            app: Application instance

        Returns:
            Tuple of (success, error_message)
        """
        for dep_id in app.depends_on:
            status = self.get_status(config_id, dep_id)

            if status.state != AppState.RUNNING:
                return False, f"Dependency '{dep_id}' is not running"

            if status.health == HealthStatus.UNHEALTHY:
                return False, f"Dependency '{dep_id}' is unhealthy"

        return True, None

    def _prepare_environment(
        self,
        config_id: str,
        app: ApplicationInstance,
        config: Any,
    ) -> dict[str, str]:
        """Prepare environment variables for the application.

        Args:
            config_id: Configuration identifier
            app: Application instance
            config: Configuration instance

        Returns:
            Environment dictionary
        """
        # Start with system environment
        env = os.environ.copy()

        # Add application-specific environment
        env.update(app.env)

        # Add dependency ports
        for dep_id in app.depends_on:
            dep_status = self.get_status(config_id, dep_id)
            if dep_status.allocated_port:
                # Find the dependency app to get its port_env_var
                dep_app = next((a for a in config.applications if a.id == dep_id), None)
                if dep_app and dep_app.port_env_var:
                    env[f"{dep_id.upper()}_PORT"] = str(dep_status.allocated_port)

        return env

    def _run_build(
        self,
        app: ApplicationInstance,
        env: dict[str, str],
    ) -> tuple[bool, str | None]:
        """Run build command for the application.

        Args:
            app: Application instance
            env: Environment variables

        Returns:
            Tuple of (success, error_message)
        """
        if not app.build_command:
            return True, None

        try:
            logger.info(f"Running build command for {app.id}: {app.build_command}")
            result = subprocess.run(
                app.build_command,
                shell=True,
                cwd=app.working_dir,
                env=env,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout for builds
                check=False,
            )

            if result.returncode != 0:
                error_msg = result.stderr or result.stdout or "Build failed"
                logger.error(f"Build failed for {app.id}: {error_msg}")
                return False, error_msg

            logger.info(f"Build successful for {app.id}")
            return True, None

        except subprocess.TimeoutExpired:
            return False, "Build timeout (5 minutes)"
        except Exception as e:
            return False, f"Build error: {e}"

    def _start_process(
        self,
        app: ApplicationInstance,
        env: dict[str, str],
        handler: Any,
    ) -> subprocess.Popen[bytes] | None:
        """Start the application process.

        Args:
            app: Application instance
            env: Environment variables
            handler: Application type handler

        Returns:
            Process instance or None
        """
        try:
            # Let handler prepare the command if needed
            command = handler.prepare_command(app, env) if handler else app.command

            logger.info(f"Starting process for {app.id}: {command}")

            process = subprocess.Popen(
                command,
                shell=True,
                cwd=app.working_dir,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                # Start new process group for clean termination
                start_new_session=True,
            )

            return process

        except Exception as e:
            logger.error(f"Failed to start process for {app.id}: {e}")
            return None

    def _start_log_capture(
        self,
        config_id: str,
        app_id: str,
        process: subprocess.Popen[bytes],
    ) -> None:
        """Start threads to capture stdout and stderr.

        Args:
            config_id: Configuration identifier
            app_id: Application identifier
            process: Process instance
        """
        status_key = f"{config_id}/{app_id}"
        stop_event = threading.Event()
        self._stop_events[status_key] = stop_event

        def capture_stream(stream: Any, stream_name: str) -> None:
            """Capture output from a stream."""
            try:
                for line in iter(stream.readline, b""):
                    if stop_event.is_set():
                        break
                    if line:
                        self.log_manager.write_log(
                            config_id,
                            app_id,
                            line.decode("utf-8", errors="replace").rstrip(),
                            stream_name,
                        )
            except Exception as e:
                logger.error(f"Error capturing {stream_name} for {app_id}: {e}")

        # Start capture threads
        stdout_thread = threading.Thread(
            target=capture_stream,
            args=(process.stdout, "stdout"),
            daemon=True,
        )
        stderr_thread = threading.Thread(
            target=capture_stream,
            args=(process.stderr, "stderr"),
            daemon=True,
        )

        stdout_thread.start()
        stderr_thread.start()

        self._log_threads[status_key] = [stdout_thread, stderr_thread]

    def _wait_for_startup(
        self,
        config_id: str,
        app_id: str,
        app: ApplicationInstance,
    ) -> bool:
        """Wait for application to start and pass health check.

        Args:
            config_id: Configuration identifier
            app_id: Application identifier
            app: Application instance

        Returns:
            True if startup successful
        """
        status_key = f"{config_id}/{app_id}"
        start_time = time.time()

        while time.time() - start_time < app.startup_timeout:
            # Check if process is still running
            if status_key in self._processes:
                process = self._processes[status_key]
                if process.poll() is not None:
                    # Process has exited
                    logger.error(f"Process {app_id} exited during startup")
                    return False

            # Run health check if configured
            if app.health_check:
                health = self._check_health(app)
                if health == HealthStatus.HEALTHY:
                    return True

            time.sleep(1)

        # If no health check, just check process is running
        if not app.health_check:
            if status_key in self._processes:
                process = self._processes[status_key]
                return process.poll() is None

        return False

    def _check_health(self, app: ApplicationInstance) -> HealthStatus:
        """Check application health.

        Args:
            app: Application instance

        Returns:
            Health status
        """
        if not app.health_check:
            return HealthStatus.UNKNOWN

        try:
            if app.health_check.type == HealthCheckType.HTTP:
                return self._check_http_health(app)
            elif app.health_check.type == HealthCheckType.TCP:
                return self._check_tcp_health(app)
            elif app.health_check.type == HealthCheckType.PROCESS:
                return HealthStatus.HEALTHY  # Process check done in wait_for_startup

        except Exception as e:
            logger.debug(f"Health check failed for {app.id}: {e}")

        return HealthStatus.UNHEALTHY

    def _check_http_health(self, app: ApplicationInstance) -> HealthStatus:
        """Check HTTP health.

        Args:
            app: Application instance

        Returns:
            Health status
        """
        if not app.health_check or not app.health_check.url:
            return HealthStatus.UNKNOWN

        try:
            response = httpx.get(
                app.health_check.url,
                timeout=app.health_check.timeout,
                follow_redirects=True,
            )
            if 200 <= response.status_code < 400:
                return HealthStatus.HEALTHY
        except Exception:
            pass

        return HealthStatus.UNHEALTHY

    def _check_tcp_health(self, app: ApplicationInstance) -> HealthStatus:
        """Check TCP health.

        Args:
            app: Application instance

        Returns:
            Health status
        """
        if not app.health_check or not app.health_check.port:
            return HealthStatus.UNKNOWN

        import socket

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(app.health_check.timeout)
            result = sock.connect_ex(("127.0.0.1", app.health_check.port))
            sock.close()
            return HealthStatus.HEALTHY if result == 0 else HealthStatus.UNHEALTHY
        except Exception:
            return HealthStatus.UNHEALTHY

    def _terminate_gracefully(self, process: subprocess.Popen[bytes], timeout: int) -> None:
        """Terminate a process gracefully.

        Args:
            process: Process to terminate
            timeout: Timeout in seconds
        """
        try:
            # Send SIGTERM
            process.terminate()

            # Wait for process to exit
            try:
                process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                # Force kill if timeout
                logger.warning("Graceful shutdown timeout, force killing process")
                self._terminate_forcefully(process)

        except Exception as e:
            logger.error(f"Error during graceful termination: {e}")
            self._terminate_forcefully(process)

    def _terminate_forcefully(self, process: subprocess.Popen[bytes]) -> None:
        """Terminate a process forcefully.

        Args:
            process: Process to terminate
        """
        try:
            # Kill entire process group
            if process.pid:
                try:
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                except ProcessLookupError:
                    pass  # Process already gone

            process.kill()
            process.wait(timeout=5)
        except Exception as e:
            logger.error(f"Error during forced termination: {e}")

    def _cleanup_process(self, config_id: str, app_id: str) -> None:
        """Clean up process resources.

        Args:
            config_id: Configuration identifier
            app_id: Application identifier
        """
        status_key = f"{config_id}/{app_id}"

        # Remove from tracking
        if status_key in self._processes:
            del self._processes[status_key]

        if status_key in self._log_threads:
            del self._log_threads[status_key]

        if status_key in self._stop_events:
            del self._stop_events[status_key]

        # Update status
        if status_key in self._status:
            self._status[status_key].state = AppState.STOPPED
            self._status[status_key].pid = None

        # Release port
        self.port_manager.release_port(status_key)

        # Stop logging
        self.log_manager.stop_logging(config_id, app_id)

    def _handle_auto_restart(
        self,
        config_id: str,
        app_id: str,
        app: ApplicationInstance,
    ) -> None:
        """Handle auto-restart with exponential backoff.

        Args:
            config_id: Configuration identifier
            app_id: Application identifier
            app: Application instance
        """
        status_key = f"{config_id}/{app_id}"
        current_time = time.time()

        # Initialize restart tracking
        if status_key not in self._restart_timestamps:
            self._restart_timestamps[status_key] = []

        # Clean up old timestamps (older than 1 hour)
        self._restart_timestamps[status_key] = [
            ts for ts in self._restart_timestamps[status_key] if current_time - ts < 3600
        ]

        # Check restart limit
        if len(self._restart_timestamps[status_key]) >= 10:
            logger.error(f"Restart limit reached for {app_id}, giving up")
            return

        # Calculate backoff
        restart_count = len(self._restart_timestamps[status_key])
        backoff = min(2**restart_count, 30)  # Max 30 seconds

        logger.info(f"Auto-restarting {app_id} in {backoff} seconds...")
        time.sleep(backoff)

        # Record restart attempt
        self._restart_timestamps[status_key].append(current_time)

        # Attempt restart (this would need handler_registry passed in)
        # For now, just log
        logger.info(f"Auto-restart triggered for {app_id}")

    def shutdown_all(self) -> None:
        """Shutdown all managed processes."""
        logger.info("Shutting down all managed processes...")

        for status_key in list(self._processes.keys()):
            config_id, app_id = status_key.split("/", 1)
            self.stop_application(config_id, app_id, graceful=True, timeout=5)

        logger.info("All processes shut down")
