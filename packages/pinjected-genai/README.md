# pinjected-genai

Google GenAI (Gemini) bindings for the pinjected library.

## Features

- Seamless integration with Google GenAI SDK
- Support for Gemini 2.0 Flash image generation
- Async support with @injected decorators
- Rate limiting and retry logic

## Installation

```bash
pip install pinjected-genai
```

## Usage

```python
from pinjected_genai import genai_client, generate_image

# Use with dependency injection
@injected
async def my_function(generate_image, /):
    result = await generate_image("A cute baby turtle in 3D art style")
    return result
```