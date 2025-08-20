# Debugging IProxy Features in PyCharm Plugin

## Testing the Features

1. **Run the plugin:**
   ```bash
   ./gradlew runIde
   ```

2. **Open the test file:**
   - Open `test_iproxy_features.py` in the IDE
   - You should see gutter icons next to IProxy variables

3. **Enable Debug Logging:**
   - In the IDE, go to Help → Diagnostic Tools → Debug Log Settings
   - Add these categories:
     ```
     #com.proboscis.pinjectdesign.kotlin.lineMarkers.IProxyGutterIconProvider
     #com.proboscis.pinjectdesign.kotlin.util.GutterActionUtilEnhanced
     #com.proboscis.pinjectdesign.kotlin.hints.IProxyInlayHintsProvider
     #com.proboscis.pinjectdesign.kotlin.util.IProxyActionUtil
     ```

4. **Enable Inlay Hints (if not visible):**
   - Go to Settings → Editor → Inlay Hints
   - Look for "IProxy Actions" in the list
   - Make sure it's enabled
   - If not in list, try:
     - Settings → Editor → General → Code Completion
     - Enable "Show parameter name hints"

5. **Check the logs:**
   - Open Help → Show Log in Finder/Explorer
   - Open `idea.log`
   - Look for messages like:
     - "Found IProxy variable"
     - "Extracted IProxy type"
     - "Adding inlay hint for IProxy"

## Troubleshooting

### Issue: No "Find @injected Functions" menu
**Possible causes:**
1. IProxy type extraction failing
2. Element type mismatch

**Debug steps:**
1. Check logs for "Extracted IProxy type: null"
2. Look for "Element type:" in logs to see what's being passed
3. Verify annotation detection with "Annotation text:" logs

### Issue: No inline buttons
**Possible causes:**
1. Inlay hints not enabled in IDE
2. Provider not collecting hints
3. Settings disabled

**Debug steps:**
1. Check if IProxyInlayHintsProvider is loaded:
   - Look for "Creating inlay hints collector" in logs
2. Verify element detection:
   - Look for "Found PyTargetExpression" in logs
3. Check hint creation:
   - Look for "Adding inlay hint for IProxy" in logs

### Issue: Indexer not finding @injected functions
**Possible causes:**
1. Indexer not running
2. Query failing

**Debug steps:**
1. Check if pinjected-indexer is installed:
   ```bash
   which pinjected-indexer
   ```
2. Test indexer manually:
   ```bash
   pinjected-indexer query --type User --project-root .
   ```

## Manual Testing Checklist

- [ ] Gutter icons appear next to IProxy[T] variables
- [ ] Clicking gutter icon shows hierarchical menu
- [ ] Menu has "Run Configurations" group
- [ ] Menu has "Utilities" group  
- [ ] Menu has "Find @injected Functions" group (when IProxy type detected)
- [ ] @injected functions listed match the type parameter
- [ ] Inline [→] buttons appear after IProxy variables (if enabled)
- [ ] Clicking inline button shows same menu as gutter icon

## Expected Log Output

When working correctly, you should see:
```
Creating hierarchical menu for: test_proxy
Element type: LeafPsiElement
Element text: test_proxy
Found target expression: test_proxy
Target expression annotation: PySubscriptionExpressionImpl
Annotation text: IProxy[int]
Subscription operand: IProxy
Found IProxy type parameter: int
Extracted IProxy type: int
Detected IProxy[int] variable
```