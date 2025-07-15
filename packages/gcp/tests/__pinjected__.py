"""Test configuration for pinjected_gcp tests using real Google Cloud credentials."""

import json
from pathlib import Path

from google.cloud import storage
from google.oauth2 import service_account

from pinjected import design, instance
from pinjected.picklable_logger import PicklableLogger
from pinjected_gcp.api import (
    a_download_gcs,
    a_upload_gcs,
    a_delete_gcs,
    a_delete_gcs_prefix,
)


@instance
def gcp_service_account_credentials() -> dict:
    """Load GCP service account credentials from file."""
    # First try the file in .gcp directory
    creds_path = Path("~/.gcp/keys/valued-mission-109412-ema-app.json").expanduser()
    if creds_path.exists():
        with open(creds_path) as f:
            return json.load(f)

    # Fallback to the path defined in .pinjected.py
    creds_path = Path("~/.gcp/keys/valued-mission-109412-ema-app.json").expanduser()
    with open(creds_path) as f:
        return json.load(f)


@instance
def gcp_storage_client(gcp_service_account_credentials) -> storage.Client:
    """Create a real GCP storage client using service account credentials."""
    credentials = service_account.Credentials.from_service_account_info(
        gcp_service_account_credentials
    )
    return storage.Client(credentials=credentials)


# Real functions are provided through the design
__design__ = design(
    gcp_service_account_credentials=gcp_service_account_credentials,
    gcp_storage_client=gcp_storage_client,
    logger=PicklableLogger(),
    a_upload_gcs=a_upload_gcs,
    a_download_gcs=a_download_gcs,
    a_delete_gcs=a_delete_gcs,
    a_delete_gcs_prefix=a_delete_gcs_prefix,
)
