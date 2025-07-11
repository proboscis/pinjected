"""Test file for PINJ035: No deprecated design functions"""

from typing import Any

from pinjected import (
    instances,  # Deprecated
    providers,  # Deprecated
    classes,  # Deprecated
    destructors,  # Deprecated
    injecteds,  # Deprecated
    design,  # Modern API
    injected,
    instance,
    Injected,
)


# Placeholder classes for examples
class DatabaseConnection:
    def close(self):
        pass


class Logger:
    pass


class UserService:
    pass


class AuthService:
    pass


class Service:
    pass


class Processor:
    def __init__(self, db, logger=None):
        self.db = db
        self.logger = logger


# ❌ Incorrect: Using instances() - deprecated
# PINJ035: Function 'instances()' is deprecated
config = instances(host="localhost", port=5432, debug=True, timeout=30)


# ❌ Incorrect: Using providers() - deprecated
def create_database():
    return DatabaseConnection()


def create_logger():
    return Logger()


# PINJ035: Function 'providers()' is deprecated
services = providers(database=create_database, logger=create_logger)

# ❌ Incorrect: Using classes() - deprecated
# PINJ035: Function 'classes()' is deprecated
class_bindings = classes(UserService=UserService, AuthService=AuthService)


# ❌ Incorrect: Using destructors() - deprecated
def cleanup_database(db):
    db.close()


def cleanup_logger(logger):
    logger.flush()


# PINJ035: Function 'destructors()' is deprecated
cleanups = destructors(database=cleanup_database, logger=cleanup_logger)

# ❌ Incorrect: Using injecteds() - deprecated
# PINJ035: Function 'injecteds()' is deprecated
injected_bindings = injecteds(
    processor=Injected.bind(lambda db, logger: Processor(db, logger)),
    service=Injected.pure(Service()),
)

# ❌ Incorrect: Combining deprecated functions
# PINJ035: Multiple violations
final_design_old = config + services + class_bindings

# ❌ Incorrect: Using in augmented assignment
base = design()
# PINJ035: Function 'instances()' is deprecated
base += instances(extra_config="value")

# ❌ Incorrect: Using in expression statement
# PINJ035: Function 'providers()' is deprecated
providers(temp_service=lambda: Service())

# ❌ Incorrect: Annotated assignment
# PINJ035: Function 'instances()' is deprecated
typed_config: Any = instances(typed_host="localhost")


# ✅ Correct: Using modern design() API
modern_config = design(host="localhost", port=5432, debug=True, timeout=30)


# ✅ Correct: Using decorators with design()
@injected
def database():
    return DatabaseConnection()


@injected
def logger():
    return Logger()


@instance
def user_service():
    return UserService()


@instance
def auth_service():
    return AuthService()


# ✅ Correct: Using with design() context manager
with design() as d:
    # Add simple values
    d["host"] = "localhost"
    d["port"] = 5432
    d["debug"] = True

    # Add providers
    d.provide(database)
    d.provide(logger)
    d.provide(user_service)
    d.provide(auth_service)


# ✅ Correct: Cleanup with context managers
@injected
def managed_database():
    """Database with automatic cleanup."""
    db = DatabaseConnection()
    try:
        yield db
    finally:
        db.close()


# ✅ Correct: Direct Injected usage with design()
modern_injected = design(
    processor=Injected.bind(lambda db, logger: Processor(db, logger)),
    service=Injected.pure(Service()),
)

# ✅ Correct: Combining modern designs
base_design = design(host="localhost", port=5432)
service_design = design(timeout=30)

with design() as provider_design:
    provider_design.provide(database)
    provider_design.provide(logger)

final_design = base_design + service_design + provider_design
