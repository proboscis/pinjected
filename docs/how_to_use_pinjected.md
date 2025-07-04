# Pinjected: Usage Guide for AI

This document summarizes information for AI to effectively use "Pinjected", a Dependency Injection library for Python.

## 1. Overview of Pinjected

Pinjected is a Python Dependency Injection (DI) library designed for research and development. It enables "combining multiple Python objects to create a final object" through automatic dependency management. It was developed to solve problems with traditional configuration management and code structure (dependency on large cfg objects, proliferation of if branches, testing difficulties, etc.).

### 1.1 Key Features

- **Intuitive dependency definition**: Pythonic dependency definition using `@instance` and `@injected` decorators
- **Key-value style dependency composition**: Concise dependency assembly using the `design()` function
- **Flexible parameter overrides from CLI**: Change dependencies and parameters from the command line at runtime
- **Easy management of multiple entry points**: Define multiple executable Injected objects in the same file
- **IDE integration**: Development support through plugins for VSCode and PyCharm
- **Async support**: Parallel dependency resolution with asyncio integration
- **Dependency graph visualization**: Visualize dependencies with the `describe` command
- **Python 3.10+ support**: Leverages latest Python features

### 1.2 Comparison with Traditional Methods

Traditional configuration management tools like OmegaConf and Hydra had the following issues:

- Overall dependency on cfg objects
- Proliferation of branching logic
- Difficulty with unit testing and partial debugging
- God class problems and scalability limitations
- Complexity of manual dependency construction

Pinjected solves these problems and achieves a more flexible and reusable code structure.

### 1.3 Installation

```bash
pip install pinjected
```

## 2. Basic Features

### 2.1 @instance Decorator

The `@instance` decorator defines "object providers" in dependency resolution. All function arguments are treated as dependency parameters, and the return value is provided as an instance.

```python
from pinjected import instance

# Model definition example
@instance
def model__simplecnn(input_size, hidden_units):
    return SimpleCNN(input_size=input_size, hidden_units=hidden_units)

# Dataset definition example
@instance
def dataset__mnist(batch_size):
    return MNISTDataset(batch_size=batch_size)

# Async provider example
@instance
async def async_database_connection(host, port):
    conn = await asyncpg.connect(host=host, port=port)
    return conn
```

**Important characteristics**:
- Behaves like a singleton within the same object graph
- Supports async functions (automatically awaited)
- All arguments are injected as dependencies

### 2.2 @injected Decorator

The `@injected` decorator is a feature for defining functions that have both dependency-injected arguments and runtime-passed arguments. This allows creating partially dependency-resolved functions.

The `@injected` decorator can separate function arguments into "arguments to be injected" and "arguments to be specified at call time". Arguments to the left of `/` are injected as dependencies, and arguments to the right are passed at runtime.

#### Best Practice: Always Define and Use Protocol

**Important**: When implementing `@injected` functions, you should always define a Protocol for the function interface and specify it using the `protocol` parameter. This provides better type safety, IDE support, and makes your code more maintainable.

```python
from typing import Protocol
from pinjected import injected

# Step 1: Define the Protocol
class TextGeneratorProtocol(Protocol):
    def __call__(self, prompt: str) -> str: ...

# Step 2: Implement with protocol parameter
@injected(protocol=TextGeneratorProtocol)
def generate_text(llm_model, /, prompt: str) -> str:
    # llm_model is injected from DI
    # prompt can be passed any value at runtime
    return llm_model.generate(prompt)

# Step 3: Use with type annotation
@injected
def process_document(
    text_generator: TextGeneratorProtocol,  # Type hint with protocol
    /, 
    document: str
) -> str:
    # IDE knows text_generator accepts str and returns str
    summary = text_generator(f"Summarize: {document}")
    return summary
```

Benefits of using Protocol:
- **Type Safety**: Type checkers can verify correct usage
- **IDE Support**: Full autocomplete and parameter hints
- **Documentation**: Protocol serves as clear contract for dependencies
- **Refactoring**: Easier to find all usages and update interfaces

#### Important: Calling Other @injected Functions

When you want to call another `@injected` function from within an `@injected` function, you must declare it as a dependency by placing it before the `/` separator. This is because within `@injected` functions, you're building an AST (Abstract Syntax Tree), not executing functions directly.

```python
from typing import Protocol
from pathlib import Path

# Define Protocols for each function
class DatasetPreparerProtocol(Protocol):
    async def __call__(self, dataset_path: Path) -> Dataset: ...

class DatasetUploaderProtocol(Protocol):
    async def __call__(self, dataset: Dataset, name: str) -> str: ...

class ConvertAndUploadProtocol(Protocol):
    async def __call__(self, dataset_path: Path) -> str: ...

# Implement with protocols
@injected(protocol=DatasetPreparerProtocol)
async def a_prepare_dataset(logger, /, dataset_path: Path) -> Dataset:
    # Prepare dataset logic
    return prepared_dataset

@injected(protocol=DatasetUploaderProtocol)
async def a_upload_dataset(logger, /, dataset: Dataset, name: str) -> str:
    # Upload dataset logic
    return artifact_path

# INCORRECT - This won't work
@injected(protocol=ConvertAndUploadProtocol)
async def a_convert_and_upload_wrong(logger, /, dataset_path: Path):
    # This will fail because a_prepare_dataset is not declared as a dependency
    dataset = await a_prepare_dataset(dataset_path)  # Error!
    artifact = await a_upload_dataset(dataset, "my-dataset")  # Error!
    return artifact

# CORRECT - Declare @injected functions as dependencies with Protocol types
@injected(protocol=ConvertAndUploadProtocol)
async def a_convert_and_upload(
    logger, 
    a_prepare_dataset: DatasetPreparerProtocol,  # Declare with Protocol type
    a_upload_dataset: DatasetUploaderProtocol,   # Declare with Protocol type
    /, 
    dataset_path: Path
) -> str:
    # Now you can call them (building AST, not executing)
    # Note: Do NOT use 'await' - you're building an AST
    dataset = a_prepare_dataset(dataset_path)
    artifact = a_upload_dataset(dataset, "my-dataset")
    return artifact
```

