# Migrate IDE plugins from meta_main to pinjected run command

## Summary

Both PyCharm/IntelliJ and VSCode plugins currently use the deprecated `meta_main` entry point to create IDE configurations. They should be migrated to use the standard `pinjected run` command instead.

## Current State

### PyCharm/IntelliJ Plugin
```kotlin
// In InjectedFunctionActionHelper.kt:72
val args = "-m pinjected.meta_main pinjected.ide_supports.create_configs.create_idea_configurations $modulePath".split(" ")
```

### VSCode Plugin
```typescript
// In extension.ts:310
const result = await execAsync(`${python_path} -m pinjected.meta_main pinjected.ide_supports.create_configs.create_idea_configurations "${filePath}"`);
```

### Issues with Current Approach
1. `meta_main` is a legacy entry point that should be deprecated
2. Neither plugin passes the `design_path` parameter, relying on our backward compatibility fix
3. The command structure is inconsistent with how pinjected is normally used

## Proposed Solution

### 1. Short-term Fix (Already Implemented)
- ✅ Made `run_with_meta_context` use `pinjected_internal_design` by default when `design_path` is not provided
- ✅ Added deprecation warnings to `meta_main`
- ✅ Added tests to verify backward compatibility

### 2. Long-term Migration

#### Option A: Direct pinjected run command
```bash
# Instead of:
python -m pinjected.meta_main pinjected.ide_supports.create_configs.create_idea_configurations <file_path>

# Use:
pinjected run pinjected.ide_supports.create_configs.create_idea_configurations --module-path <file_path> --design pinjected.ide_supports.default_design.pinjected_internal_design
```

#### Option B: Create a dedicated IDE command
```bash
# Add a new command specifically for IDE integration:
pinjected ide-config <file_path>

# Or:
pinjected create-configs <file_path> --format idea
```

### 3. Refactor create_idea_configurations

The function needs to be refactored to work better with `pinjected run`:

```python
# Current signature (uses positional args which don't work well with CLI)
@injected
def create_idea_configurations(
    inspect_and_make_configurations,
    module_path: Path,
    print_to_stdout,
    /,
    wrap_output_with_tag=True,
):
    ...

# Proposed: Make it more CLI-friendly
@injected
def create_idea_configurations(
    inspect_and_make_configurations,
    print_to_stdout,
    /,
    module_path: Path | None = None,  # Get from context if not provided
    wrap_output_with_tag: bool = True,
    output_format: str = "json",  # json, yaml, etc.
):
    # If module_path not provided, get from context
    if module_path is None:
        module_path = get_current_module_path()  # From injection context
    ...
```

## Migration Plan

### Phase 1: Prepare pinjected (Current Release)
- [x] Add default design support to `run_with_meta_context`
- [x] Add deprecation warnings
- [x] Ensure backward compatibility
- [ ] Add new CLI commands for IDE integration
- [ ] Document the new approach

### Phase 2: Update IDE Plugins (Next Release)
- [ ] Update PyCharm/IntelliJ plugin to use new command
- [ ] Update VSCode plugin to use new command
- [ ] Add version detection to support both old and new pinjected versions
- [ ] Test with various pinjected versions

### Phase 3: Remove Deprecated Code (Future Release)
- [ ] Remove `meta_main.py` 
- [ ] Remove backward compatibility code
- [ ] Update documentation

## Testing Requirements

1. **Backward Compatibility Tests**
   - Old IDE plugins with new pinjected ✅
   - New IDE plugins with old pinjected (needs version detection)

2. **Integration Tests**
   - Test new command structure with both IDE plugins
   - Verify all configuration types are created correctly
   - Test error handling and edge cases

## Benefits

1. **Consistency**: Uses standard pinjected command structure
2. **Clarity**: Explicit design specification instead of hidden defaults
3. **Flexibility**: Easier to add new features and options
4. **Maintainability**: Removes special-case code for IDE integration

## Related Files

- `/Users/s22625/repos/pinjected/pinjected/meta_main.py` - To be deprecated
- `/Users/s22625/repos/pinjected/pinjected/ide_supports/create_configs.py` - Needs refactoring
- `/Users/s22625/repos/pinjected/ide-plugins/pycharm/src/main/kotlin/com/proboscis/pinjectdesign/kotlin/InjectedFunctionActionHelper.kt` - Needs update
- `/Users/s22625/repos/pinjected/vscode-plugin/pinjected-runner/src/extension.ts` - Needs update

## Acceptance Criteria

- [ ] IDE plugins can create configurations using `pinjected run` command
- [ ] No regression in functionality
- [ ] Clear migration path documented
- [ ] Version compatibility handled gracefully
- [ ] All tests pass with new implementation