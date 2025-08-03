# PINJ050: No Direct os.environ Usage

## Overview

This rule forbids direct access to `os.environ` and related methods. Instead, configuration values should be injected using pinjected's dependency injection system.

## Rationale

Direct usage of `os.environ` in pinjected code violates several dependency injection principles:

1. **Hidden Dependencies**: Environment variables are implicit dependencies not visible in function signatures
2. **Testing Difficulties**: Hard to mock or override environment variables in tests
3. **Configuration Coupling**: Code becomes tightly coupled to the runtime environment
4. **No Type Safety**: Environment variables are always strings, requiring manual parsing
5. **Initialization Order Issues**: Environment variables might not be set when code runs

## Examples

### ❌ Incorrect

```python
import os
from pinjected import injected

# Direct os.environ access
@injected
def get_api_client(/, base_url: str) -> APIClient:
    api_key = os.environ['API_KEY']  # PINJ050 violation
    return APIClient(base_url, api_key)

# Using os.environ.get()
@injected
def get_database(/, host: str) -> Database:
    password = os.environ.get('DB_PASSWORD', 'default')  # PINJ050 violation
    return Database(host, password)

# In class methods
class Config:
    def __init__(self):
        self.debug = os.environ.get('DEBUG', 'false') == 'true'  # PINJ050 violation

# Using os.environ.setdefault()
def setup():
    os.environ.setdefault('ENVIRONMENT', 'development')  # PINJ050 violation

# Subscript access
@injected
def get_service(/, name: str) -> Service:
    endpoint = os.environ['SERVICE_ENDPOINT']  # PINJ050 violation
    return Service(name, endpoint)
```

### ✅ Correct

```python
from pinjected import injected, instance
from typing import Protocol

# Define configuration protocol
class ConfigProtocol(Protocol):
    api_key: str
    db_password: str
    debug: bool
    environment: str
    service_endpoint: str

# Inject configuration
@instance
def config() -> ConfigProtocol:
    # Load from environment in one place
    import os
    return Config(
        api_key=os.environ['API_KEY'],  # noqa: PINJ050
        db_password=os.environ.get('DB_PASSWORD', 'default'),  # noqa: PINJ050
        debug=os.environ.get('DEBUG', 'false') == 'true',  # noqa: PINJ050
        environment=os.environ.get('ENVIRONMENT', 'development'),  # noqa: PINJ050
        service_endpoint=os.environ['SERVICE_ENDPOINT']  # noqa: PINJ050
    )

# Use injected configuration
@injected
def get_api_client(config: ConfigProtocol, /, base_url: str) -> APIClient:
    return APIClient(base_url, config.api_key)

@injected
def get_database(config: ConfigProtocol, /, host: str) -> Database:
    return Database(host, config.db_password)

@injected
def get_service(config: ConfigProtocol, /, name: str) -> Service:
    return Service(name, config.service_endpoint)

# Alternative: Individual configuration values
@instance
def api_key() -> str:
    import os
    return os.environ['API_KEY']  # noqa: PINJ050

@injected
def get_api_client_v2(api_key: str, /, base_url: str) -> APIClient:
    return APIClient(base_url, api_key)
```

## How to Fix

1. **Create a Configuration Protocol**: Define a protocol with all configuration values
2. **Create an Instance Function**: Use `@instance` to load environment variables in one place
3. **Inject Configuration**: Replace `os.environ` access with injected configuration
4. **Use noqa for Legitimate Cases**: If you must use `os.environ` (e.g., in the configuration loader), add `# noqa: PINJ050`

### Step-by-step Example

```python
# Step 1: Identify os.environ usage
def get_service():
    api_key = os.environ['API_KEY']  # Bad!
    timeout = int(os.environ.get('TIMEOUT', '30'))  # Bad!
    return Service(api_key, timeout)

# Step 2: Create configuration
from typing import Protocol

class ServiceConfig(Protocol):
    api_key: str
    timeout: int

@instance
def service_config() -> ServiceConfig:
    import os
    return SimpleConfig(
        api_key=os.environ['API_KEY'],  # noqa: PINJ050
        timeout=int(os.environ.get('TIMEOUT', '30'))  # noqa: PINJ050
    )

# Step 3: Convert to injected function
@injected
def get_service(service_config: ServiceConfig, /):
    return Service(service_config.api_key, service_config.timeout)
```

## Suppressing the Rule

If you have a legitimate need to use `os.environ` directly (such as in configuration loaders or initialization code), you can suppress this rule:

```python
import os

# Using noqa comment
api_key = os.environ['API_KEY']  # noqa: PINJ050

# For entire functions/classes
@instance
def load_config() -> dict:
    # This function is responsible for loading environment variables
    return {
        'api_key': os.environ['API_KEY'],  # noqa: PINJ050
        'db_url': os.environ['DATABASE_URL'],  # noqa: PINJ050
    }
```

## Configuration

This rule can be disabled in your `pyproject.toml`:

```toml
[tool.pinjected-linter]
disable = ["PINJ050"]
```

## Severity

**Error** - Direct environment variable access violates dependency injection principles and should be avoided.

## See Also

- [PINJ016: Missing Protocol](pinj016_missing_protocol.md) - Define protocols for configuration objects
- [PINJ002: Instance Defaults](pinj002_instance_defaults.md) - Use instance functions for configuration
- [Dependency Injection Best Practices](https://en.wikipedia.org/wiki/Dependency_injection)