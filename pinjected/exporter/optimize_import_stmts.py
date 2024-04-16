import ast

def fix_imports(source):
    # Parse the source code into an AST
    tree = ast.parse(source)

    # Create a dict of imported variables and their modules
    import_dict = {}
    direct_imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.asname:
                    import_dict[alias.asname] = alias.name
                else:
                    direct_imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module
            for alias in node.names:
                import_dict[alias.asname if alias.asname else alias.name] = f"{module}"

    # List all used variable names in the source code (except in the imports)
    used_variables = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            used_variables.add(node.id)

    # Create a purified dict of import statements
    purified_imports = {}
    for var_name, module in import_dict.items():
        if var_name in used_variables:
            purified_imports[var_name] = module

    # Replace the import statements in the source code with purified ones
    import_lines = []
    for var_name, module in purified_imports.items():
        import_lines.append(f"from {module} import {var_name}")
    for module in direct_imports:
        if module in used_variables:
            import_lines.append(f"import {module}")

    # Find the line numbers of import statements in the source code
    import_line_numbers = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            import_line_numbers.add(node.lineno)

    # Split the source code into lines
    source_lines = source.split("\n")

    # Remove the original import statements
    source_lines = [line for lineno, line in enumerate(source_lines, start=1) if lineno not in import_line_numbers]

    # Insert the purified import statements at the beginning
    source_lines = import_lines + [""] + source_lines

    # Join the lines back into a single string
    purified_source = "\n".join(source_lines)

    return purified_source
