# PINJ045: No Mode/Flag Parameters

## Overview

**Rule ID:** PINJ045  
**Category:** Design  
**Severity:** Error  
**Auto-fixable:** No

Functions should not accept mode or flag parameters (str, bool, enum) that control behavior paths. This violates the Single Responsibility Principle (SRP). Note that strategy objects passed as runtime parameters are acceptable - this rule focuses on primitive mode flags that cause branching logic.

## Rationale

Mode parameters lead to several issues:

1. **Violation of SRP**: A single function becomes responsible for multiple behaviors
2. **Poor testability**: Tests must cover all mode combinations, leading to complex test matrices
3. **Increased complexity**: Functions contain branching logic based on modes
4. **Difficult maintenance**: Adding new modes requires modifying existing code
5. **Hidden dependencies**: The actual behavior depends on runtime values rather than explicit dependencies

Instead, use the strategy pattern to separate different behaviors into distinct, testable components. Strategy objects can be passed as runtime parameters or injected as dependencies, depending on your use case.

## Rule Details

This rule checks `@injected` functions for parameters that indicate mode/flag behavior:

### What is detected:

1. **Mode-indicating parameter names**: `mode`, `type`, `kind`, `variant`, `format`, `style`, `method`, `approach`, `option`, `flag`, `switch`, `toggle` (Note: `strategy` is no longer flagged as it often represents legitimate objects)
2. **Boolean flag prefixes**: `use_`, `enable_`, `disable_`, `is_`, `should_` (excluding parameters containing `strategy`, `handler`, `processor`, or `provider`)
3. **Conditional prefixes**: `with_` and `include_` are only flagged if they also contain mode-indicating words
3. **Type annotations**: 
   - `bool` type parameters
   - `Literal` type hints (e.g., `Literal['fast', 'slow']`)
   - Enum types

### Examples of Violations

❌ **Bad:** String mode parameter
```python
@injected
def process_data(logger, /, data: list, mode: str) -> list:
    if mode == "fast":
        logger.info("Using fast processing")
        return quick_process(data)
    elif mode == "accurate":
        logger.info("Using accurate processing")
        return accurate_process(data)
    else:
        raise ValueError(f"Unknown mode: {mode}")
```

❌ **Bad:** Boolean flag parameter
```python
@injected
def fetch_data(http_client, cache_client, /, endpoint: str, use_cache: bool) -> dict:
    if use_cache:
        cached = cache_client.get(endpoint)
        if cached:
            return cached
    
    data = http_client.get(endpoint)
    if use_cache:
        cache_client.set(endpoint, data)
    return data
```

❌ **Bad:** Enum parameter
```python
from enum import Enum

class OutputFormat(Enum):
    JSON = "json"
    XML = "xml"
    YAML = "yaml"

@injected
def format_output(/, data: dict, format: OutputFormat) -> str:
    if format == OutputFormat.JSON:
        return json.dumps(data)
    elif format == OutputFormat.XML:
        return dict_to_xml(data)
    else:
        return yaml.dump(data)
```

❌ **Bad:** Literal type parameter
```python
from typing import Literal

@injected
def render_content(template_engine, /, content: str, style: Literal['plain', 'html', 'markdown']) -> str:
    if style == 'plain':
        return content
    elif style == 'html':
        return template_engine.render_html(content)
    else:
        return template_engine.render_markdown(content)
```

✅ **Good:** Strategy pattern with dependency injection
```python
from typing import Protocol

# Define the strategy protocol
class DataProcessor(Protocol):
    def process(self, data: list) -> list:
        ...

# Implement different strategies
class FastProcessor:
    def process(self, data: list) -> list:
        return quick_process(data)

class AccurateProcessor:
    def process(self, data: list) -> list:
        return accurate_process(data)

# Use dependency injection
@injected
def process_data(logger, processor: DataProcessor, /, data: list) -> list:
    logger.info(f"Processing with {type(processor).__name__}")
    return processor.process(data)
```

✅ **Good:** Separate implementations for different behaviors
```python
from typing import Protocol

class DataFetcher(Protocol):
    def fetch(self, endpoint: str) -> dict:
        ...

class DirectFetcher:
    @injected
    def fetch(self, http_client, /, endpoint: str) -> dict:
        return http_client.get(endpoint)

class CachedFetcher:
    @injected
    def fetch(self, http_client, cache_client, /, endpoint: str) -> dict:
        cached = cache_client.get(endpoint)
        if cached:
            return cached
        
        data = http_client.get(endpoint)
        cache_client.set(endpoint, data)
        return data

@injected
def fetch_data(fetcher: DataFetcher, /, endpoint: str) -> dict:
    return fetcher.fetch(endpoint)
```

