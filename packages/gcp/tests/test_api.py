"""Tests for GCS API functions using real Google Cloud Storage."""

import tempfile
from pathlib import Path
import uuid

from pinjected.test import injected_pytest
from pinjected import instance


@instance
def test_bucket_name() -> str:
    """Use a test bucket."""
    # This bucket should exist and the service account should have permissions
    return "valued-mission-109412.appspot.com"


@instance
def test_prefix() -> str:
    """Create a unique test prefix to avoid conflicts."""
    return f"test-{uuid.uuid4().hex}/"


@injected_pytest
async def test_upload_gcs(
    a_upload_gcs, gcp_storage_client, test_bucket_name, test_prefix
):
    """Test uploading a file to GCS."""

    # Create a temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as temp:
        temp.write(b"test upload content")
        temp_path = Path(temp.name)

    blob_name = f"{test_prefix}test-upload.txt"

    try:
        result = await a_upload_gcs(
            bucket_name=test_bucket_name,
            source_file_path=temp_path,
            destination_blob_name=blob_name,
        )

        # Check the result
        assert (
            result == f"https://storage.googleapis.com/{test_bucket_name}/{blob_name}"
        )

        # Verify the file exists
        bucket = gcp_storage_client.bucket(test_bucket_name)
        blob = bucket.blob(blob_name)
        assert blob.exists()

    finally:
        temp_path.unlink(missing_ok=True)
        # Try to clean up
        try:
            bucket = gcp_storage_client.bucket(test_bucket_name)
            blob = bucket.blob(blob_name)
            blob.delete()
        except Exception:
            pass


@injected_pytest
async def test_download_gcs(
    a_upload_gcs, a_download_gcs, gcp_storage_client, test_bucket_name, test_prefix
):
    """Test downloading a file from GCS."""

    # Create source file
    test_content = b"test download content"
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as temp:
        temp.write(test_content)
        source_file = Path(temp.name)

    temp_dir = Path(tempfile.mkdtemp())
    download_path = temp_dir / "downloaded-file.txt"
    blob_name = f"{test_prefix}test-download.txt"

    try:
        # Upload a file first
        await a_upload_gcs(
            bucket_name=test_bucket_name,
            source_file_path=source_file,
            destination_blob_name=blob_name,
        )

        # Download the file
        result = await a_download_gcs(
            bucket_name=test_bucket_name,
            source_blob_name=blob_name,
            destination_file_path=download_path,
        )

        # Check the result
        assert result == download_path
        assert download_path.exists()
        assert download_path.read_bytes() == test_content
    finally:
        source_file.unlink(missing_ok=True)
        if download_path.exists():
            download_path.unlink()
        temp_dir.rmdir()
        # Clean up
        try:
            bucket = gcp_storage_client.bucket(test_bucket_name)
            blob = bucket.blob(blob_name)
            blob.delete()
        except Exception:
            pass


@injected_pytest
async def test_delete_gcs(
    a_upload_gcs, a_delete_gcs, gcp_storage_client, test_bucket_name, test_prefix
):
    """Test deleting a file from GCS."""

    # Create a temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as temp:
        temp.write(b"test delete content")
        temp_path = Path(temp.name)

    blob_name = f"{test_prefix}file-to-delete.txt"

    try:
        # Upload a file first
        await a_upload_gcs(
            bucket_name=test_bucket_name,
            source_file_path=temp_path,
            destination_blob_name=blob_name,
        )

        # Delete the file
        result = await a_delete_gcs(
            bucket_name=test_bucket_name,
            blob_name=blob_name,
        )

        # Check the result
        assert result is True

        # Try to delete the same file again (should return False)
        result = await a_delete_gcs(
            bucket_name=test_bucket_name,
            blob_name=blob_name,
        )

        # Should return False for non-existent file
        assert result is False
    finally:
        temp_path.unlink(missing_ok=True)


@injected_pytest
async def test_delete_gcs_prefix(
    a_upload_gcs, a_delete_gcs_prefix, gcp_storage_client, test_bucket_name, test_prefix
):
    """Test deleting multiple files under a prefix from GCS."""

    # Create a test file
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as temp:
        temp.write("test content for prefix deletion")
        temp_path = Path(temp.name)

    try:
        # Upload multiple files under different prefixes
        test_files = [
            f"{test_prefix}a/b/c/file1.txt",
            f"{test_prefix}a/b/c/d/file2.txt",
            f"{test_prefix}a/b/c/d/e/file3.txt",
            f"{test_prefix}a/b/x/file4.txt",
            f"{test_prefix}a/file5.txt",
        ]

        for blob_name in test_files:
            await a_upload_gcs(
                bucket_name=test_bucket_name,
                source_file_path=temp_path,
                destination_blob_name=blob_name,
            )

        # Delete all files under "a/b/c/"
        result = await a_delete_gcs_prefix(
            bucket_name=test_bucket_name,
            prefix=f"{test_prefix}a/b/c/",
        )

        # Should have deleted 3 files (file1.txt, file2.txt, file3.txt)
        assert result == 3

        # Test deleting with no trailing slash (should be added automatically)
        result = await a_delete_gcs_prefix(
            bucket_name=test_bucket_name,
            prefix=f"{test_prefix}a/b/x",
        )

        # Should have deleted 1 file (file4.txt)
        assert result == 1

        # Delete remaining file
        result = await a_delete_gcs_prefix(
            bucket_name=test_bucket_name,
            prefix=f"{test_prefix}a/",
        )

        # Should have deleted 1 file (file5.txt)
        assert result == 1

        # Test deleting non-existent prefix
        result = await a_delete_gcs_prefix(
            bucket_name=test_bucket_name,
            prefix=f"{test_prefix}non/existent/prefix/",
        )

        # Should return 0 for no files found
        assert result == 0

    finally:
        temp_path.unlink(missing_ok=True)
        # Clean up any remaining test files
        await a_delete_gcs_prefix(
            bucket_name=test_bucket_name,
            prefix=test_prefix,
        )


@injected_pytest
async def test_large_batch_delete(
    a_upload_gcs, a_delete_gcs_prefix, gcp_storage_client, test_bucket_name, test_prefix
):
    """Test batch deletion with many files (>100)."""

    # Create 120 files to test batch deletion (batch size is 100)
    num_files = 120
    blob_prefix = f"{test_prefix}batch-test/"

    # Create a single temp file to upload multiple times
    with tempfile.NamedTemporaryFile(delete=False) as temp:
        temp.write(b"Batch test content")
        temp_path = Path(temp.name)

    try:
        # Upload many files
        for i in range(num_files):
            blob_name = f"{blob_prefix}file-{i:04d}.txt"
            await a_upload_gcs(
                bucket_name=test_bucket_name,
                source_file_path=temp_path,
                destination_blob_name=blob_name,
            )

        # Delete all files with prefix
        delete_count = await a_delete_gcs_prefix(
            bucket_name=test_bucket_name,
            prefix=blob_prefix,
        )

        # Should have deleted all 120 files
        assert delete_count == num_files

    finally:
        temp_path.unlink(missing_ok=True)
        # Clean up any remaining files
        await a_delete_gcs_prefix(
            bucket_name=test_bucket_name,
            prefix=test_prefix,
        )
