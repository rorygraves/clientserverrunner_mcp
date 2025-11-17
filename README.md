# ClientServerRunner MCP Server

A powerful MCP (Model Context Protocol) server for managing multi-application configurations. Perfect for AI agents like Claude Code to manage, monitor, and test complex application stacks.

## Features

- 🚀 **Multi-Application Management**: Run and coordinate multiple applications (backend, frontend, services)
- 🔄 **Dependency Management**: Automatic ordered startup based on dependencies
- 🏥 **Health Monitoring**: HTTP, TCP, and process-based health checks
- 📊 **Log Management**: Capture, search, and archive application logs
- 🔌 **Port Management**: Dynamic port allocation with inter-app communication
- 🔧 **Custom Commands**: Run lint, format, test, and other commands per app
- 🔥 **Hot Reload**: Trigger hot reload for supported frameworks
- 🎯 **Application Types**: Built-in support for Python, NPM/Node.js, and Scala/SBT

## Installation

### Requirements

- Python 3.12 or higher
- Poetry (for development)

### Using Poetry

```bash
git clone https://github.com/yourusername/clientserverrunner_mcp.git
cd clientserverrunner_mcp
poetry install
```

### Using pip (future)

```bash
pip install clientserverrunner
```

## Quick Start

### 1. Start the MCP Server

```bash
poetry run clientserverrunner
```

Or with custom data directory:

```bash
poetry run clientserverrunner --data-dir /path/to/data
```

### 2. Configure MCP Client

Add to your MCP client configuration (e.g., Claude Code):

```json
{
  "mcpServers": {
    "clientserverrunner": {
      "command": "poetry",
      "args": ["run", "clientserverrunner"],
      "cwd": "/path/to/clientserverrunner_mcp"
    }
  }
}
```

### 3. Create a Configuration

Use the MCP tools to create a configuration:

```python
# Create a configuration for a web application
create_configuration(
    name="my-webapp",
    description="FastAPI backend + React frontend",
    applications=[
        {
            "id": "backend",
            "name": "API Server",
            "app_type": "python",
            "working_dir": "/path/to/backend",
            "command": "uvicorn main:app --reload --port 8000",
            "health_check": {
                "type": "http",
                "url": "http://localhost:8000/health",
                "interval": 5,
                "timeout": 3
            }
        },
        {
            "id": "frontend",
            "name": "Web App",
            "app_type": "npm",
            "working_dir": "/path/to/frontend",
            "command": "npm run dev",
            "depends_on": ["backend"],
            "env": {
                "VITE_API_URL": "http://localhost:8000"
            }
        }
    ]
)
```

### 4. Start Applications

```python
# Start all applications in dependency order
start_configuration("my-webapp")

# Check status
get_status("my-webapp")

# View logs
get_logs("my-webapp", "backend", lines=100)

# Search logs
search_logs("my-webapp", "backend", "error|exception")

# Stop when done
stop_configuration("my-webapp")
```

## MCP Tools Reference

### Configuration Management

- `list_configurations()` - List all configurations
- `create_configuration(name, applications, description?)` - Create new configuration
- `get_configuration(config_id)` - Get configuration details
- `update_configuration(config_id, updates)` - Update configuration
- `delete_configuration(config_id, force?)` - Delete configuration

### Lifecycle Management

- `start_configuration(config_id, app_ids?)` - Start applications
- `stop_configuration(config_id, app_ids?, graceful?)` - Stop applications
- `restart_configuration(config_id, app_ids?)` - Restart applications
- `get_status(config_id, app_ids?)` - Get application status

### Log Management

- `get_logs(config_id, app_id, lines?, run_id?)` - Get recent logs
- `search_logs(config_id, app_id, query, max_results?, case_sensitive?)` - Search logs
- `list_log_runs(config_id, app_id)` - List archived log runs

### Custom Commands

- `run_command(config_id, app_id, command, args?)` - Run custom command
- `trigger_reload(config_id, app_id)` - Trigger hot reload

## Application Types

### Python Applications

**Supported Frameworks**: FastAPI, Flask, Django, any Python app

**Start Commands**:
```bash
uvicorn main:app --reload --port 8000
python -m flask run --debug
python manage.py runserver
```

**Custom Commands**: `lint`, `format`, `typecheck`, `test`

**Auto-reload**: Detected via `--reload`, `--debug`, `runserver` flags

### NPM/Node.js Applications

**Supported Frameworks**: Vite, Next.js, Create React App, Express, any npm app

