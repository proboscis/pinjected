# PINJ050: No Environment Variable Access

## Overview

This rule forbids **ALL** access to environment variables. Environment variables are a bad pattern and must NEVER be used. Instead, configuration values are provided through pinjected's proper configuration mechanisms.

## How Configuration Works in Pinjected

Configuration values are provided by users through:
- Command line arguments: `pinjected run --xxx-api-key YOUR_KEY --database-url postgres://...`
- Default design in `~/.pinjected.py` or project configuration
- NEVER through environment variables

Your code simply declares what it needs as dependencies, and pinjected provides them

## Rationale

Direct access to environment variables violates dependency injection principles:

1. **Hidden Dependencies**: Environment variables are implicit dependencies not visible in function signatures
2. **Testing Difficulties**: Hard to mock or override environment variables in tests
3. **Configuration Coupling**: Code becomes tightly coupled to the runtime environment
4. **No Type Safety**: Environment variables are always strings, requiring manual parsing
5. **Initialization Order Issues**: Environment variables might not be set when code runs
6. **Breaks Inversion of Control**: Your code shouldn't know where values come from

## Important: Feature Flags are an Anti-Pattern

**WARNING**: Using environment variables for feature flags (e.g., `ENABLE_FEATURE_X`, `USE_NEW_ALGORITHM`) is an anti-pattern in dependency injection. Instead, use the **Strategy Pattern** to inject different implementations based on configuration.

### ❌ Bad: Feature Flag Anti-Pattern
```python
# DON'T DO THIS - Feature flags are anti-patterns
@injected
def process_data(enable_feature_x: bool, /, data: str):
    if enable_feature_x:  # Anti-pattern: switching behavior with a flag
        return new_algorithm(data)
    else:
        return old_algorithm(data)
```

### ✅ Good: Strategy Pattern
```python
from typing import Protocol

class DataProcessorProtocol(Protocol):
    def process(self, data: str) -> str: ...

class NewAlgorithmProcessor:
    def process(self, data: str) -> str:
        return new_algorithm(data)

class OldAlgorithmProcessor:
    def process(self, data: str) -> str:
        return old_algorithm(data)

# Inject the strategy, not a flag
@injected
def process_data(data_processor: DataProcessorProtocol, /, data: str):
    return data_processor.process(data)  # No conditional logic needed!
```

## Examples

### ❌ Incorrect - ALL of these are forbidden

```python
import os
from pinjected import injected
from dotenv import load_dotenv, dotenv_values
from decouple import config
from environs import Env

# Direct os.environ access for API keys
@injected
def get_api_client(/, base_url: str) -> APIClient:
    api_key = os.environ['XXX_API_KEY']  # PINJ050 violation
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
from pinjected import injected

# NEVER ACCESS os.environ - Values come from pinjected configuration!

# Example 1: Declare what you need
@injected
def get_api_client(xxx_api_key: str, /, base_url: str) -> APIClient:
    # xxx_api_key is provided via:
    #   pinjected run --xxx-api-key YOUR_KEY
    # or from default design in ~/.pinjected.py
    return APIClient(base_url, xxx_api_key)

# Example 2: Multiple configuration values
@injected  
def connect_to_database(
    database_url: str,      # Provided via --database-url
    database_password: str, # Provided via --database-password
    /, 
    timeout: int = 30
) -> Database:
    # Values are injected from pinjected configuration
    return Database(database_url, database_password, timeout)

# Example 3: Using specific API keys
@injected
def setup_services(
    stripe_api_key: str,   # Provided via --stripe-api-key
    openai_api_key: str,   # Provided via --openai-api-key  
    sendgrid_api_key: str, # Provided via --sendgrid-api-key
    /,
) -> Services:
    # All values come from pinjected configuration, NOT environment!
    return Services(
        stripe=StripeClient(stripe_api_key),
        openai=OpenAIClient(openai_api_key),
        email=SendGridClient(sendgrid_api_key)
    )

@injected
def get_database(config: ConfigProtocol, /, host: str) -> Database:
    return Database(host, config.db_password)

@injected
def get_service(config: ConfigProtocol, /, name: str) -> Service:
    return Service(name, config.service_endpoint)

# Example 4: Users provide values when running the application
# Run with: pinjected run --stripe-secret-key sk_live_xxx --payment-webhook-url https://...
@injected
def process_payment(
    stripe_secret_key: str,     # From --stripe-secret-key
    payment_webhook_url: str,    # From --payment-webhook-url
    enable_test_mode: bool,      # From --enable-test-mode
    /,
    amount: float,
    customer_id: str
) -> PaymentResult:
    # All configuration is injected - your code is pure business logic
    client = StripeClient(stripe_secret_key, test_mode=enable_test_mode)
    return client.charge(amount, customer_id, webhook=payment_webhook_url)
```

