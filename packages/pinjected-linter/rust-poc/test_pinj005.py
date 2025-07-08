from pinjected import injected, instance


@injected
def user_data(db, /, user_id):  # Bad - noun form
    return db.query(user_id)


@injected
def result(calculator, /, input):  # Bad - noun form
    return calculator.compute(input)


@injected
def configuration(loader, /):  # Bad - noun form
    return loader.load_config()


@injected
def user_manager(db, /):  # Bad - noun suffix
    return UserManager(db)


@injected
def response(api_client, /, endpoint):  # Bad - noun form
    return api_client.call(endpoint)


# Good examples - verb forms
@injected
def fetch_user_data(db, /, user_id):  # Good - verb form
    return db.query(user_id)


@injected
def calculate_result(calculator, /, input):  # Good - verb form
    return calculator.compute(input)


@injected
def load_configuration(loader, /):  # Good - verb form
    return loader.load_config()


@injected
def create_user_manager(db, /):  # Good - verb form
    return UserManager(db)


@injected
def get_response(api_client, /, endpoint):  # Good - verb form
    return api_client.call(endpoint)


@injected
def process(data, /):  # Good - standalone verb
    return data.transform()


@injected
def initialize(config, /):  # Good - standalone verb
    return System(config)


# Async examples
@injected
async def a_user_data(db, /, user_id):  # Bad - noun form after prefix
    return await db.query_async(user_id)


@injected
async def a_fetch_user_data(db, /, user_id):  # Good - verb form after prefix
    return await db.query_async(user_id)


@injected
async def a_process_data(processor, /, data):  # Good - verb form after prefix
    return await processor.process(data)


@injected
async def a_result(calculator, /):  # Bad - noun form after prefix
    return await calculator.compute_async()


# Edge cases
@injected
def data(db, /):  # Bad - single noun
    return db.all()


@injected
def info(api, /):  # Bad - single noun
    return api.get_info()


@injected
def get(api, /, resource):  # Good - single verb
    return api.get(resource)


@injected
def fetch(db, /, id):  # Good - single verb
    return db.fetch(id)


@injected
def _private_data(db, /):  # Bad - noun form even with underscore prefix
    return db.private_data()


@injected
def get_user_data_and_process_it(db, /, id):  # Good - starts with verb
    return process(db.get_user(id))


# Not @injected - should be ignored
def user_data_regular():  # OK - no decorator
    return get_data()


@instance
def database():  # OK - @instance, not @injected
    return Database()


class MyClass:
    def result(self):  # OK - class method
        return self.compute()


# Mock classes/functions for examples
class UserManager:
    pass


class System:
    pass


class Database:
    pass


def get_data():
    return "data"
