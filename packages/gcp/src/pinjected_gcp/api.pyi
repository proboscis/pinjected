from typing import Protocol, overload
from pathlib import Path
from google.cloud import storage
from pinjected import IProxy

# Protocol definitions for @injected functions
class AUploadGcsProtocol(Protocol):
    """Protocol for uploading files to Google Cloud Storage."""
    async def __call__(
        self,
        bucket_name: str,
        source_file_path: str | Path,
        destination_blob_name: str | None = None,
    ) -> str: ...

class ADownloadGcsProtocol(Protocol):
    """Protocol for downloading files from Google Cloud Storage."""
    async def __call__(
        self,
        bucket_name: str,
        source_blob_name: str,
        destination_file_path: str | Path,
    ) -> Path: ...

class ADeleteGcsProtocol(Protocol):
    """Protocol for deleting files from Google Cloud Storage."""
    async def __call__(
        self,
        bucket_name: str,
        blob_name: str,
    ) -> bool: ...

class ADeleteGcsPrefixProtocol(Protocol):
    """Protocol for deleting all files under a prefix in Google Cloud Storage."""
    async def __call__(
        self,
        bucket_name: str,
        prefix: str,
    ) -> int: ...

# @instance function typed as IProxy
gcp_storage_client: IProxy[storage.Client]

# @injected functions use @overload showing only runtime arguments
@overload
async def a_upload_gcs(
    bucket_name: str,
    source_file_path: str | Path,
    destination_blob_name: str | None = None,
) -> str: ...
@overload
async def a_download_gcs(
    bucket_name: str,
    source_blob_name: str,
    destination_file_path: str | Path,
) -> Path: ...
@overload
async def a_delete_gcs(
    bucket_name: str,
    blob_name: str,
) -> bool: ...
@overload
async def a_delete_gcs_prefix(
    bucket_name: str,
    prefix: str,
) -> int: ...
