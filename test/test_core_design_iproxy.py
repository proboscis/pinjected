"""Tests for design() function and IProxy functionality."""

import pytest
from pinjected import design, instance, injected, Injected
from pinjected import IProxy


def test_design_basic():
    """Test basic design() functionality."""
    d = design(host="localhost", port=5432, debug=True)

    g = d.to_graph()

    assert g.provide("host") == "localhost"
    assert g.provide("port") == 5432
    assert g.provide("debug") is True


def test_design_combination():
    """Test combining multiple designs with + operator."""
    base_design = design(host="localhost", port=5432, username="admin")

    dev_design = design(debug=True, log_level="DEBUG")

    prod_design = design(
        debug=False,
        log_level="ERROR",
        port=443,  # Override port
    )

    # Combine designs - later values override earlier ones
    dev_config = base_design + dev_design
    prod_config = base_design + prod_design

    dev_graph = dev_config.to_graph()
    assert dev_graph.provide("host") == "localhost"
    assert dev_graph.provide("port") == 5432  # From base
    assert dev_graph.provide("debug") is True
    assert dev_graph.provide("log_level") == "DEBUG"

    prod_graph = prod_config.to_graph()
    assert prod_graph.provide("host") == "localhost"
    assert prod_graph.provide("port") == 443  # Overridden
    assert prod_graph.provide("debug") is False


def test_design_bind_instance():
    """Test design.bind_instance() method."""
    d = design()
    d = d.bind_instance(api_key="secret123", max_retries=3)

    g = d.to_graph()
    assert g.provide("api_key") == "secret123"
    assert g.provide("max_retries") == 3


def test_design_bind_provider():
    """Test binding providers with design."""

    def create_connection_string(host, port, username):
        return f"{username}@{host}:{port}"

    # Use providers() helper function
    from pinjected import providers

    d = design(host="localhost", port=5432, username="admin") + providers(
        connection_string=create_connection_string
    )

    g = d.to_graph()
    assert g.provide("connection_string") == "admin@localhost:5432"


def test_design_bind_class():
    """Test binding classes with design."""

    class Config:
        def __init__(self, host, port):
            self.host = host
            self.port = port

        def to_url(self):
            return f"http://{self.host}:{self.port}"

    # Use classes() helper function
    from pinjected import classes

    d = design(host="localhost", port=8080) + classes(config=Config)

    g = d.to_graph()
    config = g.provide("config")
    assert isinstance(config, Config)
    assert config.to_url() == "http://localhost:8080"


def test_design_with_context():
    """Test using design with context manager."""

    @instance
    def service(mode):
        return f"Service in {mode} mode"

    base_design = design(mode="production")

    # Normal execution
    g1 = base_design.to_graph()
    assert g1.provide(service) == "Service in production mode"

    # Override with new design
    test_design = base_design + design(mode="testing")
    g2 = test_design.to_graph()
    assert g2.provide(service) == "Service in testing mode"

    # Base design unchanged
    g3 = base_design.to_graph()
    assert g3.provide(service) == "Service in production mode"


def test_iproxy_basic():
    """Test basic IProxy functionality."""

    @instance
    def value():
        return 42

    # @instance returns a value that can be provided by the graph
    # No need to assert specific type

    d = design()
    g = d.to_graph()

    # Resolve the proxy
    assert g.provide(value) == 42


def test_iproxy_map():
    """Test IProxy.map() functionality."""
    base = Injected.by_name("base_value")

    # Map operations
    doubled = base.map(lambda x: x * 2)
    squared = base.map(lambda x: x**2)
    chained = base.map(lambda x: x * 2).map(lambda x: x + 10)

    d = design(base_value=5)
    g = d.to_graph()

    assert g.provide(doubled) == 10
    assert g.provide(squared) == 25
    assert g.provide(chained) == 20  # (5 * 2) + 10


def test_iproxy_operations():
    """Test IProxy arithmetic operations."""
    a = Injected.by_name("a").proxy
    b = Injected.by_name("b").proxy

    # Arithmetic operations - only + and * are supported
    sum_proxy = a + b
    prod_proxy = a * b

    d = design(a=10, b=3)
    g = d.to_graph()

    assert g.provide(sum_proxy) == 13
    assert g.provide(prod_proxy) == 30

    # For other operations, use zip and map
    diff = (
        Injected.by_name("a").zip(Injected.by_name("b")).map(lambda ab: ab[0] - ab[1])
    )
    div = Injected.by_name("a").zip(Injected.by_name("b")).map(lambda ab: ab[0] / ab[1])

    assert g.provide(diff) == 7
    assert g.provide(div) == 10 / 3


