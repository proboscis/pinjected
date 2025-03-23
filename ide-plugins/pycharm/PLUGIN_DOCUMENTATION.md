# Pinjected PyCharm Plugin Documentation

## Overview

The Pinjected PyCharm Plugin integrates the Pinjected dependency injection framework with PyCharm, providing enhanced IDE support for working with injected functions and variables. This plugin simplifies the development workflow when using the Pinjected framework by offering convenient run configurations, code navigation, and visualization tools.

## Features

### 1. Gutter Icons for Injected Functions/Variables

The plugin adds gutter icons (▶️) next to injected functions and variables in your Python code. Clicking on these icons provides a menu with the following actions:

- **Run [variable_name]**: Executes the injected function using the 'run' environment configuration (default)
- **Show [variable_name]**: Visualizes the result of the injected function (uses _viz configurations if available)
- **Make Sandbox**: Creates a sandbox file for experimenting with the injected function
- **Run [variable_name] in Interpreter**: Optional execution in the interpreter environment
- **Select Configuration**: Choose from available run configurations
- **Update Configuration**: Refresh the configuration cache

### 2. Code Completion and Navigation

- **Code Completion**: Provides intelligent code completion for injected functions and variables
- **Parameter Information**: Shows parameter information for injected functions
- **Go to Declaration**: Navigate to the declaration of injected functions and variables
- **Parameter Info Tooltips**: Displays tooltips with parameter information for injected functions

### 3. Run Actions

The plugin adds several actions to the Tools menu:

- **Find Injected Runnables**: Scans the current file for all injected functions and adds run configurations
- **Run Selected Injected**: Runs the injected variable at the current cursor position
- **Execute Test Script**: Executes a test script in the console

## Execution Environments

The plugin supports two execution environments for injected variables:

1. **Run Environment (Default)**: Executes the injected function using run configurations, providing a more integrated experience with PyCharm's run system.

2. **Interpreter Environment (Optional)**: Executes the injected function directly in the Python interpreter, which can be useful for debugging or when run configurations are not available.

## Installation

### From ZIP File

1. Build the plugin or download the latest release
2. In PyCharm, go to **Settings/Preferences** → **Plugins** → ⚙️ → **Install Plugin from Disk...**
3. Select the ZIP file from the build/distributions directory
4. Restart PyCharm when prompted

## Usage Guide

### Running Injected Functions

1. Look for the gutter icon (▶️) next to injected functions or variables
2. Click the icon to see available actions
3. Select "Run [variable_name]" to execute the function in the default environment
4. For alternative execution options, select one of the other actions from the menu

### Finding All Injected Functions

1. Go to **Tools** → **Find Injected Runnables**
2. The plugin will scan the current file and add run configurations for all injected functions
3. A notification will appear showing how many injected functions were found

### Creating a Sandbox

1. Click the gutter icon next to an injected function
2. Select "Make Sandbox"
3. A new file will be created with a sandbox environment for the selected function
4. The sandbox file will be opened automatically in the editor

### Visualizing Results

1. Click the gutter icon next to an injected function
2. Select "Show [variable_name]"
3. If a visualization configuration exists (ending with "_viz"), it will be used
4. Otherwise, the standard run configuration will be used

### Selecting Configurations

1. Click the gutter icon next to an injected function
2. Select "Select Configuration"
3. A popup will appear with available configurations
4. Select the desired configuration to run

## Configuration

In **Settings/Preferences** → **Tools** → **PInject Design**, you can configure:

- Python interpreter path
- Default run configurations
- Analysis settings

## Troubleshooting

### Common Issues

1. **No gutter icons appear**:
   - Ensure your Python file contains properly defined injected functions/variables
   - Check that the Pinjected framework is properly installed in your project
   - Verify that the plugin is enabled in PyCharm settings

2. **Run configurations fail**:
   - Verify that the Python interpreter is correctly configured
   - Check that all required dependencies are installed
   - Update the configuration cache using the "Update Configuration" action

3. **Plugin doesn't load**:
   - Check PyCharm's compatibility with the plugin version
   - Look for errors in the PyCharm logs (Help → Show Log in Explorer/Finder)

## Building from Source

### Prerequisites

- IntelliJ IDEA with the Gradle and Plugin Development plugins
- Java 17+
- Gradle 8.0+

### Build Steps

1. Clone the repository:
   ```bash
   git clone https://github.com/CyberAgentAILab/pinjected.git
   cd pinjected/ide-plugins/pycharm
   ```

2. Build the plugin using Gradle:
   ```bash
   ./gradlew clean build --refresh-dependencies
   ```

3. The built plugin will be available at:
   ```
   build/distributions/pinjected-pycharm-plugin-<version>.zip
   ```

### Running in Development Mode

```bash
./gradlew runIde
```

This will start a new PyCharm instance with the plugin installed for testing.

## Development

### Project Structure

- `src/main/kotlin/com/cyberagent/ailab/pinjectdesign/kotlin/`: Main plugin code
  - `actions/`: Action classes for menu items and toolbar buttons
  - `completion/`: Code completion contributors
  - `data/`: Data classes for configurations and actions
  - `handlers/`: Handlers for navigation and parameter info
  - `lineMarkers/`: Gutter icon providers
  - `util/`: Utility classes

### Key Components

- **InjectedFunctionActionHelper**: Core helper class for working with injected functions
- **GutterActionUtil**: Utility for creating and managing gutter actions
- **PinjectedConsoleUtil**: Utility for running injected functions in the console
- **InjectedFunctionGutterIconProvider**: Provides gutter icons for injected functions
- **FindInjectedRunnablesAction**: Action to find all injected functions in a file
- **RunSelectedInjectedAction**: Action to run the selected injected function
- **TestExecuteScriptAction**: Action to execute a test script

## Contributing

Contributions to the plugin are welcome! Please feel free to submit a Pull Request to the [Pinjected repository](https://github.com/CyberAgentAILab/pinjected).
