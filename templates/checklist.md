# Code Review Checklist

First, copy this checklist to tasks/<datetime>-<taskname>/todo.md.
Then, update the checklist as you review the codebase.

## Planning and Architecture
- [ ] Create /tasks/<datetime>-<taskname>/architecture.md with clear protocols, class and function definitions
  * Document interfaces, class hierarchies, and function signatures without implementation details
  * Ensure the architecture supports modularity and separation of concerns
- [ ] Review architecture.md against coding guidelines
  * Check that the proposed design adheres to all coding principles
  * Identify potential violations before implementation begins
- [ ] Define inputs, outputs, and functionality clearly
  * Specify expected input formats, valid ranges, and edge cases
  * Document return types and potential error conditions
  * Clearly articulate the purpose and behavior of each component

## Function Design
- [ ] Ensure each function has a single responsibility
  * Functions should do one thing and do it well
  * Extract separate concerns into their own functions
- [ ] Keep functions under 50 lines of code
  * Split large functions into smaller, focused components
  * Improves readability and testability
- [ ] Check that functions return a single type or meaningful value
  * Consistent return types make code more predictable
  * Avoid returning different types based on conditions when possible
- [ ] Use dataclasses for complex return values with proper documentation
  * Create named structures instead of anonymous tuples or dictionaries
  * Document field meanings in class docstrings
- [ ] Limit function arguments (ideally ≤ 5)
  * Use dataclasses for parameter groups when more are needed
  * Excessive parameters often indicate a need for restructuring
- [ ] Avoid returning tuples with multiple semantic values
  * Creates implicit dependencies on position and count
  * Makes code less maintainable and more error-prone
- [ ] Ensure no mixing of side effects with computational logic
  * Functions should either compute values or perform actions, rarely both
  * Makes testing and reasoning about code much easier
- [ ] Avoid monolithic multi-purpose functions
  * Functions trying to do too much are harder to understand and maintain
  * Violates single responsibility principle

## Control Flow
- [ ] Limit to one loop per function (except when matching nested data structures)
  * Multiple loops often indicate a function is doing too much
  * Extract loop bodies into separate functions when appropriate
- [ ] Keep conditional nesting to maximum of two levels
  * Deep nesting makes code hard to read and reason about
  * Use guard clauses, early returns, or extracted functions instead
- [ ] Replace any `continue` statements with guard clauses or function extraction
  * Improves readability by reducing flow complexity
  * Use if/else or extract logic to separate functions
- [ ] Extract complex conditional expressions to functions
  * Encapsulate complex conditions behind meaningful function names
  * Improves readability and testability
- [ ] Eliminate deeply nested conditional statements
  * Use early returns, guard clauses, or polymorphism instead
  * Flatten logic where possible

## Data Structures and Immutability
- [ ] Use dataclasses for complex data structures
  * Provides clear structure with defined fields
  * Improves code readability and maintainability
- [ ] Make dataclasses immutable (frozen=True) when possible
  * Prevents unexpected mutations and side effects
  * Makes code more predictable and easier to reason about
- [ ] Add appropriate type annotations to all functions and variables
  * Clarifies expected types and improves IDE support
  * Catches type errors at development time
- [ ] Apply beartype decorator for runtime type validation
  * Verifies type correctness during execution
  * Catches type errors that static analysis might miss
- [ ] Avoid direct modification of shared data within functions
  * Creates unpredictable behavior and hard-to-find bugs
  * Return new values instead of modifying existing ones
- [ ] Eliminate use of global variables or state
  * Makes code harder to test and reason about
  * Pass dependencies explicitly as arguments instead
- [ ] Replace raw tuples/lists containing multiple semantic values
  * Use dataclasses with named fields for clarity
  * Improves code readability and maintainability

## Error Handling
- [ ] Use dedicated data classes for error information
  * Structured error information is more useful than strings
  * Allows for programmatic handling of error conditions
- [ ] Ensure try-except blocks re-raise exceptions unless specific handling is required
  * Don't swallow exceptions silently
  * Only catch exceptions you can meaningfully handle
- [ ] Avoid returning values from except blocks without raising exceptions
  * Transforms errors into silent failures
  * Makes bugs harder to detect and diagnose
- [ ] Limit `except Exception` usage to only when re-raising
  * Broad exception catching often hides real problems
  * Be specific about which exceptions to catch
- [ ] Raise exceptions instead of returning default values for undefined cases
  * Make errors explicit rather than implicit
  * Prevents incorrect assumptions downstream
