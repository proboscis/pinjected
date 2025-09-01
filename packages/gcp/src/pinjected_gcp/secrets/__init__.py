"""Google Cloud Secret Manager integration for pinjected."""

from .client import (
    gcp_secret_manager_client,
    a_gcp_secret_value,
    gcp_secret_value,
    a_list_gcp_secrets,
    a_create_gcp_secret,
    a_delete_gcp_secret,
    AGcpSecretValueProtocol,
    GcpSecretValueProtocol,
    AListGcpSecretsProtocol,
    ACreateGcpSecretProtocol,
    ADeleteGcpSecretProtocol,
    __design__ as client_design,
)

from .cache import (
    a_gcp_secret_value_cached,
    gcp_secret_value_cached,
    AGcpSecretValueCachedProtocol,
    GcpSecretValueCachedProtocol,
    __design__ as cache_design,
)

__all__ = [
    "ACreateGcpSecretProtocol",
    "ADeleteGcpSecretProtocol",
    "AGcpSecretValueCachedProtocol",
    "AGcpSecretValueProtocol",
    "AListGcpSecretsProtocol",
    "GcpSecretValueCachedProtocol",
    "GcpSecretValueProtocol",
    "a_create_gcp_secret",
    "a_delete_gcp_secret",
    "a_gcp_secret_value",
    "a_gcp_secret_value_cached",
    "a_list_gcp_secrets",
    "cache_design",
    "client_design",
    "gcp_secret_manager_client",
    "gcp_secret_value",
    "gcp_secret_value_cached",
]

# Combined design for all secret manager functionality
from pinjected import design

__design__ = design() + client_design + cache_design
