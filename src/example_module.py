"""Example module to test PINJ036 rule"""


def public_function(x: int, y: str = "default") -> str:
    """A public function that should be in the stub file"""
    return f"{x}: {y}"


async def async_public_function(data: dict) -> None:
    """An async public function"""
    await process_data(data)


class PublicClass:
    """A public class with methods"""

    def __init__(self, name: str):
        self.name = name

    def public_method(self, value: int) -> int:
        """A public method"""
        return value * 2

    def _private_method(self):
        """This should not be in the stub"""
        pass


PUBLIC_CONSTANT: int = 42
config_dict = {"key": "value"}

# Private stuff
_private_var = "hidden"


def _private_function():
    pass


async def process_data(data):
    pass