## How to Fix

1. **NEVER access environment variables**: Environment variables are forbidden - use pinjected configuration
2. **Just declare dependencies**: Use meaningful parameter names for what you need
3. **Users provide values**: Via command line (`--param-name value`) or configuration files
4. **No os.environ ever**: Environment variables are a bad pattern - don't use them
5. **Pure dependency injection**: Your code just declares needs, pinjected provides values

### Step-by-step Example

```python
# Step 1: Identify ALL environment variable usage  
def get_service():
    api_key = os.getenv('XXX_API_KEY')  # FORBIDDEN!
    timeout = int(os.environ.get('SERVICE_TIMEOUT', '30'))  # FORBIDDEN!
    load_dotenv()  # FORBIDDEN!
    return Service(api_key, timeout)

# Step 2: Replace with dependency injection
from pinjected import injected

@injected
def get_service(
    xxx_api_key: str,      # User provides via --xxx-api-key
    service_timeout: int,  # User provides via --service-timeout
    /
):
    # Values come from pinjected configuration, NOT environment!
    return Service(xxx_api_key, service_timeout)

# Step 3: Users run your application with configuration
# pinjected run --xxx-api-key "sk_live_..." --service-timeout 60

# Step 4: All functions declare their dependencies
@injected
def process_data(
    service_timeout: int,  # Injected from pinjected configuration
    /, 
    data: str
):
    if service_timeout > 60:
        return slow_process(data)
    return fast_process(data)

# Step 5: For production applications
@injected
def create_application(
    database_url: str,         # --database-url "postgres://..."
    redis_url: str,            # --redis-url "redis://..."
    secret_key: str,           # --secret-key "your-secret"
    debug_mode: bool,          # --debug-mode
    max_connections: int,      # --max-connections 100
    /
) -> Application:
    # Pure business logic - configuration is injected!
    return Application(
        db=Database(database_url, max_connections),
        cache=Redis(redis_url),
        config=AppConfig(secret_key, debug_mode)
    )

# Users can also set defaults in ~/.pinjected.py:
# default_design = design(
#     xxx_api_key="default_key",
#     database_url="postgres://localhost/mydb",
#     ...
# )
```

## Suppressing the Rule

**NEVER suppress this rule.** Environment variables are forbidden in pinjected.

```python
# ❌ NEVER DO THIS - Environment variables are bad!
def some_function():
    value = os.environ['SOME_VAR']  # noqa: PINJ050  # WRONG!
    
# ✅ ALWAYS DO THIS - Use dependency injection
@injected
def some_function(some_var: str, /):
    # some_var is provided via pinjected configuration:
    # pinjected run --some-var "value"
    pass
```

## Why Environment Variables Are Bad

1. **Global mutable state**: Environment variables are global and can be changed by any part of the system
2. **No type safety**: Always strings, requiring error-prone parsing
3. **Hidden dependencies**: Not visible in function signatures
4. **Testing nightmare**: Hard to mock or control in tests
5. **Security risks**: Can be exposed through process inspection
6. **No validation**: Values can be missing or invalid

Pinjected's configuration system solves all these problems through proper dependency injection.

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