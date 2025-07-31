# ALL Configuration Feature

The pinjected-linter now supports using `"ALL"` in the enable list to enable all available rules at once.

## Usage

In your `pyproject.toml`:

```toml
[tool.pinjected-linter]
# Enable all rules
enable = ["ALL"]

# Then disable specific rules you don't want
disable = ["PINJ001", "PINJ005", "PINJ015"]
```

## Benefits

1. **Easier Configuration**: No need to list every rule you want enabled
2. **Future-proof**: New rules are automatically included when using "ALL"
3. **Cleaner Config**: Focus on what you want to disable rather than listing everything to enable

## How It Works

When the linter detects `"ALL"` in the enable list:
1. It dynamically gets all available rule IDs from the rules module
2. Applies any rules in the disable list to filter them out
3. Results in a complete list of enabled rules

## Example

Before (explicit listing):
```toml
enable = ["PINJ002", "PINJ003", "PINJ004", "PINJ006", "PINJ007", "PINJ008", "PINJ009", "PINJ010", "PINJ011", "PINJ012", "PINJ013", "PINJ014", "PINJ016", "PINJ017", "PINJ018", "PINJ019", "PINJ026", "PINJ027", "PINJ028", "PINJ029"]
disable = ["PINJ001", "PINJ005", "PINJ015"]
```

After (with ALL):
```toml
enable = ["ALL"]
disable = ["PINJ001", "PINJ005", "PINJ015"]
```

Both configurations result in the same enabled rules, but the ALL version is much cleaner and will automatically include any new rules added in the future.