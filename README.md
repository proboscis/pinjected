


# Pinjected Monorepo
[![codecov](https://codecov.io/gh/proboscis/pinjected/branch/main/graph/badge.svg)](https://codecov.io/gh/proboscis/pinjected)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue)](https://github.com/CyberAgentAILab/pinjected/actions/workflows/pytest.yml)

This repository is organized as a monorepo with the following packages:

- **pinjected**: Core dependency injection framework
- **pinjected-openai**: OpenAI API bindings for pinjected (in packages/openai_support)

## Working with the Monorepo

### Installation

To install all packages for development:

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Set up the workspace
make sync
make setup-all
```

### Running Tests

Run tests for all packages:

```bash
make test
```

### Building Packages

Build individual packages:

```bash
make publish          # Build and publish pinjected
make publish-openai   # Build and publish pinjected-openai
```

## Core Pinjected Framework

Welcome to Pinjected, a powerful dependency injection and dependency resolver library for Python inspired by pinject.
## Prerequisites
- Python 3.10 or higher
- Basic understanding of Python decorators and functions

## Installation
```bash
pip install pinjected
```

## What is Dependency Injection?
Dependency injection is a design pattern where objects receive their dependencies from an external source rather than creating them internally. This makes code more:
- **Flexible**: Easy to change implementations
- **Testable**: Simple to mock dependencies
- **Maintainable**: Clear separation of concerns

## Core Concepts
- **@instance**: Decorator that marks a function as a dependency provider
- **design()**: Creates a design with dependencies (both value-based and function-based)
- **Design**: Configuration registry that manages dependencies
- **to_graph()**: Creates an object graph that resolves dependencies

## Development
Please refer to [Coding Guidelines](CODING_GUIDELINES.md) for development standards and best practices.

This project uses uv for dependency management. 

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or install with pip
pip install uv

# Install dependencies
uv pip sync
```

[日本語記事](https://zenn.dev/proboscis/articles/4a10d26b13a940)

# Quick Start Guide

## Basic Example
```python
from pinjected import design, instance

# Define a simple configuration
@instance
def database_config():
    return {
        "host": "localhost",
        "port": 5432,
        "name": "mydb"
    }

@instance
def database_connection(database_config):
    # Dependencies are automatically injected
    return f"Connected to {database_config['name']} at {database_config['host']}:{database_config['port']}"

# Create a design with our configurations
di = design(
    db_config=database_config,
    connection=database_connection
)

# Use the dependency injection
graph = di.to_graph()
connection = graph['connection']
print(connection)  # "Connected to mydb at localhost:5432"
```

## Common Use Cases

### 1. Configuration Management
```python
from pinjected import design

# Base configuration
base_config = design(
    api_url="https://api.example.com",
    timeout=30
)

# Development overrides
dev_config = base_config + design(
    api_url="http://localhost:8000"
)

# Production overrides
prod_config = base_config + design(
    timeout=60
)
```

### 2. Service Dependencies
```python
from pinjected import instance, design

@instance
def api_client(api_url, timeout):
    return f"Client configured with {api_url} (timeout: {timeout}s)"

@instance
def service(api_client):
    return f"Service using {api_client}"

# Create and use the service
di = dev_config + design(
    client=api_client,
    service=service
)
graph = di.to_graph()
my_service = graph['service']
```

### 3. Testing with Mock Dependencies
```python
# Override dependencies for testing
test_config = design(
    api_url="mock://test",
    timeout=1
)

test_design = test_config + design(
    client=api_client,
    service=service
)
```

For more detailed documentation and advanced features, see:

# Table of Contents

- [Introduction](docs_md/01_introduction.md)
- [Design](docs_md/02_design.md)
- [Decorators](docs_md/03_decorators.md)
- [Injected](docs_md/04_injected.md)
- [Running](docs_md/05_running.md)
- [Async Support](docs_md/06_async.md)
- [Resolver](docs_md/07_resolver.md)
- [Miscellaneous](docs_md/08_misc.md)
- [Appendix](docs_md/09_appendix.md)
- [Updates](docs_md/10_updates.md)
- [Migration Guides](docs_md/migration/migration_to_design.md)

## [Introduction](docs_md/01_introduction.md)
Pinjected makes it easy to compose multiple Python objects to create a final object. It automatically creates dependencies and composes them, providing a clean and modular approach to dependency management. To learn more about the motivation behind Pinjected and its key concepts, check out the Introduction.
Design

- VSCode plugin is available at [pinjected-runner](https://marketplace.visualstudio.com/items?itemName=Proboscis.pinjected-runner)

## [Design](docs_md/02_design.md)
The Design section covers the core concept of Pinjected. It explains how to define a collection of objects and their dependencies using the Design class. You'll learn about binding instances, providers, and classes to create a dependency graph.

## [Decorators](docs_md/03_decorators.md)
Pinjected provides two decorators, @instance and @injected, to define provider functions. The Decorators section explains the differences between these decorators and how to use them effectively in your code.

## [Injected](docs_md/04_injected.md)
In the Injected section, you'll learn about the Injected class, which represents a variable that requires injection. This section covers how to create Injected instances, compose them, and use them as providers in your dependency graph.

## [Running](docs_md/05_running.md)
Pinjected supports running Injected instances from the command line and integrating with IDEs like IntelliJ IDEA. The Running section provides details on how to use the CLI and set up IDE integration for a smooth development experience.

## [Async Support](docs_md/06_async.md)
Pinjected offers support for asynchronous programming, allowing you to use async functions as providers. The Async Support section explains how to define and use async providers, as well as how to compose async Injected instances.

## [Resolver](docs_md/07_resolver.md)
The Resolver section dives into the object graph and resolver concepts in Pinjected. You'll learn how the resolver manages the lifecycle of injected variables and how to use it to retrieve instances from the dependency graph.

## [Miscellaneous](docs_md/08_misc.md)
For additional information, refer to the Miscellaneous section, which covers topics like performance considerations, comparisons with other DI libraries, and troubleshooting.

## [Appendix](docs_md/09_appendix.md)
The Appendix contains supplementary information, such as a comparison with pinject and other relevant details.

## [Updates](docs_md/10_updates.md)
Stay up to date with the latest changes and releases by checking the Updates section, which includes a changelog and release information.

## [Migration Guides](docs_md/migration/migration_to_design.md)
The Migration Guides section provides step-by-step instructions for transitioning from deprecated APIs to newer ones. Currently featuring a comprehensive guide for migrating from `instances()`, `providers()`, and `classes()` to the new unified `design()` function.

We hope you find Pinjected helpful in your projects! If you have any questions or feedback, please don't hesitate to reach out.
