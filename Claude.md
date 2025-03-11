# How to follow user instructions.

## `build`
use poetry to build the package
`poetry build`

## `smart push`
First check git status and diffs to compose a summary.
Then, add files to the staging area and commit with a message.
Finally, push the changes to the remote repository.

## `bump version`
Bump the version number in the `pyproject.toml` file.
Compose a CHANGELOG.md entry for the new version, reading the git history and issues as needed.
Add a tag for the new version.
Then, commit the changes with a message.
Finally, push the changes to the remote repository.


## `release`
Run the `bump version` command.
Make sure the pyproject's version and current tag match and that the tag is pushed to the remote repository.
Then, build the package and upload it to PyPI. 
Example:
`poetry build && poetry publish`

# How to respond
The user types in english for speed, but your response should be in Japanese.
