# Pinjected GCP

Google Cloud Platform bindings for the pinjected dependency injection framework.

## Installation

```bash
pip install pinjected-gcp
```

## Features

### Authentication
- Multiple authentication methods (service account file, dictionary, ADC)
- Shared credentials across all GCP services
- Automatic project ID detection

### Secret Manager
- Fetch secrets from GCP Secret Manager
- Async and sync operations
- In-memory caching with configurable TTL
- Secret management (create, list, delete)
- Version support

### Cloud Storage
- Upload/download files to/from GCS
- Async operations
- Batch deletion with prefix support
- Public URL generation

## Usage

### Secret Manager Example

```python
from pinjected import design, injected
from pinjected_gcp import (
    a_gcp_secret_value_cached,
    gcp_credentials_from_env,
)
from pathlib import Path

# Define your application function
@injected
async def fetch_api_keys(
    a_gcp_secret_value_cached,
    logger,
    /,
):
    # Fetch secret with caching (1 hour TTL by default)
    api_key = await a_gcp_secret_value_cached(
        secret_id="external-api-key"
    )
    
    # Fetch with custom TTL (5 minutes)
    db_password = await a_gcp_secret_value_cached(
        secret_id="database-password",
        cache_ttl=300  # 5 minutes
    )
    
    logger.info("Secrets fetched successfully")
    return {
        "api_key": api_key,
        "db_password": db_password,
    }

# Create a design with Application Default Credentials
di = design(
    gcp_credentials=gcp_credentials_from_env,
)

# Run using the CLI (recommended approach)
# python -m pinjected run your.module.fetch_api_keys
```

### Cloud Storage Example

```python
from pinjected import design, injected
from pinjected_gcp import a_upload_gcs, a_download_gcs
from pathlib import Path

# Define your application function
@injected
async def upload_and_download_example(
    a_upload_gcs,
    a_download_gcs,
    logger,
    /,
):
    # Upload a file to GCS
    upload_result = await a_upload_gcs(
        bucket_name="your-bucket",
        source_file_path=Path("local_file.txt"),
        destination_blob_name="remote_file.txt"
    )
    
    logger.info(f"Uploaded file URL: {upload_result}")
    
    # Download a file from GCS
    download_result = await a_download_gcs(
        bucket_name="your-bucket",
        source_blob_name="remote_file.txt",
        destination_file_path=Path("downloaded_file.txt")
    )
    
    logger.info(f"Downloaded file path: {download_result}")
    return download_result

# Run using the CLI
# python -m pinjected run your.module.upload_and_download_example
```

### Authentication Methods

```python
from pinjected import design
from pinjected_gcp.auth import (
    gcp_credentials_from_file,
    gcp_credentials_from_dict,
    gcp_credentials_from_env,
)
from pathlib import Path
import json

# Method 1: From service account file
file_auth_design = design(
    gcp_credentials=gcp_credentials_from_file,
    gcp_service_account_path=Path("~/.gcp/service-account.json"),
)

# Method 2: From environment (Application Default Credentials)
env_auth_design = design(
    gcp_credentials=gcp_credentials_from_env,
)

# Method 3: From dictionary
dict_auth_design = design(
    gcp_credentials=gcp_credentials_from_dict,
    gcp_service_account_dict=lambda: json.loads(
        Path("~/.gcp/service-account.json").expanduser().read_text()
    ),
)
```

## Module Structure

The package is organized into three main modules:

### `pinjected_gcp.auth`
- Credential management
- Multiple authentication methods
- Project ID detection

### `pinjected_gcp.secrets`
- Secret Manager client
- Async/sync secret access
- Caching layer
- Secret CRUD operations

### `pinjected_gcp.storage`
- Cloud Storage client
- File upload/download
- Batch operations
- Prefix-based deletion

## Advanced Usage

### Creating Application-Specific Secret Bindings

```python
from pinjected import IProxy
from pinjected_gcp import a_gcp_secret_value_cached

# Create IProxy bindings for your app's secrets
database_url: IProxy[str] = a_gcp_secret_value_cached(
    secret_id="database-url"
)

api_key: IProxy[str] = a_gcp_secret_value_cached(
    secret_id="external-api-key"
)

jwt_secret: IProxy[str] = a_gcp_secret_value_cached(
    secret_id="jwt-signing-secret"
)

# Use these in your design
app_design = design(
    database_url=database_url,
    api_key=api_key,
    jwt_secret=jwt_secret,
)
```

### Cache Management

```python
from pinjected_gcp.secrets.cache import (
    clear_secret_cache,
    get_cache_stats,
)

# Clear all cached secrets
num_cleared = clear_secret_cache()
print(f"Cleared {num_cleared} cached secrets")

# Get cache statistics
stats = get_cache_stats()
print(f"Cache has {stats['total_entries']} entries")
for entry in stats['entries']:
    print(f"  - {entry['secret_id']}: {entry['age_seconds']:.1f}s old")
```

## Requirements

- Python 3.10+
- pinjected
- google-cloud-storage>=2.0.0
- google-cloud-secret-manager>=2.24.0
- google-auth>=2.0.0

## License

MIT