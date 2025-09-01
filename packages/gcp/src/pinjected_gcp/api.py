"""
Backward compatibility module.

This module re-exports the storage functionality from the new modular structure.
For new code, please import directly from pinjected_gcp.storage instead.
"""

# Re-export everything from storage for backward compatibility
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
    __design__,
)

# For backward compatibility, export test examples
test_upload_gcs = a_upload_gcs(
    bucket_name="example-bucket",
    source_file_path="example.txt",
    destination_blob_name="example.txt",
)

test_download_gcs = a_download_gcs(
    bucket_name="example-bucket",
    source_blob_name="example.txt",
    destination_file_path="downloaded_example.txt",
)

test_delete_gcs = a_delete_gcs(
    bucket_name="example-bucket",
    blob_name="example.txt",
)

test_delete_gcs_prefix = a_delete_gcs_prefix(
    bucket_name="example-bucket",
    prefix="a/b/c/",
)

__all__ = [
    "ADeleteGcsPrefixProtocol",
    "ADeleteGcsProtocol",
    "ADownloadGcsProtocol",
    "AUploadGcsProtocol",
    "__design__",
    "a_delete_gcs",
    "a_delete_gcs_prefix",
    "a_download_gcs",
    "a_upload_gcs",
    "gcp_storage_client",
    "test_delete_gcs",
    "test_delete_gcs_prefix",
    "test_download_gcs",
    "test_upload_gcs",
]
