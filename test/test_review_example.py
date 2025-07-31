"""Test file to demonstrate review_pinjected command."""

from typing import Protocol

from pinjected import injected, instance, design


# Mock classes and functions for test
class Database:
    def query(self, data):
        return {"result": data}


class Logger:
    def info(self, msg):
        print(msg)


class ApiClient:
    async def fetch(self, query):
        return [{"item": query}]


def connect(host, port):
    return f"Connected to {host}:{port}"


class ProcessDataProtocol(Protocol):
    def __call__(
        self,
    ) -> dict: ...


# Fixed: injected function with type annotations
@injected(protocol=ProcessDataProtocol)
def process_data(database: "Database", logger: "Logger", /, data: str) -> dict:
    logger.info(f"Processing data: {data}")
    return database.query(data)


class AFetchItemsProtocol(Protocol):
    async def __call__(
        self,
    ) -> list: ...


# Fixed: async injected function with a_ prefix
@injected(protocol=AFetchItemsProtocol)
async def a_fetch_items(api_client: "ApiClient", /, query: str) -> list:
    return await api_client.fetch(query)


# Fixed: instance function without default arguments
@instance
def database_connection(host: str, port: int):
    # Mock connection logic
    return {"host": host, "port": port}


# Fixed: using bind for configuration
__meta_design__ = design(database=database_connection.bind(host="localhost", port=5432))
