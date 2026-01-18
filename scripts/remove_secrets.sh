#!/usr/bin/env bash
# Script to scrub secrets from git history using git-filter-repo.
# WARNING: This rewrites git history. Coordinate with your team and back up the repo.

set -euo pipefail

if [ -z "${1-}" ]; then
  echo "Usage: $0 <repo-mirror-path>"
  echo "Example: $0 /tmp/the_one_mirror.git"
  exit 1
fi

MIRROR_DIR="$1"

echo "This script will prepare a mirror clone and remove paths containing secrets (example: config/config.json, .env)."
echo "Edit the '--paths' or use --replace-text for targeted replacements before running."

git clone --mirror "$(git config --get remote.origin.url)" "$MIRROR_DIR"
cd "$MIRROR_DIR"

# Example: remove tracked file path entirely from history
git filter-repo --invert-paths --paths config/config.json --paths .env || true

echo "Push the rewritten history back to origin (force). Review before pushing!"
echo "To push: git push --force --all && git push --force --tags"

echo "Done. Review the mirror repo at: $MIRROR_DIR"
