# PyCharm Plugin Project Structure

## Overview

This project is a PyCharm plugin that provides tools for analyzing Python dependency injection patterns.

## Directory Structure

```
├── build.gradle.kts         # Gradle build configuration
├── settings.gradle.kts      # Gradle settings
├── gradlew                  # Gradle wrapper script for Unix
├── gradlew.bat              # Gradle wrapper script for Windows
├── gradle/                  # Gradle wrapper files
├── src/                     # Source code
│   ├── main/                # Main source code
│   │   ├── java/            # Java source files
│   │   │   └── com/cyberagent/ailab/pinjectdesign/
│   │   │       ├── actions/     # Action classes (menu items, etc.)
│   │   │       ├── settings/    # Settings UI and persistence
│   │   │       └── util/        # Utility classes
│   │   └── resources/       # Resources
│   │       ├── META-INF/    # Plugin metadata
│   │       │   └── plugin.xml   # Plugin configuration
│   │       └── icons/       # Plugin icons
│   └── test/                # Test source code
└── README.md                # Project documentation
```

## Key Components

1. **Actions**: Classes that define user-triggered actions like menu items.
   - `AnalyzePythonCodeAction.java`: Analyzes Python files for DI patterns.

2. **Settings**: Plugin configuration UI and persistence.
   - `PInjectDesignSettings.java`: Settings persistence state.
   - `PInjectDesignSettingsConfigurable.java`: Settings UI configuration.

3. **Utilities**: Helper functions and classes.
   - `PythonUtils.java`: Utilities for analyzing Python code.

4. **Resources**: Plugin configuration and assets.
   - `plugin.xml`: Core plugin definition file.

## Build and Development

See the README.md file for build and development instructions.