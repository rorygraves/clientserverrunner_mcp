# ClientServerRunner MCP Server - Specification

## Overview

A Python-based MCP (Model Context Protocol) server that manages the lifecycle of multi-application configurations. Designed to help AI agents like Claude Code manage, monitor, and test complex application stacks (e.g., backend + frontend).

## Core Concepts

### Configuration
A named group of related application instances that work together (e.g., "my-webapp" containing a FastAPI backend and React frontend).

### Application Instance
A single runnable application within a configuration, with:
- Type (Python, NPM, Scala/SBT)
- Start command
- Working directory
- Environment variables
- Build/compilation requirements
- Health check configuration

### Application Lifecycle States
- `stopped`: Not running
- `starting`: Being started
- `running`: Successfully running
- `failed`: Crashed or failed to start (with error code)
- `stopping`: Being stopped

## Architecture

### Component Structure

```
┌─────────────────────────────────────────────────────────┐
│                    MCP Server (FastMCP)                  │
│  ┌───────────────────────────────────────────────────┐  │
│  │  Configuration Manager                            │  │
│  │  - CRUD operations                                │  │
│  │  - Persistent storage (JSON)                      │  │
│  └───────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────┐  │
│  │  Process Manager                                  │  │
│  │  - Start/Stop/Restart                            │  │
│  │  - Status monitoring                             │  │
│  │  - Process health checks                         │  │
│  └───────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────┐  │
│  │  Log Manager                                      │  │
│  │  - Log capture (stdout/stderr)                   │  │
│  │  - Log storage and rotation                      │  │
│  │  - Log search capabilities                       │  │
│  └───────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────┐  │
│  │  Application Type Registry (Plugin System)       │  │
│  │  ┌─────────────┬─────────────┬─────────────┐    │  │
│  │  │   Python    │     NPM     │  Scala/SBT  │    │  │
│  │  │   Handler   │   Handler   │   Handler   │    │  │
│  │  └─────────────┴─────────────┴─────────────┘    │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### Plugin System: Application Type Handlers

Each application type implements:
- `prepare()`: Pre-flight checks, compilation
- `start()`: Start command construction
- `health_check()`: Determine if app is healthy
- `reload()`: Trigger hot-reload if supported
- `run_custom_command()`: Lint, format, test, etc.

#### Python Handler
- Supports: FastAPI, Flask, Django, etc.
- Auto-reload: uvicorn --reload, flask --debug
- Custom commands: mypy, ruff, pytest, black

#### NPM Handler
- Supports: npm run dev, Vite, Next.js, CRA
- Auto-reload: Built into dev servers
- Handles port conflicts and build failures
- Custom commands: npm run lint, npm run format, npm test

#### Scala/SBT Handler
- Supports: sbt run, sbt ~run (continuous compilation)
- Health check: HTTP endpoint ping
- Compilation trigger: URL-based reload for Play Framework
- Custom commands: sbt compile, sbt test, scalafmt

## Data Models

### Configuration (Pydantic)
```python
class Configuration:
    id: str                          # Unique identifier
    name: str                        # Human-readable name
    description: str | None          # Optional description
    applications: List[ApplicationInstance]
    created_at: datetime
    updated_at: datetime
```

### ApplicationInstance (Pydantic)
```python
class ApplicationInstance:
    id: str                          # Unique within configuration
    name: str                        # Human-readable name
    app_type: str                    # "python", "npm", "scala"
    working_dir: Path                # Execution directory
    command: str                     # Start command
    env: Dict[str, str]              # Environment variables
    build_command: str | None        # Pre-flight build (e.g., "sbt compile")
    health_check: HealthCheck | None # Health check configuration
    auto_restart: bool               # Restart on failure
    startup_timeout: int             # Seconds to wait for startup
    depends_on: List[str]            # List of app IDs that must start first
    port: int | None                 # Fixed port, or None for dynamic
    port_env_var: str | None         # Env var name to receive allocated port
```

### HealthCheck (Pydantic)
```python
class HealthCheck:
    type: str                        # "http", "tcp", "process"
    url: str | None                  # For HTTP checks
    port: int | None                 # For TCP checks
    interval: int                    # Check interval (seconds)
    timeout: int                     # Check timeout (seconds)
```

### ApplicationStatus (Pydantic)
```python
class ApplicationStatus:
    app_id: str
    state: str                       # stopped, starting, running, failed, stopping
    pid: int | None                  # Process ID if running
    exit_code: int | None            # Exit code if failed
    started_at: datetime | None
    error_message: str | None
    health: str                      # "healthy", "unhealthy", "unknown"
```

## MCP Tools (API)

### Configuration Management

#### `list_configurations`
```
Returns: List of configuration names and IDs
```

#### `create_configuration`
```
Parameters:
  - name: str
  - description: str (optional)
  - applications: List[ApplicationConfig]
Returns: Configuration ID
```

#### `get_configuration`
```
Parameters:
  - config_id: str
Returns: Full configuration details
```

#### `update_configuration`
```
Parameters:
  - config_id: str
  - updates: Partial configuration
Returns: Updated configuration
```

#### `delete_configuration`
```
Parameters:
  - config_id: str
  - force: bool (stop running apps first)
