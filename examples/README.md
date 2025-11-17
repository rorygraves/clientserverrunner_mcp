# Example Configurations

This directory contains example configurations for common application setups.

## webapp_config.json

A simple full-stack web application with:
- **Backend**: FastAPI server on port 8000
- **Frontend**: React + Vite dev server on port 5173

The frontend depends on the backend, ensuring the API is ready before starting the UI.

### Usage

```python
import json

with open("examples/webapp_config.json") as f:
    config_data = json.load(f)

# Update paths to your actual directories
config_data["applications"][0]["working_dir"] = "/path/to/your/backend"
config_data["applications"][1]["working_dir"] = "/path/to/your/frontend"

# Create the configuration
create_configuration(**config_data)

# Start it
start_configuration(config_id)
```

## microservices_config.json

A more complex microservices architecture with:
- **Auth Service**: Python authentication microservice (dynamic port)
- **User Service**: Scala/SBT user management service (dynamic port)
- **API Gateway**: Node.js gateway on port 3000
- **Frontend**: React frontend on port 5173

Features demonstrated:
- Dynamic port allocation
- Dependency chains
- Multiple application types
- Build commands (Scala compilation)
- Port passing between services

### Usage

```python
import json

with open("examples/microservices_config.json") as f:
    config_data = json.load(f)

# Update all working_dir paths
for app in config_data["applications"]:
    app["working_dir"] = f"/path/to/{app['id']}"

# Create and start
create_configuration(**config_data)
start_configuration(config_id)
```

## Customizing Examples

### Changing Ports

For fixed ports, modify the `port` field:

```json
{
  "id": "backend",
  "port": 9000
}
```

For dynamic ports:

```json
{
  "id": "backend",
  "port": 0,
  "port_env_var": "PORT"
}
```

### Adding Health Checks

HTTP health check:

```json
{
  "health_check": {
    "type": "http",
    "url": "http://localhost:8000/health",
    "interval": 5,
    "timeout": 3
  }
}
```

TCP health check:

```json
{
  "health_check": {
    "type": "tcp",
    "port": 8000,
    "interval": 5,
    "timeout": 3
  }
}
```

### Adding Environment Variables

```json
{
  "id": "backend",
  "env": {
    "DATABASE_URL": "postgresql://localhost/mydb",
    "LOG_LEVEL": "debug",
    "SECRET_KEY": "your-secret"
  }
}
```

### Adding Build Steps

```json
{
  "id": "scala-app",
  "build_command": "sbt compile",
  "command": "sbt run"
}
```

### Setting Up Dependencies

```json
{
  "id": "frontend",
  "depends_on": ["backend", "auth-service"],
  "startup_timeout": 60
}
```

## Testing Examples

After creating a configuration, test it:

```python
# Check status
get_status(config_id)

# View logs
get_logs(config_id, "backend", lines=50)

# Search for errors
search_logs(config_id, "backend", "error|exception")

# Run tests
run_command(config_id, "backend", "test")

# Stop when done
stop_configuration(config_id)
```

## Creating Your Own Configurations

1. Start with one of these examples
2. Modify paths and ports for your applications
3. Adjust startup commands
4. Add appropriate health checks
5. Set up dependencies
6. Test thoroughly before production use

## Common Patterns

### Backend + Frontend

```json
[
  {
    "id": "backend",
    "depends_on": []
  },
  {
    "id": "frontend",
    "depends_on": ["backend"]
  }
]
```

### Service Mesh

```json
[
  {
    "id": "service-a",
    "depends_on": []
  },
  {
    "id": "service-b",
    "depends_on": ["service-a"]
  },
  {
    "id": "service-c",
    "depends_on": ["service-a", "service-b"]
  },
  {
    "id": "gateway",
    "depends_on": ["service-a", "service-b", "service-c"]
  }
]
```

### Development + Testing

```json
[
  {
    "id": "app",
    "command": "npm run dev",
    "health_check": {...}
  },
  {
    "id": "test-runner",
    "command": "npm run test:watch",
    "depends_on": ["app"]
  }
]
```
