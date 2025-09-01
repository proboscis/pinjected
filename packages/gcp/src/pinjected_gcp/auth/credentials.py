"""Shared GCP authentication and credentials management."""

import json
from pathlib import Path
from typing import Dict, Any

from google.auth import default
from google.oauth2 import service_account
from google.auth.credentials import Credentials
from loguru import logger
from pinjected import design, instance
from pinjected.di.iproxy import IProxy


@instance
def gcp_service_account_dict_from_file(
    gcp_service_account_path: Path,
) -> Dict[str, Any]:
    """
    Load service account JSON as a dictionary.

    Args:
        gcp_service_account_path: Path to the service account JSON file

    Returns:
        Service account info as a dictionary
    """
    if not gcp_service_account_path.exists():
        raise FileNotFoundError(
            f"Service account file not found: {gcp_service_account_path}"
        )

    with open(gcp_service_account_path, "r") as f:
        return json.load(f)


@instance
def gcp_credentials_from_file(
    gcp_service_account_path: Path,
    gcp_scopes: list[str],
) -> Credentials:
    """
    Create GCP credentials from a service account JSON file.

    Args:
        gcp_service_account_path: Path to the service account JSON file
        gcp_scopes: List of OAuth2 scopes.

    Returns:
        Google auth credentials object
    """
    if not gcp_service_account_path.exists():
        raise FileNotFoundError(
            f"Service account file not found: {gcp_service_account_path}"
        )

    logger.info(f"Loading GCP credentials from {gcp_service_account_path}")
    return service_account.Credentials.from_service_account_file(
        str(gcp_service_account_path),
        scopes=gcp_scopes,
    )


@instance
def gcp_credentials_from_dict(
    gcp_service_account_dict: Dict[str, Any],
    gcp_scopes: list[str],
) -> Credentials:
    """
    Create GCP credentials from a service account dictionary.

    Args:
        gcp_service_account_dict: Service account info as a dictionary
        gcp_scopes: List of OAuth2 scopes.

    Returns:
        Google auth credentials object
    """
    project_id = gcp_service_account_dict.get("project_id", "unknown")
    logger.info(f"Creating GCP credentials for project: {project_id}")

    return service_account.Credentials.from_service_account_info(
        gcp_service_account_dict,
        scopes=gcp_scopes,
    )


@instance
def gcp_credentials_from_env(
    gcp_scopes: list[str],
) -> Credentials:
    """
    Create GCP credentials from environment (Application Default Credentials).

    This will try to get credentials in the following order:
    1. GOOGLE_APPLICATION_CREDENTIALS environment variable
    2. gcloud auth application-default login
    3. GCE/GKE metadata service

    Args:
        gcp_scopes: List of OAuth2 scopes.

    Returns:
        Google auth credentials object
    """
    logger.info("Loading GCP credentials from environment (ADC)")
    credentials, project = default(scopes=gcp_scopes)

    if project:
        logger.info(f"Using GCP project from ADC: {project}")

    return credentials


@instance
def gcp_project_id_from_dict(gcp_service_account_dict: Dict[str, Any]) -> str:
    """
    Extract project ID from service account dictionary.

    Args:
        gcp_service_account_dict: Service account dictionary

    Returns:
        GCP project ID
    """
    if "project_id" in gcp_service_account_dict:
        return gcp_service_account_dict["project_id"]

    raise ValueError("No project_id found in service account dictionary")


@instance
def gcp_project_id_from_env() -> str:
    """
    Get project ID from Application Default Credentials.

    Returns:
        GCP project ID
    """
    try:
        _, project = default()
        if project:
            return project
    except Exception:
        pass

    raise ValueError(
        "Could not determine GCP project ID from Application Default Credentials"
    )


# Default scopes
default_gcp_scopes = IProxy.bind(["https://www.googleapis.com/auth/cloud-platform"])

# Design for auth module
__design__ = design(
    # Default scopes
    gcp_scopes=default_gcp_scopes,
    # Service account loading
    gcp_service_account_dict_from_file=gcp_service_account_dict_from_file,
    # Specific credential providers - user should choose which one to use
    gcp_credentials_from_file=gcp_credentials_from_file,
    gcp_credentials_from_dict=gcp_credentials_from_dict,
    gcp_credentials_from_env=gcp_credentials_from_env,
    # Alias for the most common use case (env/ADC)
    gcp_credentials=gcp_credentials_from_env,
    # Project ID providers
    gcp_project_id_from_dict=gcp_project_id_from_dict,
    gcp_project_id_from_env=gcp_project_id_from_env,
    gcp_project_id=gcp_project_id_from_env,  # Default alias
)
