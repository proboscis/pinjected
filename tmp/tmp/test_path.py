# Test the path formatting function
def format_path_for_display(path: str, max_length: int = 50) -> str:
    """Format a file path for display, shortening if necessary."""
    if len(path) <= max_length:
        return path

    parts = [p for p in path.split("/") if p]  # Remove empty strings
    if len(parts) > 3:
        return ".../" + "/".join(parts[-3:])
    return path


# Test cases
test_path = "/very/long/path/to/some/deeply/nested/module/in/the/project/database.py"
print(f"Original: {test_path}")
print(f"Formatted: {format_path_for_display(test_path)}")

test_path2 = "/app/module/submodule/config.py"
print(f"\nOriginal: {test_path2}")
print(f"Formatted (max=20): {format_path_for_display(test_path2, max_length=20)}")
