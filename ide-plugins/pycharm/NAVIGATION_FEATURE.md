# PyCharm Plugin: Navigation from Dependency Parameters

## Overview

This feature allows users to navigate from dependency parameters in `@injected`/`@instance` functions to their corresponding function definitions in the PyCharm IDE.

## How it Works

When you click on a parameter name in a function decorated with `@injected` or `@instance`, the plugin will:

1. Search for all functions in the project with the same name
2. Filter to only include functions decorated with `@injected` or `@instance`
3. Show a dropdown list if multiple matching functions are found
4. Navigate directly to the function if only one match is found

## Example Usage

```python
from pinjected import injected, instance

@instance
def database_connection(host, port):
    """Provides a database connection."""
    return connect_to_db(host, port)

@injected
def fetch_users(database_connection, /, user_id):  
    # Click on "database_connection" to navigate to the @instance function above
    return database_connection.query(user_id)
```

## Implementation Details

### Files Modified

1. **plugin.xml** - Added `gotoDeclarationHandler` extension registration
2. **InjectedGotoDeclarationHandler.kt** - Main handler implementation
3. **InjectedGotoDeclarationHandlerTest.kt** - Unit tests

### Key Features

- Supports clicking on parameter names in function signatures
- Supports clicking on parameter references within function bodies  
- Handles both `@injected` and `@instance` decorators
- Handles decorator variations: `@injected`, `@injected()`, `@injected(protocol=...)`
- Shows dropdown for multiple matches (PyCharm's built-in behavior)

## Building and Testing

```bash
cd ide-plugins/pycharm
./gradlew build
```

The tests can be run with:
```bash
./gradlew test
```

## Future Enhancements

- Support for navigating from type annotations to Protocol definitions
- Support for navigating to functions imported from other modules
- Integration with PyCharm's "Find Usages" feature