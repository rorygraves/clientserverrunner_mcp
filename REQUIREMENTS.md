# ClientServerRunner MCP Server - Requirements Document

## 1. Overview

### 1.1 Purpose
The ClientServerRunner MCP Server provides lifecycle management for multi-application configurations, enabling AI agents to efficiently manage, monitor, and test complex application stacks.

### 1.2 Scope
This document defines functional and non-functional requirements for version 1.0 of the ClientServerRunner MCP Server.

### 1.3 Target Users
- AI agents (e.g., Claude Code)
- Software developers testing multi-service applications
- DevOps engineers managing local development environments

## 2. Functional Requirements

### 2.1 Configuration Management

#### FR-1: Create Configuration
**Priority**: MUST
**Description**: System shall allow creating a new configuration with multiple application instances.
**Acceptance Criteria**:
- Accept configuration name, description, and list of applications
- Validate all application definitions
- Generate unique configuration ID
- Persist configuration to disk
- Return configuration ID on success

#### FR-2: List Configurations
**Priority**: MUST
**Description**: System shall list all available configurations.
**Acceptance Criteria**:
- Return configuration IDs, names, and descriptions
- Include created/updated timestamps
- Support filtering by status (has running apps)

#### FR-3: Get Configuration Details
**Priority**: MUST
**Description**: System shall retrieve full details of a specific configuration.
**Acceptance Criteria**:
- Accept configuration ID
- Return complete configuration including all application definitions
- Include metadata (created_at, updated_at)

#### FR-4: Update Configuration
**Priority**: MUST
**Description**: System shall allow updating configuration details.
**Acceptance Criteria**:
- Support partial updates
- Validate changes before applying
- Prevent updates to configurations with running applications
- Update timestamp on successful modification

#### FR-5: Delete Configuration
**Priority**: MUST
**Description**: System shall allow deleting configurations.
**Acceptance Criteria**:
- Support force deletion (stops running apps first)
- Prevent deletion of running configurations without force flag
- Remove configuration files and associated logs
- Return success/failure status

### 2.2 Application Lifecycle Management

#### FR-6: Start Applications
**Priority**: MUST
**Description**: System shall start applications within a configuration.
**Acceptance Criteria**:
- Support starting all applications or specific subset
- Respect dependency order (depends_on field)
- Wait for health checks before starting dependents
- Execute build commands before starting if specified
- Allocate dynamic ports when configured
- Pass allocated ports to dependent applications via environment variables
- Handle startup timeouts
- Capture and store startup logs

#### FR-7: Stop Applications
**Priority**: MUST
**Description**: System shall stop running applications.
**Acceptance Criteria**:
- Support stopping all applications or specific subset
- Support graceful shutdown (SIGTERM) with timeout
- Support forced shutdown (SIGKILL) after timeout or when requested
- Archive current logs on shutdown
- Update application status
- Stop dependents before dependencies (reverse order)

#### FR-8: Restart Applications
**Priority**: MUST
**Description**: System shall restart applications.
**Acceptance Criteria**:
- Equivalent to stop + start
- Preserve dependency ordering
- Archive logs from previous run
- Support restarting subset of applications

#### FR-9: Get Application Status
**Priority**: MUST
**Description**: System shall report status of applications.
**Acceptance Criteria**:
- Report state: stopped, starting, running, failed, stopping
- Include process ID when running
- Include exit code when failed
- Include error messages
- Include health check status
- Include start time and uptime
- Support querying all or specific applications

#### FR-10: Auto-Restart on Failure
**Priority**: SHOULD
**Description**: System shall optionally auto-restart failed applications.
**Acceptance Criteria**:
- Respect auto_restart flag in configuration
- Implement exponential backoff (1s, 2s, 4s, 8s, 16s, 30s max)
- Limit restart attempts (max 10 per hour)
- Log restart attempts and reasons

### 2.3 Health Monitoring

#### FR-11: HTTP Health Checks
**Priority**: MUST
**Description**: System shall support HTTP-based health checks.
**Acceptance Criteria**:
- Make GET request to configured URL
- Consider 2xx/3xx responses healthy
- Respect timeout configuration
- Retry on network errors
- Run checks at configured interval

#### FR-12: TCP Health Checks
**Priority**: MUST
**Description**: System shall support TCP port health checks.
**Acceptance Criteria**:
- Attempt TCP connection to configured port
- Consider successful connection as healthy
- Respect timeout configuration
- Handle connection refused gracefully

#### FR-13: Process Health Checks
**Priority**: MUST
**Description**: System shall support process-based health checks.
**Acceptance Criteria**:
- Check if process is running (PID exists)
- Verify process hasn't become a zombie
- Consider running non-zombie process as healthy