**Key points**:
- `@injected` functions must be declared as dependencies (before `/`) when used inside other `@injected` functions
- Do NOT use `await` when calling `@injected` functions inside other `@injected` functions
- You're building an AST (computation graph), not executing the functions directly

### 2.3 design() Function

The `design()` function creates a "blueprint" that groups dependency objects and parameters in key=value format. Multiple designs can be composed using the `+` operator.

```python
from pinjected import design

# Base design
base_design = design(
    learning_rate=0.001,
    batch_size=128,
    image_size=32
)

# Model-specific design
mnist_design = base_design + design(
    model=model__simplecnn,
    dataset=dataset__mnist,
    trainer=Trainer
)

# Create graph from design and execute
graph = mnist_design.to_graph()
trainer = graph['trainer']
trainer.train()
```

### 2.4 __design__ (__meta_design__ is deprecated)

`__design__` is the recommended configuration method to use in `__pinjected__.py` files. `__meta_design__` is deprecated and should not be used in new code.

```python
# Recommended way in __pinjected__.py
__design__ = design(
    learning_rate=0.001,
    batch_size=128,
    model=model__simplecnn
)

# Legacy way (deprecated - do not use)
# __meta_design__ = design(
#     overrides=mnist_design
# )
```

## 3. Execution Methods and CLI Options

### 3.1 Basic Execution Method

Pinjected is executed in the format `python -m pinjected run <path.to.target>`.

```bash
# Example of executing run_train
python -m pinjected run example.run_train

# Example of visualizing dependency graph
python -m pinjected describe example.run_train
```

### 3.2 Parameter Overrides

You can override the design by specifying individual parameters or dependency items using the `--` option.

```bash
# Example of overriding batch_size and learning_rate
python -m pinjected run example.run_train --batch_size=64 --learning_rate=0.0001
```

### 3.3 Dependency Object Replacement

You can dynamically replace dependency objects by specifying paths enclosed in `{}`.

```bash
# Example of replacing model and dataset
python -m pinjected run example.run_train --model='{example.model__another}' --dataset='{example.dataset__cifar10}'

# Example of switching LLM provider
python -m pinjected run some.llm.module.chat --llm="{some.llm.module.llm_openai}" "hello!"
```

### 3.4 Design Switching with overrides

You can specify a pre-defined design with the `--overrides` option.

```bash
# Example of executing with mnist_design
python -m pinjected run example.run_train --overrides={example.mnist_design}
```

## 4. Advanced Features

### 4.1 Local Configuration with .pinjected.py

The `.pinjected.py` file can be placed in the current directory or home directory to manage project-specific or user-specific settings. It's suitable for managing sensitive information or path settings that differ per user, such as API keys and local paths.

```python
# .pinjected.py (current directory or ~/.pinjected.py)
from pinjected import design

__design__ = design(
    openai_api_key = "sk-xxxxxx_your_secret_key_here",
    cache_dir = "/home/user/.cache/myproject",
    database_url = "postgresql://localhost:5432/mydb"
)
```

### 4.2 Design Override with with Statement

You can perform temporary overrides using the `with` statement. This allows you to use different settings only within a specific context.

```python
from pinjected import design, instance

# Default trainer
@instance
def trainer(learning_rate, batch_size):
    return Trainer(lr=learning_rate, bs=batch_size)

# Normal execution
default_design = design(learning_rate=0.001, batch_size=32)

# Temporary override
with design(batch_size=64):  # Temporarily change batch_size to 64
    # Within this with block, batch_size is resolved as 64
    graph = default_design.to_graph()
    trainer_64 = graph['trainer']  # Created with batch_size=64
```

### 4.3 Injected and IProxy

#### 4.3.1 Basic Concepts

- **Injected**: Object representing "unresolved dependencies"
- **IProxy**: Proxy class for manipulating Injected with Pythonic DSL

```python
from pinjected import Injected

a = Injected.by_name('a')  # Injected object representing dependency value named 'a'
b = Injected.by_name('b')

# Convert to IProxy for arithmetic operations
a_proxy = a.proxy
b_proxy = b.proxy
sum_proxy = a_proxy + b_proxy
```

#### 4.3.2 Functional Composition with map/zip

```python
# Transformation with map
a_plus_one = a.map(lambda x: x + 1)

# Combining multiple dependency values with zip
ab_tuple = Injected.zip(a, b)  # Tuple of (resolved_a, resolved_b)
```

#### 4.3.3 Injected.dict() and Injected.list()

```python
# Group in dictionary format
my_dict = Injected.dict(
    learning_rate=Injected.by_name("learning_rate"),
    batch_size=Injected.by_name("batch_size")
)

# Group in list format
my_list = Injected.list(
    Injected.by_name("model"),
    Injected.by_name("dataset"),
    Injected.by_name("optimizer")
)
```

#### 4.3.4 injected() Function

The `injected()` function has two different usage patterns:

