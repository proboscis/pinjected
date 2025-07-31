from pinjected import injected


@injected
def process_data(transformer, /):
    return transformer.process()


@injected
def validate_data(validator, /):
    return validator.validate()


@injected
def workflow(database, /):
    # Bad - calling other @injected functions without declaring them
    data = process_data("test")  # ❌ process_data not declared
    valid = validate_data(data)  # ❌ validate_data not declared
    return database.save(valid)


@injected
def another_workflow(logger, /):
    # Also bad
    result = process_data("input")  # ❌ process_data not declared
    return result


@injected
def good_workflow(database, process_data, validate_data, /):
    # Good - these are declared as dependencies
    data = process_data("test")  # ✅ Declared
    valid = validate_data(data)  # ✅ Declared
    return database.save(valid)


@injected
def complex_workflow(logger, process_data, /):
    # Good - process_data is declared
    result = process_data("input")  # ✅ Declared
    logger.info(f"Result: {result}")
    return result


# Regular functions can call @injected functions
def regular_function():
    result1 = process_data("test")  # OK - not in @injected function
    result2 = validate_data("data")  # OK - not in @injected function
    return result1, result2
