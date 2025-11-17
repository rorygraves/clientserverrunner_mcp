# Development Guide

## Getting Started

### Prerequisites

- Python 3.12 or higher
- Poetry 1.8.0 or higher
- Git

### Initial Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/clientserverrunner_mcp.git
cd clientserverrunner_mcp
```

2. Install dependencies:
```bash
poetry install
```

3. Install pre-commit hooks:
```bash
poetry run pre-commit install
```

4. Verify installation:
```bash
poetry run pytest
poetry run mypy src/clientserverrunner
poetry run ruff check .
```

## Project Structure

```
clientserverrunner_mcp/
├── src/clientserverrunner/      # Main source code
│   ├── __init__.py
│   ├── __main__.py              # Entry point
│   ├── server.py                # FastMCP server implementation
│   ├── models.py                # Pydantic data models
│   ├── config_manager.py        # Configuration CRUD
│   ├── process_manager.py       # Process lifecycle management
│   ├── log_manager.py           # Log capture and search
│   ├── port_manager.py          # Port allocation
│   ├── types/                   # Application type handlers
│   │   ├── base.py              # Handler interface
│   │   ├── python.py            # Python handler
│   │   ├── npm.py               # NPM handler
│   │   └── scala.py             # Scala/SBT handler
│   └── utils/                   # Utilities
│       ├── logging.py
│       └── validation.py
├── tests/                       # Test suite
│   ├── unit/                    # Unit tests
│   ├── integration/             # Integration tests
│   └── fixtures/                # Test fixtures
├── examples/                    # Example configurations
├── .github/workflows/           # CI/CD
└── docs/                        # Documentation
```

## Code Standards

### Type Hints

All functions must have type hints:

```python
def process_data(input: str, count: int = 10) -> list[str]:
    """Process the input data."""
    return input.split()[:count]
```

### Docstrings

Use Google-style docstrings for all public functions:

```python
def create_configuration(
    name: str,
    applications: list[dict],
    description: str | None = None,
) -> Configuration:
    """Create a new configuration.

    Args:
        name: Configuration name
        applications: List of application definitions
        description: Optional description

    Returns:
        Created configuration

    Raises:
        ValueError: If configuration is invalid
    """
    pass
```

### Error Handling

- Use specific exceptions
- Include context in error messages
- Log errors appropriately

```python
try:
    config = self.get_configuration(config_id)
except KeyError:
    logger.error(f"Configuration {config_id} not found")
    raise KeyError(f"Configuration '{config_id}' not found")
```

## Testing

### Running Tests

```bash
# All tests
poetry run pytest

# With coverage
poetry run pytest --cov=src/clientserverrunner --cov-report=html

# Specific test
poetry run pytest tests/unit/test_models.py::TestConfiguration::test_valid_configuration

# Integration tests only
poetry run pytest tests/integration/

# Watch mode (requires pytest-watch)
poetry run ptw
```

### Writing Tests

#### Unit Tests

Test individual components in isolation:

```python
def test_create_configuration(config_manager: ConfigManager, temp_dir: Path):
    """Test creating a configuration."""
    config = config_manager.create_configuration(
        name="Test",
        applications=[{
            "id": "app1",
            "name": "App 1",
            "app_type": "python",
            "working_dir": str(temp_dir),
            "command": "python server.py",
        }]
    )
    assert config.name == "Test"
    assert len(config.applications) == 1
```

#### Integration Tests

Test full workflows with real processes:

```python
def test_start_stop_python_app(
    config_manager,
    process_manager,
    handler_registry,
    python_test_app: Path
):
    """Test starting and stopping a Python application."""
    # Create config, start app, verify running, stop app
    # ...
```

### Test Coverage

Maintain >85% code coverage:

```bash
poetry run pytest --cov=src/clientserverrunner --cov-fail-under=85
```

## Code Quality Tools

### Ruff (Linting and Formatting)

```bash
# Check for issues
poetry run ruff check .

# Fix auto-fixable issues
poetry run ruff check --fix .

# Format code
poetry run ruff format .

# Check formatting without changing
poetry run ruff format --check .
```

### MyPy (Type Checking)

```bash
# Type check all source code
poetry run mypy src/clientserverrunner

# Specific file
poetry run mypy src/clientserverrunner/models.py
```

### Pre-commit Hooks

Hooks run automatically on `git commit`:

```bash
# Run manually on all files
poetry run pre-commit run --all-files

# Update hooks to latest versions
poetry run pre-commit autoupdate
```

## Adding New Features

### 1. Add New Application Type Handler

Create a new handler in `src/clientserverrunner/types/`:

```python
# src/clientserverrunner/types/rust.py

from .base import ApplicationHandler
from ..models import ApplicationInstance, CommandResult


