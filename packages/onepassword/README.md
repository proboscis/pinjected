# Pinjected OnePassword

OnePassword API integration for the pinjected dependency injection framework.

## Installation

```bash
pip install pinjected-onepassword
```

## Usage

Basic usage examples:

```python
from pinjected import injected
from pinjected_onepassword import get_secret

@injected
def my_function(api_key, /):
    # api_key is automatically retrieved from OnePassword
    ...
```
