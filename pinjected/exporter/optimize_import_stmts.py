import ast


def fix_imports(source):
    if not source.strip():
        return source

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

    # Find the line number ranges of import statements
    import_line_ranges = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            # For multiline imports, we need to find the full range
            start_line = node.lineno
            # The end_lineno attribute gives us the last line of the node
            end_line = getattr(node, "end_lineno", node.lineno)
            for line in range(start_line, end_line + 1):
                import_line_ranges.add(line)

    # Split the source code into lines
    source_lines = source.split("\n")

    # Remove the original import statements
    filtered_lines = []
    for lineno, line in enumerate(source_lines, start=1):
        if lineno not in import_line_ranges:
            filtered_lines.append(line)

    # Remove leading empty lines from filtered content
    while filtered_lines and not filtered_lines[0].strip():
        filtered_lines.pop(0)

    # Insert the purified import statements at the beginning
    if import_lines:
        result_lines = import_lines + [""] + filtered_lines
    else:
        result_lines = filtered_lines

    # Join the lines back into a single string
    purified_source = "\n".join(result_lines)

    return purified_source
