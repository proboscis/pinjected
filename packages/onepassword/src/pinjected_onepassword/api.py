import asyncio
import os
from pathlib import Path

import loguru
from beartype import beartype
from onepassword.client import Client

from pinjected import design, injected, instance


@beartype
@instance
async def op_client(
    logger,
    op_service_account_token: str | None = None,
    integration_name: str = "pinjected-onepassword",
    integration_version: str = "v0.1.0",
) -> Client:
    """Initialize the OnePassword client.

    Uses environment variables or arguments to authenticate:
    - OP_SERVICE_ACCOUNT_TOKEN: Token for service account authentication

    Precedence: Function arguments > Environment variables
    """
    try:
        # Get authentication info from environment if not provided
        token = op_service_account_token or os.environ.get("OP_SERVICE_ACCOUNT_TOKEN")

        if not token:
            raise ValueError(
                "Missing OnePassword service account token. Provide op_service_account_token or set OP_SERVICE_ACCOUNT_TOKEN environment variable."
            )

        logger.debug("Initializing OnePassword client with service account token")
        return await Client.authenticate(
            auth=token,
            integration_name=integration_name,
            integration_version=integration_version,
        )

    except Exception as e:
        logger.error(f"Failed to initialize OnePassword client: {e}")
        raise


@beartype
@injected
async def get_secret(
    op_client: Client,
    logger,
    /,
    vault: str,
    item: str,
    field: str = "password",
) -> str:
    """Retrieve a secret from OnePassword vault using secret references.

    Args:
        vault: Name of the vault
        item: Name of the item
        field: Field name to retrieve (default: password)

    Returns:
        The secret value as a string
    """
    try:
        secret_reference = f"op://{vault}/{item}/{field}"
        logger.debug(f"Retrieving secret with reference: {secret_reference}")

        # Resolve the secret reference
        secret = await op_client.secrets.resolve(secret_reference)
        return secret

    except Exception as e:
        logger.error(f"Failed to retrieve secret: {e}")
        raise


@beartype
@injected
async def get_secrets(
    op_client: Client,
    logger,
    /,
    secret_references: list[str],
) -> dict[str, str]:
    """Retrieve multiple secrets from OnePassword vault in bulk.

    Args:
        secret_references: List of secret references using format 'op://vault/item/field'

    Returns:
        Dictionary mapping secret references to their values
    """
    try:
        logger.debug(f"Retrieving {len(secret_references)} secrets in bulk")

        # Resolve all secret references
        tasks = [op_client.secrets.resolve(ref) for ref in secret_references]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results and check for errors
        secrets = {}
        for i, ref in enumerate(secret_references):
            result = results[i]
            if isinstance(result, Exception):
                logger.error(f"Error retrieving secret {ref}: {result}")
                raise result
            secrets[ref] = result

        return secrets

    except Exception as e:
        logger.error(f"Failed to retrieve secrets: {e}")
        raise


@beartype
@injected
async def get_document(
    op_client: Client,
    logger,
    /,
    vault: str,
    item: str,
    field: str = "document",
    output_path: Path | None = None,
) -> bytes:
    """Retrieve a document from OnePassword vault.

    Args:
        vault: Name of the vault
        item: Name of the item containing the file
        field: Name of the file field (default: "document")
        output_path: Optional path to save the document to

    Returns:
        The document content as bytes. If output_path is provided, also saves the document there.
    """
    try:
        # Use the files API to download the file
        secret_reference = f"op://{vault}/{item}/{field}"
        logger.debug(f"Retrieving document with reference: {secret_reference}")

        # Get the document content
        document = await op_client.files.download_file_by_secret_reference(
            secret_reference
        )

        # Save to file if path is provided
        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(document)
            logger.debug(f"Document saved to {output_path}")

        return document

    except Exception as e:
        logger.error(f"Failed to retrieve document: {e}")
        raise


# Example design for testing and usage
__design__ = design(
    logger=loguru.logger,
)

# Examples for testing
_test_get_secret = get_secret(vault="Test Vault", item="API Keys", field="api_key")

_test_get_document = get_document(
    vault="Test Vault",
    item="Config",
    field="document",
    output_path=Path("./downloaded_config.json"),
)
