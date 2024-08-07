import ast
import inspect
from collections import defaultdict


class AsyncMethodVisitor(ast.NodeVisitor):
    def __init__(self):
        self.async_methods = defaultdict(set)
        self.current_method = None

    def visit_AsyncFunctionDef(self, node):
        self.current_method = node.name
        self.generic_visit(node)
        self.current_method = None

    def visit_Attribute(self, node):
        if isinstance(node.value, ast.Name) and node.value.id == 'self':
            if self.current_method:
                self.async_methods[self.current_method].add(node.attr)
        self.generic_visit(node)


def extract_attribute_accesses(cls)->dict[str,set[str]]:
    source_code = inspect.getsource(cls)
    tree = ast.parse(source_code)
    visitor = AsyncMethodVisitor()
    visitor.visit(tree)
    return dict(visitor.async_methods)


# Example usage
example_class = """
class ExampleClass:
    _dep1:str

    def __init__(self):
        self.attribute1 = 1
        self.attribute2 = 2

    async def async_method1(self):
        return self.attribute1

    async def async_method2(self):
        self.attribute2 += 1
        return self.attribute1 + self.attribute2 + self._dep1

    def regular_method(self):
        return self.attribute1 * self.attribute2
"""


# Demonstration of ast.unparse
def get_async_method_source(source_code, method_name):
    tree = ast.parse(source_code)
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == method_name:
            return ast.unparse(node)
    return None


if __name__ == '__main__':
    result = extract_attribute_accesses(example_class)
    print(result)
    # Example usage of ast.unparse
    async_method_source = get_async_method_source(example_class, 'async_method2')
    print("\nSource of async_method2:")
    print(async_method_source)
