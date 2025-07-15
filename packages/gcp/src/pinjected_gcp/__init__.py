import loguru

from pinjected import *
from pinjected_gcp.api import (
    a_download_gcs,
    a_upload_gcs,
    a_delete_gcs,
    a_delete_gcs_prefix,
    gcp_storage_client,
)

__version__ = "0.1.0"

__all__ = [
    "a_delete_gcs",
    "a_delete_gcs_prefix",
    "a_download_gcs",
    "a_upload_gcs",
    "gcp_storage_client",
]

__design__ = design(
    logger=loguru.logger,
    gcp_storage_client=gcp_storage_client,
)
