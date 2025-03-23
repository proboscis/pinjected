# PInject Design PyCharm Plugin

A PyCharm plugin for Python dependency injection design.

## Features

- Analyze Python code structures
- Detect dependency injection patterns
- Suggest improvements for dependency management

## Development

### Prerequisites

- IntelliJ IDEA (Community or Ultimate) with the Gradle and Plugin Development plugins
- Java 17+
- Gradle 8.0+

### Building the Plugin

```bash
./gradlew buildPlugin
```

The plugin ZIP file will be created in `build/distributions/`.

### Running in Development Mode

```bash
./gradlew runIde
```

This will start a new PyCharm instance with the plugin installed.

### Plugin Structure

- `src/main/java`: Java source code
- `src/main/resources`: Resources including plugin.xml and icons
- `src/test`: Test sources

## Installation

- In PyCharm, go to Settings > Plugins > ⚙️ > Install Plugin from Disk...
- Select the ZIP file from `build/distributions/`
- Restart PyCharm

## Usage

1. Open a Python file
2. Go to Tools > Analyze Python Code
3. View the analysis results

## Configuration

In Settings > Tools > PInject Design, you can configure:

- Enable detailed analysis
- Check for dependencies