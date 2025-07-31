"""Test file for PINJ029: No function/class calls inside Injected.pure()"""

from pinjected import Injected, IProxy


class MyService:
    def __init__(self, config):
        self.config = config


class DatabaseClient:
    def __init__(self, host="localhost", port=5432):
        self.host = host
        self.port = port


def factory():
    return MyService({"debug": True})


def get_config():
    return {"api_key": "secret"}


class ConfigLoader:
    def load(self):
        return {"db_host": "localhost"}


config_loader = ConfigLoader()


# BAD: Class instantiation inside Injected.pure()
service1 = Injected.pure(MyService({"debug": True}))  # PINJ029
service2 = Injected.pure(DatabaseClient(host="prod.db"))  # PINJ029
service3 = Injected.pure(DatabaseClient("localhost", 5432))  # PINJ029


# BAD: Function calls inside Injected.pure()
service4 = Injected.pure(factory())  # PINJ029
config1 = Injected.pure(get_config())  # PINJ029
config2 = Injected.pure(config_loader.load())  # PINJ029


# BAD: Lambda calls inside Injected.pure()
value1 = Injected.pure((lambda x: x + 1)(5))  # PINJ029
value2 = Injected.pure((lambda: {"key": "value"})())  # PINJ029


# BAD: Nested calls
nested1 = Injected.pure(MyService(get_config()))  # PINJ029
nested2 = Injected.pure(factory().config)  # PINJ029 (factory() is called)


# GOOD: Using IProxy pattern (should not trigger)
service_good1 = IProxy(MyService)({"debug": True})
service_good2 = IProxy(DatabaseClient)(host="prod.db")
service_good3 = IProxy(factory)()
config_good1 = IProxy(get_config)()
config_good2 = IProxy(config_loader.load)()
value_good1 = IProxy(lambda x: x + 1)(5)


# GOOD: No call expression inside Injected.pure()
ref1 = Injected.pure(42)  # Literal
ref2 = Injected.pure("string")  # Literal
ref3 = Injected.pure(factory)  # Function reference (not called)
ref4 = Injected.pure(MyService)  # Class reference (not instantiated)
ref5 = Injected.pure(lambda x: x + 1)  # Lambda reference (not called)
ref6 = Injected.pure(config_loader)  # Object reference
ref7 = Injected.pure([1, 2, 3])  # List literal
ref8 = Injected.pure({"key": "value"})  # Dict literal
ref9 = Injected.pure(None)  # None literal
ref10 = Injected.pure(True)  # Boolean literal


# GOOD: With noqa comment (should not trigger)
service_noqa = Injected.pure(factory())
config_noqa = Injected.pure(get_config())


# Edge cases
# BAD: Built-in function calls
list1 = Injected.pure(list([1, 2, 3]))  # PINJ029
dict1 = Injected.pure(dict(a=1, b=2))  # PINJ029
str1 = Injected.pure(str(123))  # PINJ029


# GOOD: Built-in types without calls
list2 = Injected.pure(list)  # Type reference
dict2 = Injected.pure(dict)  # Type reference


# BAD: Comprehensions with function calls (these create calls internally)
# Note: These might be tricky to detect depending on AST structure
comp1 = Injected.pure([factory() for _ in range(3)])  # Might not detect inner calls
comp2 = Injected.pure(
    {i: get_config() for i in range(2)}
)  # Might not detect inner calls
