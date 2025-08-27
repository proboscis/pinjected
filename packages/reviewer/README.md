# Pinjected Reviewer

Code review utilities for the [pinjected](https://github.com/CyberAgentAILab/pinjected) dependency injection framework. This package provides automated code review capabilities to ensure your code follows pinjected best practices and coding standards.

## Features

- **Automated Code Reviews**: Analyzes Python code for pinjected coding style violations
- **Pre-commit Hook Integration**: Automatically reviews code changes before commits
- **LLM-Powered Analysis**: Uses structured LLMs to provide detailed feedback on code issues
- **Customizable Review Rules**: Supports both Python and Markdown-based reviewer definitions
- **Command-line Interface**: Simple CLI for running reviews and managing hooks

## Installation

Currently, the package should be installed directly from the GitHub repository:

```bash
# Install from GitHub
pip install git+https://github.com/CyberAgentAILab/pinjected.git#subdirectory=packages/reviewer
```

## Requirements

- Python 3.10 or higher
- OpenRouter API key (for LLM-powered reviews)
- Git (for pre-commit hook functionality)

### Setting up the OpenRouter API Key

Create a `~/.pinjected.py` file to configure your OpenRouter API key:

```python
from pinjected import design

default_design = design(
    openrouter_api_key="your_openrouter_api_key_here"
)
```

This file is used for user-local settings and will be automatically loaded by pinjected.

## Usage

### Command-line Interface

The package provides a command-line interface with the following commands:

```bash
# Review staged changes in git
pinjected-reviewer review

# Install the git pre-commit hook
pinjected-reviewer install

# Uninstall the git pre-commit hook
pinjected-reviewer uninstall

# List all available reviewers
pinjected-reviewer list-reviewers
```

### Pre-commit Hook

The pre-commit hook automatically runs before each commit to ensure your code follows pinjected best practices:

```bash
# Install the pre-commit hook
pinjected-reviewer install
```

Once installed, the hook will run automatically when you attempt to commit changes. If any violations are found, the commit will be blocked, and detailed feedback will be provided.

### Using with uv (Recommended)

If you're using the uv package manager within the pinjected monorepo:

```bash
# Run the reviewer
uv run python -m pinjected_reviewer review

# Install the pre-commit hook
uv run python -m pinjected_reviewer install
```

## Reviewer Configuration

The reviewer loads review rules from the `.reviewers` directory in your project. This directory can contain:

- Python files (*.py) with reviewer definitions
- Markdown files (*.md) with review rules

### Example Markdown Reviewer

Create a file in `.reviewers/decorator_rule.md`:

```markdown
# Pinjected decorator usage reviewer
This reviewer checks code diff and see if @instance and @injected decorator is correctly used.
- When to trigger: pre_commit
- Return Type: Approval
- Target Files: .py
- Model: google/gemini-2.5-pro-preview-03-25

# Rules for @instance and @injected decorators

## @instance decorator
- Used to define singleton object providers
- Function arguments are treated as dependencies
- Return value is provided as an instance

## @injected decorator
- Separates injected arguments from runtime arguments
- Arguments before `/` are injected, after are runtime
- Used for functions that should be called multiple times

## Naming conventions
- @instance functions should use noun names
- @injected functions should use verb names
```

### Example Python Reviewer

Create a file in `.reviewers/decorator_misuse_reviewer.py`:

```python
from dataclasses import dataclass, field
from typing import Callable

from pinjected import injected, IProxy
from pinjected_reviewer.schema.reviewer_def import Reviewer, PreCommitFileDiffInterest
from pinjected_reviewer.schema.types import FileDiff, Review


@dataclass
class DecoratorMisuseDetector(Reviewer[FileDiff]):
    _a_detect_injected_function_call_without_requesting: Callable
    name: str = "Pinjected Decorator Misuse Reviewer"
    interests: set = field(default_factory=lambda: {PreCommitFileDiffInterest(".py")})

    async def __call__(self, file_diff: FileDiff) -> Review:
        if not str(file_diff.filename).endswith(".py"):
            return Review(
                name="Pinjected Decorator Misuse Reviewer",
                review_text="skipped since non-python file",
                approved=True
            )
        diagnostics = await self._a_detect_injected_function_call_without_requesting(
            file_diff.filename
        )
        if not diagnostics:
            return Review(
                name="Pinjected Decorator Misuse Reviewer",
                review_text="No pinjected decorator misuse detected.",
                approved=True
            )
        return Review(
            name="Pinjected Decorator Misuse Reviewer",
            review_text="\n".join([d.message for d in diagnostics]),
            approved=False
        )


# This is automatically picked up by pinjected-reviewer
__reviewer__: IProxy[Reviewer] = injected(DecoratorMisuseDetector)()
```

The reviewer automatically ignores files with the following comment:

```python
# pinjected-reviewer: ignore
```

## Development

To contribute to the pinjected-reviewer package:

1. Clone the pinjected repository
2. Navigate to the reviewer package directory
3. Install development dependencies:

```bash
cd packages/reviewer
uv sync --group dev
```

4. Run tests:

```bash
pytest
```

## License

MIT