def test_iproxy_attribute_access():
    """Test IProxy attribute access."""

    @instance
    def config():
        class Config:
            host = "localhost"
            port = 8080

            def get_url(self):
                return f"http://{self.host}:{self.port}"

        return Config()

    # Access attributes through proxy
    host_proxy = config.host
    port_proxy = config.port
    url_proxy = config.get_url()

    d = design()
    g = d.to_graph()

    assert g.provide(host_proxy) == "localhost"
    assert g.provide(port_proxy) == 8080
    assert g.provide(url_proxy) == "http://localhost:8080"


def test_iproxy_item_access():
    """Test IProxy item access (indexing)."""

    @instance
    def data():
        return {
            "users": ["alice", "bob", "charlie"],
            "settings": {"theme": "dark", "language": "en"},
        }

    # Access items through proxy
    users_proxy = data["users"]
    first_user_proxy = data["users"][0]
    theme_proxy = data["settings"]["theme"]

    d = design()
    g = d.to_graph()

    assert g.provide(users_proxy) == ["alice", "bob", "charlie"]
    assert g.provide(first_user_proxy) == "alice"
    assert g.provide(theme_proxy) == "dark"


def test_injected_dict():
    """Test Injected.dict() functionality."""
    config_dict = Injected.dict(
        host=Injected.by_name("host"),
        port=Injected.by_name("port"),
        debug=Injected.by_name("debug"),
    )

    d = design(host="localhost", port=8080, debug=True)
    g = d.to_graph()

    result = g.provide(config_dict)
    assert result == {"host": "localhost", "port": 8080, "debug": True}


def test_injected_list():
    """Test Injected.list() functionality."""
    services_list = Injected.list(
        Injected.by_name("service1"),
        Injected.by_name("service2"),
        Injected.by_name("service3"),
    )

    d = design(service1="auth", service2="database", service3="cache")
    g = d.to_graph()

    result = g.provide(services_list)
    assert result == ["auth", "database", "cache"]


def test_injected_zip():
    """Test Injected.zip() functionality."""
    a = Injected.by_name("a")
    b = Injected.by_name("b")

    # zip takes exactly 2 arguments
    zipped = Injected.zip(a, b)

    d = design(a=1, b=2, c=3)
    g = d.to_graph()

    result = g.provide(zipped)
    assert result == (1, 2)

    # For multiple values, use list
    three_values = Injected.list(a, b, Injected.by_name("c"))
    assert g.provide(three_values) == [1, 2, 3]


def test_injected_pure():
    """Test Injected.pure() for constant values."""
    pure_value = Injected.pure(42)
    pure_string = Injected.pure("constant")
    pure_list = Injected.pure([1, 2, 3])

    d = design()  # No dependencies needed
    g = d.to_graph()

    assert g.provide(pure_value) == 42
    assert g.provide(pure_string) == "constant"
    assert g.provide(pure_list) == [1, 2, 3]


def test_injected_alias():
    """Test creating aliases for injected values."""
    original = Injected.by_name("database_url")

    # Create aliases by binding to the same value
    d = design(database_url="postgresql://localhost/mydb")
    # Add aliases by binding the original injected
    d = d + design(db_url=original, connection_string=original)

    g = d.to_graph()

    # All aliases resolve to the same value
    assert g.provide(original) == "postgresql://localhost/mydb"
    assert g.provide("db_url") == "postgresql://localhost/mydb"
    assert g.provide("connection_string") == "postgresql://localhost/mydb"


def test_design_provide_method():
    """Test design.provide() convenience method."""
    d = design(name="test", value=42)

    # Direct provide without creating graph
    assert d.provide("name") == "test"
    assert d.provide("value") == 42


def test_design_provide_all():
    """Test providing multiple values from design."""
    d = design(a=1, b=2, c=3, d=4)

    # Provide multiple values using individual calls
    g = d.to_graph()
    results = {"a": g.provide("a"), "c": g.provide("c"), "d": g.provide("d")}
    assert results == {"a": 1, "c": 3, "d": 4}


def test_iproxy_entry_points():
    """Test defining entry points with IProxy."""

    @instance
    def trainer():
        class Trainer:
            def train(self, model):
                return f"Training {model}"

        return Trainer()

    @instance
    def model():
        return "ResNet50"

    # Define entry points as IProxy variables
    run_training: IProxy = trainer.train(model)  # Must have IProxy annotation

    d = design()
    g = d.to_graph()

    result = g.provide(run_training)
    assert result == "Training ResNet50"


def test_injected_function_shorthand():
    """Test injected() function as shorthand for Injected.by_name().proxy."""
    # These are equivalent
    a_proxy1 = Injected.by_name("value").proxy
    a_proxy2 = injected("value")

    d = design(value=42)
    g = d.to_graph()

    assert g.provide(a_proxy1) == 42
    assert g.provide(a_proxy2) == 42


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
