from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pinjected_onepassword import (
    get_document,
    get_secret,
    get_secrets,
    hello,
    op_client,
)


def test_hello():
    assert hello() == "Hello from pinjected-onepassword!"


@pytest.fixture
def mock_op_client():
    with patch(
        "pinjected_onepassword.api.Client.authenticate", new_callable=AsyncMock
    ) as mock_auth:
        mock_instance = MagicMock()
        mock_auth.return_value = mock_instance

        # Create mocks for API sections
        mock_instance.secrets = AsyncMock()
        mock_instance.files = AsyncMock()

        yield mock_instance


@pytest.mark.asyncio
async def test_op_client_init(mock_op_client):
    # Setup
    logger = MagicMock()
    token = "test-token"

    # Execute
    client = await op_client.raw_func(
        logger,
        op_service_account_token=token,
        integration_name="test-integration",
        integration_version="v1.0.0",
    )

    # Verify
    assert client is mock_op_client


@pytest.mark.asyncio
async def test_get_secret(mock_op_client):
    # Setup
    mock_op_client.secrets.resolve.return_value = "secret-value"

    # Inject dependencies manually for testing
    logger = MagicMock()

    # Execute
    result = await get_secret.raw_func(
        mock_op_client, logger, vault="Test", item="API Key"
    )

    # Verify
    assert result == "secret-value"
    mock_op_client.secrets.resolve.assert_called_once_with("op://Test/API Key/password")


@pytest.mark.asyncio
async def test_get_secrets(mock_op_client):
    # Setup
    mock_op_client.secrets.resolve.side_effect = ["password-value", "username-value"]

    # Inject dependencies manually for testing
    logger = MagicMock()
    secret_refs = ["op://Test/API Key/password", "op://Test/API Key/username"]

    # Execute
    result = await get_secrets.raw_func(
        mock_op_client, logger, secret_references=secret_refs
    )

    # Verify
    assert result == {
        "op://Test/API Key/password": "password-value",
        "op://Test/API Key/username": "username-value",
    }
    assert mock_op_client.secrets.resolve.call_count == 2
    mock_op_client.secrets.resolve.assert_any_call("op://Test/API Key/password")
    mock_op_client.secrets.resolve.assert_any_call("op://Test/API Key/username")


@pytest.mark.asyncio
async def test_get_document(mock_op_client, tmp_path):
    # Setup
    mock_document_content = b"document content"
    mock_op_client.files.download_file_by_secret_reference.return_value = (
        mock_document_content
    )

    # Inject dependencies manually for testing
    logger = MagicMock()
    output_path = tmp_path / "test_doc.txt"

    # Execute
    result = await get_document.raw_func(
        mock_op_client,
        logger,
        vault="Test",
        item="Document",
        field="document",
        output_path=output_path,
    )

    # Verify
    assert result == mock_document_content
    assert output_path.read_bytes() == mock_document_content
    mock_op_client.files.download_file_by_secret_reference.assert_called_once_with(
        "op://Test/Document/document"
    )
