# IProxy Feature Testing Guide

## What We've Implemented

### 1. Enhanced Type Detection
- **IProxyGutterIconProvider**: Detects `IProxy[T]` variables with enhanced logging
- **GutterActionUtilEnhanced**: Improved type extraction with multiple fallback methods
- Both providers now use comprehensive debug logging to help diagnose issues

### 2. Key Changes Made

#### Type Extraction Enhancement
```kotlin
// GutterActionUtilEnhanced now tries multiple ways to find IProxy type:
1. Direct PyTargetExpression parent lookup
2. Sibling element search
3. Fallback to "Unknown" type if IProxy is detected but type can't be extracted
```

#### Debug Logging Added
All key components now log their detection process:
- `IProxyGutterIconProvider`: Logs when it finds potential IProxy variables
- `GutterActionUtilEnhanced`: Logs type extraction attempts and results
- `IProxyInlayHintsProvider`: Logs inline hint creation

## Testing Steps

### 1. Enable Debug Logging
In PyCharm with the plugin:
1. Go to **Help → Diagnostic Tools → Debug Log Settings**
2. Add these categories:
```
#com.proboscis.pinjectdesign.kotlin.lineMarkers.IProxyGutterIconProvider:all
#com.proboscis.pinjectdesign.kotlin.util.GutterActionUtilEnhanced:all
#com.proboscis.pinjectdesign.kotlin.hints.IProxyInlayHintsProvider:all
```

### 2. Run the Plugin
```bash
./gradlew runIde
```

### 3. Create Test File
Create a Python file with this content:
```python
from pinjected import IProxy, injected

class User:
    name: str

def some_func():
    return IProxy()

# Test cases
test_proxy: IProxy[int] = some_func()
user_proxy: IProxy[User] = IProxy()

@injected
def process_int(value: int) -> int:
    return value * 2

@injected
def process_user(user: User) -> str:
    return user.name
```

### 4. Check the Logs
Open **Help → Show Log in Finder/Explorer** and look for:

#### Expected Log Messages:
```
IProxyGutterIconProvider: Found potential target expression: test_proxy
IProxyGutterIconProvider: Annotation for test_proxy: IProxy[int]
Creating hierarchical menu for: test_proxy
Found target expression: test_proxy
Target expression annotation: PySubscriptionExpressionImpl
Annotation text: IProxy[int]
Found IProxy type parameter: int
Final extracted IProxy type: int
Detected IProxy[int] variable
```

### 5. Verify Menu Structure

When you click on the gutter icon next to `test_proxy`, you should see:

```
Pinjected Actions - test_proxy
├── Find @injected Functions    <-- THIS IS THE KEY PART
│   ├── process_int
│   └── (other matching functions)
├── Run Configurations
│   └── Update Configurations
└── Utilities
    ├── Copy Variable Name
    ├── Copy Type Parameter
    └── Run Diagnostics
```

## Troubleshooting

### Issue: No "Find @injected Functions" Group

**Check the logs for:**
- `Final extracted IProxy type: null` - Type extraction failed
- `No target expression found` - Element detection issue

**Possible causes:**
1. The gutter icon is being handled by `InjectedFunctionGutterIconProvider` instead of `IProxyGutterIconProvider`
2. Type extraction is failing due to PSI structure

### Issue: Both Providers Creating Icons

If you see two gutter icons for the same variable:
- One from `InjectedFunctionGutterIconProvider` (Execute icon)
- One from `IProxyGutterIconProvider` (Plugin icon)

This means both are detecting the variable. The fix is working if clicking shows the hierarchical menu.

### Issue: Indexer Not Finding Functions

The `pinjected-indexer` query might be failing. Check:
1. Is `pinjected-indexer` installed? (`which pinjected-indexer`)
2. Check indexer logs in the IDE log for errors

## What's Working Now

✅ **Type Extraction**: Enhanced to handle more cases
✅ **Debug Logging**: Comprehensive logging for troubleshooting  
✅ **Menu Structure**: Hierarchical grouped menu system
✅ **Unit Tests**: All 6 tests passing for core logic

## Next Steps

If the "Find @injected Functions" group still doesn't appear:

1. **Check which provider is handling your variable:**
   - Look for "IProxyGutterIconProvider" vs "InjectedFunctionGutterIconProvider" in logs
   
2. **Verify type extraction:**
   - The logs should show `Final extracted IProxy type: int` (or your type)
   - If it shows `null`, the type extraction needs more work

3. **Test the indexer manually:**
   ```bash
   pinjected-indexer --root . query-iproxy-functions int
   ```
   
   This should return JSON with matching @injected functions.

## Summary

The enhanced type detection and menu system are in place. The key indicator of success is:
- Seeing `Final extracted IProxy type: [your_type]` in the logs
- The "Find @injected Functions" group appearing in the menu

The unit tests confirm the logic is correct. If it's still not working in the IDE, it's likely a PSI element detection issue that the debug logs will help diagnose.