1. **Use as decorator** (`@injected`): Apply to functions to separate dependency-injected arguments from runtime arguments
2. **Use as function** (`injected(MyClass)`): Apply to classes or constructors to create dependency-injectable factory functions

```python
from pinjected import injected

# The following are equivalent
a_proxy = Injected.by_name("a").proxy
a_proxy = injected("a")

# Example of defining injection function for a class
class MyClass:
    def __init__(self, dependency1, dependency2, non_injected_arg):
        self.dependency1 = dependency1
        self.dependency2 = dependency2
        self.non_injected_arg = non_injected_arg

# Handling parameter names starting with `_`
class AnotherClass:
    def __init__(self, _a_system, _logger, normal_arg):
        # `_a_system` is injected with dependency value named `a_system`
        # `_logger` is injected with dependency value named `logger`
        self.a_system = _a_system
        self.logger = _logger
        self.normal_arg = normal_arg

# Example using dataclass
from dataclasses import dataclass

@dataclass
class DataclassExample:
    # Parameters to be dependency-injected
    _a_system: callable
    _logger: object
    _storage_resolver: object

    # Non-injected parameters
    project_name: str
    output_dir: Path = Path("/tmp")
    options: List[str] = field(default_factory=list)

# Define injection function for MyClass
new_MyClass = injected(MyClass)

# Usage example
# Create instance passing only non-injected arguments
# dependency1 and dependency2 are automatically injected
my_instance: IProxy = new_MyClass(non_injected_arg="value")

# Define injection function for dataclass
new_DataclassExample = injected(DataclassExample)
# Usage example
data_example: IProxy = new_DataclassExample(project_name="my-project", output_dir=Path("/custom/path"))

# Note: You don't need to wrap with injected() twice like below
# my_instance: IProxy = injected(new_MyClass)(non_injected_arg="value") # Unnecessary double injection
```

#### 4.3.4 DSL-style Notation

```python
# Path operations
cache_subdir = injected("cache_dir") / "subdir" / "data.pkl"

# Index access
train_sample_0 = injected("dataset")["train"][0]
```

## 5. Use Case Examples

### 5.1 Model Loading and Runtime Parameters

When dealing with large models like Large Language Models (LLMs) or diffusion models (Stable Diffusion), you often want to load the model once and reuse it while changing input/output parameters each time.

```python
@instance
def llm_client(openai_api_key):
    openai.api_key = openai_api_key
    return openai.ChatCompletion

@injected
def generate_text(llm_client, /, prompt: str):
    # llm_client is injected via DI
    # prompt is a parameter specified at runtime
    response = llm_client.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message["content"]
```

### 5.2 Cache Path and External Resource Path Management

You can flexibly handle resource paths that differ by environment.

```python
@instance
def cache_dir():
    # This value can be overridden in ~/.pinjected.py
    return Path("/tmp/myproject_cache")

@instance
def embeddings_cache_path(cache_dir):
    # Automatically changes when cache_dir changes
    return cache_dir / "embeddings.pkl"
```

### 5.3 Configuration Variation Generation and Reuse

Convenient when trying many hyperparameter searches or conditional experiments.

```python
# Base design
base_design = design(
    learning_rate=0.001,
    batch_size=128,
    model_identifier="model_base"
)

# Learning rate variations
conf_lr_001 = base_design + design(learning_rate=0.001)
conf_lr_01 = base_design + design(learning_rate=0.01)
conf_lr_1 = base_design + design(learning_rate=0.1)

# Model variations
model_resnet = design(model=model__resnet)
model_transformer = design(model=model__transformer)

# Combinations
conf_lr_001_resnet = conf_lr_001 + model_resnet
conf_lr_001_transformer = conf_lr_001 + model_transformer
```

## 6. IDE Support

### 6.1 VSCode/PyCharm Plugins

- **One-click execution**: Functions with `@injected`/`@instance` decorators or variables with `IProxy` type annotations can be executed with one click
- **Dependency visualization**: Visually display dependency graphs in the browser

### 6.2 Execution Example

```python
# Execution button appears when IProxy annotation is added
check_dataset: IProxy = injected('dataset')[0]
```

## 7. Implementation Patterns and Best Practices

### 7.1 Test Structure and Recommended Practices

In Pinjected projects, the following test structure is recommended:

1. Test files should be placed in the format `<repo_root>/tests/test*.py`
2. Test functions should be defined using the `@injected_pytest` decorator
3. Functions or objects to be tested should be directly injected as arguments to test functions

```python
# <repo_root>/tests/test_example.py
from pinjected.test import injected_pytest
@injected_pytest()
def test_some_function(some_function):
    # some_function is provided through dependency injection
    return some_function("test_input")
```

### 7.2 Dependency Naming Conventions

The following patterns are recommended for dependency naming to avoid collisions:

- Use module names or categories as prefixes: `model__resnet`, `dataset__mnist`
- For library use, include package name: `my_package__module__param1`

### 7.3 Design Considerations

- **Avoid dependency key collisions**: Be careful not to define the same named key in different places
- **Split dependencies at appropriate granularity**: Dependencies that are too large reduce reusability
- **Consider testability**: Design for easy unit testing and partial execution

## 8. Async Support

### 8.1 Async Providers

Pinjected fully supports async functions:

```python
@instance
async def async_database(host, port):
    conn = await asyncpg.connect(host=host, port=port)
    return conn

@injected  
async def async_query(async_database, /, query: str):
    result = await async_database.fetch(query)
    return result
```

### 8.2 Parallel Dependency Resolution

Dependencies are collected in parallel, and provider functions are called in an async context. This allows efficient resolution of multiple dependencies including I/O operations.

