import ast
import json
from contextlib import contextmanager
from pathlib import Path
from pprint import pformat

import click

from pinjected import injected, Injected


@click.group()
def main():
    pass


@main.command()
@click.argument('script_path', type=click.Path(exists=True))
@click.argument('func_name')
def extract_func_source_and_imports(script_path: str, func_name: str):
    func_and_imports = extract_func_source_and_imports_dict(func_name, script_path)

    # Prepare the data containing the requested function source and imports
    data = {
        'code': func_and_imports['functions'].get(func_name, f"Function {func_name} not found."),
        'imports': list(set(func_and_imports['imports']))
    }
    # Convert the data to JSON format and print it
    text = json.dumps(data, indent=4)
    # Ensure that the output does not contain "<pinjected>" to prevent code injection
    assert "<pinjected>" not in text
    text = "<pinjected>\n" + text + "\n</pinjected>"
    print(text)


def extract_func_source_and_imports_dict(script_path):
    # Read the content of the script file
    file_content = Path(script_path).read_text()
    # Parse the file content into an AST node tree
    node_tree = ast.parse(file_content)

    # Function to get the source code of decorators with "@"
    def get_decorators_source(decorators):
        return ["@" + ast.get_source_segment(file_content, decorator).strip() for decorator in decorators]

    # Initialize a dictionary to store functions and imports
    func_and_imports = {'functions': {}, 'imports': []}
    # Walk through the AST nodes
    for node in ast.walk(node_tree):
        # Check if the node is a function
        if isinstance(node, ast.FunctionDef):
            # Get decorators source code with "@"
            decorators_source = get_decorators_source(node.decorator_list)
            # Get the source code of the function definition
            func_source_lines = file_content.splitlines()[node.lineno - 1:node.end_lineno]
            func_source = "\n".join(decorators_source + func_source_lines)
            # Store the function source code in the dictionary
            func_and_imports['functions'][node.name] = func_source
        # Check if the node is an import or import from statement
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            # Get the source code of the import
            import_source = ast.get_source_segment(file_content, node)
            # Store the import source code in the list
            func_and_imports['imports'].append(import_source)
    return func_and_imports





class WithBlockVisitor(ast.NodeVisitor):
    def __init__(self):
        self.result = {}

    def visit_With(self, node):
        # In Python 3.9 and above, 'with' statements use 'items' which is a list of 'withitem' objects.
        # In earlier versions, the context expression was directly available as 'context_expr'.
        # We'll check for both to ensure compatibility.
        with_items = getattr(node, 'items', None) or [node]

        for item in with_items:
            context_expr = getattr(item, 'context_expr', None) or item

            # Check if the with statement contains a call to reload
            if isinstance(context_expr, ast.Call) and getattr(context_expr.func, 'id', None) == 'reload':
                # Get the list of reload targets
                reload_targets = [arg.s for arg in context_expr.args]
                # Process each item in the with block
                for body_item in node.body:
                    if isinstance(body_item, ast.AnnAssign) and isinstance(body_item.target, ast.Name):
                        variable_name = body_item.target.id
                        # Assign reload targets to the variable in the result dict
                        self.result[variable_name] = {
                            'reload_targets': reload_targets
                        }


def extract_with_block_structure(source_code):
    # Parse the source code into an AST
    parsed_ast = ast.parse(source_code)
    # Create a visitor instance
    visitor = WithBlockVisitor()
    # Visit the parsed AST
    visitor.visit(parsed_ast)
    # Return the collected results
    return visitor.result


def extrract_assignments(source_code):
    """
    Extract assignment statements from the given Python source code.
    Returns a dictionary with variable names as keys and the source code of the assigned value as values.
    This updated version handles type annotations.
    """

    class AssignmentVisitor(ast.NodeVisitor):
        def __init__(self):
            self.assignments = {}

        def visit_AnnAssign(self, node):
            # Handle assignments with annotations
            if isinstance(node.target, ast.Name):
                var_name = node.target.id
                value_code = ast.get_source_segment(source_code, node.value)
                self.assignments[var_name] = value_code

        def visit_Assign(self, node):
            # Handle normal assignments
            for target in node.targets:
                if isinstance(target, ast.Name):
                    var_name = target.id
                    value_code = ast.get_source_segment(source_code, node.value)
                    self.assignments[var_name] = value_code
                # Handle tuple assignments
                elif isinstance(target, ast.Tuple):
                    for elt in target.elts:
                        if isinstance(elt, ast.Name):
                            var_name = elt.id
                            value_code = ast.get_source_segment(source_code, node.value)
                            self.assignments[var_name] = value_code

    # Parse the source code into an AST
    parsed_ast = ast.parse(source_code)
    # Create a visitor instance
    visitor = AssignmentVisitor()
    # Visit the parsed AST
    visitor.visit(parsed_ast)
    # Return the collected assignments
    return visitor.assignments

@main.command()
@click.argument('script_path', type=click.Path(exists=True))
@click.argument('target_name')
def generate_code_with_reload(
        script_path: str,
        target_name: str,
):
    """
    1. find all function names using extract_func_source_and_imports
    2. check the reload target of target_name
    3. concat all sources and return it as a pinjected json
    :param script_path:
    :param target_name:
    :return:
    """
    from loguru import logger
    source = Path(script_path).read_text()
    func_table = extract_func_source_and_imports_dict(script_path)
    logger.info(f"func_table:{pformat(func_table)}")
    reload_table = extract_with_block_structure(source)
    if target_name not in reload_table:
        reload_targets = []
    else:
        reload_targets = reload_table[target_name]['reload_targets']
    funcs_to_reload = [func_table['functions'][func_name] for func_name in reload_targets]
    imports = func_table['imports']
    imports = '\n'.join(imports)
    func_defs = '\n'.join(funcs_to_reload)
    assignments: dict[str, str] = extrract_assignments(source)
    # logger.info(pformat(assignments))

    """
    How can I add the child session?
    """
    code = f"""
if '__graph__' not in globals():
    from pinjected.helper_structure import MetaContext
    from pathlib import Path
    exec(Path("{script_path}").read_text())
    __meta_context__ = MetaContext.gather_from_path(Path("{script_path}"))
    __design__ = __meta_context__.final_design
    __graph__ = __design__.to_graph().auto_sync()
{imports}
{func_defs}
{target_name} = {assignments[target_name]}
__graph__[{target_name}]
"""
    # oops, target_name is not in the scope
    logger.debug(f"generated code:{code}")
    data = "<pinjected>\n" + json.dumps({'code': code}) + "\n</pinjected>"
    print(data)


@injected
def test_target_function():
    print(f"hello")


@contextmanager
def reload(*targets):
    # this is just a placeholder for the AST visitor
    yield


with reload('test_target_function'):
    x = 0
    run_test: Injected = test_target_function


def is_pydevd():
    import os
    return 'PYDEVD_LOAD_VALUES_ASYNC' in os.environ


if __name__ == '__main__' and not is_pydevd():
    """
    this code generation works, 
    now the remaining task is, 
    how to get the script path and its var name,
    
    Options:
    1. use the gutter icon
    2. action: run current thing? nah. 
    so,, what is the way to rerun the current thing? quickly?
    I think, placing a cursor on the target and then running the command is the best way.
    so, let's make an action. 
    """
    main()