✅ **Good:** Strategy objects as runtime parameters
```python
# These are legitimate uses - strategy objects can be runtime parameters
@injected
async def a_run_market_backtest(
    logger,
    /,
    a_ee_signal_based_trading_strategy: TradingStrategy,  # OK: Strategy object
    market_data: MarketData,
    config: BacktestConfig
) -> BacktestResult:
    # Strategy is a proper object, not a mode flag
    return await a_ee_signal_based_trading_strategy.backtest(market_data, config)

@injected
def process_with_handler(
    logger,
    /,
    data: Data,
    error_handler: ErrorHandler,  # OK: Handler object
    result_processor: ResultProcessor  # OK: Processor object
) -> Result:
    try:
        result = process(data)
        return result_processor.process(result)
    except Exception as e:
        return error_handler.handle(e)
```

## Common Patterns and Solutions

### 1. Replace mode strings with strategy objects
```python
# ❌ Bad
@injected
def execute_task(/, task: Task, mode: str):
    if mode == "sync":
        return sync_executor.run(task)
    else:
        return async_executor.run(task)

# ✅ Good
class TaskExecutor(Protocol):
    def run(self, task: Task): ...

@injected
def execute_task(executor: TaskExecutor, /, task: Task):
    return executor.run(task)
```

### 2. Replace boolean flags with separate functions
```python
# ❌ Bad
@injected
def save_data(storage, /, data: dict, validate: bool):
    if validate:
        validate_data(data)
    storage.save(data)

# ✅ Good
@injected
def save_data(storage, /, data: dict):
    storage.save(data)

@injected
def save_validated_data(storage, validator, /, data: dict):
    validator.validate(data)
    storage.save(data)
```

### 3. Replace format parameters with formatter objects
```python
# ❌ Bad
@injected
def export_data(/, data: dict, format: str) -> str:
    if format == "json":
        return json.dumps(data)
    elif format == "csv":
        return to_csv(data)

# ✅ Good
class DataExporter(Protocol):
    def export(self, data: dict) -> str: ...

@injected
def export_data(exporter: DataExporter, /, data: dict) -> str:
    return exporter.export(data)
```

## Configuration

This rule has a fixed severity of "error" and does not currently support configuration options. If you need to disable this rule for specific cases, use the `noqa` comment approach shown below.

## When to Disable

You might disable this rule when:
- Interfacing with external APIs that require mode parameters
- Working with legacy code during migration
- Building backward-compatible wrappers

To disable for a specific function:
```python
@injected
def legacy_api(/, data: dict, mode: str):  # noqa: PINJ045
    # Legacy API that must maintain compatibility
    return process_with_mode(data, mode)
```

To disable in configuration:
```toml
[tool.pinjected-linter]
disable = ["PINJ045"]
```

## Migration Guide

### Step 1: Identify different behaviors
```python
# Original code with mode parameter
@injected
def process(/, data, mode: str):
    if mode == "fast":
        # Fast processing logic
    elif mode == "accurate":
        # Accurate processing logic
```

### Step 2: Create a protocol
```python
class ProcessingStrategy(Protocol):
    def process(self, data): ...
```

### Step 3: Implement strategies
```python
class FastStrategy:
    def process(self, data):
        # Fast processing logic

class AccurateStrategy:
    def process(self, data):
        # Accurate processing logic
```

### Step 4: Update the function
```python
@injected
def process(strategy: ProcessingStrategy, /, data):
    return strategy.process(data)
```

### Step 5: Update the design
```python
# Development design
dev_design = design(
    ProcessingStrategy=FastStrategy
)

# Production design
prod_design = design(
    ProcessingStrategy=AccurateStrategy
)
```

## Related Rules

- **PINJ001-PINJ006:** Naming conventions for pinjected functions
- **PINJ010:** Design usage patterns
- **PINJ028:** No design in injected functions

## See Also

- [Single Responsibility Principle](https://en.wikipedia.org/wiki/Single-responsibility_principle)
- [Strategy Pattern](https://refactoring.guru/design-patterns/strategy)
- [Dependency Injection Best Practices](https://pinjected.readthedocs.io/best-practices)
- [SOLID Principles in Python](https://realpython.com/solid-principles-python/)

## Version History

- **0.1.0:** Initial implementation to enforce SRP and prevent mode parameters in @injected functions