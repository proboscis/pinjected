# Changelog

All notable changes to the pinjected-openai project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.2-beta.2] - 2025-03-23

### Changed
- Bumped beta version for PyPI publishing

## [1.0.2-beta.1] - 2025-03-22

### Changed
- Added beta prefix to version for PyPI publishing preparation

## [1.0.2] - 2025-03-02

### Added
- Added new `is_gemini_compatible` function to check Pydantic models for compatibility with Google Gemini API's more restrictive schema requirements
- Implemented custom exception classes `SchemaCompatibilityError`, `OpenAPI3CompatibilityError`, and `GeminiCompatibilityError` for better error handling
- Added Gemini compatibility checks in `a_openrouter_chat_completion` and `a_llm__openrouter` functions when using Gemini models
- Created comprehensive test cases for schema compatibility with different model patterns

### Changed
- Enhanced dictionary compatibility checking to properly handle different key and value types
- Improved error messages to be more specific about compatibility issues

## [1.0.1] - 2025-03-02

### Added
- Improved documentation

## [1.0.0] - 2025-03-02

### Added
- Initial stable release
