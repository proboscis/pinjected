"""Test file for PINJ032: @injected/@instance functions should not have IProxy return type"""

from typing import Optional, Union, List, Dict
from pinjected import injected, instance, IProxy


# Mock classes and functions for test
class DatabaseClient:
    def __init__(self, url):
        self.url = url


async def process(config):
    return {"processed": True, "config": config}


async def create_client(config):
    return DatabaseClient(config["url"])


# BAD: @injected function with IProxy return type
@injected
def my_service(config, db) -> IProxy:  # PINJ032
    return {"config": config, "db": db}


# BAD: @injected function with IProxy[T] return type
@injected
def typed_service(config) -> IProxy[dict]:  # PINJ032
    return {"config": config}


# BAD: @instance function with IProxy return type
@instance
def database_client(config) -> IProxy:  # PINJ032
    return DatabaseClient(config["db_url"])


# BAD: @instance function with IProxy[T] return type
@instance
def typed_client(config) -> IProxy[DatabaseClient]:  # PINJ032
    return DatabaseClient(config["db_url"])


# BAD: pinjected.IProxy with module prefix
@injected
def api_handler(auth, cache) -> IProxy:  # PINJ032 - testing module prefix detection
    return {"auth": auth, "cache": cache}


# BAD: Complex return types with IProxy
@injected
def complex_service(config) -> Optional[IProxy[dict]]:  # PINJ032
    if config:
        return {"config": config}
    return None


# BAD: Union types with IProxy
@injected
def union_service(config, mode) -> Union[IProxy, dict]:  # PINJ032
    if mode == "proxy":
        return {"proxy": True}
    return {"config": config}


# BAD: Async functions with IProxy return
@injected
async def async_service(config) -> IProxy:  # PINJ032
    return await process(config)


@instance
async def async_client(config) -> IProxy[DatabaseClient]:  # PINJ032
    return await create_client(config)


# GOOD: Normal return type annotations
@injected
def proper_service(config, db) -> dict:
    return {"config": config, "db": db}


@instance
def proper_client(config) -> DatabaseClient:
    return DatabaseClient(config["db_url"])


# GOOD: Optional normal types
@injected
def optional_service(config) -> Optional[dict]:
    if config:
        return {"config": config}
    return None


# GOOD: Union of normal types
@injected
def union_normal(config, mode) -> Union[dict, list]:
    if mode == "list":
        return [config]
    return {"config": config}


# GOOD: No return type annotation
@injected
def no_annotation(config):
    return {"config": config}


# GOOD: Regular functions can return IProxy
def regular_function(config) -> IProxy:
    # This is fine - not @injected/@instance
    return IProxy(lambda: {"config": config})


# GOOD: With noqa comment
@injected
def service_with_noqa(config) -> IProxy:
    return {"config": config}


# Edge case: Custom class named IProxy (should not trigger if it's not pinjected.IProxy)
class MyIProxy:
    pass


@injected
def custom_iproxy(config) -> MyIProxy:  # Should not trigger
    return MyIProxy()


# Edge case: Nested generic types
@injected
def nested_generic(config) -> List[Dict[str, IProxy]]:  # PINJ032
    return [{"proxy": IProxy(lambda: config)}]
