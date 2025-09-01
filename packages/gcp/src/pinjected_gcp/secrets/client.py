"""Google Cloud Secret Manager client and operations."""

import asyncio
from typing import Optional, Protocol, List, Dict, Any

from google.cloud import secretmanager
from google.auth.credentials import Credentials
from loguru import logger
from pinjected import design, instance, injected


@instance
def gcp_secret_manager_client(
    gcp_credentials: Credentials,
) -> secretmanager.SecretManagerServiceClient:
    """
    Create a Secret Manager client with the provided credentials.

    Args:
        gcp_credentials: Google auth credentials

    Returns:
        Secret Manager client instance
    """
    logger.info("Creating GCP Secret Manager client")
    return secretmanager.SecretManagerServiceClient(credentials=gcp_credentials)


# Protocol definitions
class AGcpSecretValueProtocol(Protocol):
    """Async protocol for fetching secret values."""

    async def __call__(
        self,
        secret_id: str,
        project_id: Optional[str] = None,
        version: str = "latest",
    ) -> str: ...


class GcpSecretValueProtocol(Protocol):
    """Sync protocol for fetching secret values."""

    def __call__(
        self,
        secret_id: str,
        project_id: Optional[str] = None,
        version: str = "latest",
    ) -> str: ...


class AListGcpSecretsProtocol(Protocol):
    """Protocol for listing secrets."""

    async def __call__(
        self,
        project_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]: ...


class ACreateGcpSecretProtocol(Protocol):
    """Protocol for creating secrets."""

    async def __call__(
        self,
        secret_id: str,
        secret_value: str,
        project_id: Optional[str] = None,
        labels: Optional[Dict[str, str]] = None,
    ) -> str: ...


class ADeleteGcpSecretProtocol(Protocol):
    """Protocol for deleting secrets."""

    async def __call__(
        self,
        secret_id: str,
        project_id: Optional[str] = None,
    ) -> bool: ...


@injected(protocol=AGcpSecretValueProtocol)
async def a_gcp_secret_value(
    gcp_secret_manager_client: secretmanager.SecretManagerServiceClient,
    gcp_project_id: str,
    logger: logger,
    /,
    secret_id: str,
    project_id: Optional[str] = None,
    version: str = "latest",
) -> str:
    """
    Fetch a secret value from GCP Secret Manager (async).

    Args:
        secret_id: The ID of the secret to access
        project_id: The GCP project ID (uses injected default if not specified)
        version: The version of the secret (defaults to "latest")

    Returns:
        The secret value as a string

    Raises:
        RuntimeError: If the secret is not found or access is denied
    """
    # Use injected project if not specified
    if project_id is None:
        project_id = gcp_project_id

    # Build the secret name
    secret_name = f"projects/{project_id}/secrets/{secret_id}/versions/{version}"

    logger.info(f"Fetching secret {secret_id} from project {project_id}")

    def fetch_secret():
        try:
            response = gcp_secret_manager_client.access_secret_version(
                request={"name": secret_name}
            )
            return response.payload.data.decode("UTF-8")
        except Exception as e:
            if "404" in str(e) or "not found" in str(e).lower():
                raise RuntimeError(
                    f"Secret '{secret_id}' not found in project '{project_id}'. "
                    f"Please ensure the secret exists in GCP Secret Manager."
                ) from e
            if "403" in str(e) or "permission" in str(e).lower():
                raise RuntimeError(
                    f"Permission denied accessing secret '{secret_id}' in project '{project_id}'. "
                    f"Please check IAM permissions for the service account."
                ) from e
            raise

    # Run in executor to avoid blocking
    result = await asyncio.get_event_loop().run_in_executor(None, fetch_secret)
    logger.debug(f"Successfully fetched secret {secret_id}")
    return result


@injected(protocol=GcpSecretValueProtocol)
def gcp_secret_value(
    gcp_secret_manager_client: secretmanager.SecretManagerServiceClient,
    gcp_project_id: str,
    logger: logger,
    /,
    secret_id: str,
    project_id: Optional[str] = None,
    version: str = "latest",
) -> str:
    """
    Fetch a secret value from GCP Secret Manager (sync).

    Args:
        secret_id: The ID of the secret to access
        project_id: The GCP project ID (uses injected default if not specified)
        version: The version of the secret (defaults to "latest")

    Returns:
        The secret value as a string

    Raises:
        RuntimeError: If the secret is not found or access is denied
    """
    # Use injected project if not specified
    if project_id is None:
        project_id = gcp_project_id

    # Build the secret name
    secret_name = f"projects/{project_id}/secrets/{secret_id}/versions/{version}"

    logger.info(f"Fetching secret {secret_id} from project {project_id}")

    try:
        response = gcp_secret_manager_client.access_secret_version(
            request={"name": secret_name}
        )
        secret_value = response.payload.data.decode("UTF-8")
        logger.debug(f"Successfully fetched secret {secret_id}")
        return secret_value

    except Exception as e:
        if "404" in str(e) or "not found" in str(e).lower():
            raise RuntimeError(
                f"Secret '{secret_id}' not found in project '{project_id}'. "
                f"Please ensure the secret exists in GCP Secret Manager."
            ) from e
        if "403" in str(e) or "permission" in str(e).lower():
            raise RuntimeError(
                f"Permission denied accessing secret '{secret_id}' in project '{project_id}'. "
                f"Please check IAM permissions for the service account."
            ) from e
        raise


