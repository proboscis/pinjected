# PyCharm Plugin Testing Guide

This guide covers comprehensive testing approaches for the IProxy[T] PyCharm plugin, including unit tests, integration tests, UI automation, and manual testing procedures.

## Table of Contents
1. [Test Architecture](#test-architecture)
2. [Running Tests](#running-tests)
3. [Debugging Tests](#debugging-tests)
4. [Manual Testing Procedures](#manual-testing-procedures)
5. [CI/CD Integration](#cicd-integration)

## Test Architecture

### Test Levels

1. **Unit Tests** - Test individual components in isolation
   - `IProxyGutterIconProviderSimpleTest` - Basic provider functionality
   - `IProxyActionUtilSimpleTest` - JSON serialization and data classes
   - `IndexerIntegrationTest` - Mock server integration

2. **Functional Tests** - Test with simulated IDE environment
   - `IProxyFunctionalTest` - Full project simulation with indexing
   - Tests actual Python file parsing and gutter icon detection

3. **Debugger Tests** - Test debugging functionality
   - `IProxyDebuggerTest` - Breakpoints in @injected functions
   - Variable inspection and stepping

4. **UI Tests** - Automated UI testing
   - `IProxyUITest` - Remote Robot UI automation
   - Full user interaction simulation

## Running Tests

### Prerequisites

```bash
# Install the indexer globally
cd packages/pinjected-indexer
cargo install --path .

# Build the plugin
cd ide-plugins/pycharm
./gradlew build
```

### Run All Tests

```bash
# Run all plugin tests
./gradlew test

# Run specific test class
./gradlew test --tests "*.IProxyFunctionalTest"

# Run with detailed output
./gradlew test --info

# Generate test report
./gradlew test jacocoTestReport
```

### Run UI Tests with Remote Robot

1. **Install Robot Server Plugin in PyCharm:**
   - File → Settings → Plugins
   - Search for "Robot Server Plugin"
   - Install and restart

2. **Start PyCharm with Robot Server:**
   ```bash
   # macOS
   /Applications/PyCharm.app/Contents/MacOS/pycharm -Drobot-server.port=8082
   
   # Windows
   pycharm64.exe -Drobot-server.port=8082
   
   # Linux
   pycharm.sh -Drobot-server.port=8082
   ```

3. **Run UI tests:**
   ```bash
   ./gradlew test --tests "*.IProxyUITest"
   ```

## Debugging Tests

### Debug in IntelliJ IDEA

1. Open the project in IntelliJ IDEA
2. Right-click on test class → Debug
3. Set breakpoints in test or production code
4. Use debugger to step through

### Debug the Plugin in PyCharm

1. **Create Plugin Run Configuration:**
   - Run → Edit Configurations
   - Add → Gradle
   - Task: `:runIde`
   - Click OK

2. **Debug the Plugin:**
   - Click Debug button
   - A new PyCharm instance launches with plugin
   - Set breakpoints in plugin code
   - Interact with the test PyCharm instance

### Debug with Logs

```kotlin
// Add logging in your code
private val LOG = Logger.getInstance(IProxyGutterIconProvider::class.java)
LOG.debug("Found IProxy variable: $variableName")

// View logs in: Help → Show Log in Finder/Explorer
```

## Manual Testing Procedures

### Test Case 1: Basic IProxy Gutter Icon Display

**Setup:**
1. Install the plugin in PyCharm
2. Create a new Python project
3. Install pinjected: `pip install pinjected`

**Steps:**
1. Create a new Python file `test_iproxy.py`
2. Add the following code:
   ```python
   from pinjected import IProxy, injected, Protocol
   
   class User:
       def __init__(self, name: str):
           self.name = name
   
   # Should show gutter icon here →
   user_proxy: IProxy[User] = IProxy()
   ```

**Expected Result:**
- Gutter icon appears next to line 8 (user_proxy line)
- Icon tooltip shows: "IProxy[User]: Find @injected functions"

### Test Case 2: Clicking Gutter Icon Shows Functions

**Prerequisite:** Complete Test Case 1

**Steps:**
1. Add an @injected function to the file:
   ```python
   class ProcessUserProtocol(Protocol):
       def __call__(self) -> str: ...
   
   @injected(protocol=ProcessUserProtocol)
   def process_user(user: User) -> str:
       return f"Processing {user.name}"
   ```
2. Save the file
3. Wait 2 seconds for indexing
4. Click the gutter icon next to `user_proxy`

**Expected Result:**
- Dropdown menu appears showing:
  - "process_user (test_iproxy)"
  - Function location and docstring

### Test Case 3: Complex Type Parameters

**Steps:**
1. Create file with complex types:
   ```python
   from pinjected import IProxy
   from typing import List, Dict, Optional
   
   list_proxy: IProxy[List[User]] = IProxy()
   dict_proxy: IProxy[Dict[str, User]] = IProxy()
   optional_proxy: IProxy[Optional[User]] = IProxy()
   ```

**Expected Result:**
- Three gutter icons appear
- Each shows correct type in tooltip

### Test Case 4: Debugging @injected Functions

**Steps:**
1. Create a runnable script:
   ```python
   from pinjected import IProxy, injected, Protocol
   
   class User:
       def __init__(self, name: str):
           self.name = name
   
   class ProcessProtocol(Protocol):
       def __call__(self) -> str: ...
   
   @injected(protocol=ProcessProtocol)
   def process_user(user: User) -> str:
       result = f"Processing {user.name}"  # Set breakpoint here
       return result
   
   if __name__ == "__main__":
       test_user = User("Alice")
       print(process_user(test_user))
   ```

2. Set breakpoint on line 12 (inside process_user)
3. Right-click → Debug 'test_script'

**Expected Result:**
- Debugger stops at breakpoint
- Variables panel shows:
  - `user` object with name="Alice"
  - `result` string value
- Step over/into/out work correctly

### Test Case 5: Multi-Module Project

**Setup:**
1. Create project structure:
   ```
   project/
   ├── models/
   │   └── user.py
   ├── services/
   │   └── user_service.py
   └── main.py
   ```

2. In `models/user.py`:
   ```python
   class User:
       def __init__(self, id: int, name: str):
           self.id = id
           self.name = name
   ```

3. In `services/user_service.py`:
   ```python
   from pinjected import injected, Protocol
   from models.user import User
   
   class GetUserProtocol(Protocol):
       def __call__(self) -> User: ...
   
   @injected(protocol=GetUserProtocol)
   def get_user_by_id(user_id: int) -> User:
       return User(user_id, f"User_{user_id}")
   ```

4. In `main.py`:
   ```python
   from pinjected import IProxy
   from models.user import User
   
   current_user: IProxy[User] = IProxy()
   ```

**Steps:**
1. Open `main.py`
2. Click gutter icon next to `current_user`

**Expected Result:**
- Dropdown shows `get_user_by_id` from services module
- Function location shows correct file path

### Test Case 6: Performance Test

**Setup:**
1. Create a large project with 100+ Python files
2. Add 50+ @injected functions
3. Add 20+ IProxy variables

**Steps:**
1. Open a file with IProxy variables
2. Click gutter icon
3. Measure response time

**Expected Result:**
- Dropdown appears in < 200ms (warm cache)
- First query takes < 500ms (cold cache)

### Test Case 7: Edge Cases

**Test missing indexer:**
1. Uninstall pinjected-indexer
2. Click gutter icon
3. **Expected:** Error notification with helpful message

**Test invalid type parameter:**
```python
user_proxy: IProxy = IProxy()  # No type parameter
```
**Expected:** Gutter icon shows with "Any" type

**Test class member (should be ignored):**
```python
class MyClass:
    user_proxy: IProxy[User] = IProxy()  # No gutter icon
```
**Expected:** No gutter icon for class members

## CI/CD Integration

### GitHub Actions Workflow

Create `.github/workflows/plugin-test.yml`:

```yaml
name: Plugin Tests

on:
  push:
    paths:
      - 'ide-plugins/pycharm/**'
  pull_request:
    paths:
      - 'ide-plugins/pycharm/**'

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up JDK 17
      uses: actions/setup-java@v3
      with:
        java-version: '17'
        distribution: 'temurin'
    
    - name: Install Rust
      uses: actions-rs/toolchain@v1
      with:
        toolchain: stable
    
    - name: Build Indexer
      run: |
        cd packages/pinjected-indexer
        cargo build --release
        cargo install --path .
    
    - name: Run Plugin Tests
      run: |
        cd ide-plugins/pycharm
        ./gradlew test
    
    - name: Upload Test Results
      uses: actions/upload-artifact@v3
      if: always()
      with:
        name: test-results
        path: ide-plugins/pycharm/build/reports/tests/
    
    - name: Generate Coverage Report
      run: |
        cd ide-plugins/pycharm
        ./gradlew jacocoTestReport
    
    - name: Upload Coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        files: ./ide-plugins/pycharm/build/reports/jacoco/test/jacocoTestReport.xml
```

### Local Pre-commit Testing

Add to `.git/hooks/pre-commit`:

```bash
#!/bin/bash
echo "Running plugin tests..."
cd ide-plugins/pycharm
./gradlew test --daemon

if [ $? -ne 0 ]; then
    echo "Tests failed! Commit aborted."
    exit 1
fi
```

## Test Coverage Goals

- **Unit Tests:** 80% code coverage
- **Integration Tests:** All major workflows
- **UI Tests:** Critical user paths
- **Manual Tests:** Before each release

## Troubleshooting

### Common Issues

1. **Tests fail with "indexer not found"**
   - Solution: `cargo install --path packages/pinjected-indexer`

2. **UI tests timeout**
   - Solution: Increase timeout in test configuration
   - Check Robot Server is running on correct port

3. **Debugger tests fail**
   - Solution: Ensure Python interpreter is configured
   - Check PyCharm has debugging enabled

4. **Gutter icons don't appear**
   - Solution: Rebuild project and restart IDE
   - Check plugin.xml has lineMarkerProvider registered

## Performance Benchmarks

| Operation | Target | Actual |
|-----------|--------|--------|
| Gutter icon detection | < 50ms | ~30ms |
| Indexer query (warm) | < 100ms | ~10ms |
| Indexer query (cold) | < 500ms | ~130ms |
| Dropdown display | < 200ms | ~150ms |
| Debug breakpoint hit | < 1s | ~800ms |

## Contact

For issues or questions about testing:
- Create issue in GitHub repository
- Contact plugin maintainers
- Check CI/CD logs for automated test results