### 8.3 Resolver Selection

- `to_graph()`: Returns blocking resolver (uses `asyncio.run()` internally)
- `to_resolver()`: Returns async resolver (use with await)

## 9. Notes and Limitations

### 9.1 Test Automation with injected_pytest

Pinjected provides the `injected_pytest` decorator, which can convert test functions using pinjected into test functions executable with pytest.

#### 9.1.1 Basic Usage

```python
from pinjected.test import injected_pytest
from pinjected import design

# Basic usage
@injected_pytest()
def test_some_function(some_dependency):
    # some_dependency is provided through dependency injection
    return some_dependency.do_something()

# When overriding design
test_design = design(
    some_dependency=MockDependency()
)

@injected_pytest(test_design)
def test_with_override(some_dependency):
    # some_dependency is injected with MockDependency specified in test_design
    return some_dependency.do_something()
```

#### 9.1.2 Internal Operation

The `injected_pytest` decorator performs the following operations:

1. Automatically obtains the caller's file path
2. Wraps the test function with `@instance` to convert it into a dependency-injectable object
3. Sets up the execution environment using asyncio to enable tests containing async processing
4. Resolves dependencies by overriding with the specified design

#### 9.1.3 Actual Usage Example

```python
import pytest
from pinjected.test import injected_pytest
from pinjected import design, instances

# Mock logger for testing
class MockLogger:
    def __init__(self):
        self.logs = []

    def info(self, message):
        self.logs.append(message)

# Design for testing
test_design = design()
test_design += instances(
    logger=MockLogger()
)

# Create test function using injected_pytest
@injected_pytest(test_design)
def test_logging_function(logger):
    logger.info("Test message")
    return "Test successful"
```

#### 9.1.4 Differences from Regular pytest Tests

There are the following differences between tests using the `injected_pytest` decorator and regular pytest tests:

- **Dependency injection**: With `injected_pytest`, test function arguments are automatically provided through dependency injection
- **Design override**: Can override with specific design at test execution time
- **Async support**: Tests containing async processing can be easily executed
- **Meta context**: Automatically collects meta context from the caller's file path

#### 9.1.5 Example of Tests with Async Processing

Since `injected_pytest` uses `asyncio.run()` internally, you can easily write tests containing async processing:

```python
from pinjected.test import injected_pytest
from pinjected import design, instances
import asyncio

# Mock service performing async processing
class AsyncMockService:
    async def fetch_data(self):
        await asyncio.sleep(0.1)  # Simulate async processing
        return {"status": "success"}

# Design for testing
async_test_design = design()
async_test_design += instances(
    service=AsyncMockService()
)

# Test containing async processing
@injected_pytest(async_test_design)
async def test_async_function(service):
    # service is provided through dependency injection
    # Async methods can be directly awaited
    result = await service.fetch_data()
    assert result["status"] == "success"
    return "Async test successful"
```

#### 9.1.6 Notes and Best Practices

Notes and best practices when using `injected_pytest`:

1. **Test isolation**: Design each test to be executable independently
2. **Utilize mocks**: Replace external dependencies with mocks to increase test reliability
3. **Reuse designs**: Create and reuse common test designs
4. **Release async resources**: In async tests, ensure resources are properly released
5. **Error handling**: Write tests considering behavior when exceptions occur

```python
# Example of creating and reusing common test design
base_test_design = design(
    logger=MockLogger(),
    config=test_config
)
```

#### 9.1.7 Example of Tests with Complex Dependencies

In actual projects, complex test cases with multiple dependencies may be needed. Here's an example of a test with multiple dependencies including database, cache, and logger:

```python
from pinjected.test import injected_pytest
from pinjected import design, instances, injected

# Mock database
class MockDatabase:
    def __init__(self):
        self.data = {}

    def get(self, key):
        return self.data.get(key)

    def set(self, key, value):
        self.data[key] = value

# Mock cache
class MockCache:
    def __init__(self):
        self.cache = {}

    def get(self, key):
        return self.cache.get(key)

    def set(self, key, value, ttl=None):
        self.cache[key] = value

# Function to test
@injected
def fetch_user_data(database, cache, logger, /, user_id: str):
    # Check cache
    cached_data = cache.get(f"user:{user_id}")
    if cached_data:
        logger.info(f"Cache hit for user {user_id}")
        return cached_data

    # Fetch from database
    logger.info(f"Cache miss for user {user_id}, fetching from database")
    data = database.get(f"user:{user_id}")
    if data:
        # Save to cache
        cache.set(f"user:{user_id}", data, ttl=3600)
    return data

# Complex test case
@injected_pytest(design(
    database=MockDatabase(),
    cache=MockCache(),
    logger=MockLogger()
))
def test_fetch_user_data_cache_miss(fetch_user_data):
    # Set up test data
    user_id = "user123"
    user_data = {"name": "Test User", "email": "test@example.com"}
    database.set(f"user:{user_id}", user_data)

    # Execute function (cache miss case)
    result = fetch_user_data(user_id)

    # Verify
    assert result == user_data
    assert cache.get(f"user:{user_id}") == user_data
    assert any("Cache miss" in log for log in logger.logs)
```

#### 9.1.8 Note: Compatibility with pytest Fixtures

`injected_pytest` is not compatible with pytest fixtures (`@pytest.fixture`). Instead of using pytest fixtures, it's recommended to provide test data and dependencies using Pinjected's dependency injection mechanism.

```python
# Incorrect usage (does not work)
@pytest.fixture
def test_data():
    return {"key": "value"}
```

### 9.2 Learning Cost and Impact on Development System