**Start Commands**:
```bash
npm run dev
npm start
node server.js
```

**Custom Commands**: `lint`, `format`, `test`, `build`

**Auto-reload**: Built-in HMR for modern dev servers

### Scala/SBT Applications

**Supported Frameworks**: Play Framework, Akka, any SBT project

**Start Commands**:
```bash
sbt run
sbt ~run  # Continuous compilation
```

**Custom Commands**: `compile`, `test`, `format`, `clean`

**Auto-reload**: `~run` for continuous compilation

## Advanced Features

### Dependency Management

Applications can depend on others, ensuring correct startup order:

```python
{
    "id": "frontend",
    "depends_on": ["backend", "database"],
    # ...
}
```

### Port Management

#### Fixed Ports

```python
{
    "id": "backend",
    "port": 8000,
    # ...
}
```

#### Dynamic Ports

```python
{
    "id": "backend",
    "port": 0,  # or null - OS assigns port
    "port_env_var": "PORT",  # Receives allocated port
    # ...
}
```

#### Port Passing

```python
[
    {
        "id": "backend",
        "port": 0,
        "port_env_var": "PORT"
    },
    {
        "id": "frontend",
        "depends_on": ["backend"],
        # Automatically receives BACKEND_PORT env var
    }
]
```

### Health Checks

#### HTTP Health Check

```python
{
    "health_check": {
        "type": "http",
        "url": "http://localhost:8000/health",
        "interval": 5,
        "timeout": 3
    }
}
```

#### TCP Health Check

```python
{
    "health_check": {
        "type": "tcp",
        "port": 8000,
        "interval": 5,
        "timeout": 3
    }
}
```

#### Process Health Check

```python
{
    "health_check": {
        "type": "process",
        "interval": 5,
        "timeout": 3
    }
}
```

### Build Commands

Execute build steps before starting:

```python
{
    "id": "scala-app",
    "build_command": "sbt compile",
    "command": "sbt run",
    # ...
}
```

### Auto-Restart

Automatically restart failed applications:

```python
{
    "id": "backend",
    "auto_restart": true,
    "startup_timeout": 60,
    # ...
}
```

## Development

### Setup Development Environment

```bash
git clone https://github.com/yourusername/clientserverrunner_mcp.git
cd clientserverrunner_mcp
poetry install
poetry run pre-commit install
```

### Run Tests

```bash
# All tests
poetry run pytest

# With coverage
poetry run pytest --cov=src/clientserverrunner

# Specific test file
poetry run pytest tests/unit/test_models.py
```

### Code Quality

```bash
# Linting
poetry run ruff check .

# Format
poetry run ruff format .

# Type checking
poetry run mypy src/clientserverrunner
```

### Pre-commit Hooks

```bash
# Install hooks
poetry run pre-commit install

# Run manually
poetry run pre-commit run --all-files
```

## Architecture

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
│  │  Application Type Registry                       │  │
│  │  ┌─────────────┬─────────────┬─────────────┐    │  │
│  │  │   Python    │     NPM     │  Scala/SBT  │    │  │
│  │  │   Handler   │   Handler   │   Handler   │    │  │
│  │  └─────────────┴─────────────┴─────────────┘    │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

## Configuration Storage

Configurations are stored in JSON format:

```
~/.clientserverrunner/
├── configurations/
│   ├── {config-id}.json
│   └── ...
├── logs/
│   ├── {config-id}/
│   │   ├── {app-id}/
│   │   │   ├── current.log
│   │   │   ├── 2025-01-15-10-30-00.log
│   │   │   └── ...
│   │   └── ...
│   └── ...
└── state/
```

## Troubleshooting

### Application Won't Start

1. Check logs: `get_logs(config_id, app_id)`
2. Verify working directory exists
3. Ensure command is correct
4. Check for port conflicts

### Health Check Failing

1. Verify health check URL/port is correct
2. Increase timeout if application is slow to start
3. Check application logs for startup errors

### Port Conflicts

1. Use dynamic ports (port: 0)
2. Check for other processes using the port: `lsof -i :8000`
3. Verify port is released when application stops

## License

MIT License - see LICENSE file for details

## Contributing

Contributions welcome! Please see DEVELOPMENT.md for guidelines.

## Support

For issues and questions:
- GitHub Issues: https://github.com/yourusername/clientserverrunner_mcp/issues
- Documentation: See SPECIFICATION.md and REQUIREMENTS.md
