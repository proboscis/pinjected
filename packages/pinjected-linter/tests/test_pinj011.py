"""Test PINJ011: IProxy type annotations."""

import ast
from pathlib import Path
from pinjected_linter.rules.pinj011_iproxy_annotations import PINJ011IProxyAnnotations
from pinjected_linter.models import RuleContext, Severity
from pinjected_linter.utils.symbol_table import SymbolTable


def test_pinj011_detects_missing_iproxy_in_injected():
    """Test that PINJ011 detects missing IProxy in @injected function parameters."""
    source = """
from pinjected import injected, IProxy
from typing import Any

class DatabaseService:
    def query(self, sql: str): pass

class LoggerService:
    def log(self, msg: str): pass

class ConfigManager:
    def get(self, key: str): pass

@injected
def process_data(
    database_service: DatabaseService,  # Bad - should be IProxy[DatabaseService]
    logger: LoggerService,             # Bad - should be IProxy[LoggerService]
    config_manager: ConfigManager,     # Bad - should be IProxy[ConfigManager]
    /,
    data: dict
):
    logger.log("Processing data")
    config = config_manager.get("processing_config")
    return database_service.query(f"INSERT INTO processed VALUES ({data})")

@injected
def fetch_user(
    user_repository,  # OK - no annotation, so no warning
    cache_service,    # OK - no annotation, so no warning
    /,
    user_id: int
):
    cached = cache_service.get(f"user:{user_id}")
    if cached:
        return cached
    return user_repository.find_by_id(user_id)
"""

    rule = PINJ011IProxyAnnotations()
    tree = ast.parse(source)
    context = RuleContext(
        file_path=Path("test.py"),
        source=source,
        tree=tree,
        symbol_table=SymbolTable(),
        config={},
    )

    violations = rule.check(context)

    # Should detect violations for service-typed parameters
    assert len(violations) == 3  # Only the 3 with type annotations

    for violation in violations:
        assert violation.rule_id == "PINJ011"
        assert "IProxy" in violation.message
        assert violation.severity == Severity.WARNING
        assert "IProxy[" in violation.suggestion


def test_pinj011_allows_proper_iproxy_usage():
    """Test that PINJ011 allows proper IProxy usage."""
    source = """
from pinjected import injected, IProxy, instance

class DatabaseService:
    def query(self, sql: str): pass

class CacheService:
    def get(self, key: str): pass

@injected
def process_with_deps(
    database: IProxy[DatabaseService],  # Good - uses IProxy
    cache: IProxy[CacheService],        # Good - uses IProxy
    /,
    request_id: str,
    data: dict
):
    # Process with dependencies
    cached = cache.get(request_id)
    if not cached:
        database.query(f"INSERT INTO requests VALUES ({data})")
    return {"status": "processed"}

class HTTPClient:
    async def get(self, url: str): pass

class Logger:
    def info(self, msg: str): pass

@injected
async def a_fetch_data(
    http_client: IProxy[HTTPClient],    # Good - async injected with IProxy
    logger: IProxy[Logger],             # Good
    /,
    url: str
):
    logger.info(f"Fetching {url}")
    return await http_client.get(url)

# No dependencies - all runtime args
@injected
def pure_calculation(x: int, y: int) -> int:
    return x + y
"""

    rule = PINJ011IProxyAnnotations()
    tree = ast.parse(source)
    context = RuleContext(
        file_path=Path("test.py"),
        source=source,
        tree=tree,
        symbol_table=SymbolTable(),
        config={},
    )

    violations = rule.check(context)

    # Should have no violations
    assert len(violations) == 0


def test_pinj011_detects_instance_return_type():
    """Test that PINJ011 detects @instance functions that should return IProxy."""
    source = """
from pinjected import instance, IProxy

class APIService:
    def call(self, endpoint: str): pass

class DatabaseClient:
    def connect(self): pass

class NotificationHandler:
    def send(self, msg: str): pass

@instance
def api_service() -> APIService:  # Bad - entry point should return IProxy[APIService]
    return APIService()

@instance
def database_client() -> DatabaseClient:  # Bad - should return IProxy[DatabaseClient]
    client = DatabaseClient()
    client.connect()
    return client

@instance
def notification_handler() -> NotificationHandler:  # Bad
    return NotificationHandler()

# These are OK - not service types
@instance
def config_dict() -> dict:
    return {"timeout": 30, "retries": 3}

@instance
def port_number() -> int:
    return 8080
"""

    rule = PINJ011IProxyAnnotations()
    tree = ast.parse(source)
    context = RuleContext(
        file_path=Path("test.py"),
        source=source,
        tree=tree,
        symbol_table=SymbolTable(),
        config={},
    )

    violations = rule.check(context)

    # Should detect service-returning instances
    assert len(violations) >= 3

    for violation in violations:
        assert violation.rule_id == "PINJ011"
        assert "@instance function" in violation.message
        assert "IProxy" in violation.message


