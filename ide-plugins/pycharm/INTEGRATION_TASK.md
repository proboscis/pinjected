# Integration Task: InjectedFunctionActionHelper for PyCharm Plugin

## Overview

This task involves integrating the `InjectedFunctionActionHelper` from the existing Kotlin OpenAI plugin into the new PyCharm plugin. The helper provides functionality for running Python code with dependency injection features, managing configurations, and executing code in the console.

## Source Analysis

### Kotlin OpenAI Plugin (`intellij-openai-kotlint/kotlin-openai`)

**Key components:**

1. **InjectedFunctionActionHelper**: A helper class that provides:
   - Creation and execution of Python run configurations
   - Finding Python configurations for files with injection points
   - Running Python code with proper environment setup
   - Background task management
   - Caching mechanisms for configurations

2. **Supporting classes**:
   - `PyConfiguration`: Data class for Python run configuration details
   - `ConfigurationWrapper`: Wrapper for multiple configurations
   - `CustomCompletion`: Data class for code completion items
   - `DesignMetadata`: Data class for design metadata
   - `ActionItem`: Represents an action that can be executed
   - `PinjectedConsoleUtil`: Utility for running injected code in the console

3. **Features provided by this code**:
   - Console execution for Python scripts
   - Run configuration generation
   - Dependency injection detection and handling
   - Caching of configurations for better performance
   - Background task processing

### PInject Design PyCharm Plugin (`pinject-design/ide-plugins/pycharm`)

**Current structure:**
- Basic PyCharm plugin for analyzing Python code
- Focuses on detecting dependency injection patterns
- Has configuration UI and action handling
- Uses Java implementation instead of Kotlin

## Integration Tasks

1. **Add Kotlin Support**
   - Add Kotlin dependencies to the Gradle build script
   - Configure Kotlin compiler settings

2. **Port InjectedFunctionActionHelper**
   - Create a Kotlin version compatible with the Java PyCharm plugin
   - Adapt the helper to work with the PyCharm plugin architecture
   - Ensure proper dependency resolution

3. **Add Required Data Classes**
   - Port `PyConfiguration`, `ConfigurationWrapper`, etc.
   - Adapt serialization handling

4. **Create Actions for Injected Functions**
   - Add action for running selected injected functions
   - Add action for testing scripts in console
   - Register actions in plugin.xml

5. **Add Extension Points**
   - Configure parameter info handler
   - Add code completion contributor if needed
   - Set up goto declaration handler

6. **Update Plugin Dependencies**
   - Ensure all required dependencies are properly declared
   - Check compatibility with PyCharm 2024.3.5

7. **Implement Console Execution**
   - Port the console execution functionality
   - Ensure proper Python environment setup

8. **Testing and Integration**
   - Test with sample Python code containing injected functions
   - Verify all features work properly in PyCharm

## Requirements

1. **Maintain Compatibility**: The integrated code must work with PyCharm 2024.3.5.
2. **Keep Structure**: Follow the existing package structure of the PyCharm plugin.
3. **Dependencies**: Ensure all required dependencies are properly handled.
4. **Documentation**: Update documentation to reflect new features.

## Implementation Approach

1. **Gradual Integration**: Add features one by one, starting with the core helper.
2. **Compatibility Layer**: Create adapters between Java and Kotlin code if needed.
3. **Testing**: Test each feature as it's integrated.

## Deliverables

1. Updated Gradle build script with Kotlin support
2. Ported InjectedFunctionActionHelper and related classes
3. New actions for injected function handling
4. Updated plugin.xml with new extensions and actions
5. Updated documentation describing new features