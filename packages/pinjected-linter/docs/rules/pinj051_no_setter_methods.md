# PINJ051: No Setter Methods

## Description

Classes should not have setter methods by default to minimize mutable state. Setter methods make objects mutable and can lead to harder-to-track state changes throughout the application lifecycle.

## Why This Rule Exists

Setter methods violate the principle of immutability and can lead to:
- Unpredictable state changes
- Harder debugging due to state mutations at various points
- Violations of the Single Responsibility Principle
- More complex testing scenarios

Instead of setter methods, prefer:
1. Setting all values through the constructor
2. Using immutable patterns (creating new instances with updated values)
3. Using dependency injection for configuration

## Examples

### ❌ Bad

```python
class MarketStatusTracker:
    def __init__(self):
        self._mut_market = "US"
    
    def set_market(self, market: str) -> None:
        """Set which market to track (e.g., 'US', 'EU', 'ASIA').
        
        Args:
            market: Market identifier to track.
        """
        self._mut_market = market
        logger.info(f"MarketStatusTracker now tracking {market} market")
```

### ✅ Good - Using Constructor

```python
class MarketStatusTracker:
    def __init__(self, market: str = "US"):
        self._market = market
        logger.info(f"MarketStatusTracker tracking {market} market")
```

### ✅ Good - Using Immutable Pattern

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class MarketStatusTracker:
    market: str = "US"
    
    def with_market(self, market: str) -> 'MarketStatusTracker':
        """Create a new tracker for a different market."""
        return MarketStatusTracker(market=market)
```

### ✅ Good - Using Dependency Injection

```python
from pinjected import injected

@injected
def create_market_tracker(market_config: MarketConfig) -> MarketStatusTracker:
    return MarketStatusTracker(market=market_config.default_market)
```

## When to Disable This Rule

In rare cases where a setter is truly necessary (e.g., for framework compatibility or specific design patterns), you can disable this rule with a `noqa` comment:

```python
class LegacyAdapter:
    def set_value(self, value: str) -> None:  # noqa: PINJ051
        """Required by legacy framework."""
        self._value = value
```

## Configuration

This rule is enabled by default. To disable it globally, add to your `pyproject.toml`:

```toml
[tool.pinjected-linter]
disable = ["PINJ051"]
```