def test_pinj011_allows_instance_with_iproxy():
    """Test that PINJ011 allows @instance functions returning IProxy."""
    source = """
from pinjected import instance, IProxy

class EmailService:
    def send(self, to: str, subject: str, body: str): pass

class PaymentGateway:
    def process(self, amount: float): pass

@instance
def email_service() -> IProxy[EmailService]:  # Good - returns IProxy
    return EmailService()

@instance
def payment_gateway() -> IProxy[PaymentGateway]:  # Good
    gateway = PaymentGateway()
    # Some initialization
    return gateway

class AsyncService:
    @classmethod
    async def create(cls): return cls()

@instance
async def async_service() -> IProxy[AsyncService]:  # Good - async instance with IProxy
    service = await AsyncService.create()
    return service
"""

    rule = PINJ011IProxyAnnotations()
    tree = ast.parse(source)
    context = RuleContext(
        file_path=Path("test.py"),
        source=source,
        tree=tree,
        symbol_table=SymbolTable(),
        config={},
    )

    violations = rule.check(context)

    # Should have no violations
    assert len(violations) == 0


def test_pinj011_handles_no_slash_injected():
    """Test that PINJ011 handles @injected functions without slash (all runtime args)."""
    source = """
from pinjected import injected

@injected
def process_data(x: int, y: int, transformer) -> dict:
    # No slash - all args are runtime args, no injection happens
    return transformer.transform(x, y)

@injected  
def calculate(a: float, b: float, operation: str) -> float:
    # No slash - these are all runtime arguments
    if operation == "add":
        return a + b
    return a * b
"""

    rule = PINJ011IProxyAnnotations()
    tree = ast.parse(source)
    context = RuleContext(
        file_path=Path("test.py"),
        source=source,
        tree=tree,
        symbol_table=SymbolTable(),
        config={},
    )

    violations = rule.check(context)

    # Should have no violations - no injection happening
    assert len(violations) == 0


def test_pinj011_recognizes_dependency_patterns():
    """Test that PINJ011 recognizes service types in annotations."""
    source = """
from pinjected import injected

class UserRepository:
    pass

class AuthService:
    pass

class EmailClient:
    pass

@injected
def workflow(
    user_repository: UserRepository,      # Bad - Repository type
    auth_service: AuthService,           # Bad - Service type  
    email_client: EmailClient,           # Bad - Client type
    task_manager: TaskManager,           # Bad - Manager type
    event_handler: EventHandler,         # Bad - Handler type
    data_processor: DataProcessor,       # Bad - Processor type
    input_validator: InputValidator,     # Bad - Validator type
    app_logger: Logger,                  # Bad - Logger type
    redis_cache: Cache,                  # Bad - Cache type
    db: Database,                        # Bad - Database type
    /,
    request: dict
):
    # Complex workflow using many dependencies
    pass
"""

    rule = PINJ011IProxyAnnotations()
    tree = ast.parse(source)
    context = RuleContext(
        file_path=Path("test.py"),
        source=source,
        tree=tree,
        symbol_table=SymbolTable(),
        config={},
    )

    violations = rule.check(context)

    # Should detect all service-typed parameters
    assert len(violations) == 10

    # Check that various service types were detected
    for violation in violations:
        assert "should use IProxy[T] annotation" in violation.message


def test_pinj011_ignores_non_dependency_params():
    """Test that PINJ011 ignores parameters that don't look like dependencies."""
    source = """
from pinjected import injected, IProxy

class Calculator:
    def compute(self, x, y, op, opts): pass

@injected
def calculate(
    calculator: IProxy[Calculator],  # Good - has IProxy
    /,
    x: int,                         # OK - runtime arg
    y: float,                       # OK - runtime arg  
    operation: str,                 # OK - runtime arg
    options: dict,                  # OK - runtime arg
    items: list,                    # OK - runtime arg
    user_id: str,                   # OK - runtime arg
    timestamp: int,                 # OK - runtime arg
):
    return calculator.compute(x, y, operation, options)
"""

    rule = PINJ011IProxyAnnotations()
    tree = ast.parse(source)
    context = RuleContext(
        file_path=Path("test.py"),
        source=source,
        tree=tree,
        symbol_table=SymbolTable(),
        config={},
    )

    violations = rule.check(context)

    # Should have no violations - runtime args don't need IProxy
    assert len(violations) == 0


if __name__ == "__main__":
    test_pinj011_detects_missing_iproxy_in_injected()
    test_pinj011_allows_proper_iproxy_usage()
    test_pinj011_detects_instance_return_type()
    test_pinj011_allows_instance_with_iproxy()
    test_pinj011_handles_no_slash_injected()
    test_pinj011_recognizes_dependency_patterns()
    test_pinj011_ignores_non_dependency_params()
    print("All PINJ011 tests passed!")
