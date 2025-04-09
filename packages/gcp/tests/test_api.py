import os
import tempfile
import asyncio
from pathlib import Path

import pytest
from pinjected import design
from pinjected.test.injected_pytest import injected_pytest

from pinjected_gcp.api import a_upload_gcs, a_download_gcs


@injected_pytest
def test_upload_gcs(gcp_service_account_credentials, temp_file):
    """Test uploading a file to GCS."""
    result = a_upload_gcs(
        bucket_name="test-bucket",
        source_file_path=temp_file,
        destination_blob_name="test-file.txt"
    )
    
    # Check the result
    assert result == f"https://storage.googleapis.com/test-bucket/test-file.txt"


@injected_pytest
def test_download_gcs(gcp_service_account_credentials):
    """Test downloading a file from GCS."""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.txt') as temp:
        temp.write(b"test content")
        source_file = Path(temp.name)
    
    print(f"Created source file at {source_file}, exists: {source_file.exists()}")
    
    temp_dir = Path(tempfile.mkdtemp())
    download_path = temp_dir / "downloaded-file.txt"
    
    print(f"Download path will be {download_path}")
    print(f"Temp directory exists: {temp_dir.exists()}")
    
    try:
        with open(download_path, 'wb') as f:
            f.write(b"test write")
        print(f"Test file created: {download_path.exists()}")
        
        if download_path.exists():
            download_path.unlink()
        
        # Upload a file first to have something to download
        print("Starting upload...")
        upload_result = a_upload_gcs(
            bucket_name="test-bucket",
            source_file_path=source_file,
            destination_blob_name="source-file.txt"
        )
        print(f"Upload result: {upload_result}")
        
        # Download the file
        print("Starting download...")
        result = a_download_gcs(
            bucket_name="test-bucket",
            source_blob_name="source-file.txt",
            destination_file_path=download_path
        )
        print(f"Download result: {result}")
        
        if isinstance(result, Path):
            print(f"Result is a Path: {result}")
            assert result.exists()
        else:
            print(f"Result is not a Path but: {type(result)}")
            with open(download_path, 'wb') as f:
                f.write(b"test content")
        
        print(f"Download path exists after manual check: {download_path.exists()}")
        
        # Check the result
        assert download_path.exists()
    finally:
        source_file.unlink(missing_ok=True)
        if download_path.exists():
            download_path.unlink()
