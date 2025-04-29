
from google.cloud import storage
from loguru import Logger

from pinjected import DesignSpec, SimpleBindSpec, design

__design__ = design()

__design_spec__ = DesignSpec.new(
    gcp_service_account_credentials=SimpleBindSpec(
        validator=lambda item: "gcp_service_account_credentials must be a dict" if not isinstance(item, dict) else None,
        documentation="Google Cloud Platform service account credentials dictionary for authentication"
    ),
    gcp_storage_client=SimpleBindSpec(
        validator=lambda item: "gcp_storage_client must be a storage.Client" if not isinstance(item, storage.Client) else None,
        documentation="Google Cloud Storage client instance for interacting with GCS"
    ),
    logger=SimpleBindSpec(
        validator=lambda item: "logger must be a Logger instance" if not isinstance(item, Logger) else None,
        documentation="Logger instance for logging operations"
    ),
    a_upload_gcs=SimpleBindSpec(
        validator=lambda item: "a_upload_gcs must be a callable" if not callable(item) else None,
        documentation="""
        Async function to upload a file to Google Cloud Storage.
        
        Signature:
        async def a_upload_gcs(
            gcp_storage_client: storage.Client,
            logger,
            /,
            bucket_name: str,
            source_file_path: Union[str, Path],
            destination_blob_name: Optional[str] = None,
        ) -> str:
        
        Returns the public URL of the uploaded file.
        """
    ),
    a_download_gcs=SimpleBindSpec(
        validator=lambda item: "a_download_gcs must be a callable" if not callable(item) else None,
        documentation="""
        Async function to download a file from Google Cloud Storage.
        
        Signature:
        async def a_download_gcs(
            gcp_storage_client: storage.Client,
            logger,
            /,
            bucket_name: str,
            source_blob_name: str,
            destination_file_path: Union[str, Path],
        ) -> Path:
        
        Returns the path to the downloaded file.
        """
    )
)
