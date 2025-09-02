"""Authentication module for GCP services."""

from .credentials import (
    gcp_credentials_from_file,
    gcp_credentials_from_dict,
    gcp_credentials_from_env,
    __design__ as auth_design,
)

__all__ = [
    "auth_design",
    "gcp_credentials_from_dict",
    "gcp_credentials_from_env",
    "gcp_credentials_from_file",
]
