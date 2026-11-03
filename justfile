# Lint baseline recipes. The hooks in .pre-commit-config.yaml are the single source of truth;
# these just run them.

# Install the git hooks (pre-commit and pre-push)
setup:
    prek install

# Every check, including the slow pre-push ones
lint:
    prek run --all-files
    prek run --all-files --hook-stage pre-push

# Apply fixes: formatters, then ruff's and typos' safe fixes
fix:
    -prek run --all-files
    -ruff check --fix .
    -typos --write-changes

# Run one hook on every file, e.g. `just hook ruff-check`
hook id:
    prek run {{id}} --all-files