### 2.4 Log Management

#### FR-14: Capture Application Logs
**Priority**: MUST
**Description**: System shall capture stdout and stderr from applications.
**Acceptance Criteria**:
- Stream output to current log file
- Add timestamps to each line
- Handle high-volume output without blocking
- Separate stdout and stderr streams or interleave with markers

#### FR-15: Retrieve Recent Logs
**Priority**: MUST
**Description**: System shall provide access to recent application logs.
**Acceptance Criteria**:
- Return last N lines (default 100, configurable)
- Include timestamps
- Support retrieving from current run or archived runs
- Handle non-existent logs gracefully

#### FR-16: Search Logs
**Priority**: MUST
**Description**: System shall support searching application logs.
**Acceptance Criteria**:
- Accept keyword or regex pattern
- Support case-sensitive and case-insensitive search
- Return matching lines with context (line before/after)
- Limit results (default 100, configurable)
- Search across current and archived logs
- Include line numbers and timestamps

#### FR-17: List Log Runs
**Priority**: SHOULD
**Description**: System shall list available log archives for an application.
**Acceptance Criteria**:
- Return list of archived log runs with timestamps
- Include log file sizes
- Sort by timestamp (newest first)

#### FR-18: Log Rotation and Retention
**Priority**: MUST
**Description**: System shall manage log file size and retention.
**Acceptance Criteria**:
- Archive current logs on application restart
- Keep last N runs (default 10, configurable)
- Delete oldest logs when limit exceeded
- Support per-application retention override
- Compress archived logs (optional)

### 2.5 Application Type Handlers

#### FR-19: Python Application Support
**Priority**: MUST
**Description**: System shall support Python applications.
**Acceptance Criteria**:
- Start Python scripts and modules
- Support common frameworks (FastAPI, Flask, Django)
- Detect auto-reload capability
- Execute custom commands: mypy, ruff, pytest, black
- Detect Python version incompatibilities

#### FR-20: NPM Application Support
**Priority**: MUST
**Description**: System shall support NPM/Node.js applications.
**Acceptance Criteria**:
- Execute npm scripts (npm run dev, etc.)
- Support modern frameworks (Vite, Next.js, CRA)
- Detect port conflicts
- Handle build failures gracefully
- Execute custom commands: npm test, npm run lint, etc.

#### FR-21: Scala/SBT Application Support
**Priority**: MUST
**Description**: System shall support Scala applications using SBT.
**Acceptance Criteria**:
- Execute sbt commands (sbt run, sbt ~run)
- Support Play Framework applications
- Trigger compilation via HTTP endpoint if configured
- Execute custom commands: sbt compile, sbt test, scalafmt
- Handle long compilation times

#### FR-22: Custom Command Execution
**Priority**: MUST
**Description**: System shall execute custom commands on applications.
**Acceptance Criteria**:
- Accept command name and optional arguments
- Execute in application working directory
- Use application environment variables
- Capture output (stdout/stderr)
- Return exit code and output
- Support common commands: lint, format, test, typecheck

#### FR-23: Trigger Hot Reload
**Priority**: SHOULD
**Description**: System shall trigger hot reload for supported applications.
**Acceptance Criteria**:
- Detect if application supports hot reload
- Trigger reload via appropriate mechanism (file touch, HTTP endpoint)
- Verify reload success
- Report reload status

### 2.6 Port Management

#### FR-24: Fixed Port Assignment
**Priority**: MUST
**Description**: System shall support fixed port configuration.
**Acceptance Criteria**:
- Accept port number in application configuration
- Detect port conflicts before starting
- Report clear error if port unavailable

#### FR-25: Dynamic Port Allocation
**Priority**: MUST
**Description**: System shall allocate ports dynamically when requested.
**Acceptance Criteria**:
- Use port 0 to request OS-assigned port
- Detect actual port after binding
- Store allocated port in application status
- Make port available for dependent applications

#### FR-26: Port Passing Between Applications
**Priority**: MUST
**Description**: System shall pass allocated ports to dependent applications.
**Acceptance Criteria**:
- Support port_env_var configuration
- Set environment variable with allocated port value
- Resolve ports before starting dependents
- Support referencing multiple dependency ports

### 2.7 Dependency Management

#### FR-27: Ordered Startup
**Priority**: MUST
**Description**: System shall start applications in dependency order.
**Acceptance Criteria**:
- Parse depends_on configuration
- Detect circular dependencies
- Start dependencies before dependents
- Fail fast if dependency fails to start