- Team members need to get used to DI and DSL-like notation
- Establishing common understanding is important

### 9.3 Debugging and Error Tracking

- Since dependency resolution is deferred, it may be difficult to understand when errors occur
- Stack traces can become complex

### 9.4 Maintainability and Scale

- Dependency key management can become complex in large projects
- Variation management may become enormous

### 9.5 Notes on Global Variable Injection

Global variables (including `test_*` variables for testing) are not injected just by defining them globally. The following points need attention:

- Just defining as a global variable does not make it a target for pinjected's dependency resolution
- Functions decorated with `@injected` or `@instance` are injected by function name, but global variables are different
- To inject global variables, you need to explicitly inject them using `__design__` (`__meta_design__` is deprecated)

```python
# Just defining as a global variable like below doesn't inject it
my_global_var = some_function(arg1="value")  # IProxy object

# Correct method: Explicitly inject using __design__ (in __pinjected__.py)
__design__ = design(
    my_global_var=some_function(arg1="value")
    # Tests are recommended to use @injected_pytest
)

# Old method (deprecated - do not use __meta_design__)
# __meta_design__ = design(
#     overrides=design(
#         my_global_var=some_function(arg1="value")
#     )
# )
```

### 9.6 Usage of __design__ (__meta_design__ is deprecated)

When using `__design__`, define it in the `__pinjected__.py` file as follows:

```python
# In __pinjected__.py
__design__ = design(
    key1=value1,
    key2=value2
)
```

**Important**: `__meta_design__` is deprecated. Always use `__design__` in new code.

If you find `__meta_design__` in old code, migrate as follows:

```python
# Deprecated (do not use)
# __meta_design__ = design(
#     overrides=design(key1=value1, key2=value2)
# )

# Recommended method
__design__ = design(
    key1=value1,
    key2=value2
)
```

### 9.7 Types and Usage of @instance and @injected

From a type perspective, `@instance` and `@injected` can be distinguished as follows:

- **`@instance`**: Returns `IProxy[T]`
  - `T` is the type of the function's return value
  - IProxy object representing a dependency-resolved "instance"
  - Cannot be called as a function

- **`@injected`**: Returns `IProxy[Callable[[non_injected], T]]`
  - IProxy object representing a dependency-resolvable "function"
  - Can be called by passing non-injected arguments

The following points need attention:

1. **Functions defined with `@instance` cannot be called directly**:
```python
@instance
def my_instance(dep1, dep2) -> SomeClass:
    return SomeClass(dep1, dep2)

# Type of my_instance: IProxy[SomeClass]

# Incorrect usage (direct call)
result = my_instance(arg1, arg2)  # Error!
```

2. **The result of calling `@injected` functions is also an `IProxy` object**:
```python
@injected
def my_function(dep1, dep2, /, arg1: str, arg2: int) -> Result:
    return Result(dep1, dep2, arg1, arg2)

# Type of my_function: IProxy[Callable[[str, int], Result]]

# Type of call result
f: IProxy[Callable[[str, int], Result]] = my_function
y: IProxy[Result] = f("value", 42)  # Call result is also IProxy
```

3. **Functions defined with `@injected` can be called by passing non-injected arguments**:
```python
@injected
def my_function(dep1, dep2, /, arg1: str, arg2: int) -> Result:
    return Result(dep1, dep2, arg1, arg2)

# Type of my_function: IProxy[Callable[[str, int], Result]]

# Correct usage
result = my_function("value", 42)  # OK
```

4. **When applying `injected()` to a class**:
```python
class MyClass:
    def __init__(self, dep1, dep2, non_injected_arg: str):
        self.dep1 = dep1
        self.dep2 = dep2
        self.non_injected_arg = non_injected_arg

# Type of new_MyClass: IProxy[Callable[[str], MyClass]]
new_MyClass = injected(MyClass)

# Correct usage
# Type of my_instance: IProxy[MyClass]
my_instance = new_MyClass("value")  # OK
```

Understanding these type differences makes the usage of `@instance` and `@injected` clearer.

### 9.8 Common Mistakes and Recommended Practices

Here are common mistakes when using pinjected and their recommended practices:

#### 1. Direct Call of `@instance` Functions

```python
# Incorrect way
@instance
def my_instance(dep1, dep2) -> MyClass:
    return MyClass(dep1, dep2)

# Mistake: Calling @instance function directly
result = my_instance(arg1, arg2)  # Error!

# Recommended way
# @instance returns IProxy[T], so it cannot be called directly
# Use __design__ for setting dependencies (in __pinjected__.py)
__design__ = design(
    # Dependency settings
    my_dependency=my_instance
)

# Deprecated (__meta_design__ should not be used)
# __meta_design__ = design(
#     overrides=design(
#         my_dependency=my_instance
#     )
# )
```

#### 2. Incomplete Use of `@injected` Functions

```python
# Incorrect way
@injected
def my_function(dep1, dep2, /, arg1: str, arg2: int) -> Result:
    return Result(dep1, dep2, arg1, arg2)

# Mistake: Just assigning @injected function to variable without calling
my_result = my_function  # Incomplete

# Recommended way
# @injected functions need to be called
my_result = my_function("value", 42)  # OK
```

#### 3. Wrong Position of `/`

```python
# Incorrect way
@injected
def my_function(dep1, /, dep2, arg1: str):  # dep2 is on the right side of /
    return Result(dep1, dep2, arg1)

# Recommended way
@injected
def my_function(dep1, dep2, /, arg1: str):  # All dependencies are on the left side of /
    return Result(dep1, dep2, arg1)
```

