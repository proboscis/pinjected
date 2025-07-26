"""Test cases for PINJ042: No Unmarked Calls to @injected Functions"""

from pinjected import injected, instance


# Test Case 1: Basic unmarked call from regular function (should error)
@injected
def database_service(db_connection, logger, /, query: str):
    logger.info(f"Executing query: {query}")
    return db_connection.execute(query)


def get_user_data(user_id: int):
    # ERROR: Unmarked call to @injected function
    result = database_service(f"SELECT * FROM users WHERE id = {user_id}")
    return result


# Test Case 2: Marked call with explicit comment (should pass)
def get_user_data_marked(user_id: int):
    # OK: Explicitly marked as intentional
    result = database_service(
        f"SELECT * FROM users WHERE id = {user_id}"
    )  # pinjected: explicit-call
    return result


# Test Case 3: Marked call with noqa (should pass)
def get_user_data_noqa(user_id: int):
    # OK: Using noqa to suppress
    result = database_service(
        f"SELECT * FROM users WHERE id = {user_id}"
    )  # pinjected: explicit-call
    return result


# Test Case 4: Call from class method (should error)
@injected
async def a_process_data(processor, /, data):
    return await processor.process(data)


class DataHandler:
    def handle(self, data):
        # ERROR: Unmarked call from method
        return a_process_data(data)

    def handle_marked(self, data):
        # OK: Marked call
        return a_process_data(data)  # pinjected: explicit-call


# Test Case 5: Call from @instance function (should error)
@instance
def api_handler():
    def handler(request):
        # ERROR: Unmarked call from @instance
        data = database_service("SELECT * FROM api_logs")
        return {"status": "ok", "data": data}

    return handler


# Test Case 6: Call from nested function (should error)
def create_processor():
    def process(item):
        # ERROR: Unmarked call in nested function
        return database_service(
            f"UPDATE items SET processed = true WHERE id = {item.id}"
        )

    return process


# Test Case 7: Lambda with unmarked call (should error)
# ERROR: Lambda calling @injected
def get_all_users():
    return database_service("SELECT * FROM users")


# Test Case 8: Lambda with marked call (should pass)
# OK: Lambda with marked call
def get_all_users_marked():
    return database_service("SELECT * FROM users")  # pinjected: explicit-call


# Test Case 9: Call inside @injected function (should NOT error - PINJ009 handles this)
@injected
def composite_service(logger, /, query: str):
    # This should NOT trigger PINJ042 (PINJ009 handles calls within @injected)
    result = database_service(query)
    return result


# Test Case 10: Multiple calls, some marked, some not
def batch_operations():
    # ERROR: First call unmarked
    users = database_service("SELECT * FROM users")

    # OK: Second call marked
    products = database_service("SELECT * FROM products")  # pinjected: explicit-call

    # ERROR: Third call unmarked
    orders = database_service("SELECT * FROM orders")

    return users, products, orders


# Test Case 11: Call in comprehension (should error)
def get_multiple_tables(table_names):
    # ERROR: Unmarked calls in list comprehension
    results = [database_service(f"SELECT * FROM {table}") for table in table_names]
    return results


# Test Case 12: Call in if/else (should error both branches)
def conditional_query(use_cache: bool):
    if use_cache:
        # ERROR: Unmarked call in if branch
        result = database_service("SELECT * FROM cache")
    else:
        # ERROR: Unmarked call in else branch
        result = database_service("SELECT * FROM live_data")
    return result


# Test Case 13: Regular function calling regular function (should NOT error)
def regular_helper(data):
    return data.upper()


def use_regular_helper(text):
    # OK: regular_helper is not @injected
    return regular_helper(text)


# Test Case 14: Import and call @injected from another module
# from .other_module import external_service  # Assume this is @injected


# def call_external():
#     # ERROR: Calling imported @injected function without marking
#     return external_service("data")


# def call_external_marked():
#     # OK: Marked call to imported @injected
#     return external_service("data")  # pinjected: explicit-call


# Test Case 15: Async function calling async @injected
@injected
async def a_fetch_data(http_client, /, url: str):
    return await http_client.get(url)


async def fetch_user_data(user_id: int):
    # ERROR: Unmarked await of @injected
    data = await a_fetch_data(f"/api/users/{user_id}")
    return data


async def fetch_user_data_marked(user_id: int):
    # OK: Marked await of @injected
    data = await a_fetch_data(
        f"/api/users/{user_id}"
    )  # pinjected: explicit-call - API entry point
    return data
