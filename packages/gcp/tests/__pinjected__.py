import tempfile
from pathlib import Path

import loguru
from pinjected_gcp.api import a_download_gcs, a_upload_gcs

from pinjected import design


class MockBlob:
    def __init__(self, name):
        self.name = name
        self.public_url = f"https://storage.googleapis.com/test-bucket/{name}"
        self._content = b"test content"

    def upload_from_filename(self, filename):
        with open(filename, "rb") as f:
            self._content = f.read()
        return self.public_url

    def download_to_filename(self, filename):
        path = Path(filename)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(filename, "wb") as f:
            f.write(self._content)
        return filename


class MockBucket:
    def __init__(self, name):
        self.name = name
        self.blobs = {}

    def blob(self, name):
        if name not in self.blobs:
            self.blobs[name] = MockBlob(name)
        return self.blobs[name]


class MockStorageClient:
    def __init__(self, credentials=None):
        self.credentials = credentials
        self.buckets = {}

    def bucket(self, name):
        if name not in self.buckets:
            self.buckets[name] = MockBucket(name)
        return self.buckets[name]


__design__ = design(
    gcp_service_account_credentials={
        "type": "service_account",
        "project_id": "test-project",
        "private_key_id": "test-key-id",
        "private_key": "test-private-key",
        "client_email": "test@example.com",
        "client_id": "test-client-id",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/test%40example.com"
    },
    
    gcp_storage_client=MockStorageClient(),
    
    temp_file=Path(tempfile.NamedTemporaryFile(delete=False, suffix='.txt').name).absolute(),
    
    logger=loguru.logger,
    
    a_upload_gcs=a_upload_gcs,
    a_download_gcs=a_download_gcs
)
