"""Core data models for ClientServerRunner."""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class AppState(str, Enum):
    """Application lifecycle states."""

    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    FAILED = "failed"
    STOPPING = "stopping"


class HealthStatus(str, Enum):
    """Health check status."""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class HealthCheckType(str, Enum):
    """Types of health checks."""

    HTTP = "http"
    TCP = "tcp"
    PROCESS = "process"


class HealthCheck(BaseModel):
    """Health check configuration."""

    type: HealthCheckType
    url: str | None = None
    port: int | None = None
    interval: int = Field(default=5, ge=1, description="Check interval in seconds")
    timeout: int = Field(default=3, ge=1, description="Check timeout in seconds")

    @model_validator(mode="after")
    def validate_health_check(self) -> "HealthCheck":
        """Validate health check configuration based on type."""
        if self.type == HealthCheckType.HTTP and not self.url:
            raise ValueError("HTTP health check requires url")
        if self.type == HealthCheckType.TCP and not self.port:
            raise ValueError("TCP health check requires port")
        return self


class ApplicationInstance(BaseModel):
    """Single application instance within a configuration."""

    id: str = Field(description="Unique identifier within configuration")
    name: str = Field(description="Human-readable name")
    app_type: str = Field(description="Application type (python, npm, scala)")
    working_dir: Path = Field(description="Execution directory")
    command: str = Field(description="Start command")
    env: dict[str, str] = Field(default_factory=dict, description="Environment variables")
    build_command: str | None = Field(
        default=None, description="Pre-flight build command (e.g., 'sbt compile')"
    )
    health_check: HealthCheck | None = Field(default=None, description="Health check config")
    auto_restart: bool = Field(default=False, description="Restart on failure")
    startup_timeout: int = Field(default=60, ge=1, description="Startup timeout in seconds")
    depends_on: list[str] = Field(
        default_factory=list, description="List of app IDs that must start first"
    )
    port: int | None = Field(default=None, description="Fixed port, or None for dynamic")
    port_env_var: str | None = Field(
        default=None, description="Env var name to receive allocated port"
    )

    @field_validator("working_dir", mode="before")
    @classmethod
    def validate_working_dir(cls, v: str | Path) -> Path:
        """Convert string to Path and validate it's a directory."""
        path = Path(v) if isinstance(v, str) else v
        if not path.is_absolute():
            path = path.absolute()
        return path

    @field_validator("app_type")
    @classmethod
    def validate_app_type(cls, v: str) -> str:
        """Validate app type is supported."""
        supported_types = {"python", "npm", "scala"}
        if v not in supported_types:
            raise ValueError(
                f"Unsupported app type: {v}. Supported types: {', '.join(supported_types)}"
            )
        return v

    @field_validator("port")
    @classmethod
    def validate_port(cls, v: int | None) -> int | None:
        """Validate port is in valid range."""
        if v is not None and (v < 0 or v > 65535):
            raise ValueError(f"Port must be between 0 and 65535, got {v}")
        return v


class Configuration(BaseModel):
    """Configuration containing multiple application instances."""

    id: str = Field(description="Unique identifier")
    name: str = Field(description="Human-readable name")
    description: str | None = Field(default=None, description="Optional description")
    applications: list[ApplicationInstance] = Field(
        description="List of application instances"
    )
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    @model_validator(mode="after")
    def validate_configuration(self) -> "Configuration":
        """Validate configuration consistency."""
        # Check for duplicate app IDs
        app_ids = [app.id for app in self.applications]
        if len(app_ids) != len(set(app_ids)):
            raise ValueError("Duplicate application IDs found")

        # Validate dependencies exist
        for app in self.applications:
            for dep_id in app.depends_on:
                if dep_id not in app_ids:
                    raise ValueError(
                        f"Application '{app.id}' depends on non-existent app '{dep_id}'"
                    )

        # Check for circular dependencies
        self._check_circular_dependencies()

        return self

    def _check_circular_dependencies(self) -> None:
        """Check for circular dependencies using DFS."""
        app_deps = {app.id: set(app.depends_on) for app in self.applications}

        def has_cycle(app_id: str, visited: set[str], rec_stack: set[str]) -> bool:
            visited.add(app_id)
            rec_stack.add(app_id)

            for dep_id in app_deps.get(app_id, set()):
                if dep_id not in visited:
                    if has_cycle(dep_id, visited, rec_stack):
                        return True
                elif dep_id in rec_stack:
                    return True

            rec_stack.remove(app_id)
            return False

        visited: set[str] = set()
        for app in self.applications:
            if app.id not in visited:
                if has_cycle(app.id, visited, set()):
                    raise ValueError(f"Circular dependency detected involving '{app.id}'")


class ApplicationStatus(BaseModel):
    """Runtime status of an application instance."""

    app_id: str
    state: AppState
    pid: int | None = None
    exit_code: int | None = None
    started_at: datetime | None = None
    error_message: str | None = None
    health: HealthStatus = HealthStatus.UNKNOWN
    allocated_port: int | None = None

    def uptime_seconds(self) -> int | None:
        """Calculate uptime in seconds if running."""
        if self.started_at is None:
            return None
        return int((datetime.now() - self.started_at).total_seconds())


class LogEntry(BaseModel):
    """Single log entry."""

    timestamp: datetime
    line_number: int
    content: str
    stream: str = "stdout"  # stdout or stderr


class LogRunInfo(BaseModel):
    """Information about a log run archive."""

    run_id: str
    started_at: datetime
    ended_at: datetime | None
    file_path: Path
    file_size: int


class CommandResult(BaseModel):
    """Result of a command execution."""

    exit_code: int
    stdout: str
    stderr: str
    duration_seconds: float


class ConfigurationSummary(BaseModel):
    """Summary of a configuration for listing."""

    id: str
    name: str
    description: str | None
    app_count: int
    created_at: datetime
    updated_at: datetime
    has_running_apps: bool = False


class StartResult(BaseModel):
    """Result of starting an application."""

    app_id: str
    success: bool
    message: str
    pid: int | None = None
    allocated_port: int | None = None


class StopResult(BaseModel):
    """Result of stopping an application."""

    app_id: str
    success: bool
    message: str


class ServerConfig(BaseModel):
    """Server configuration."""

    data_dir: Path = Field(default=Path.home() / ".clientserverrunner")
    log_retention_runs: int = Field(default=10, ge=1)
    log_max_size_mb: int = Field(default=100, ge=1)
    default_startup_timeout: int = Field(default=60, ge=1)

    @field_validator("data_dir", mode="before")
    @classmethod
    def validate_data_dir(cls, v: str | Path) -> Path:
        """Convert string to Path."""
        return Path(v) if isinstance(v, str) else v

    def ensure_directories(self) -> None:
        """Create necessary directories."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / "configurations").mkdir(exist_ok=True)
        (self.data_dir / "logs").mkdir(exist_ok=True)
        (self.data_dir / "state").mkdir(exist_ok=True)


class SearchResult(BaseModel):
    """Result of a log search."""

    line_number: int
    timestamp: datetime | None
    content: str
    context_before: list[str] = Field(default_factory=list)
    context_after: list[str] = Field(default_factory=list)
    run_id: str = "current"
