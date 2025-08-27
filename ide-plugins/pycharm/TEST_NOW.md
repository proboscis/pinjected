# Test IProxy Debug Output

## Run the Plugin

```bash
./gradlew runIde
```

## Create Test File

Create a Python file with this exact content:

```python
from pinjected import IProxy, injected

class User:
    name: str

def some_func():
    return IProxy()

# Test cases - watch the console output!
test_proxy: IProxy[int] = some_func()
user_proxy: IProxy[User] = IProxy()

@injected
def process_int(value: int) -> int:
    return value * 2

@injected
def process_user(user: User) -> str:
    return user.name
```

## What to Look For in Console

When you open the file, you should see in the **terminal where you ran `./gradlew runIde`**:

### 1. When the file loads:
```
[IProxyGutterIcon] Found potential target: test_proxy
[IProxyGutterIcon] Annotation for test_proxy: IProxy[int]
```
OR
```
[InjectedGutterIcon] Found injected target: test_proxy
```

This tells us which provider is detecting the variable.

### 2. When you click the gutter icon:
```
[IProxy Debug] Creating hierarchical menu for: test_proxy
[IProxy Debug] Element type: LeafPsiElement
[IProxy Debug] Element text: test_proxy
[IProxy Debug] Attempting to extract IProxy type...
[IProxy Debug] Direct parent PyTargetExpression: test_proxy
[IProxy Debug] Target expression annotation class: PySubscriptionExpressionImpl
[IProxy Debug] Annotation text: IProxy[int]
[IProxy Debug] Found IProxy type parameter: int
[IProxy Debug] Final extracted IProxy type: int
```

## The Problem We're Diagnosing

The issue is that `IProxy` is in the `INJECTED_TYPE_MARKERS` list, which means:
- `InjectedFunctionGutterIconProvider` detects it first
- `IProxyGutterIconProvider` never gets a chance to handle it

## What the Debug Output Will Tell Us

1. **Which provider is handling IProxy variables** - Look for either `[IProxyGutterIcon]` or `[InjectedGutterIcon]`

2. **Why type extraction might be failing** - Look for:
   - `Final extracted IProxy type: null` means extraction failed
   - `Final extracted IProxy type: int` means it worked

3. **Where in the extraction process it fails** - The debug messages show each step

## Next Steps Based on Output

**If you see `[InjectedGutterIcon]`:**
- The InjectedFunctionGutterIconProvider is handling it (expected)
- Check if type extraction works

**If type shows as `null`:**
- Look at which step failed in the extraction
- Share the full debug output

**If type shows correctly (e.g., `int`):**
- The extraction works, but the menu isn't showing functions
- Check if indexer is running

Share the console output and I'll know exactly what to fix!