@injected(protocol=AListGcpSecretsProtocol)
async def a_list_gcp_secrets(
    gcp_secret_manager_client: secretmanager.SecretManagerServiceClient,
    gcp_project_id: str,
    logger: logger,
    /,
    project_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    List all secrets in a GCP project.

    Args:
        project_id: The GCP project ID (uses injected default if not specified)

    Returns:
        List of secret metadata dictionaries
    """
    if project_id is None:
        project_id = gcp_project_id

    parent = f"projects/{project_id}"
    logger.info(f"Listing secrets in project {project_id}")

    def list_secrets():
        secrets = []
        for secret in gcp_secret_manager_client.list_secrets(parent=parent):
            secrets.append(
                {
                    "name": secret.name,
                    "secret_id": secret.name.split("/")[-1],
                    "create_time": secret.create_time,
                    "labels": dict(secret.labels) if secret.labels else {},
                }
            )
        return secrets

    result = await asyncio.get_event_loop().run_in_executor(None, list_secrets)
    logger.info(f"Found {len(result)} secrets in project {project_id}")
    return result


@injected(protocol=ACreateGcpSecretProtocol)
async def a_create_gcp_secret(
    gcp_secret_manager_client: secretmanager.SecretManagerServiceClient,
    gcp_project_id: str,
    logger: logger,
    /,
    secret_id: str,
    secret_value: str,
    project_id: Optional[str] = None,
    labels: Optional[Dict[str, str]] = None,
) -> str:
    """
    Create a new secret in GCP Secret Manager.

    Args:
        secret_id: The ID for the new secret
        secret_value: The secret value to store
        project_id: The GCP project ID (uses injected default if not specified)
        labels: Optional labels to attach to the secret

    Returns:
        The name of the created secret

    Raises:
        RuntimeError: If the secret already exists or creation fails
    """
    if project_id is None:
        project_id = gcp_project_id

    parent = f"projects/{project_id}"
    logger.info(f"Creating secret {secret_id} in project {project_id}")

    def create_secret():
        # Create the secret
        secret = gcp_secret_manager_client.create_secret(
            request={
                "parent": parent,
                "secret_id": secret_id,
                "secret": {
                    "replication": {"automatic": {}},
                    "labels": labels or {},
                },
            }
        )

        # Add the secret version with the value
        gcp_secret_manager_client.add_secret_version(
            request={
                "parent": secret.name,
                "payload": {"data": secret_value.encode("UTF-8")},
            }
        )

        return secret.name

    try:
        result = await asyncio.get_event_loop().run_in_executor(None, create_secret)
        logger.info(f"Successfully created secret {secret_id}")
        return result
    except Exception as e:
        if "already exists" in str(e).lower():
            raise RuntimeError(
                f"Secret '{secret_id}' already exists in project '{project_id}'"
            ) from e
        raise


@injected(protocol=ADeleteGcpSecretProtocol)
async def a_delete_gcp_secret(
    gcp_secret_manager_client: secretmanager.SecretManagerServiceClient,
    gcp_project_id: str,
    logger: logger,
    /,
    secret_id: str,
    project_id: Optional[str] = None,
) -> bool:
    """
    Delete a secret from GCP Secret Manager.

    Args:
        secret_id: The ID of the secret to delete
        project_id: The GCP project ID (uses injected default if not specified)

    Returns:
        True if deletion was successful, False if the secret didn't exist
    """
    if project_id is None:
        project_id = gcp_project_id

    secret_name = f"projects/{project_id}/secrets/{secret_id}"
    logger.info(f"Deleting secret {secret_id} from project {project_id}")

    def delete_secret():
        try:
            gcp_secret_manager_client.delete_secret(request={"name": secret_name})
            return True
        except Exception as e:
            if "404" in str(e) or "not found" in str(e).lower():
                logger.warning(f"Secret {secret_id} not found in project {project_id}")
                return False
            raise

    result = await asyncio.get_event_loop().run_in_executor(None, delete_secret)
    if result:
        logger.info(f"Successfully deleted secret {secret_id}")
    return result


# Design for client module
__design__ = design(
    # Client
    gcp_secret_manager_client=gcp_secret_manager_client,
    # Operations
    a_gcp_secret_value=a_gcp_secret_value,
    gcp_secret_value=gcp_secret_value,
    a_list_gcp_secrets=a_list_gcp_secrets,
    a_create_gcp_secret=a_create_gcp_secret,
    a_delete_gcp_secret=a_delete_gcp_secret,
)
