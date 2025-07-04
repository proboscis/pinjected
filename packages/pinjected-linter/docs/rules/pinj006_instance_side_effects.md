# PINJ006: Instance Function Side Effects

## Overview

**Rule ID:** PINJ006  
**Category:** Purity  
**Severity:** Error  
**Auto-fixable:** No

Functions decorated with `@instance` should be pure providers without side effects such as I/O operations, logging, or state modifications.

## Rationale

`@instance` functions are dependency providers that should be pure factories. They should only construct and return objects without performing side effects. This ensures:

1. **Predictability:** Calling the provider multiple times yields consistent results
2. **Testability:** No need to mock external systems when testing providers
3. **Performance:** No unnecessary I/O or computation during dependency resolution
4. **Separation of Concerns:** Configuration and construction are separate from business logic
5. **Startup Safety:** Application startup won't fail due to external service availability

## Rule Details

This rule detects various types of side effects in `@instance` functions:
- File I/O operations
- Network calls
- Database operations
- Logging statements
- Print statements
- Environment variable access
- OS system calls
- Global state modifications

### Examples of Violations

❌ **Bad:** Instance functions with side effects
```python
@instance
def database():
    # File I/O
    with open("config.json") as f:  # Error: File I/O
        config = json.load(f)
    return Database(**config)

@instance
def api_client():
    # Network call
    response = requests.get("https://api.example.com/config")  # Error: Network call
    return APIClient(base_url=response.json()["endpoint"])

@instance
def logger():
    # Logging/printing
    print("Creating logger")  # Error: Print statement
    logging.info("Logger initialized")  # Error: Logging
    return logging.getLogger()

@instance
def cache():
    # Environment access
    redis_url = os.environ["REDIS_URL"]  # Error: Environment access
    return RedisCache(redis_url)

@instance
def service():
    # Database operation
    db.execute("INSERT INTO startup_log VALUES (?)", [datetime.now()])  # Error: DB operation
    return Service()
```

✅ **Good:** Pure instance functions
```python
@instance
def database():
    # Pure construction with hardcoded or injected config
    return Database(host="localhost", port=5432)

@instance
def api_client():
    # Configuration is static or injected separately
    return APIClient(base_url="https://api.example.com")

@instance
def logger():
    # Just create and return
    return logging.getLogger("myapp")

@instance
def cache():
    # Use static configuration
    return RedisCache("redis://localhost:6379")

@instance
def service():
    # Pure factory
    return Service()
```

## Common Patterns and Best Practices

### 1. Move configuration to separate providers
```python
# ❌ Bad - reading config file
@instance
def database():
    with open("database.yaml") as f:
        config = yaml.load(f)
    return Database(**config["database"])

# ✅ Good - separate config provider
@instance
def database_config():
    # This could be hardcoded, from env, etc.
    return {
        "host": os.environ.get("DB_HOST", "localhost"),
        "port": int(os.environ.get("DB_PORT", "5432"))
    }

@injected
def database(config=database_config, /):
    return Database(**config)
```

### 2. Use lazy initialization
```python
# ❌ Bad - connecting during construction
@instance
def redis_client():
    client = Redis()
    client.ping()  # Error: Network operation
    return client

# ✅ Good - lazy connection
@instance
def redis_client():
    # Connection happens on first use, not during construction
    return Redis(host="localhost", port=6379)
```

### 3. Move side effects to @injected functions
```python
# ❌ Bad - logging in provider
@instance
def expensive_service():
    logger.info("Creating expensive service")  # Error
    service = ExpensiveService()
    logger.info("Service created")  # Error
    return service

# ✅ Good - side effects in usage, not creation
@instance
def expensive_service():
    return ExpensiveService()

@injected
def startup_routine(logger, expensive_service, /):
    logger.info("Starting up with expensive service")
    expensive_service.initialize()
    logger.info("Startup complete")
```

### 4. Handle optional features properly
```python
# ❌ Bad - checking feature availability
@instance
def optional_feature():
    if requests.get("http://feature-flag-service/enabled").json()["feature_x"]:
        return FeatureX()
    return None

# ✅ Good - static or configuration-based
@instance
def optional_feature():
    # Feature flag from config, not runtime check
    if config.FEATURE_X_ENABLED:
        return FeatureX()
    return None
```

## Detected Side Effects

The rule detects these categories of side effects:

1. **File I/O:** `open()`, `read()`, `write()`, Path operations
2. **Logging:** `logger.*`, `logging.*`, `print()`
3. **Network:** `requests.*`, `urllib.*`, `socket.*`, `aiohttp.*`
4. **Database:** `connect()`, `execute()`, `commit()`
5. **OS Operations:** `os.system()`, `subprocess.*`, `os.environ`
6. **Global State:** `globals()`, `setattr()`, `delattr()`

## Configuration

This rule has no configuration options.

## When to Disable

This rule should rarely be disabled. Consider disabling only if:
- You have legacy code that cannot be refactored immediately
- You have a very specific use case that requires side effects

To disable for a specific function:
```python
# noqa: PINJ006
@instance
def legacy_service():
    # Legacy code that will be refactored
    print("Creating service")
    return Service()
```

To disable in configuration:
```toml
[tool.pinjected-linter]
disable = ["PINJ006"]
```

## Related Rules

- **PINJ005:** Instance function imports (imports are a form of side effect)

## See Also

- [Pure Functions](https://en.wikipedia.org/wiki/Pure_function)
- [Dependency Injection Best Practices](https://www.martinfowler.com/articles/injection.html)

## Version History

- **1.0.0:** Initial implementation