- [ ] Limit try-except blocks to a maximum of 1 per function
  * Multiple exception handlers indicate a function is doing too much
  * Split complex error handling into separate functions
- [ ] Eliminate empty exception handlers
  * Silent failure is worse than explicit failure
  * At minimum, log the exception if you must catch it
- [ ] Avoid mixing error handling with normal flow logic
  * Separates concerns and improves readability
  * Makes both normal flow and error paths clearer

## Functional Programming
- [ ] Make functions pure (free of side effects, compute results based only on inputs)
  * Improves testability and predictability
  * Makes reasoning about code behavior much easier
- [ ] Return new values rather than modifying existing data structures
  * Prevents unexpected side effects
  * Follows immutability principles
- [ ] Pass required services as arguments explicitly
  * Makes dependencies clear and avoids hidden coupling
  * Improves testability by allowing dependency substitution
- [ ] Avoid overuse of lambda and reduce
  * Can reduce readability in Python
  * Use comprehensions or explicit functions when appropriate
- [ ] Use returns.safe appropriately for safer code
  * Provides better error handling for pure functions
  * Makes error flow more explicit

## Code Structure
- [ ] Separate UI, business logic, and data access
  * Promotes clean separation of concerns
  * Makes components independently testable and maintainable
- [ ] Implement dependency injection via constructor or function parameters
  * Makes dependencies explicit
  * Improves testability through substitution
- [ ] Make dependencies explicit (inject rather than instantiate directly)
  * Avoids hidden coupling between components
  * Improves testability and flexibility
- [ ] Avoid UI operations or data persistence within business logic
  * Violates separation of concerns
  * Makes business logic harder to test and reuse
- [ ] Eliminate tightly coupled class dependencies
  * Use interfaces or protocols instead of concrete classes
  * Enhances modularity and testability

## Naming Conventions
- [ ] Start function names with verbs (get_*, create_*, build_*, is_*)
  * Clearly indicates the function's action or purpose
  * Makes code more readable and self-documenting
- [ ] Use specific, clear variable names (avoid `data` or `result`)
  * Names should indicate what data represents
  * Improves code readability and maintenance
- [ ] Use concise nouns or noun phrases for module names
  * Reflects the module's content or responsibility
  * Makes imports more intuitive
- [ ] Avoid single-character variable names (except loop counters)
  * Reduces code readability
  * Makes searching and refactoring more difficult
- [ ] Avoid abbreviations (unless well-established)
  * Can cause confusion and reduce readability
  * Saves minimal typing but costs in comprehension
- [ ] Eliminate overly abstract naming
  * Names should reflect specific purpose
  * Avoid manager, processor, handler without context

## Logging and Debugging
- [ ] Use loguru instead of print statements for logging
  * Provides structured logging with levels and formatting
  * Allows configuration of log destinations and filtering
- [ ] Verify no print() statements exist in the code
  * Print statements lack context and configuration
  * Not appropriate for production code

## Complex Operations
- [ ] Avoid performing multiple types of operations in a single loop
  * Mixes concerns and reduces clarity
  * Extract different operations to separate functions
- [ ] Split complex operations into pure functions
  * Separates concerns and improves testability
  * Makes each step independently verifiable
- [ ] Implement generators for multi-step operations
  * Allows for streaming processing of large datasets
  * Separates generation from consumption

## Type Checking and Asynchronous Functions
- [ ] Use beartype decorator for runtime type validation
  * Catches type errors at runtime
  * Provides additional safety beyond static typing
- [ ] Use `Result[T]` from returns.result for success/failure types
  * Makes error handling explicit in return types
  * Enforces handling of potential failures
- [ ] Prefix asynchronous functions with `a_`
  * Clearly identifies async functions by convention
  * Prevents confusion about execution model

## Testing
- [ ] Ensure all tests pass
  * Verification that implementation meets expectations
  * No changes should break existing functionality
- [ ] Verify no test hacks/cheats have been introduced
  * Tests should genuinely validate behavior
  * Avoid modifications that artificially make tests pass
- [ ] Check both test implementation and logic implementation
  * Tests themselves should follow coding guidelines
  * Both production code and test code should be well-crafted

## Final Review
- [ ] Conduct final review against all coding guidelines
  * Systematic check of all guidelines
  * Ensure no principles were overlooked during development
- [ ] Run typechecking and linting tools
  * Catch common errors and style issues automatically
  * Ensure consistent code quality
- [ ] Verify tests pass after all changes
  * Final verification of correctness
  * Ensures no regressions were introduced