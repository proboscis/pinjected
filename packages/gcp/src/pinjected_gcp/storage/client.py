"""Google Cloud Storage client and operations."""

import asyncio
from pathlib import Path
from typing import Protocol

from google.cloud import storage
from google.auth.credentials import Credentials
from loguru import logger
from pinjected import design, injected, instance


@instance
def gcp_storage_client(gcp_credentials: Credentials) -> storage.Client:
    """
    Create a GCP storage client using the provided credentials.

    Args:
        gcp_credentials: Google auth credentials

    Returns:
        GCS client instance
    """
    logger.info("Creating GCP Storage client")
    return storage.Client(credentials=gcp_credentials)


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


@injected(protocol=AUploadGcsProtocol)
async def a_upload_gcs(
    gcp_storage_client: storage.Client,
    logger: logger,
    /,
    bucket_name: str,
    source_file_path: str | Path,
    destination_blob_name: str | None = None,
) -> str:
    """
    Uploads a file to Google Cloud Storage.

    Args:
        bucket_name: Name of the GCS bucket
        source_file_path: Path to the file to upload
        destination_blob_name: Name to give the uploaded file in GCS (defaults to filename)

    Returns:
        The public URL of the uploaded file
    """
    source_file_path = Path(source_file_path)
    if not destination_blob_name:
        destination_blob_name = source_file_path.name

    logger.info(
        f"Uploading {source_file_path} to {bucket_name}/{destination_blob_name}"
    )

    def upload_task():
        bucket = gcp_storage_client.bucket(bucket_name)
        blob = bucket.blob(destination_blob_name)
        blob.upload_from_filename(str(source_file_path))
        return blob.public_url

    # Run the upload in a thread to avoid blocking the event loop
    result = await asyncio.get_event_loop().run_in_executor(None, upload_task)
    logger.info(f"Uploaded {source_file_path} to {bucket_name}/{destination_blob_name}")
    return result


@injected(protocol=ADownloadGcsProtocol)
async def a_download_gcs(
    gcp_storage_client: storage.Client,
    logger: logger,
    /,
    bucket_name: str,
    source_blob_name: str,
    destination_file_path: str | Path,
) -> Path:
    """
    Downloads a file from Google Cloud Storage.

    Args:
        bucket_name: Name of the GCS bucket
        source_blob_name: Name of the blob to download
        destination_file_path: Path where the file should be saved

    Returns:
        The path to the downloaded file
    """
    destination_file_path = Path(destination_file_path)
    destination_file_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info(
        f"Downloading {bucket_name}/{source_blob_name} to {destination_file_path}"
    )

    def download_task():
        bucket = gcp_storage_client.bucket(bucket_name)
        blob = bucket.blob(source_blob_name)
        blob.download_to_filename(str(destination_file_path))
        return destination_file_path

    # Run the download in a thread to avoid blocking the event loop
    result = await asyncio.get_event_loop().run_in_executor(None, download_task)
    logger.info(
        f"Downloaded {bucket_name}/{source_blob_name} to {destination_file_path}"
    )
    return result


@injected(protocol=ADeleteGcsProtocol)
async def a_delete_gcs(
    gcp_storage_client: storage.Client,
    logger: logger,
    /,
    bucket_name: str,
    blob_name: str,
) -> bool:
    """
    Deletes a file from Google Cloud Storage.

    Args:
        bucket_name: Name of the GCS bucket
        blob_name: Name of the blob to delete

    Returns:
        True if the deletion was successful, False if the blob didn't exist
    """
    logger.info(f"Deleting {bucket_name}/{blob_name}")

    def delete_task():
        try:
            bucket = gcp_storage_client.bucket(bucket_name)
            blob = bucket.blob(blob_name)
            blob.delete()
            return True
        except Exception as e:
            # Google Cloud Storage returns 404 if blob doesn't exist
            if "404" in str(e):
                logger.warning(f"Blob {bucket_name}/{blob_name} not found")
                return False
            raise

    # Run the delete in a thread to avoid blocking the event loop
    result = await asyncio.get_event_loop().run_in_executor(None, delete_task)
    if result:
        logger.info(f"Deleted {bucket_name}/{blob_name}")
    return result


@injected(protocol=ADeleteGcsPrefixProtocol)
async def a_delete_gcs_prefix(
    gcp_storage_client: storage.Client,
    logger: logger,
    /,
    bucket_name: str,
    prefix: str,
) -> int:
    """
    Deletes all files under a given prefix in Google Cloud Storage.

    For example, if you have blobs:
    - a/b/c/file1.txt
    - a/b/c/d/file2.txt
    - a/b/c/d/e/file3.txt
    - a/b/x/file4.txt

    Calling with prefix="a/b/c/" will delete the first three files.

    Args:
        bucket_name: Name of the GCS bucket
        prefix: The prefix path (e.g., "a/b/c/" to delete everything under that path)

    Returns:
        The number of blobs deleted
    """
    # Ensure prefix ends with / for proper directory-like behavior
    if prefix and not prefix.endswith("/"):
        prefix = prefix + "/"

    logger.info(f"Deleting all blobs under {bucket_name}/{prefix}")

    def delete_prefix_task():
        bucket = gcp_storage_client.bucket(bucket_name)
        blobs = list(bucket.list_blobs(prefix=prefix))

        if not blobs:
            logger.warning(f"No blobs found under {bucket_name}/{prefix}")
            return 0

        # Delete blobs in batches for efficiency
        batch_size = 100
        total_deleted = 0

        for i in range(0, len(blobs), batch_size):
            batch = blobs[i : i + batch_size]
            # Use batch delete for efficiency
            with gcp_storage_client.batch():
                for blob in batch:
                    logger.debug(f"Deleting {blob.name}")
                    blob.delete()
            total_deleted += len(batch)
            logger.info(f"Deleted {total_deleted}/{len(blobs)} blobs")

        return total_deleted

    # Run the delete in a thread to avoid blocking the event loop
    result = await asyncio.get_event_loop().run_in_executor(None, delete_prefix_task)
    logger.info(f"Deleted {result} blobs under {bucket_name}/{prefix}")
    return result


# Design for storage module
__design__ = design(
    # Client
    gcp_storage_client=gcp_storage_client,
    # Operations
    a_upload_gcs=a_upload_gcs,
    a_download_gcs=a_download_gcs,
    a_delete_gcs=a_delete_gcs,
    a_delete_gcs_prefix=a_delete_gcs_prefix,
)
