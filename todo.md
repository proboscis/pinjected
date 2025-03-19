# Implementation Todo for Module Helper Refactoring

## First Phase: Custom Exceptions

- [ ] Define custom exception classes:
  - [ ] `InvalidPythonFileError`: For invalid Python files
  - [ ] `ModulePathError`: For path-related issues
  - [ ] `ModuleLoadError`: For module loading failures
  - [ ] `ModuleAttributeError`: For attribute extraction issues
  - [ ] `SpecialFileError`: For special file processing issues

## Second Phase: Utility Functions

- [ ] Refactor `validate_python_file_path` to raise exceptions instead of returning tuples
- [ ] Fix `normalize_special_filenames` (rename from `_normalize_special_filenames`) for more explicit error handling
- [ ] Improve `get_module_name` to handle errors properly
- [ ] Enhance `build_module_hierarchy` with better validation

## Third Phase: Core Functions

- [ ] Rewrite `load_module_from_path` to follow guidelines
  - [ ] Ensure proper error propagation
  - [ ] Remove empty except blocks
- [ ] Fix `extract_module_attribute` to follow guidelines
- [ ] Update `find_special_files` to raise exceptions properly

## Fourth Phase: Processing Functions

- [ ] Rewrite `process_special_file` to ensure:
  - [ ] No silent error swallowing
  - [ ] Proper exception propagation
- [ ] Fix `process_directory` to:
  - [ ] Remove inappropriate try/except blocks
  - [ ] Ensure each exception is properly handled/raised
  - [ ] Remove continue statements

## Fifth Phase: Main Function

- [ ] Refactor `walk_module_with_special_files` to:
  - [ ] Validate inputs properly
  - [ ] Handle errors correctly (no silent failures)
  - [ ] Replace silent returns with exceptions
  - [ ] Remove continue statements
  - [ ] Ensure proper error propagation
  - [ ] Make sure exception blocks don't just log

## Sixth Phase: Testing

- [ ] Write unit tests to verify correct behavior
- [ ] Test error handling paths
- [ ] Ensure all exceptions are properly propagated

## Seventh Phase: Review and Validation

- [ ] Review code against all CLAUDE.md guidelines:
  - [ ] Function Design
    - [ ] Single responsibility
    - [ ] Max 50 lines per function
    - [ ] Appropriate return values
  - [ ] Control Flow
    - [ ] Verify no continue statements
    - [ ] Check nesting depth
  - [ ] Data Structures
    - [ ] Verify proper use of immutable dataclasses
    - [ ] Check type annotations
  - [ ] Error Handling
    - [ ] No empty exception handlers
    - [ ] No exception blocks with only logging
    - [ ] No silent returns from exception blocks
  - [ ] Functional Programming
    - [ ] Functions are free of side effects where possible
    - [ ] New values are returned instead of modifying existing ones
  - [ ] Code Structure
    - [ ] Clear separation of concerns
    - [ ] Dependencies are properly injected
  - [ ] Naming Conventions
    - [ ] Function names start with verbs
    - [ ] Variable names are specific and clear
  - [ ] Logging
    - [ ] No print statements
    - [ ] Appropriate logging