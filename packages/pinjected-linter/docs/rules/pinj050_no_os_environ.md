# PINJ050: No Direct Environment Variable Access

## Overview

This rule forbids **all** direct access to environment variables through any method or library. You must **NEVER** access environment variables directly. Instead, all configuration values must be injected using pinjected's dependency injection system with `@injected`.

## Rationale

Direct access to environment variables in pinjected code violates several dependency injection principles:

1. **Hidden Dependencies**: Environment variables are implicit dependencies not visible in function signatures
2. **Testing Difficulties**: Hard to mock or override environment variables in tests
3. **Configuration Coupling**: Code becomes tightly coupled to the runtime environment
4. **No Type Safety**: Environment variables are always strings, requiring manual parsing
5. **Initialization Order Issues**: Environment variables might not be set when code runs

## Examples

### ❌ Incorrect - ALL of these are forbidden

```python
import os
from pinjected import injected
from dotenv import load_dotenv, dotenv_values
from decouple import config
from environs import Env

# Direct os.environ access
@injected
def get_api_client(/, base_url: str) -> APIClient:
    api_key = os.environ['API_KEY']  # PINJ050 violation
    return APIClient(base_url, api_key)

# Using os.getenv() - FORBIDDEN
@injected
def get_config(/, name: str) -> str:
    return os.getenv('CONFIG_VALUE')  # PINJ050 violation

# Using os.environ.get()
@injected
def get_database(/, host: str) -> Database:
    password = os.environ.get('DB_PASSWORD', 'default')  # PINJ050 violation
    return Database(host, password)

# Using os.putenv() or os.unsetenv() - FORBIDDEN
def modify_env():
    os.putenv('API_KEY', 'secret')  # PINJ050 violation
    os.unsetenv('OLD_KEY')  # PINJ050 violation

# Using os.environb - FORBIDDEN
def get_bytes_config():
    return os.environb[b'API_KEY']  # PINJ050 violation

# Using dotenv library - FORBIDDEN
def load_config():
    load_dotenv()  # PINJ050 violation
    env_vars = dotenv_values('.env')  # PINJ050 violation

# Using python-decouple - FORBIDDEN
def get_decouple_config():
    api_key = config('API_KEY')  # PINJ050 violation
    debug = config('DEBUG', cast=bool)  # PINJ050 violation

# Using environs library - FORBIDDEN
def get_environs_config():
    env = Env()  # PINJ050 violation
    env.read_env()
    return env.str('API_KEY')

# In class methods
class Config:
    def __init__(self):
        self.debug = os.environ.get('DEBUG', 'false') == 'true'  # PINJ050 violation
        self.api_key = os.getenv('API_KEY')  # PINJ050 violation

# Any other method of accessing env vars
def any_env_access():
    os.environ.clear()  # PINJ050 violation
    backup = os.environ.copy()  # PINJ050 violation
    os.environ.update({'KEY': 'value'})  # PINJ050 violation
```

### ✅ Correct - Use @injected to request dependencies

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

# IMPORTANT: Environment variables should ONLY be accessed in a single @instance function
# marked with noqa comments. This is the ONLY acceptable place.
@instance
def config() -> ConfigProtocol:
    # This is the ONLY place where env vars should be accessed
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

1. **NEVER access environment variables directly**: No `os.getenv`, `os.environ`, `dotenv`, `decouple`, or any other method
2. **Create a Configuration Protocol**: Define a protocol with all configuration values your application needs
3. **Create ONE Instance Function**: Use `@instance` to load environment variables in exactly ONE place in your entire codebase
4. **Use @injected everywhere else**: Replace ALL environment variable access with `@injected` functions that request the configuration as a dependency
5. **Use noqa ONLY in the instance function**: The ONLY legitimate use of `# noqa: PINJ050` is in your single configuration instance function

### Step-by-step Example

```python
# Step 1: Identify ALL environment variable usage
def get_service():
    api_key = os.getenv('API_KEY')  # FORBIDDEN!
    timeout = int(os.environ.get('TIMEOUT', '30'))  # FORBIDDEN!
    load_dotenv()  # FORBIDDEN!
    return Service(api_key, timeout)

# Step 2: Create configuration protocol and instance
from typing import Protocol
from pinjected import injected, instance

class ServiceConfig(Protocol):
    api_key: str
    timeout: int

# This is the ONLY place in your entire codebase where env vars are accessed
@instance
def service_config() -> ServiceConfig:
    import os
    return SimpleConfig(
        api_key=os.environ['API_KEY'],  # noqa: PINJ050
        timeout=int(os.environ.get('TIMEOUT', '30'))  # noqa: PINJ050
    )

# Step 3: ALWAYS use @injected to request dependencies
@injected
def get_service(service_config: ServiceConfig, /):
    # NEVER access env vars here - use the injected config
    return Service(service_config.api_key, service_config.timeout)

# Step 4: All other functions must also use @injected
@injected
def process_data(service_config: ServiceConfig, /, data: str):
    # Request the config through dependency injection
    if service_config.timeout > 60:
        # Use the injected values
        return slow_process(data)
    return fast_process(data)
```

## Suppressing the Rule

**WARNING**: You should ONLY suppress this rule in exactly ONE place - your configuration instance function.

```python
# The ONLY legitimate use case for suppressing PINJ050:
@instance
def load_config() -> ConfigProtocol:
    # This is the SINGLE place in your entire codebase where env vars are loaded
    import os
    return Config(
        api_key=os.environ['API_KEY'],  # noqa: PINJ050
        db_url=os.environ['DATABASE_URL'],  # noqa: PINJ050
    )

# NEVER suppress this rule anywhere else!
# If you think you need to suppress it elsewhere, you're doing it wrong.
# Use @injected to request the configuration instead.
```

## Configuration

This rule can be disabled in your `pyproject.toml`:

```toml
[tool.pinjected-linter]
disable = ["PINJ050"]
```

## Severity

**Error** - Direct environment variable access is **strictly forbidden**. You must **NEVER** access environment variables directly. Always use `@injected` to request dependencies.

## See Also

- [PINJ016: Missing Protocol](pinj016_missing_protocol.md) - Define protocols for configuration objects
- [PINJ002: Instance Defaults](pinj002_instance_defaults.md) - Use instance functions for configuration
- [Dependency Injection Best Practices](https://en.wikipedia.org/wiki/Dependency_injection)