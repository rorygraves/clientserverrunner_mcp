"""MCP server implementation for ClientServerRunner."""

import atexit
from typing import Any

from fastmcp import FastMCP

from .config_manager import ConfigManager
from .log_manager import LogManager
from .models import ServerConfig
from .port_manager import PortManager
from .process_manager import ProcessManager
from .types import create_default_registry
from .utils.logging import setup_logger

logger = setup_logger(__name__)

# Initialize server
mcp = FastMCP("ClientServerRunner")

# Global managers (initialized in main)
config_manager: ConfigManager
process_manager: ProcessManager
log_manager: LogManager
port_manager: PortManager
handler_registry: Any
server_config: ServerConfig


def initialize_managers(data_dir: str | None = None) -> None:
    """Initialize all managers.

    Args:
        data_dir: Optional data directory path
    """
    global config_manager, process_manager, log_manager, port_manager
    global handler_registry, server_config

    # Initialize server config
    server_config = ServerConfig()
    if data_dir:
        from pathlib import Path

        server_config.data_dir = Path(data_dir)

    server_config.ensure_directories()

    # Initialize managers
    config_manager = ConfigManager(server_config)
    log_manager = LogManager(server_config)
    port_manager = PortManager()
    handler_registry = create_default_registry()
    process_manager = ProcessManager(config_manager, log_manager, port_manager)

    # Register cleanup on exit
    atexit.register(cleanup)

    logger.info("ClientServerRunner MCP server initialized")


def cleanup() -> None:
    """Clean up resources on shutdown."""
    logger.info("Shutting down ClientServerRunner...")
    if process_manager:
        process_manager.shutdown_all()
    logger.info("Shutdown complete")


# Configuration Management Tools


@mcp.tool()
def list_configurations() -> list[dict[str, Any]]:
    """List all available configurations.

    Returns a list of configuration summaries including ID, name, description,
    and metadata. Useful for discovering what configurations are available.

    Returns:
        List of configuration summaries
    """
    summaries = config_manager.list_configurations()
    return [summary.model_dump() for summary in summaries]


@mcp.tool()
def create_configuration(
    name: str,
    applications: list[dict[str, Any]],
    description: str | None = None,
) -> dict[str, Any]:
    """Create a new configuration with multiple application instances.

    A configuration is a named group of related applications (e.g., backend + frontend).
    Each application defines how to start, monitor, and manage a process.

    Args:
        name: Human-readable configuration name
        applications: List of application definitions. Each must include:
            - id: Unique identifier within config
            - name: Human-readable name
            - app_type: Type (python, npm, scala)
            - working_dir: Absolute path to working directory
            - command: Start command to execute
            - env: Environment variables (optional)
            - depends_on: List of app IDs to start first (optional)
            - port: Fixed port or None for dynamic (optional)
            - health_check: Health check config (optional)
        description: Optional description of the configuration

    Returns:
        Created configuration details including generated ID

    Examples:
        >>> create_configuration(
        ...     name="my-webapp",
        ...     description="FastAPI backend + React frontend",
        ...     applications=[
        ...         {
        ...             "id": "backend",
        ...             "name": "API Server",
        ...             "app_type": "python",
        ...             "working_dir": "/path/to/backend",
        ...             "command": "uvicorn main:app --reload --port 8000",
        ...             "health_check": {"type": "http", "url": "http://localhost:8000/health"}
        ...         },
        ...         {
        ...             "id": "frontend",
        ...             "name": "Web App",
        ...             "app_type": "npm",
        ...             "working_dir": "/path/to/frontend",
        ...             "command": "npm run dev",
        ...             "depends_on": ["backend"],
        ...             "env": {"VITE_API_URL": "http://localhost:8000"}
        ...         }
        ...     ]
        ... )
    """
    config = config_manager.create_configuration(name, applications, description)
    return config.model_dump()


@mcp.tool()
def get_configuration(config_id: str) -> dict[str, Any]:
    """Get full details of a specific configuration.

    Args:
        config_id: Configuration identifier

    Returns:
        Complete configuration including all application definitions
    """
    config = config_manager.get_configuration(config_id)
    return config.model_dump()


@mcp.tool()
def update_configuration(
    config_id: str,
    updates: dict[str, Any],
) -> dict[str, Any]:
    """Update a configuration.

    Cannot update configurations with running applications - stop them first.

    Args:
        config_id: Configuration identifier
        updates: Dictionary of fields to update (name, description, applications, etc.)

    Returns:
        Updated configuration
    """
    # Check for running apps
    config = config_manager.get_configuration(config_id)
    for app in config.applications:
        status = process_manager.get_status(config_id, app.id)
        if status.state.value in ["starting", "running", "stopping"]:
            raise ValueError(
                f"Cannot update configuration with running applications. " f"Stop '{app.id}' first."
            )

    updated = config_manager.update_configuration(config_id, updates)
    return updated.model_dump()


