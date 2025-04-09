# Pinjected GCP

Google Cloud Platform bindings for the pinjected dependency injection framework.

## Installation

```bash
pip install pinjected-gcp
```

## Usage

```python
from pinjected import design
from pinjected_gcp import a_upload_gcs, a_download_gcs
from pathlib import Path

# Create a design with your GCP credentials
di = design(
    gcp_service_account_credentials={"your": "credentials", "here": "..."}
)

# Upload a file to GCS
result = await a_upload_gcs(
    bucket_name="your-bucket",
    source_file_path=Path("local_file.txt"),
    destination_blob_name="remote_file.txt"
)(di)

# Download a file from GCS
downloaded_path = await a_download_gcs(
    bucket_name="your-bucket",
    source_blob_name="remote_file.txt",
    destination_file_path=Path("downloaded_file.txt")
)(di)
```

## Features

- Asynchronous GCS operations
- Dependency injection for GCP credentials
- Simple API for common GCS operations
