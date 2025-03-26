.PHONY: setup-gradle build-plugin run-ide clean all

# Default target
all: setup-gradle build-plugin

# Setup Gradle dependencies
setup-gradle:
	@echo "Setting up Gradle dependencies..."
	chmod +x ./gradlew
	./gradlew --refresh-dependencies

# Build the plugin
build-plugin: setup-gradle
	@echo "Building the PyCharm plugin..."
	./gradlew clean build buildPlugin

# Run the plugin in development mode
run-ide: setup-gradle
	@echo "Running PyCharm with the plugin installed..."
	./gradlew runIde

# Clean the build directories
clean:
	@echo "Cleaning build directories..."
	./gradlew clean