class RustHandler(ApplicationHandler):
    """Handler for Rust applications."""

    def prepare_command(
        self,
        app: ApplicationInstance,
        env: dict[str, str],
    ) -> str:
        return app.command

    def run_custom_command(
        self,
        app: ApplicationInstance,
        command: str,
        args: list[str],
        env: dict[str, str],
    ) -> CommandResult:
        # Implement custom commands (cargo test, cargo fmt, etc.)
        pass

    def supports_reload(self, app: ApplicationInstance) -> bool:
        return False

    def trigger_reload(self, app: ApplicationInstance) -> tuple[bool, str]:
        return False, "Rust applications don't support hot reload"
```

Register in `src/clientserverrunner/types/__init__.py`:

```python
def create_default_registry() -> HandlerRegistry:
    registry = HandlerRegistry()
    registry.register("python", PythonHandler())
    registry.register("npm", NpmHandler())
    registry.register("scala", ScalaHandler())
    registry.register("rust", RustHandler())  # Add this
    return registry
```

### 2. Add New MCP Tool

Add to `src/clientserverrunner/server.py`:

```python
@mcp.tool()
def my_new_tool(
    config_id: str,
    param: str,
) -> dict[str, Any]:
    """Description of what the tool does.

    Args:
        config_id: Configuration identifier
        param: Description of parameter

    Returns:
        Description of return value
    """
    # Implementation
    pass
```

### 3. Add Tests

Create corresponding test file:

```python
# tests/unit/test_rust_handler.py

def test_rust_handler():
    """Test Rust handler functionality."""
    pass
```

## Debugging

### Enable Debug Logging

```bash
poetry run clientserverrunner --log-level DEBUG
```

### Interactive Debugging

Use `breakpoint()` in code:

```python
def problematic_function():
    data = get_data()
    breakpoint()  # Debugger will stop here
    process_data(data)
```

Run with debugger:

```bash
poetry run python -m pdb -m clientserverrunner
```

### Inspect MCP Communication

FastMCP provides debug output. Check logs for MCP message exchange.

## Performance Profiling

### Profile Code

```python
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()

# Code to profile
result = expensive_function()

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(20)  # Top 20 functions
```

### Memory Profiling

```bash
poetry add --dev memory-profiler
poetry run python -m memory_profiler script.py
```

## Release Process

### 1. Update Version

Edit `pyproject.toml`:

```toml
[tool.poetry]
version = "1.1.0"
```

Edit `src/clientserverrunner/__init__.py`:

```python
__version__ = "1.1.0"
```

### 2. Update Changelog

Add release notes to `CHANGELOG.md`

### 3. Create Git Tag

```bash
git add pyproject.toml src/clientserverrunner/__init__.py CHANGELOG.md
git commit -m "Bump version to 1.1.0"
git tag v1.1.0
git push origin main --tags
```

### 4. Build and Publish (Future)

```bash
poetry build
poetry publish
```

## CI/CD

### GitHub Actions

Workflow runs on:
- Push to `main`
- Pull requests to `main`
- Push to `claude/**` branches

Jobs:
1. **Lint and Type Check**
   - Ruff linting
   - Ruff format check
   - MyPy type checking

2. **Test**
   - Matrix: Python 3.12, 3.13 on Ubuntu and macOS
   - Run tests with coverage
   - Upload coverage to Codecov

### Local CI Simulation

```bash
# Run what CI runs locally
poetry run ruff check .
poetry run ruff format --check .
poetry run mypy src/clientserverrunner
poetry run pytest --cov=src/clientserverrunner --cov-fail-under=85
```

## Common Tasks

### Add a Dependency

```bash
# Production dependency
poetry add package-name

# Development dependency
poetry add --dev package-name

# Update dependencies
poetry update
```

### Generate Documentation

```bash
# (Future) Generate API docs
poetry run pdoc --html --output-dir docs/api clientserverrunner
```

### Clean Up

```bash
# Remove generated files
find . -type d -name __pycache__ -exec rm -rf {} +
find . -type d -name .pytest_cache -exec rm -rf {} +
find . -type d -name .mypy_cache -exec rm -rf {} +
find . -type d -name .ruff_cache -exec rm -rf {} +
rm -rf .coverage htmlcov/
```

## Troubleshooting

### Poetry Issues

```bash
# Clear cache
poetry cache clear pypi --all

# Reinstall dependencies
rm -rf .venv
poetry install
```

### Test Failures

```bash
# Run with verbose output
poetry run pytest -vv

# Show print statements
poetry run pytest -s

# Run last failed tests
poetry run pytest --lf
```

### Import Errors

Ensure project is installed in editable mode:

```bash
poetry install
```

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make changes with tests
4. Run quality checks: `poetry run pre-commit run --all-files`
5. Commit: `git commit -m "Add my feature"`
6. Push: `git push origin feature/my-feature`
7. Create pull request

## Resources

- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Poetry Documentation](https://python-poetry.org/docs/)
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [MyPy Documentation](https://mypy.readthedocs.io/)
