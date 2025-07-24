#!/bin/bash
set -e
set -o pipefail

# --- Argument Parsing ---
# Check if the first argument is '--all'
FORMAT_ALL=false
if [[ "$1" == "--all" ]]; then
    FORMAT_ALL=true
    shift # Consume the '--all' argument so it doesn't interfere with later logic if any
fi

# Sort Spelling Allowlist
# This operation is independent of file formatting logic, keeping it at the top.
SPELLING_ALLOW_FILE=".github/actions/spelling/allow.txt"
if [ -f "$SPELLING_ALLOW_FILE" ]; then
    echo "Sorting and de-duplicating $SPELLING_ALLOW_FILE"
    sort -u "$SPELLING_ALLOW_FILE" -o "$SPELLING_ALLOW_FILE"
fi

CHANGED_FILES=""

if $FORMAT_ALL; then
    echo "The '--all' flag was passed. Formatting all Python files in the repository."
    # The prompt requested "all files (.)" but the script's formatters (pyupgrade, autoflake, ruff)
    # are Python-specific. Therefore, this command will find and format all Python files.
    # It excludes files under './src/a2a/grpc/' as per the original script's logic.
    CHANGED_FILES=$(find . -name '*.py' -not -path './src/a2a/grpc/*' | sort -u)

    if [ -z "$CHANGED_FILES" ]; then
        echo "No Python files found to format."
        exit 0
    fi
else
    echo "No '--all' flag found. Formatting changed Python files based on git diff."
    TARGET_BRANCH="origin/${GITHUB_BASE_REF:-main}"
    # Fetch the target branch to ensure it's available for git merge-base
    git fetch origin "${GITHUB_BASE_REF:-main}" --depth=1

    # Find the merge base commit between HEAD (current branch) and the target branch
    MERGE_BASE=$(git merge-base HEAD "$TARGET_BRANCH")

    # Get Python files that have been Added, Copied, Modified, Renamed, had Type change, are Unmerged, Unknown, or Broken pairing.
    # Exclude files under 'src/a2a/grpc/' from the list.
    CHANGED_FILES=$(git diff --name-only --diff-filter=ACMRTUXB "$MERGE_BASE" HEAD -- '*.py' ':!src/a2a/grpc/*')

    if [ -z "$CHANGED_FILES" ]; then
        echo "No changed Python files to format."
        exit 0
    fi
fi

echo "Files to be formatted:"
# Using echo "$CHANGED_FILES" directly will print files separated by newlines, which is clear.
echo "$CHANGED_FILES"

# Define a helper function to run formatters with the list of files.
# The list of files is passed to xargs via stdin.
run_formatter() {
    # `xargs -r` ensures the command is not run if there are no inputs.
    # This is important to prevent formatters from running without files,
    # which might result in errors or unintended behavior.
    echo "$CHANGED_FILES" | xargs -r "$@"
}

echo "Running pyupgrade..."
run_formatter pyupgrade --exit-zero-even-if-changed --py310-plus
echo "Running autoflake..."
run_formatter autoflake -i -r --remove-all-unused-imports
echo "Running ruff check (fix-only)..."
run_formatter ruff check --fix-only
echo "Running ruff format..."
run_formatter ruff format

echo "Formatting complete."
