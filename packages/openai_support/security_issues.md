# Security Issues in pinjected-openai

This document tracks potential security issues and hardcoded secrets found in the pinjected-openai repository.

## Summary

After a thorough review of the codebase, the following issues were identified:

1. **API Key Storage in Plaintext File** - Low Severity
2. **Hardcoded File Path in Test Code** - Low Severity

No direct hardcoded API keys or critical secrets were found in the codebase.

## Detailed Findings

### 1. API Key Storage in Plaintext File

**File:** `pinjected_openai/clients.py`  
**Line:** 16-22  
**Severity:** Low  
**Type:** Security Best Practice

**Description:**  
The OpenAI API key is retrieved from either an environment variable or a plaintext file in the user's home directory:

```python
@instance
def openai_api_key() -> str:
    from loguru import logger
    logger.warning(f"using openai api key from environment variable or ~/.openai_api_key.txt")
    if (api_key := os.environ.get('OPENAI_API_KEY', None)) is None:
        api_key = Path(os.path.expanduser("~/.openai_api_key.txt")).read_text().strip()
    return api_key
```

While this is not a hardcoded API key, storing API keys in plaintext files in the home directory is not a recommended security practice. API keys should be stored in a secure credential manager or environment variables.

**Recommendation:**
1. Remove the fallback to reading from a plaintext file
2. Use a secure credential manager or keyring library
3. Add documentation recommending users to set the environment variable instead of creating a plaintext file

### 2. Hardcoded File Path in Test Code

**File:** `pinjected_openai/whisper.py`  
**Line:** 202-205  
**Severity:** Low  
**Type:** Configuration Issue

**Description:**  
There is a hardcoded file path in a design object used for testing:

```python
with design(
        input_file='/Users/s22625/Downloads/2024.10.15 13.56 Backtrack.mp4'
):
    test_transcribe_mp4: IProxy = cmd_save_transcribe
```

This is a hardcoded path to a specific MP4 file in the user's Downloads directory. While this isn't a secret or API key, it's a hardcoded path that could cause issues if the code is run on a different system or if the file is moved or deleted.

**Recommendation:**
1. Use a relative path or a path that's configurable
2. Consider using a sample file that's included in the repository for testing
3. If the test requires a specific file, document this requirement and provide instructions for obtaining or creating the file

## Conclusion

The codebase generally follows good security practices by not hardcoding API keys directly in the source code. The identified issues are of low severity but addressing them would improve the security posture and portability of the codebase.

## Next Steps

1. Create GitHub issues for each finding
2. Prioritize and address the issues in upcoming releases
3. Consider implementing a security scanning tool in the CI/CD pipeline to prevent similar issues in the future