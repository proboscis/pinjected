# Git Tag Best Practices for Library Development

This document outlines best practices for using git tags during the development of the `pinjected-openai` library.

## Table of Contents

1. [Semantic Versioning and Git Tags](#semantic-versioning-and-git-tags)
2. [When to Create Tags](#when-to-create-tags)
3. [Tag Creation Process](#tag-creation-process)
4. [Tag Content Best Practices](#tag-content-best-practices)
5. [Release Workflow Integration](#release-workflow-integration)
6. [Automation Options](#automation-options)
7. [Tag Management](#tag-management)
8. [Example GitHub Workflow](#example-github-workflow)

## Semantic Versioning and Git Tags

Git tags should align with [Semantic Versioning](https://semver.org/) (SemVer) principles:

- Use the format: `MAJOR.MINOR.PATCH`
  - **MAJOR**: Increment for incompatible API changes
  - **MINOR**: Increment for backward-compatible new features
  - **PATCH**: Increment for backward-compatible bug fixes

- Prefix tags with 'v' for clarity (e.g., `v0.4.37`)
- Pre-release versions can use suffixes like `-alpha.1`, `-beta.2`, `-rc.1`

## When to Create Tags

- Create a tag for each published release of the library
- Tag only stable, tested commits that are ready for users
- Create tags after merging to the main/master branch, not on feature branches
- Tag immediately before or after publishing to PyPI
- Consider creating tags for significant pre-releases that users might want to reference

## Tag Creation Process

```bash
# Ensure you're on the correct commit
git checkout main
git pull

# Create an annotated tag (preferred over lightweight tags)
git tag -a v0.4.38 -m "Release v0.4.38: Add feature X and fix bug Y"

# Push the tag to remote
git push origin v0.4.38

# Push all tags (alternative)
git push --tags
```

## Tag Content Best Practices

- Use annotated tags (`-a` flag) to include metadata rather than lightweight tags
- Write meaningful messages describing key changes in the release
- Reference issue/PR numbers in tag messages for traceability
- Consider including migration notes for breaking changes
- Keep messages concise but informative

Example of a good tag message:
```
Release v0.4.38

- Add support for GPT-4o model (#123)
- Fix rate limiting issue with concurrent requests (#125)
- Improve error handling for API timeouts
```

## Release Workflow Integration

1. Update version in `pyproject.toml` (e.g., 0.4.37 → 0.4.38)
2. Update changelog if you maintain one
3. Commit these changes with a message like "Bump version to 0.4.38"
4. Create and push git tag matching the version
5. Build and publish package to PyPI

Example workflow:
```bash
# Update version in pyproject.toml and changelog
# Commit changes
git add pyproject.toml CHANGELOG.md
git commit -m "Bump version to 0.4.38"

# Create and push tag
git tag -a v0.4.38 -m "Release v0.4.38: Add feature X and fix bug Y"
git push origin main
git push origin v0.4.38

# Build and publish
python -m build
twine upload dist/*
```

## Automation Options

- Use GitHub Actions or similar CI/CD to:
  - Validate version matches between code and tag
  - Run tests before creating release
  - Auto-publish to PyPI when tags are pushed
  - Generate release notes from commits
  - Create GitHub Releases automatically from tags

- Consider using tools like [bump2version](https://github.com/c4urself/bump2version) to automate version updates

## Tag Management

- Never delete or move tags that have been pushed publicly
- If a mistake is made, create a new tag rather than modifying existing ones
- Use release candidates for pre-releases: `v1.0.0-rc.1`
- Document tag naming conventions for your team
- Periodically clean up local tags that were never pushed

## Example GitHub Workflow

This GitHub Actions workflow automatically builds and publishes the package to PyPI when a tag is pushed:

```yaml
name: Release

on:
  push:
    tags:
      - 'v*'

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: pip install build twine
      - name: Build package
        run: python -m build
      - name: Publish to PyPI
        env:
          TWINE_USERNAME: ${{ secrets.PYPI_USERNAME }}
          TWINE_PASSWORD: ${{ secrets.PYPI_PASSWORD }}
        run: twine upload dist/*
      - name: Create GitHub Release
        uses: softprops/action-gh-release@v1
        with:
          generate_release_notes: true
```

---

By following these practices, you'll maintain a clear version history, make releases more predictable for users, and streamline your development workflow.
## Git Tags and Dependency Management

### Depending on Specific Git Tags in Other Projects

When other projects need to depend on specific versions of this library directly from Git (rather than PyPI), they can reference specific tags. This is particularly useful for development or when you need features that haven't been published to PyPI yet.

#### Using Rye with pyproject.toml

To depend on a specific Git tag of this library in a project using Rye, add the following to the project's `pyproject.toml`:

```toml
[project]
# ... other project configuration ...
dependencies = [
    # ... other dependencies ...
    "pinjected-openai @ git+https://github.com/proboscis/pinjected_openai.git@v1.0.0",
]
```

You can also specify a specific commit or branch:

```toml
# Depend on a specific commit
"pinjected-openai @ git+https://github.com/proboscis/pinjected_openai.git@5ad6099",

# Depend on a branch
"pinjected-openai @ git+https://github.com/proboscis/pinjected_openai.git@main",
```

#### Using Poetry

If using Poetry instead of Rye, the syntax is similar:

```toml
[tool.poetry.dependencies]
pinjected-openai = {git = "https://github.com/proboscis/pinjected_openai.git", tag = "v1.0.0"}
```

#### Using pip

With pip, you can install directly from a Git tag:

```bash
pip install git+https://github.com/proboscis/pinjected_openai.git@v1.0.0
```

### Benefits of Using Tagged Versions

- **Stability**: Depending on a specific tag ensures you get a stable, tested version
- **Reproducibility**: Builds are reproducible since the exact code version is pinned
- **Flexibility**: You can easily switch between versions by changing the tag reference
- **Pre-release Access**: Access new features before they're published to PyPI