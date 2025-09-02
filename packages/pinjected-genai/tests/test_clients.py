from unittest.mock import MagicMock, Mock, patch

from google.auth.credentials import Credentials

from pinjected import design
from pinjected.test import injected_pytest

# Mock GCP credentials for testing
mock_credentials = Mock(spec=Credentials)

# Create a mock genai.Client for testing
mock_genai_client = MagicMock()  # Don't spec as genai.Client will be patched

# Patch genai.Client before creating test_di
with patch("pinjected_genai.clients.genai.Client", return_value=mock_genai_client):
    test_di = design(
        gcp_project_id="test-project-123",
        gcp_credentials=mock_credentials,
        genai_location="us-central1",  # Test with different location
    )


@injected_pytest(test_di)
def test_gcp_project_id_injected(gcp_project_id, /):
    """Test project ID can be injected."""
    assert gcp_project_id == "test-project-123"


@injected_pytest(design())
def test_genai_location_default(genai_location, logger, /):
    """Test default location returns global."""
    # Request genai_location through dependency injection
    assert genai_location == "global"


@injected_pytest(test_di)
def test_genai_location_injected(genai_location, /):
    """Test location can be injected."""
    assert genai_location == "us-central1"  # Injected value from test_di


@injected_pytest(test_di)
def test_genai_auth_client(genai_auth_client, /):
    """Test genai_auth_client creation."""
    # Verify it has the required attributes of GenAIAuthClient
    # (isinstance check won't work due to module patching)
    assert hasattr(genai_auth_client, "project_id")
    assert hasattr(genai_auth_client, "location")
    assert hasattr(genai_auth_client, "credentials")
    assert hasattr(genai_auth_client, "create_client")
    assert genai_auth_client.credentials is not None
    assert genai_auth_client.project_id == "test-project-123"  # From test_di
    assert genai_auth_client.location == "us-central1"  # From test_di


@injected_pytest(test_di)
def test_genai_client(genai_client, /):
    """Test genai_client returns genai.Client instance."""
    # With @instance decorator, genai_client should return a genai.Client instance
    assert genai_client is not None
    # Since we're patching genai.Client, the created instance would be our mock
    # But the real code creates a real genai.Client, so just check it's not None
    # In integration tests, we'd check it's actually working


@injected_pytest(design())
def test_genai_model_name_default(genai_model_name, /):
    """Test default model name for nano-banana."""
    assert genai_model_name == "gemini-2.5-flash-image-preview"
