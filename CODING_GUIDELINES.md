# Coding Guidelines

## Dependency Injection Patterns

### Design Configuration
```python
# Basic design configuration
base_design = design(
    param1=value1,
    param2=value2
)

# Composing designs
final_design = base_design + design(
    implementation=specific_implementation
)
```

### Instance and Injected Decorators
```python
@instance
def provider_function():
    return specific_implementation

@injected
async def consumer_function(dependency: Type / arg1: str, arg2: int):
    # dependency is automatically injected, arg1 and arg2 are regular arguments
    result = await dependency.process(arg1, arg2)
```

### Async Patterns
- Prefix async functions with `a_`
- Use TaskGroup for concurrent operations
```python
async with TaskGroup() as tg:
    for item in items:
        tg.create_task(process_item(item))
```

### Best Practices
1. Class Methods and Dependency Injection
   - Pass injection targets as constructor parameters
   - Initialize dependencies during class instantiation
   - Avoid using @injected or @instance decorators on class methods

2. Design Composition
   - Use design() for configuration management
   - Compose designs using the + operator
   - Override specific implementations while keeping base configuration

3. Error Handling in Injected Code
   - Let errors propagate naturally through the dependency chain
   - Avoid catching exceptions unless specific handling is needed
   - Document expected exceptions in function signatures

4. Testing Injected Code
   - Use providers() context manager for testing specific implementations
   - Create test-specific designs for dependency configuration
   - Mock complex dependencies using the Design system


