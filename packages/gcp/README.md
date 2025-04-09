# Pinjected GCP

Google Cloud Platform bindings for the pinjected dependency injection framework.

## Installation

```bash
pip install pinjected-gcp
```

## Usage

```python
from pinjected import design, injected
from pinjected_gcp import a_upload_gcs, a_download_gcs
from pathlib import Path
import asyncio

# Define your application function
@injected
async def upload_and_download_example(
    gcp_service_account_credentials,
    /,
):
    # Upload a file to GCS
    upload_result = await a_upload_gcs(
        bucket_name="your-bucket",
        source_file_path=Path("local_file.txt"),
        destination_blob_name="remote_file.txt"
    )
    
    print(f"Uploaded file URL: {upload_result}")
    
    # Download a file from GCS
    download_result = await a_download_gcs(
        bucket_name="your-bucket",
        source_blob_name="remote_file.txt",
        destination_file_path=Path("downloaded_file.txt")
    )
    
    print(f"Downloaded file path: {download_result}")
    return download_result

# Create a design with your GCP credentials
di = design(
    gcp_service_account_credentials={
        "type": "service_account",
        "project_id": "your-project-id",
        # Add other required credential fields
    }
)

# Run the example
async def main():
    result = await upload_and_download_example(di)
    print(f"Final result: {result}")

# Run with asyncio
asyncio.run(main())

# Alternatively, run using the CLI
# python -m pinjected run your.module.upload_and_download_example
```

## Features

- Asynchronous GCS operations
- Dependency injection for GCP credentials
- Simple API for common GCS operations