@mcp.tool()
def delete_configuration(
    config_id: str,
    force: bool = False,
) -> dict[str, str]:
    """Delete a configuration.

    Args:
        config_id: Configuration identifier
        force: If true, stop running applications before deleting

    Returns:
        Success message
    """
    if force:
        # Stop all running apps first
        config = config_manager.get_configuration(config_id)
        for app in config.applications:
            status = process_manager.get_status(config_id, app.id)
            if status.state.value != "stopped":
                process_manager.stop_application(config_id, app.id)

    # Check no apps are running
    config = config_manager.get_configuration(config_id)
    for app in config.applications:
        status = process_manager.get_status(config_id, app.id)
        if status.state.value != "stopped":
            raise ValueError(
                "Cannot delete configuration with running applications. "
                "Use force=true to stop them first."
            )

    config_manager.delete_configuration(config_id)
    return {"status": "success", "message": f"Configuration '{config_id}' deleted"}


# Lifecycle Management Tools


@mcp.tool()
def start_configuration(
    config_id: str,
    app_ids: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Start applications within a configuration.

    Applications are started in dependency order (respecting depends_on).
    Health checks are performed before starting dependents.

    Args:
        config_id: Configuration identifier
        app_ids: List of specific app IDs to start, or None for all apps

    Returns:
        List of start results for each application

    Examples:
        >>> # Start all applications in dependency order
        >>> start_configuration("my-webapp")

        >>> # Start only specific applications
        >>> start_configuration("my-webapp", app_ids=["backend"])
    """
    config = config_manager.get_configuration(config_id)

    # Determine which apps to start
    apps_to_start = config.applications
    if app_ids:
        apps_to_start = [app for app in config.applications if app.id in app_ids]

    # Sort by dependencies (topological sort)
    sorted_apps = _topological_sort_apps(apps_to_start, config.applications)

    results = []
    for app in sorted_apps:
        result = process_manager.start_application(config_id, app.id, handler_registry)
        results.append(result.model_dump())

        # If startup failed and this is a dependency, stop here
        if not result.success and any(app.id in other.depends_on for other in sorted_apps):
            logger.error(f"Failed to start dependency '{app.id}', stopping startup sequence")
            break

    return results


@mcp.tool()
def stop_configuration(
    config_id: str,
    app_ids: list[str] | None = None,
    graceful: bool = True,
) -> list[dict[str, Any]]:
    """Stop applications within a configuration.

    Applications are stopped in reverse dependency order (dependents before dependencies).

    Args:
        config_id: Configuration identifier
        app_ids: List of specific app IDs to stop, or None for all apps
        graceful: Use graceful shutdown (SIGTERM) if true, force kill (SIGKILL) if false

    Returns:
        List of stop results for each application
    """
    config = config_manager.get_configuration(config_id)

    # Determine which apps to stop
    apps_to_stop = config.applications
    if app_ids:
        apps_to_stop = [app for app in config.applications if app.id in app_ids]

    # Sort in reverse dependency order
    sorted_apps = _topological_sort_apps(apps_to_stop, config.applications)
    sorted_apps.reverse()

    results = []
    for app in sorted_apps:
        result = process_manager.stop_application(config_id, app.id, graceful)
        results.append(result.model_dump())

    return results


@mcp.tool()
def restart_configuration(
    config_id: str,
    app_ids: list[str] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Restart applications within a configuration.

    Equivalent to stop + start, maintaining dependency order.

    Args:
        config_id: Configuration identifier
        app_ids: List of specific app IDs to restart, or None for all apps

    Returns:
        Dictionary with 'stop_results' and 'start_results' lists
    """
    stop_results = stop_configuration(config_id, app_ids, graceful=True)
    start_results = start_configuration(config_id, app_ids)

    return {"stop_results": stop_results, "start_results": start_results}


@mcp.tool()
def get_status(
    config_id: str,
    app_ids: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Get status of applications within a configuration.

    Returns detailed status including state, PID, health, errors, and uptime.

    Args:
        config_id: Configuration identifier
        app_ids: List of specific app IDs to query, or None for all apps

    Returns:
        List of application statuses
    """
    config = config_manager.get_configuration(config_id)

    apps_to_query = config.applications
    if app_ids:
        apps_to_query = [app for app in config.applications if app.id in app_ids]

    statuses = []
    for app in apps_to_query:
        status = process_manager.get_status(config_id, app.id)
        status_dict = status.model_dump()
        status_dict["uptime_seconds"] = status.uptime_seconds()
        statuses.append(status_dict)

    return statuses


# Log Management Tools


@mcp.tool()
def get_logs(
    config_id: str,
    app_id: str,
    lines: int = 100,
    run_id: str = "current",
) -> list[dict[str, Any]]:
    """Get recent log entries for an application.

    Args:
        config_id: Configuration identifier
        app_id: Application identifier
        lines: Number of recent lines to retrieve (default 100)
        run_id: Run identifier - 'current' for active logs, or timestamp for archived runs

    Returns:
        List of log entries with timestamps and content
    """
    entries = log_manager.get_logs(config_id, app_id, lines, run_id)
    return [entry.model_dump() for entry in entries]


@mcp.tool()
def search_logs(
    config_id: str,
    app_id: str,
    query: str,
    max_results: int = 100,
    case_sensitive: bool = False,
    run_id: str = "current",
) -> list[dict[str, Any]]:
    """Search application logs for a pattern.

    Supports regex patterns for advanced searching.

    Args:
        config_id: Configuration identifier
        app_id: Application identifier
        query: Search pattern (regex supported)
        max_results: Maximum results to return (default 100)
        case_sensitive: Case-sensitive search if true
        run_id: Run identifier - 'current' or archived run timestamp

    Returns:
        List of matching log entries with context lines

    Examples:
        >>> # Search for errors
        >>> search_logs("my-webapp", "backend", "error|exception", case_sensitive=False)

        >>> # Search for specific HTTP status
        >>> search_logs("my-webapp", "backend", "status.*404")
    """
    results = log_manager.search_logs(config_id, app_id, query, max_results, case_sensitive, run_id)
    return [result.model_dump() for result in results]


@mcp.tool()
def list_log_runs(
    config_id: str,
    app_id: str,
) -> list[dict[str, Any]]:
    """List available archived log runs for an application.

    Each time an application restarts, its logs are archived with a timestamp.
    This allows querying historical logs.

    Args:
        config_id: Configuration identifier
        app_id: Application identifier

    Returns:
        List of log run information including timestamps and file sizes
    """
    runs = log_manager.list_runs(config_id, app_id)
    return [run.model_dump() for run in runs]


# Custom Command Tools


@mcp.tool()
def run_command(
    config_id: str,
    app_id: str,
    command: str,
    args: list[str] | None = None,
) -> dict[str, Any]:
    """Run a custom command for an application.

    Common commands by app type:
    - Python: lint, format, typecheck, test
    - NPM: lint, format, test, build
    - Scala: compile, test, format, clean

    Args:
        config_id: Configuration identifier
        app_id: Application identifier
        command: Command name
        args: Additional command arguments

    Returns:
        Command result with exit code, stdout, and stderr

    Examples:
        >>> # Run tests
        >>> run_command("my-webapp", "backend", "test")

        >>> # Run linter
        >>> run_command("my-webapp", "frontend", "lint", args=["--fix"])
    """
    config = config_manager.get_configuration(config_id)
    app = next((a for a in config.applications if a.id == app_id), None)

    if app is None:
        raise ValueError(f"Application '{app_id}' not found in configuration")

    handler = handler_registry.get_handler(app.app_type)

    # Prepare environment
    env = process_manager._prepare_environment(config_id, app, config)

    result = handler.run_custom_command(app, command, args or [], env)
    result_dict: dict[str, Any] = result.model_dump()
    return result_dict


@mcp.tool()
def trigger_reload(
    config_id: str,
    app_id: str,
) -> dict[str, Any]:
    """Trigger hot reload for an application.

    Works for applications with auto-reload support:
    - Python: uvicorn --reload, flask --debug
    - NPM: Vite, Next.js, CRA (HMR)
    - Scala: sbt ~run, Play Framework

    Args:
        config_id: Configuration identifier
        app_id: Application identifier

    Returns:
        Reload result with success status and message
    """
    config = config_manager.get_configuration(config_id)
    app = next((a for a in config.applications if a.id == app_id), None)

    if app is None:
        raise ValueError(f"Application '{app_id}' not found in configuration")

    handler = handler_registry.get_handler(app.app_type)

    success, message = handler.trigger_reload(app)
    return {"success": success, "message": message, "app_id": app_id}


# Helper Functions


def _topological_sort_apps(
    apps_to_sort: list[Any],
    all_apps: list[Any],
) -> list[Any]:
    """Sort applications in dependency order using topological sort.

    Args:
        apps_to_sort: Applications to sort
        all_apps: All applications in config (for dependency lookup)

    Returns:
        Sorted list of applications
    """
    from collections import deque

    # Build dependency graph
    app_map = {app.id: app for app in all_apps}
    in_degree = {app.id: 0 for app in apps_to_sort}
    adj_list: dict[str, list[str]] = {app.id: [] for app in apps_to_sort}

    for app in apps_to_sort:
        for dep_id in app.depends_on:
            if dep_id in adj_list:
                adj_list[dep_id].append(app.id)
                in_degree[app.id] += 1

    # Kahn's algorithm
    queue = deque([app_id for app_id, degree in in_degree.items() if degree == 0])
    sorted_ids = []

    while queue:
        app_id = queue.popleft()
        sorted_ids.append(app_id)

        for dependent_id in adj_list[app_id]:
            in_degree[dependent_id] -= 1
            if in_degree[dependent_id] == 0:
                queue.append(dependent_id)

    # Return sorted apps
    return [app_map[app_id] for app_id in sorted_ids]
