import asyncio
from pathlib import Path
from typing import Protocol

from google.cloud import storage
from google.oauth2 import service_account

from pinjected import design, injected, instance
from pinjected.picklable_logger import PicklableLogger


@instance
def gcp_storage_client(gcp_service_account_credentials: dict):
    """Create a GCP storage client using the provided service account credentials."""
    credentials = service_account.Credentials.from_service_account_info(
        gcp_service_account_credentials
    )
    return storage.Client(credentials=credentials)


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


@injected(protocol=AUploadGcsProtocol)
async def a_upload_gcs(
    gcp_storage_client: storage.Client,
    logger: PicklableLogger,
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
    logger: PicklableLogger,
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


# Example usage for testing
test_upload_gcs = a_upload_gcs(
    bucket_name="example-bucket",
    source_file_path=Path("example.txt"),
    destination_blob_name="example.txt",
)

test_download_gcs = a_download_gcs(
    bucket_name="example-bucket",
    source_blob_name="example.txt",
    destination_file_path=Path("downloaded_example.txt"),
)

__design__ = design()
