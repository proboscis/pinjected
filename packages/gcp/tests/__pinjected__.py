"""Test configuration for pinjected_gcp tests using real Google Cloud credentials."""

from google.cloud import storage

from pinjected import design, instance
from pinjected.picklable_logger import PicklableLogger
from pinjected_gcp.api import (
    a_download_gcs,
    a_upload_gcs,
    a_delete_gcs,
    a_delete_gcs_prefix,
)


@instance
def gcp_storage_client() -> storage.Client:
    """Create a GCP storage client using default credentials (gcloud auth)."""
    # This will use the credentials from gcloud auth
    # (currently masui_kento@cyberagent.co.jp with project cyberagent-050)
    return storage.Client()


# Real functions are provided through the design
__design__ = design(
    gcp_storage_client=gcp_storage_client,
    logger=PicklableLogger(),
    a_upload_gcs=a_upload_gcs,
    a_download_gcs=a_download_gcs,
    a_delete_gcs=a_delete_gcs,
    a_delete_gcs_prefix=a_delete_gcs_prefix,
)
