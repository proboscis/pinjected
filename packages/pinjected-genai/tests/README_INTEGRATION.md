# Integration Tests

These integration tests use the real Google Gen AI SDK with Vertex AI mode.

## Running Integration Tests

### Prerequisites
The tests assume that GCP credentials and project ID are properly injected through dependency injection.

### Run All Integration Tests
```bash
uv run pytest tests/test_integration.py -m integration
```

### Run Specific Integration Test
```bash
uv run pytest tests/test_integration.py::test_real_generate_single_image -m integration
```

### Skip Integration Tests
When running all tests, integration tests can be skipped:
```bash
uv run pytest tests/ -m "not integration"
```

## Test Coverage

The integration tests cover:
- Single image generation with `gemini-2.5-flash-image-preview` (nano-banana)
- Multiple image generation
- Image generation with story/narrative
- Custom prompt generation
- Image description from file
- Error handling with invalid models
- Credential verification

## Dependencies Injection

The tests expect the following to be injected:
- `gcp_credentials`: Google Cloud Platform credentials
- `gcp_project_id`: GCP project ID
- `genai_location`: Gen AI location (defaults to "global" for nano-banana support)

These can be provided through your `~/.pinjected.py` configuration or passed directly to the test design.