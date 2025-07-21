#!/bin/bash
set -e

# Sort Spelling Allowlist
# The user did not provide this file, so we check for its existence.
SPELLING_ALLOW_FILE=".github/actions/spelling/allow.txt"
if [ -f "$SPELLING_ALLOW_FILE" ]; then
    sort -u "$SPELLING_ALLOW_FILE" -o "$SPELLING_ALLOW_FILE"
fi

TARGET_BRANCH="origin/${GITHUB_BASE_REF:-main}"
git fetch origin "${GITHUB_BASE_REF:-main}" --depth=1

# Find merge base between HEAD and target branch
MERGE_BASE=$(git merge-base HEAD "$TARGET_BRANCH")

# Get python files changed in this PR, excluding grpc generated files
CHANGED_FILES=$(git diff --name-only --diff-filter=ACMRTUXB "$MERGE_BASE" HEAD | grep '\.py$' | grep -v 'src/a2a/grpc/' || true)

if [ -z "$CHANGED_FILES" ]; then
    echo "No changed Python files to format."
    exit 0
fi

echo "Formatting changed files:"
echo "$CHANGED_FILES"

# Formatters are already installed in the activated venv from the GHA step.
# Use xargs to pass the file list to the formatters.
echo "$CHANGED_FILES" | xargs -r no_implicit_optional --use-union-or
echo "$CHANGED_FILES" | xargs -r pyupgrade --exit-zero-even-if-changed --py310-plus
echo "$CHANGED_FILES" | xargs -r autoflake -i -r --remove-all-unused-imports
echo "$CHANGED_FILES" | xargs -r ruff check --fix-only
echo "$CHANGED_FILES" | xargs -r ruff format