#### FR-28: Health-Based Dependency Waiting
**Priority**: MUST
**Description**: System shall wait for dependencies to be healthy before starting dependents.
**Acceptance Criteria**:
- Check health of dependencies after startup
- Wait for healthy status (up to timeout)
- Proceed with dependent startup only after health check passes
- Report clear error if dependency unhealthy

### 2.8 Build and Compilation

#### FR-29: Pre-Start Build Execution
**Priority**: MUST
**Description**: System shall execute build commands before starting applications.
**Acceptance Criteria**:
- Execute build_command if configured
- Run in application working directory
- Capture build output in logs
- Fail application start if build fails
- Include build error in application status

#### FR-30: Build Failure Handling
**Priority**: MUST
**Description**: System shall handle build failures gracefully.
**Acceptance Criteria**:
- Capture complete build error output
- Set application status to failed
- Include exit code
- Preserve logs for debugging
- Do not start application after build failure

## 3. Non-Functional Requirements

### 3.1 Performance

#### NFR-1: Startup Time
**Priority**: SHOULD
**Description**: System shall start applications within reasonable time.
**Target**: <2 seconds overhead per application (excluding build time)

#### NFR-2: Log Processing
**Priority**: SHOULD
**Description**: System shall handle high-volume log output.
**Target**: Support 10,000 lines/second per application without blocking

#### NFR-3: Memory Usage
**Priority**: SHOULD
**Description**: System shall manage memory efficiently.
**Target**: <50MB base memory + <10MB per managed application

### 3.2 Reliability

#### NFR-4: Crash Recovery
**Priority**: MUST
**Description**: System shall handle crashes gracefully.
**Requirements**:
- Clean up child processes on crash
- Preserve application status
- Recover configurations from disk
- Log crash details

#### NFR-5: Data Integrity
**Priority**: MUST
**Description**: System shall prevent data corruption.
**Requirements**:
- Use atomic writes for configuration files
- Validate data before writing
- Provide rollback on write failure
- Flush logs regularly

### 3.3 Usability

#### NFR-6: Clear Error Messages
**Priority**: MUST
**Description**: System shall provide actionable error messages.
**Requirements**:
- Include root cause information
- Suggest remediation steps
- Preserve context (which app, which config)
- Log detailed errors for debugging

#### NFR-7: MCP Tool Descriptions
**Priority**: MUST
**Description**: MCP tools shall have clear, comprehensive descriptions.
**Requirements**:
- Explain purpose and use cases
- Document all parameters
- Provide examples
- Indicate return value format

### 3.4 Maintainability

#### NFR-8: Code Quality
**Priority**: MUST
**Description**: Code shall meet high quality standards.
**Requirements**:
- Pass mypy strict mode
- Pass ruff linting
- Follow consistent formatting (ruff format)
- Include type hints on all functions
- Maintain >85% test coverage

#### NFR-9: Documentation
**Priority**: MUST
**Description**: Code shall be well-documented.
**Requirements**:
- Docstrings on all public functions (Google style)
- README with quick start guide
- Usage examples for all MCP tools
- Development guide for contributors
- Architecture documentation

#### NFR-10: Testability
**Priority**: MUST
**Description**: System shall be thoroughly tested.
**Requirements**:
- Unit tests for all managers
- Integration tests for each application type
- Test fixtures for common scenarios
- Mocking for external dependencies
- CI runs tests on every commit

### 3.5 Extensibility

#### NFR-11: Plugin System
**Priority**: MUST
**Description**: Application type handlers shall be pluggable.
**Requirements**:
- Clear interface for handlers
- Registration mechanism
- Isolated handler implementations
- Easy to add new types
- No modification to core code required

#### NFR-12: Configuration Extensibility
**Priority**: SHOULD
**Description**: Configuration format shall support future extensions.
**Requirements**:
- Ignore unknown fields (forward compatibility)
- Support metadata fields
- Validate known fields strictly
- Document extension points

### 3.6 Security

#### NFR-13: Process Isolation
**Priority**: SHOULD
**Description**: System should isolate managed processes.
**Requirements**:
- Run applications in separate process groups
- Clean up process groups on shutdown
- Prevent process escape

#### NFR-14: Filesystem Safety
**Priority**: MUST
**Description**: System shall operate safely on filesystem.
**Requirements**:
- Validate all paths before use
- Prevent directory traversal
- Check permissions before writing
- Clean up temporary files

### 3.7 Compatibility

#### NFR-15: Python Version
**Priority**: MUST
**Description**: System shall require Python 3.12 or higher.
**Justification**: Modern type hints, performance improvements, better error messages