#### 4. Test Variable Definition Method

Tests are recommended to be defined using the `@injected_pytest` decorator.

```python
# Recommended way: Test using @injected_pytest
@injected_pytest()
def test_my_function(my_function):
    return my_function("test_input")

```

# Pinjected Naming Convention Best Practices

## 1. Naming Convention for @instance

The `@instance` decorator defines "providers" of dependency objects.

### Recommended Patterns
- **Noun form**: `config`, `database`, `logger`
- **Adjective_noun**: `mysql_connection`, `production_settings`
- **Category__specific_name**: `model__resnet`, `dataset__mnist`

### Patterns to Avoid
- ~~Forms containing verbs~~: `setup_database`, `initialize_config`
- ~~Verb phrases~~: `get_connection`, `build_model`

### Reason
`@instance` expresses "what to provide", so noun form is appropriate. Verbs lead to misunderstanding of "what to do".

### Examples
```python
# Good example
@instance
def rabbitmq_connection(host, port, credentials):
    return pika.BlockingConnection(...)

# Good example
@instance
def topic_exchange(channel, name):
    channel.exchange_declare(...)
    return name

# Bad example
@instance
def setup_database(host, port, username):  # × Contains verb
    return db.connect(...)
```

## 2. Naming Convention for @injected and Protocols

The `@injected` decorator defines partially dependency-resolved "functions". Always define a corresponding Protocol.

### Recommended Patterns
- **Function names**: 
  - **Verb form**: `send_message`, `process_data`, `validate_user`
  - **Verb_object**: `create_user`, `update_config`
  - **`a_` prefix for async functions (async def)**: `a_fetch_data`, `a_process_queue`
- **Protocol names**:
  - **Add `Protocol` suffix**: `SendMessageProtocol`, `ProcessDataProtocol`
  - **Match the function purpose**: `UserValidatorProtocol`, `DataFetcherProtocol`

### Examples
```python
from typing import Protocol

# Good example - synchronous function with Protocol
class MessageSenderProtocol(Protocol):
    def __call__(self, queue: str, message: str) -> bool: ...

@injected(protocol=MessageSenderProtocol)
def send_message(channel, /, queue: str, message: str) -> bool:
    # ...

# Good example - with complex parameters
class ImageProcessorProtocol(Protocol):
    def __call__(self, image_path: str) -> ProcessedImage: ...

@injected(protocol=ImageProcessorProtocol)
def process_image(model, preprocessor, /, image_path: str) -> ProcessedImage:
    # ...

# Good example of async function with Protocol
class DataFetcherProtocol(Protocol):
    async def __call__(self, user_id: str) -> UserData: ...

@injected(protocol=DataFetcherProtocol)
async def a_fetch_data(api_client, /, user_id: str) -> UserData:
    # ...
```

## 3. Key Naming Convention in design()

Key naming in the `design()` function should clarify relationships between dependency items.

### Recommended Patterns
- **Snake case**: `learning_rate`, `batch_size`
- **Category prefix**: `db_host`, `rabbitmq_port`
- **Clear namespace**: `service__feature__param`

### Examples
```python
config_design = design(
    rabbitmq_host="localhost",
    rabbitmq_port=5672,
    rabbitmq_username="guest",
    
    db_host="localhost",
    db_port=3306,
)
```

## 4. Naming Convention for Async Functions

### Async Functions Using @instance Decorator

Async functions using the @instance decorator should not have the `a_` prefix. Reasons:

1. Objects set with @instance are automatically awaited and instantiated by pinjected (AsyncResolver), so users don't need to await them themselves
2. @instance can be defined with def instead of async def unless await is needed internally
3. @instance expresses "what to provide", so maintaining noun form is important

```python
# Good example - no a_ prefix
@instance
async def rabbitmq_connection(host, port, username, password):
    connection = await aio_pika.connect_robust(...)
    return connection

# Bad example - unnecessary a_ prefix
@instance
async def a_rabbitmq_connection(host, port, username, password):  # × a_ prefix is unnecessary
    # ...
```

### Async Functions Using @injected Decorator

Async functions using the @injected decorator should have the `a_` prefix.

```python
# Good example - with a_ prefix
@injected
async def a_send_message(rabbitmq_channel, /, routing_key: str, message: str):
    await rabbitmq_channel.send(...)
    return True

# Bad example - no a_ prefix
@injected
async def fetch_data(api_client, /, user_id: str):  # × Missing a_ prefix
    # ...
```

Following this naming convention clarifies the role and processing type of functions, improving code maintainability.

# Pinjected Type and Protocol Best Practices

## 1. Basic Principles of Type Annotations

In Pinjected, using appropriate type annotations improves code safety and maintainability. **Always use Protocol definitions with the `@injected` decorator** to ensure type safety and better IDE support.

### Basic Type Annotations

```python
from typing import List, Dict, Optional, Callable, Protocol

@instance
def database_connection(host: str, port: int) -> Connection:
    return connect_to_db(host, port)

# Always define a Protocol for @injected functions
class UserFetcherProtocol(Protocol):
    def __call__(self, user_id: Optional[int] = None) -> List[Dict[str, any]]: ...

@injected(protocol=UserFetcherProtocol)  # Always specify protocol
def fetch_users(db: Connection, /, user_id: Optional[int] = None) -> List[Dict[str, any]]:
    # ...
```

## 2. Mandatory Protocol Usage with @injected

**Best Practice**: Always define and use Protocol when implementing `@injected` functions. This is now the recommended approach for all new code.

### Definition and Use of Protocol

