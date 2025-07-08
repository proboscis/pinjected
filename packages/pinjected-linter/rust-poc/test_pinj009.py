from pinjected import injected


@injected
async def a_fetch_data(api, /, user_id):
    return await api.get_user(user_id)


@injected
async def a_process_user(logger, /, user):
    logger.info(f"Processing {user}")
    return user.process()


# These are OK - a_fetch_data and a_process_user are declared dependencies
@injected
async def a_good_example(a_fetch_data, a_process_user, /, user_id):
    # These awaits are OK - dependencies are resolved functions
    data = await a_fetch_data(user_id)  # OK - declared dependency
    result = await a_process_user(data)  # OK - declared dependency
    return result


# This is BAD - calling @injected functions that are NOT dependencies
@injected
async def a_bad_example(some_service, /, user_id):
    # These awaits are WRONG - a_fetch_data is not a dependency
    data = await a_fetch_data(user_id)  # Bad - not a declared dependency
    result = await a_process_user(data)  # Bad - not a declared dependency
    return result


@injected
async def a_mixed_bad(logger, /, ids):
    # a_fetch_data is NOT a dependency, so await is wrong
    results = []
    for id in ids:
        data = await a_fetch_data(id)  # Bad - not a declared dependency
        results.append(data)
    return results


# Regular function can await @injected calls
async def regular_async(user_id):
    # This is OK - not an @injected function
    data = await a_fetch_data(user_id)
    result = await a_process_user(data)
    return result


# OK to await non-@injected calls
@injected
async def a_mixed_example(api_client, a_process_data, /, url):
    # This await is OK - api_client is not @injected
    raw_data = await api_client.fetch(url)  # Good - not @injected
    # But this should not have await
    processed = a_process_data(raw_data)  # Good - no await
    return processed


@injected
async def a_database_example(db, a_transform, /, query):
    # OK to await database operations
    results = await db.execute(query)  # Good - db is not @injected

    # Transform each result without await
    transformed = [a_transform(r) for r in results]  # Good - no await

    # More async db operations
    await db.commit()  # Good - not @injected

    return transformed


# Nested example
@injected
async def a_complex(a_helper, /, items):
    # Nested function that's not @injected
    async def process_item(item):
        # a_helper is from outer scope (declared dependency)
        return await a_helper(item)  # OK - using outer dependency

    results = []
    for item in items:
        result = await process_item(item)
        results.append(result)
    return results


@injected
async def a_bad_nested(some_service, /, items):
    # Nested function trying to use @injected without declaring dependency
    async def process_item(item):
        # This is bad - a_fetch_data is not a dependency
        return await a_fetch_data(item)  # Bad - not a declared dependency

    results = []
    for item in items:
        result = await process_item(item)
        results.append(result)
    return results
