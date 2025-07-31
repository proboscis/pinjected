from pinjected import Injected, design, instance


@instance
def database():
    """An instance function"""
    return {"host": "localhost"}


@instance
def cache():
    """Another instance function"""
    return {"type": "redis"}


@instance
def logger():
    """Logger instance"""
    return "logger"


# Good examples - empty design is allowed
base = design()

# Good - using design function with references and values
config = design(
    database=database,  # Reference to @instance function
    cache=cache,  # Reference to @instance function
    batch_size=128,  # Simple value
    learning_rate=0.001,  # Simple value
    injected_val=Injected.pure("value"),  # Factory methods are allowed
)

# Good - combining designs
combined = base + design(database=database) + design(cache=cache)

# Bad examples
bad1 = design(instance=database)  # Wrong key name (decorator name)
bad2 = design(database=database())  # Calling @instance function
bad3 = design(
    injected=database,  # Wrong key name (decorator name)
    provider=cache,  # Wrong key name (decorator name)
)
bad4 = design(
    db=database(),  # Calling @instance function
    cache=cache(),  # Calling @instance function
    logger=logger(),  # Calling @instance function
)

# Mixed good and bad
mixed = design(
    database=database,  # Good - reference
    cache=cache(),  # Bad - calling function
    batch_size=128,  # Good - value
    instance=logger,  # Bad - decorator name as key
)


# Regular function calls are fine
def get_config():
    return database()  # OK - not in design()


# design() in function
def create_app():
    return design(
        database=database,  # Good
        cache=cache(),  # Bad - calling @instance
    )


# Nested design calls
nested_config = design(
    nested=design(
        db=database,  # Good
        cache=cache(),  # Bad
    )
)


# Non-@instance functions can be called
def regular_function():
    return "regular"


# This is OK - regular_function is not @instance
ok_config = design(
    regular=regular_function(),  # OK - not @instance
    database=database,  # Good
)