```python
from typing import Protocol, runtime_checkable
from PIL import Image

# Step 1: Always define Protocol for your @injected functions
@runtime_checkable
class ImageProcessorProtocol(Protocol):
    async def __call__(self, image: Image.Image) -> Image.Image: ...

class ImageUploaderProtocol(Protocol):
    async def __call__(self, image: Image.Image, destination: str) -> str: ...

# Step 2: Always specify protocol parameter in @injected
@injected(protocol=ImageProcessorProtocol)  # Always specify protocol
async def a_process_image__v1(preprocessor, /, image: Image.Image) -> Image.Image:
    # Logic for implementation 1
    processed = preprocessor.apply(image)
    return processed

@injected(protocol=ImageProcessorProtocol)  # Same protocol for alternative implementation
async def a_process_image__v2(preprocessor, enhancer, /, image: Image.Image) -> Image.Image:
    # Logic for implementation 2 with additional dependencies
    processed = preprocessor.apply(image)
    enhanced = enhancer.enhance(processed)
    return enhanced

# Step 3: Use Protocol types when declaring dependencies
@injected(protocol=ImageUploaderProtocol)
async def a_upload_processed_image(
    a_process_image: ImageProcessorProtocol,  # Always use Protocol type annotation
    uploader,
    logger,
    /,
    image: Image.Image,
    destination: str
) -> str:
    logger.info(f"Processing and uploading image to {destination}")
    # Type checker knows a_process_image accepts and returns Image.Image
    processed_image = await a_process_image(image)
    upload_path = await uploader.upload(processed_image, destination)
    return upload_path

# Variation switching by design
base_design = design(
    a_process_image = a_process_image__v1  # Use v1 by default
)

advanced_design = base_design + design(
    a_process_image = a_process_image__v2  # Switch to v2
)

# Benefits:
# 1. Type Safety: IDEs and type checkers understand the exact interface
# 2. Documentation: Protocol serves as clear contract
# 3. Refactoring: Easy to find all implementations and usages
# 4. Testing: Can create mock implementations that satisfy the Protocol
```

# Execution from Pinjected main Block (Not Recommended)

Pinjected can be used directly from the main block. This pattern is not recommended.

## Script Execution Example

```python
from pinjected import instance, AsyncResolver, design, Design, IProxy
import pandas as pd


@instance
async def dataset(dataset_path) -> pd.DataFrame:
    return pd.read_csv(dataset_path)


if __name__ == "__main__":
    d: Design = design(
        dataset_path="dataset.csv"
    )
    resolver = AsyncResolver(d)
    dataset_proxy: IProxy = dataset
    dataset: pd.DataFrame = resolver.provide(dataset_proxy)
```

## RabbitMQ Connection Example

```python
from pinjected import instance, injected, design, Design, AsyncResolver, IProxy
import pika

@instance
def rabbitmq_connection(host, port, username, password):
    credentials = pika.PlainCredentials(username, password)
    parameters = pika.ConnectionParameters(
        host=host,
        port=port,
        credentials=credentials
    )
    return pika.BlockingConnection(parameters)

@instance
def rabbitmq_channel(rabbitmq_connection):
    return rabbitmq_connection.channel()

@injected
def send_message(rabbitmq_channel, /, routing_key: str, message: str):
    rabbitmq_channel.basic_publish(
        exchange='',
        routing_key=routing_key,
        body=message.encode()
    )
    return True

if __name__ == "__main__":
    d: Design = design(
        host="localhost",
        port=5672,
        username="guest",
        password="guest"
    )
    
    resolver = AsyncResolver(d)
    
    channel_proxy: IProxy = rabbitmq_channel
    channel = resolver.provide(channel_proxy)
    
    send_message_proxy: IProxy = send_message
    send_func = resolver.provide(send_message_proxy)
    
    result = send_func("hello", "Hello World!")
    print(f"Send result: {result}")
```

## Reasons Not Recommended

1. Configuration changes are easier using CLI
2. Increases code volume
3. Goes against Pinjected's design philosophy

Use CLI execution method instead:

```bash
python -m pinjected run my_module.my_function --param1=value1 --param2=value2
```

# Essential Differences Between @instance and @injected

## Target of Abstraction

`@instance` and `@injected` represent different abstractions:

- **@instance**: IProxy that abstracts "values"
    - Represents function execution results
    - All arguments are dependency-resolved

- **@injected**: IProxy that abstracts "functions"
    - Represents partially applied functions
    - Left side of `/` is dependency-resolved, right side still needed

Since `@instance` functions are called by the DI system and not directly by users, default arguments are inappropriate:

```python
# Inappropriate
@instance
def database_client(host="localhost", port=5432, user="default"):  # NG
    return create_db_client(host, port, user)

# Appropriate
@instance
def database_client(host, port, user):  # No default arguments
    return create_db_client(host, port, user)

# Provide configuration with design()
base_design = design(
    host="localhost", 
    port=5432, 
    user="default"
)
```

## Command Line Execution Behavior

```python
# @instance example
@instance
def my_instance(dependency1, dependency2):
    return f"{dependency1} + {dependency2}"

# Type: IProxy[str]
# pinjected run → Outputs "value1 + value2"

# @injected example
@injected
def my_injected(dependency1, /, arg1):
    return f"{dependency1} + {arg1}"

# Type: IProxy[Callable[[str], str]]
# pinjected run → Outputs function object
```

Execution results differ because:
- `@instance`: Abstracts value → Execution result is value
- `@injected`: Abstracts function → Execution result is function

## Execution of IProxy Objects

