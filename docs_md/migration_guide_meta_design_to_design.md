# Migration Guide: From `__meta_design__` to `__design__` in Your Application

## Overview

This guide outlines the process for migrating your application from using `__meta_design__` to `__design__` in the Pinjected dependency injection framework. The Pinjected library is evolving its API, and this guide will help you update your codebase to use the new recommended approach.

## Why Migrate?

The Pinjected framework is introducing `__design__` in `__pinjected__.py` files as the preferred way to configure dependencies. This change offers several benefits:

1. **Improved Code Organization**: Centralizes dependency configurations in dedicated files
2. **Enhanced Maintainability**: Provides a more consistent approach to dependency management
3. **Future Compatibility**: Ensures your code remains compatible with future Pinjected releases
4. **Better IDE Support**: Improves IDE integration and tooling support

## Migration Steps

### 1. Identify Directories Using `__meta_design__`

First, identify all directories in your application that contain files with `__meta_design__` variables:

```bash
find . -type f -name "*.py" -exec grep -l "__meta_design__" {} \;
```

### 2. Create `__pinjected__.py` Files

For each directory identified, create a new `__pinjected__.py` file with both `__meta_design__` and `__design__` variables:

```python
from pinjected import design

# Keep existing meta_design for backward compatibility
__meta_design__ = design(
    # Copy the existing configuration from the original file
    # Example:
    overrides=design()
)

# Add new design with same configuration
__design__ = design(
    # Use the same configuration as __meta_design__
    # Example:
    overrides=design()
)
```

### 3. Configuration Patterns

Different applications may use different configuration patterns. Here are common patterns you might encounter:

#### Simple Overrides

```python
# Original __meta_design__ in your_module.py
__meta_design__ = design(
    overrides=design()
)

# New __pinjected__.py
from pinjected import design

__meta_design__ = design(
    overrides=design()
)

__design__ = design(
    overrides=design()
)
```

#### With Default Design Paths

```python
# Original __meta_design__ in your_module.py
__meta_design__ = design(
    default_design_paths=["your_app.module.path.to.design"],
    overrides=design()
)

# New __pinjected__.py
from pinjected import design

__meta_design__ = design(
    default_design_paths=["your_app.module.path.to.design"],
    overrides=design()
)

__design__ = design(
    default_design_paths=["your_app.module.path.to.design"],
    overrides=design()
)
```

#### With Custom Configuration Creators

```python
# Original __meta_design__ in your_module.py
__meta_design__ = design(
    custom_idea_config_creator=Injected.bind(your_config_creator_function)
)

# New __pinjected__.py
from pinjected import design
from pinjected import Injected
from your_app.module.path import your_config_creator_function

__meta_design__ = design(
    custom_idea_config_creator=Injected.bind(your_config_creator_function)
)

__design__ = design(
    custom_idea_config_creator=Injected.bind(your_config_creator_function)
)
```

### 4. Update References (Future Phase)

In a future phase, after all `__pinjected__.py` files are created and tested, you can update your code that references `__meta_design__` to use `__design__` instead.

## Testing Your Migration

After creating `__pinjected__.py` files, run your application's test suite to ensure backward compatibility:

```bash
# Example using pytest
pytest your_tests/
```

## Best Practices

1. **Maintain Backward Compatibility**: Keep the `__meta_design__` variable with the same configuration to ensure existing code continues to work.

2. **Identical Configurations**: Ensure that `__meta_design__` and `__design__` have identical configurations during the migration phase.

3. **Avoid Hardcoded Secrets**: Never include API keys or secrets directly in design configurations. Use environment variables or other secure methods instead.

4. **Document Your Changes**: Add comments to explain the migration and help other developers understand the dual configuration approach.

5. **Gradual Migration**: Migrate one module at a time, testing thoroughly after each change.

## Example Migration

### Before: Your Module with `__meta_design__`

```python
# your_app/services/__init__.py
from pinjected import design, Injected
from your_app.services.api import create_api_client

__meta_design__ = design(
    overrides=design(
        api_client=Injected.bind(create_api_client),
        cache_ttl=3600,
        debug_mode=False
    )
)
```

### After: New `__pinjected__.py` File

```python
# your_app/services/__pinjected__.py
from pinjected import design, Injected
from your_app.services.api import create_api_client

# Keep existing meta_design for backward compatibility
__meta_design__ = design(
    overrides=design(
        api_client=Injected.bind(create_api_client),
        cache_ttl=3600,
        debug_mode=False
    )
)

# Add new design with same configuration
__design__ = design(
    overrides=design(
        api_client=Injected.bind(create_api_client),
        cache_ttl=3600,
        debug_mode=False
    )
)
```

## Timeline and Phases

The Pinjected library will support this migration through several phases:

1. **Phase 1 (Current)**: Create `__pinjected__.py` files with both variables
2. **Phase 2 (Future)**: Update your code to reference `__design__` instead of `__meta_design__`
3. **Phase 3 (Future)**: Pinjected will add deprecation warnings for `__meta_design__`
4. **Phase 4 (Distant Future)**: Pinjected may remove `__meta_design__` support

## Conclusion

This migration is a gradual process designed to maintain backward compatibility while moving toward a more consistent dependency configuration approach. By following this guide, you can ensure a smooth transition to the new `__design__` standard in your application.

## Additional Resources

- [Pinjected Documentation](https://github.com/CyberAgentAILab/pinjected)
- [Dependency Injection Best Practices](https://github.com/CyberAgentAILab/pinjected/blob/main/docs_md/best_practices.md)