Returns: Success status
```

### Lifecycle Management

#### `start_configuration`
```
Parameters:
  - config_id: str
  - app_ids: List[str] (optional, defaults to all)
Returns: Start status for each app
```

#### `stop_configuration`
```
Parameters:
  - config_id: str
  - app_ids: List[str] (optional, defaults to all)
  - graceful: bool (default true)
Returns: Stop status for each app
```

#### `restart_configuration`
```
Parameters:
  - config_id: str
  - app_ids: List[str] (optional, defaults to all)
Returns: Restart status for each app
```

#### `get_status`
```
Parameters:
  - config_id: str
  - app_ids: List[str] (optional, defaults to all)
Returns: Status for each app (state, PID, health, errors)
```

### Log Management

#### `get_logs`
```
Parameters:
  - config_id: str
  - app_id: str
  - lines: int (default 100, recent lines)
  - follow: bool (stream logs - not for MCP, returns latest)
Returns: Log lines with timestamps
```

#### `search_logs`
```
Parameters:
  - config_id: str
  - app_id: str
  - query: str (keyword or regex)
  - max_results: int (default 100)
  - case_sensitive: bool (default false)
Returns: Matching log lines with context
```

### Custom Commands

#### `run_command`
```
Parameters:
  - config_id: str
  - app_id: str
  - command: str ("lint", "format", "test", "typecheck", custom)
  - args: List[str] (optional additional arguments)
Returns: Command output and exit code
```

#### `trigger_reload`
```
Parameters:
  - config_id: str
  - app_id: str
Returns: Reload status
```

## Storage

### Configuration Storage
- Format: JSON files
- Location: `{data_dir}/configurations/{config_id}.json`
- Atomic writes with temp files

### Log Storage
- Format: Plain text with timestamps
- Location: `{data_dir}/logs/{config_id}/{app_id}/`
- Files: `current.log`, `YYYY-MM-DD-HH-MM-SS.log` (archived on restart)
- Rotation: Keep last N runs or last N days
- Max file size: Configurable (default 100MB)

### Server Configuration
- Location: `{data_dir}/server_config.json`
- Contains: Data directory, log retention, etc.

## Error Handling

### Process Failures
- Capture exit codes and stderr
- Store in application status
- Preserve logs until manual clear or restart
- Optional auto-restart with backoff

### Build Failures
- Treat as application failure
- Capture build output in logs
- Report clear error message

### Auto-Reload Failures
- Detect compilation errors in logs
- Update application status to "unhealthy"
- Preserve error state until fixed

## Code Quality

### Type Safety
- Full mypy strict mode
- Pydantic for runtime validation
- Type hints everywhere

### Code Quality Tools
- Ruff: Linting and formatting
- MyPy: Type checking
- Pre-commit hooks for all checks

### Testing Strategy
- Unit tests: Each manager and handler independently
- Integration tests: Real processes (simple Python/Node scripts)
- Test fixtures: Sample configurations
- Coverage target: >85%

## CI/CD

### GitHub Actions Workflow
- Lint: Ruff check
- Format check: Ruff format --check
- Type check: MyPy strict mode
- Tests: pytest with coverage
- Matrix: Python 3.12, 3.13
- Coverage threshold: 85%
- Cache: Poetry dependencies

## Documentation

### External
- README.md: Quick start, installation
- USAGE.md: Detailed usage examples
- DEVELOPMENT.md: Contributing guidelines

### Internal
- Docstrings: All public functions (Google style)
- Type hints: All function signatures
- Comments: Complex logic only

## Design Decisions

### 1. Process Management: Supervisor Model ✓
The MCP server runs as a supervisor, keeping application processes as children. When the MCP server stops or fails, all managed processes are automatically terminated. This ensures clean shutdown and prevents orphaned processes.

### 2. Configuration Format: JSON ✓
Configurations are stored as JSON files for machine-friendliness and native Pydantic support. JSON provides good balance between human-readability and programmatic manipulation.

### 3. Startup Dependencies: Ordered Startup with Health Checks ✓
Support `depends_on` field in application configurations to specify startup order. Each application can wait for dependencies to pass health checks before starting.

### 4. Port Management: Hybrid Approach ✓
- Support hardcoded ports in configuration (for known services)
- Support dynamic port allocation using port 0 (OS assigns)
- Allow port passing between services via environment variables
- Example: Backend gets dynamic port, frontend receives it via `BACKEND_PORT` env var

### 5. Security: Trusted Environment ✓
No sandboxing or command restrictions initially. The MCP server trusts the agent and user. Security features may be added in future versions.

### 6. Log Retention: Configurable with Sensible Defaults ✓
- Default: Keep last 10 runs per application
- Configurable: Override globally or per-application
- Support querying logs from previous runs via MCP methods
- Archive logs with timestamps on each restart

### 7. Python Version: 3.12+ ✓
Target Python 3.12+ for modern type hints, performance improvements, and latest language features.

## Future Enhancements

These features are out of scope for initial version but may be added later:
- Resource limits (CPU/memory per application)
- Docker-compose style networking
- Webhooks/notifications for state changes
- Command sandboxing and security restrictions
- YAML configuration support
- Web UI for monitoring
