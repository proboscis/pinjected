import ast
import inspect
from dataclasses import dataclass

from pinjected.injected_class.test_module import PClassExample

from loguru import logger

class AttributeReplacer(ast.NodeTransformer):
    def __init__(self, attrs_to_replace):
        self.attrs_to_replace = set(attrs_to_replace)
        self.replaced_attrs = set()
        self.in_method = False

    def visit_AsyncFunctionDef(self, node):
        if not self.in_method:
            self.in_method = True
            new_node = self.generic_visit(node)
            self.in_method = False

            for attr in self.replaced_attrs:
                new_param = ast.arg(arg=attr, annotation=None, lineno=node.lineno, col_offset=node.col_offset)
                new_node.args.args.append(new_param)

            return new_node
        else:
            return self.generic_visit(node)

    def visit_Attribute(self, node):
        if self.in_method and isinstance(node.value, ast.Name) and node.value.id == 'self':
            if node.attr in self.attrs_to_replace:
                new_name = f'__self_{node.attr}__'
                self.replaced_attrs.add(new_name)
                return ast.Name(id=new_name, ctx=node.ctx, lineno=node.lineno, col_offset=node.col_offset)
        return node


def modify_class(class_ast, method_names, attrs_to_replace):
    for node in class_ast.body:
        if isinstance(node,ast.FunctionDef) and node.name in method_names:
            raise RuntimeError(f"Method {node.name} must be an async method in order to be injected! but it is sync method.")
        if isinstance(node, ast.AsyncFunctionDef) and node.name in method_names:
            replacer = AttributeReplacer(attrs_to_replace)
            new_method = replacer.visit(node)
            class_ast.body[class_ast.body.index(node)] = new_method
    return class_ast


def ast_to_class(class_ast, class_name):
    # Wrap the class definition in a module
    module = ast.Module(body=[class_ast], type_ignores=[])

    # Fix missing attributes
    ast.fix_missing_locations(module)

    # Compile the module AST
    compiled_ast = compile(module, filename="<ast>", mode="exec")

    # Create a new namespace
    namespace = {}

    # Execute the compiled code in the new namespace
    exec(compiled_ast, namespace)

    # Retrieve and return the class object from the namespace
    return namespace[class_name]


def convert_cls(cls, methods_to_convert:list[str], attrs_to_replace:list[str]):
    logger.info(f"\nconverting class:{cls}\nmethods:{methods_to_convert}\nattrs:{attrs_to_replace}")
    class_def = inspect.getsource(cls)
    tree = ast.parse(class_def)
    class_node = tree.body[0]#tree.body[0]
    modified_class_ast = modify_class(
        class_node,
        method_names=methods_to_convert,
        attrs_to_replace=attrs_to_replace
    )
    logger.info(f"modified class:\n{ast.unparse(modified_class_ast)}")
    return ast_to_class(modified_class_ast, cls.__name__)

if __name__ == '__main__':
    convert_cls(
        PClassExample,
        [
            'simple_method',
            "method1",
            "method2"
        ],
        ['_dep1', '_dep2','c'])