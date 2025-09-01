"""Google Cloud Platform integration for pinjected."""

import loguru
from pinjected import design

# Import all submodules
from . import auth, secrets, storage

# Re-export commonly used items from auth
from .auth import (
    gcp_credentials,
    gcp_credentials_from_env,
    gcp_credentials_from_file,
    gcp_credentials_from_dict,
    gcp_project_id,
    gcp_project_id_from_env,
    gcp_project_id_from_dict,
)

# Re-export from secrets
from .secrets import (
    gcp_secret_manager_client,
    a_gcp_secret_value,
    gcp_secret_value,
    a_gcp_secret_value_cached,
    gcp_secret_value_cached,
    a_list_gcp_secrets,
    a_create_gcp_secret,
    a_delete_gcp_secret,
    AGcpSecretValueProtocol,
    GcpSecretValueProtocol,
    AGcpSecretValueCachedProtocol,
    GcpSecretValueCachedProtocol,
)

# Re-export from storage (backward compatibility)
from .storage import (
    gcp_storage_client,
    a_upload_gcs,
    a_download_gcs,
    a_delete_gcs,
    a_delete_gcs_prefix,
    AUploadGcsProtocol,
    ADownloadGcsProtocol,
    ADeleteGcsProtocol,
    ADeleteGcsPrefixProtocol,
)

__version__ = "0.1.0"

__all__ = [
    "ADeleteGcsPrefixProtocol",
    "ADeleteGcsProtocol",
    "ADownloadGcsProtocol",
    "AGcpSecretValueCachedProtocol",
    "AGcpSecretValueProtocol",
    "AUploadGcsProtocol",
    "GcpSecretValueCachedProtocol",
    "GcpSecretValueProtocol",
    "a_create_gcp_secret",
    "a_delete_gcp_secret",
    "a_delete_gcs",
    "a_delete_gcs_prefix",
    "a_download_gcs",
    "a_gcp_secret_value",
    "a_gcp_secret_value_cached",
    "a_list_gcp_secrets",
    "a_upload_gcs",
    "auth",
    "gcp_credentials",
    "gcp_credentials_from_dict",
    "gcp_credentials_from_env",
    "gcp_credentials_from_file",
    "gcp_project_id",
    "gcp_project_id_from_dict",
    "gcp_project_id_from_env",
    "gcp_secret_manager_client",
    "gcp_secret_value",
    "gcp_secret_value_cached",
    "gcp_storage_client",
    "secrets",
    "storage",
]

# Combined design for all GCP functionality
__design__ = (
    design(logger=loguru.logger)
    + auth.__design__
    + secrets.__design__
    + storage.__design__
)
