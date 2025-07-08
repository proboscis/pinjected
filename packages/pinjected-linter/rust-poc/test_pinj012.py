from pinjected import injected


# Test case 1: Simple cycle A → B → A
@injected
def service_a(service_b, /):
    return f"A uses {service_b()}"


@injected
def service_b(service_a, /):
    return f"B uses {service_a()}"


# Test case 2: Complex cycle A → B → C → D → A
@injected
def auth_service(user_service, /, request):
    user = user_service(request.user_id)
    return validate_auth(user)


@injected
def user_service(database_service, /, user_id):
    return database_service(f"SELECT * FROM users WHERE id={user_id}")


@injected
def database_service(logger_service, /, query):
    logger_service(f"Executing: {query}")
    return execute_query(query)


@injected
def logger_service(auth_service, /, message):
    if auth_service.is_admin():
        log_admin_action(message)
    return log(message)


# Test case 3: Self-reference
@injected
def recursive_service(recursive_service, /, data):
    if data:
        return recursive_service(data[1:])
    return []


# Test case 4: Multiple independent cycles
# First cycle: X → Y → X
@injected
def service_x(service_y, /):
    return service_y()


@injected
def service_y(service_x, /):
    return service_x()


# Second cycle: P → Q → R → P
@injected
def service_p(service_q, /):
    return service_q()


@injected
def service_q(service_r, /):
    return service_r()


@injected
def service_r(service_p, /):
    return service_p()


# Test case 5: Valid hierarchy (no cycles)
@injected
def logger(message):
    # No dependencies - all runtime args
    print(f"[LOG] {message}")


@injected
def config(key):
    # No dependencies - all runtime args
    return get_config(key)


@injected
def database(logger, config, /, query):
    logger(f"Query: {query}")
    db_config = config("database")
    return execute_query(query, db_config)


@injected
def user_repository(database, logger, /, user_id):
    logger(f"Fetching user {user_id}")
    return database(f"SELECT * FROM users WHERE id={user_id}")


@injected
def api_handler(user_repository, logger, /, request):
    logger(f"API request from {request.ip}")
    return user_repository(request.user_id)


# Test case 6: Async functions with cycles
@injected
async def a_service_a(a_service_b, /, data):
    result = a_service_b(data)
    return result


@injected
async def a_service_b(a_service_a, /, data):
    result = a_service_a(data)
    return result


# Test case 7: Partial cycle (not all functions in cycle)
@injected
def entry_point(circular_a, /, request):
    # entry_point depends on circular_a but is not part of the cycle
    return circular_a(request)


@injected
def circular_a(circular_b, /, data):
    return circular_b(data)


@injected
def circular_b(circular_c, /, data):
    return circular_c(data)


@injected
def circular_c(circular_a, /, data):
    # Creates cycle: A → B → C → A
    return circular_a(data)


@injected
def unrelated_service(data):
    # Not part of any cycle - no dependencies
    return data


# Mock functions for examples
def validate_auth(user):
    return True


def execute_query(query, db_config=None):
    return []


def log_admin_action(message):
    pass


def log(message):
    pass


def get_config(key):
    return {}