IProxy stored in variables and their method calls are also targets of pinjected run:

```python
@instance
def trainer(dep1):
    return Trainer()

@instance
def model(dep2):
    return Model()

# All of these can be run with pinjected
trainer_proxy: IProxy[Trainer] = trainer  # Instance reference
run_training: IProxy = trainer_proxy.train(model)  # Method call

# Execution method
# python -m pinjected run module.trainer  # Outputs trainer instance
# python -m pinjected run module.trainer_proxy  # Same as above
# python -m pinjected run module.run_training  # Outputs training execution result
```

Understanding these is important for effectively utilizing Pinjected.

# Pinjected Entry Point Design Best Practices

## 1. Entry Points Using IProxy Variables

```python
# my_module.py
@instance
def trainer(dep1, dep2):
    return Trainer(dep1, dep2)

@instance
def model(dep3):
    return Model(dep3)

@injected
def train_func(trainer,model):
    return trainer.train(model)

# Define entry points as IProxy variables
run_train_v1:IProxy = train_func() # calling @injected proxy so we get the result of running trainer.train.
run_train_v2: IProxy = trainer.run(model)
```

Define method calls or operation results of existing IProxy objects as entry points.
Entry points must have `IProxy` type annotation. Without `IProxy` type annotation, pinjected does not recognize it as an entry point.

## Execution from CLI

Both entry points can be executed from CLI similarly:

```bash
# Execute entry point using @instance
python -m pinjected run my_module.run_train_v1

# Execute entry point using IProxy variable
python -m pinjected run my_module.run_train_v2
```

## Note: @injected is Not an Entry Point

The `@injected` decorator is not typically used for defining entry points. Reason:

```python
@injected
def run_something(dep1, dep2, /, arg1, arg2):
    # Processing content
    return result
```

When executing a function defined this way with pinjected run, the execution result becomes a "function object" rather than a value. This is because `@injected` returns "IProxy that abstracts a function".

@injected is mainly suitable for defining "partially applied functions" that receive additional arguments after injecting dependencies.

## Entry Point Naming Convention

Clear naming conventions should be used for entry points:

- Recommended: `run_training`, `run_evaluation`, `run_inference`
- To avoid: General names representing specific actions (`train`, `evaluate`, `predict`)

## Common Entry Point Pattern
We have two options to set parameter for an entry point:
1. Use __design__ and `with design()` to set parameters
2. Use IProxy composition to set parameters for @injected functions args

```python
from pinjected import IProxy,design,injected
from PIL import Image
@injected
async def a_visualize(plotting_service,/,image):
    # plotting_service is a singleton in design
    # image is a parameter specified at runtime
    return plotting_service.plot(image)
image_1 = IProxy(Image).open("image1.png")
image_2 = IProxy(Image).open("image2.png")
# Using option 2 to change dynamic parameters
vis_1:IProxy[Figure] = a_visualize(image=image_1)
vis_2:IProxy[Figure] = a_visualize(image=image_2)

# Using option 1 to change injected plotting service
with design(plotting_service=mock):
    # now vis_with_mock will use the mock plotting service
    vis_with_mock:IProxy[Figure] = a_visualize(image=image_1)

# Pro-tip: Use injected('<key>') to make the parameter injectable in CLI!
injected_image = IProxy(Image).open(injected('image'))
run_vis:IProxy[Figure] = a_visualize(image=injected_image)
# This allows you to set the image parameter at runtime via CLI
# Example CLI command:
# uv run python -m pinjected run my_module.run_vis --image=image1.png
# This is recommended for making CLI commands flexible and reusable.
```

Key strategy for determining what to make a parameter injected or a runtime argument is:
- **Injected parameters**: Dependencies that are fixed for the entire execution context (e.g., services, configurations)
- **Runtime arguments**: Parameters that change per execution (e.g., input data, user inputs)


## 10. Version Update Information

### Major Changes in Latest Version

- **v0.2.115**: Documentation structure improvements, addition of `describe` command
- **Enhanced design flexibility**: Nested configuration overrides with `with` statements
- **Introduction of `__pinjected__.py`**: New recommended configuration method using `__design__` (`__meta_design__` is deprecated)
- **Enhanced async support**: Improved parallel dependency resolution

## 11. Summary

Pinjected is a solution for problems in research and development code (large cfg dependency, numerous if branches, testing difficulties).

Main benefits:

- **Configuration management**: DI definition with design(), CLI options, local configuration support with .pinjected.py
- **Code structure improvement**: Object injection with @instance and @injected reduces if branches
- **Testing ease**: Easy component unit execution and verification
- **Declarative description**: DSL-like expression with Injected/IProxy
- **Async support**: Efficient dependency resolution with asyncio integration
- **Dependency graph visualization**: Easy-to-understand dependency display with `describe` command
- **Type safety with Protocol**: Mandatory Protocol usage with @injected ensures type safety and IDE support

### Key Best Practice: Always Use Protocol with @injected

When implementing `@injected` functions, always:
1. Define a Protocol for the function interface
2. Specify the protocol using `@injected(protocol=YourProtocol)`
3. Use Protocol types when declaring dependencies

This approach provides:
- Better type safety and early error detection
- Full IDE support with autocomplete and parameter hints
- Clear documentation of interfaces
- Easier refactoring and testing

As a result, development speed improves and code reusability increases.

## Resources

- [Official Documentation](https://pinjected.readthedocs.io/en/latest/)
- [GitHub Repository](https://github.com/proboscis/pinjected)
- [VSCode Extension](https://marketplace.visualstudio.com/items?itemName=proboscis.pinjected-runner)

