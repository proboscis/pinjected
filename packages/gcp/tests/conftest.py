import tempfile
from pathlib import Path

import pytest

try:
    from google.cloud import storage

    HAS_GOOGLE_CLOUD = True
except ImportError:
    HAS_GOOGLE_CLOUD = False
    storage = None


pytestmark = pytest.mark.skipif(
    not HAS_GOOGLE_CLOUD, reason="google-cloud-storage not installed"
)


@pytest.fixture
def mock_credentials():
    """Mock GCP credentials for testing."""
    return {
        "type": "service_account",
        "project_id": "test-project",
        "private_key_id": "test-key-id",
        "private_key": "test-private-key",
        "client_email": "test@example.com",
        "client_id": "test-client-id",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/test%40example.com",
    }


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
        print(f"MockBlob.download_to_filename: Downloading to {filename}")
        path = Path(filename)
        path.parent.mkdir(parents=True, exist_ok=True)
        print(f"Parent directory exists: {path.parent.exists()}")
        with open(filename, "wb") as f:
            f.write(self._content)
        print(
            f"File exists after write: {path.exists()}, size: {path.stat().st_size if path.exists() else 0}"
        )
        return path


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


@pytest.fixture
def mock_storage_client(monkeypatch):
    """Mock the GCP storage client for testing."""

    def mock_client(credentials=None):
        return MockStorageClient(credentials)

    monkeypatch.setattr(storage, "Client", mock_client)
    return mock_client


@pytest.fixture
def temp_file():
    """Create a temporary file for testing."""
    with tempfile.NamedTemporaryFile(delete=False) as temp:
        temp.write(b"test content")
        temp_path = Path(temp.name)
    yield temp_path
    temp_path.unlink(missing_ok=True)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)
