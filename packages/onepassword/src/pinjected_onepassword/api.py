import asyncio

import loguru
from beartype import beartype
from onepassword.client import Client

from pinjected import design, injected, instance


@instance
async def op_client(
    logger,
    onepassword_service_account_token: str,
) -> Client:
    """Initialize the OnePassword client.

    Uses environment variables or arguments to authenticate:
    - OP_SERVICE_ACCOUNT_TOKEN: Token for service account authentication

    Precedence: Function arguments > Environment variables
    """
    # Get authentication info from environment if not provided

    logger.debug("Initializing OnePassword client with service account token")
    return await Client.authenticate(
        auth=onepassword_service_account_token,
        integration_name="pinjected-onepassword",
        integration_version="v1.0.0",
    )


@beartype
@injected
async def a_onepassword_secret(
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
    except Exception as e:
        logger.error(f"Failed to retrieve secrets: {e}")
        raise
    else:
        return secrets


# Example design for testing and usage
__design__ = design(
    logger=loguru.logger,
)
