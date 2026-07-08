#!/usr/bin/env bash
# Copy the ralph loop (ralph_loop.sh + ralph_format.jq) into a project folder so
# it lives with the project instead of the global skills dir.
#
# Usage:
#   bash install_ralph.sh [target-dir]     # default target: ./scripts
#
# Run it from your project root, or pass an explicit target directory.

set -euo pipefail

src_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
target="${1:-./scripts}"

mkdir -p "$target"
cp "$src_dir/ralph_loop.sh" "$src_dir/ralph_format.jq" "$target/"
chmod +x "$target/ralph_loop.sh"

echo "Installed ralph loop into $target/"
echo "Run it from this repo with:  bash $target/ralph_loop.sh Docs/Plans/<name>"
