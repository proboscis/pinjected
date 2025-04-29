from collections.abc import Callable
from dataclasses import dataclass

from makefun import create_function


@dataclass
class Provider:
    dependencies: list[str]
    function: Callable

    def get_provider_function(self):
        signature = f"provider_function({','.join(self.dependencies)})"
        return create_function(signature, self.function)
        # TODO implement this for better composable providers...
