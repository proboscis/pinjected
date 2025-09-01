"""Google Cloud Storage integration for pinjected."""

from .client import (
    gcp_storage_client,
    a_upload_gcs,
    a_download_gcs,
    a_delete_gcs,
    a_delete_gcs_prefix,
    AUploadGcsProtocol,
    ADownloadGcsProtocol,
    ADeleteGcsProtocol,
    ADeleteGcsPrefixProtocol,
    __design__ as storage_design,
)

__all__ = [
    "ADeleteGcsPrefixProtocol",
    "ADeleteGcsProtocol",
    "ADownloadGcsProtocol",
    "AUploadGcsProtocol",
    "a_delete_gcs",
    "a_delete_gcs_prefix",
    "a_download_gcs",
    "a_upload_gcs",
    "gcp_storage_client",
    "storage_design",
]

# Export design
__design__ = storage_design
