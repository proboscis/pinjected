from dataclasses import dataclass
from typing import Optional, Union
from pinjected import injected, instance


# Bad: underscore-prefixed attributes with default values
@injected
@dataclass
class ServiceWithDefaults:
    _logger: object = None  # Bad: default value
    _cache: object = "default_cache"  # Bad: default value
    _database: object = "default_db"  # Bad: default value
    name: str = "default"  # OK: not underscore-prefixed


# Bad: underscore-prefixed attributes with Optional types
@injected
@dataclass
class ServiceWithOptional:
    _logger: Optional[object]  # Bad: Optional type
    _cache: object | None  # Bad: Union with None (Python 3.10+)
    _database: Union[object, None]  # Bad: Union with None
    name: Optional[str]  # OK: not underscore-prefixed


# Bad: both default and Optional
@injected
@dataclass
class ServiceWithBoth:
    _logger: Optional[object] = None  # Bad: both Optional and default
    _cache: Union[object, None] = None  # Bad: both Union[None] and default


# Good: proper injected dataclass
@injected
@dataclass
class ProperService:
    _logger: object  # Good: no default, not Optional
    _cache: object  # Good: no default, not Optional
    _database: object  # Good: no default, not Optional
    name: str = "default"  # OK: not underscore-prefixed
    config: Optional[dict] = None  # OK: not underscore-prefixed


# Good: regular dataclass without @injected
@dataclass
class RegularDataclass:
    _private: object = None  # OK: not @injected
    _optional: Optional[object]  # OK: not @injected


# Good: @injected class without @dataclass
@injected
class InjectedNonDataclass:
    def __init__(self):
        self._logger = None  # OK: not a dataclass


# Good: neither @injected nor @dataclass
class RegularClass:
    _field: Optional[object] = None  # OK: regular class


# Define decorators for testing
def some_decorator(cls):
    return cls


def another_decorator(cls):
    return cls


# Edge case: multiple decorators with dataclass
@some_decorator
@injected
@dataclass
@another_decorator
class MultiDecoratorService:
    _service: Optional[object] = None  # Bad: still applies with multiple decorators
    regular_field: str = "ok"  # OK: not underscore-prefixed


# Function to trigger the get_default_db reference
def get_default_db():
    return "default_db"


# Test @instance for comparison (should not trigger PINJ041)
@instance
def some_instance():
    return object()