#### NFR-16: Platform Support
**Priority**: MUST (Linux/macOS), SHOULD (Windows)
**Description**: System shall run on major platforms.
**Requirements**:
- Full support for Linux
- Full support for macOS
- Best-effort support for Windows (tested in CI)

#### NFR-17: MCP Protocol
**Priority**: MUST
**Description**: System shall implement MCP protocol correctly.
**Requirements**:
- Use FastMCP library
- Follow MCP specification
- Handle errors per MCP conventions
- Support standard MCP discovery

## 4. Project Structure

```
clientserverrunner_mcp/
├── pyproject.toml              # Poetry configuration
├── README.md                   # User documentation
├── SPECIFICATION.md            # Technical specification
├── REQUIREMENTS.md             # This file
├── DEVELOPMENT.md              # Development guide
├── .github/
│   └── workflows/
│       └── ci.yml              # GitHub Actions CI
├── src/
│   └── clientserverrunner/
│       ├── __init__.py
│       ├── __main__.py         # Entry point
│       ├── server.py           # FastMCP server
│       ├── models.py           # Pydantic models
│       ├── config_manager.py   # Configuration management
│       ├── process_manager.py  # Process lifecycle
│       ├── log_manager.py      # Log capture and search
│       ├── port_manager.py     # Port allocation
│       ├── types/
│       │   ├── __init__.py
│       │   ├── base.py         # Base handler interface
│       │   ├── python.py       # Python handler
│       │   ├── npm.py          # NPM handler
│       │   └── scala.py        # Scala/SBT handler
│       └── utils/
│           ├── __init__.py
│           ├── logging.py      # Logging utilities
│           └── validation.py   # Validation helpers
├── tests/
│   ├── __init__.py
│   ├── conftest.py             # Pytest fixtures
│   ├── unit/
│   │   ├── test_models.py
│   │   ├── test_config_manager.py
│   │   ├── test_process_manager.py
│   │   ├── test_log_manager.py
│   │   └── test_handlers.py
│   ├── integration/
│   │   ├── test_python_app.py
│   │   ├── test_npm_app.py
│   │   ├── test_scala_app.py
│   │   └── test_multi_app.py
│   └── fixtures/
│       ├── sample_configs/
│       ├── test_apps/
│       │   ├── python/         # Simple Python test app
│       │   ├── npm/            # Simple Node test app
│       │   └── scala/          # Simple Scala test app
│       └── logs/
├── examples/
│   ├── webapp_config.json      # Example: FastAPI + React
│   ├── microservices_config.json  # Example: Multiple services
│   └── README.md               # Example documentation
└── .pre-commit-config.yaml     # Pre-commit hooks
```

## 5. Development Workflow

### 5.1 Code Changes
1. Create feature branch
2. Implement changes with tests
3. Run pre-commit hooks (ruff, mypy)
4. Run test suite
5. Commit with clear message
6. Create PR

### 5.2 CI Checks
All PRs must pass:
- Ruff linting
- Ruff format check
- MyPy type checking (strict mode)
- Pytest (all tests pass)
- Coverage >85%

### 5.3 Release Process
1. Update version in pyproject.toml
2. Update CHANGELOG.md
3. Tag release
4. Build with Poetry
5. Publish to PyPI (future)

## 6. Testing Strategy

### 6.1 Unit Tests
- Test each component in isolation
- Mock external dependencies
- Test error conditions
- Test edge cases
- Target >90% coverage for core components

### 6.2 Integration Tests
- Test with real applications
- Test dependency ordering
- Test log capture
- Test health checks
- Test error scenarios
- Target >80% coverage overall

### 6.3 Test Applications
Create minimal test applications:
- **Python**: Simple HTTP server (FastAPI)
- **NPM**: Simple React app (Vite)
- **Scala**: Simple Play Framework app

## 7. Success Criteria

Version 1.0 is complete when:
1. All MUST requirements implemented
2. All tests passing
3. Coverage >85%
4. CI green on supported platforms
5. Documentation complete
6. Successfully manages example configurations:
   - Single Python app
   - FastAPI + React webapp
   - Multiple microservices with dependencies

## 8. Timeline Estimate

- Project setup: 1 hour
- Core models and config manager: 2 hours
- Process manager: 3 hours
- Log manager: 2 hours
- Health checking: 2 hours
- Port management: 2 hours
- Application handlers (3x): 4 hours
- MCP server integration: 2 hours
- Unit tests: 4 hours
- Integration tests: 3 hours
- CI/CD setup: 1 hour
- Documentation: 2 hours

**Total: ~28 hours** for comprehensive implementation
