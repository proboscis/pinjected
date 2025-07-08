# Exit Codes

The pinjected-dynamic-linter uses different exit codes to indicate various types of failures. This allows scripts and CI/CD pipelines to handle different error conditions appropriately.

## Exit Code Reference

| Code | Name | Description |
|------|------|-------------|
| 0 | SUCCESS | No violations found, or only warnings found (without `--error-on-warning`) |
| 1 | VIOLATIONS_FOUND | Linting violations found (errors, or warnings with `--error-on-warning`) |
| 2 | USAGE_ERROR | Invalid command-line arguments or usage |
| 3 | FILE_ERROR | File not found or I/O error |
| 4 | PARSE_ERROR | Python syntax error in analyzed files |
| 5 | CONFIG_ERROR | Configuration file parsing error |

## Examples

### Success (Exit Code 0)
```bash
$ pinjected-dynamic-linter clean_code.py
✓ No issues found!
$ echo $?
0
```

### Violations Found (Exit Code 1)
```bash
$ pinjected-dynamic-linter code_with_errors.py
code_with_errors.py:5:1: PINJ002: @instance function 'database' has default arguments
Exit code: 1
```

### File Not Found (Exit Code 3)
```bash
$ pinjected-dynamic-linter nonexistent.py
Error: Path not found: nonexistent.py
Exiting with code 3 due to file errors
$ echo $?
3
```

### Parse Error (Exit Code 4)
```bash
$ pinjected-dynamic-linter syntax_error.py
Error analyzing syntax_error.py: invalid syntax. Got unexpected token '(' at byte offset 61
Exiting with code 4 due to parse errors
$ echo $?
4
```

## Warning Handling

By default, warnings do not cause a non-zero exit code:

```bash
$ pinjected-dynamic-linter code_with_warnings.py
code_with_warnings.py:5:1: PINJ017: @instance function 'logger' has dependencies without type annotations
Exit code: 0
```

To treat warnings as errors, use the `--error-on-warning` flag:

```bash
$ pinjected-dynamic-linter code_with_warnings.py --error-on-warning
code_with_warnings.py:5:1: PINJ017: @instance function 'logger' has dependencies without type annotations
Exit code: 1
```

## Severity Filtering and Exit Codes

You can combine severity filtering with exit codes:

```bash
# Exit with code 1 only if errors are found (ignore warnings)
$ pinjected-dynamic-linter src/ --show-only error

# Exit with code 1 if warnings OR errors are found
$ pinjected-dynamic-linter src/ --error-on-warning

# Filter to show only errors, but still exit with appropriate code
$ pinjected-dynamic-linter src/ --severity error
```

## CI/CD Integration

Example GitHub Actions workflow:

```yaml
- name: Run pinjected linter
  run: |
    pinjected-dynamic-linter src/ --error-on-warning
  continue-on-error: false
```

Example shell script with error handling:

```bash
#!/bin/bash
pinjected-dynamic-linter src/
EXIT_CODE=$?

case $EXIT_CODE in
  0)
    echo "✅ Linting passed"
    ;;
  1)
    echo "❌ Linting violations found"
    exit 1
    ;;
  3)
    echo "❌ File errors encountered"
    exit 1
    ;;
  4)
    echo "❌ Parse errors in Python files"
    exit 1
    ;;
  *)
    echo "❌ Unknown error (exit code: $EXIT_CODE)"
    exit 1
    ;;
esac
```