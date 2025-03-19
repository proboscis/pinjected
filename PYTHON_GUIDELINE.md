
## 1. Function Design
### Core Principles
* **Single Responsibility**: Each function should have one clearly defined responsibility
* **Maximum Length**: Functions should not exceed 50 lines of code
* **Return Values**: Functions should return a single type or semantically meaningful value
* **Complex Return Values**: For complex return values (tuples, dictionaries), define a dataclass and document its contents in docstring
* **Arguments**: Ideally 5 or fewer (use data classes for more complex parameter sets)

### Prohibited Practices
* ✘ Returning tuples with multiple semantic values
* ✘ Mixing side effects with computational logic
* ✘ Monolithic multi-purpose functions

## 2. Control Flow
### Core Principles
* **Loop Limitation**: Generally one loop per function
    * **Exception**: Two nested loops are acceptable only when matching nested data structures
* **Nesting Depth**: Maximum of two levels for conditional statements


### Prohibited Practices
* ✘ Using `continue` statements (replace with guard clauses or function extraction)
* ✘ Complex conditional expressions (extract to functions)
* ✘ Deeply nested conditional statements

## 3. Data Structures and Immutability
### Core Principles
* **Data Classes**: Use dataclasses for complex data structures
* **Immutability**: Data classes should be immutable with frozen=True when possible
* **Type Annotations**: Add appropriate type annotations to all functions and variables
* **Runtime Type Checking**: Use beartype decorator for runtime type validation

### Prohibited Practices
* ✘ Direct modification of shared data within functions
* ✘ Use of global variables or state
* ✘ Raw tuples/lists containing multiple semantic values

## 4. Error Handling
### Core Principles
* **Dedicated Error Types**: Express error information using dedicated data classes
* **Exception Handling**: When using try-except, always re-raise exceptions unless specific handling is required.  except blocks with only logging is strictly forbidden.
* **Return in Except Block** Never return without raising an exception in except block, unless it is logically required. raising is always better than silently returning or providing default value.
* **Broad Exception Catching**: `except Exception` is acceptable only when re-raising the exception
* **No Default Value for Undefined Case**: Do not create a default value to be returned on catching exception unless instructed to do so. Raising exceptions is always better than returning a default value when unknown situation occurs.
* **No try-except** Do not use try-except block unless it is absolutely necessary. The less try-except, the better. Any unexpected error should be propagated to the caller.  try-catch can be introduced at most 1 per a function.

### Prohibited Practices
* ✘ Empty exception handlers
* ✘ Overly broad exception catching (e.g., `except Exception`)
* ✘ Mixing error handling with normal flow logic


## 5. Functional Programming
### Core Principles
* **Pure Functions**: Functions should be free of side effects and compute results based only on inputs
* **Create New Values**: Return new values rather than modifying existing data structures
* **Explicit Dependencies**: Pass required services as arguments explicitly

### Considerations
* Consider Python-specific constraints (avoid overuse of lambda and reduce)
* Use tools like returns.safe appropriately for safer code

## 6. Code Structure
### Core Principles
* **Layer Separation**: Clearly separate UI, business logic, and data access
* **Dependency Injection**: Use constructor or function parameter injection, emphasizing single responsibility
* **Explicit Dependencies**: Inject dependencies rather than instantiating them directly

### Prohibited Practices
* ✘ UI operations or data persistence within business logic
* ✘ Tightly coupled class dependencies

## 7. Naming Conventions
### Core Principles
* **Function Names**: Start with verbs (get_*, create_*, build_*, is_*)
* **Variable Names**: Use specific, clear names (avoid ambiguous names like `data` or `result`)
* **Module Names**: Use concise nouns or noun phrases

### Prohibited Practices
* ✘ Single-character variable names (except for loop counters)
* ✘ Abbreviations (unless well-established)
* ✘ Overly abstract naming

## 8. Logging and Debugging
### Core Principles
* **Use loguru**: Always use loguru instead of print statements for logging
* **No logging restrictions**: Logging can be used at any layer as needed
* **Never use print**: Use of print() is strictrly forbidden.

## 9. Complex Operations
### Core Principles
* **Operation Segregation**: Don't perform multiple types of operations in a single loop
* When multiple operation steps seem necessary:
    * Split each step into pure functions
    * Implement generators responsible for each step

## 10. Type Checking and Asynchronous Functions
### Core Principles
* **Runtime Type Checking**: Use beartype decorator for runtime type validation
* **Result Type Usage**: Use `Result[T]` from returns.result to explicitly specify success and failure types
* **Async Function Naming**: Prefix asynchronous functions with `a_` (e.g., `a_fetch_data`)

## 11. No hacking of pytest:
A pytest cannot be cheated, hacked, or skipped to finish the implementation. You must specifically check if specific hack or cheating is introduced into neither test implementation, nor the logic implemention.

# Git Interaction Guideline

## bumping version
When bumping version, compose CHANGELOG.md by summarizing diffs and history, then commit with summary and push.

## publishing
When publishing a library, make sure the current main is tagged and CHANGELOG.md is up to date, and pushed.
