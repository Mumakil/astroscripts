#!/bin/bash

# Wrapper script for the Python script archive_sources.py

# Ensure the script exits on errors
set -euo pipefail

# Check if the correct number of arguments is provided (2 or 3 with --batch)
if [ "$#" -lt 2 ] || [ "$#" -gt 3 ]; then
    echo "Usage: $0 <source_directory> <destination_directory> [--batch]"
    exit 1
fi

SOURCE_DIR="$1"
DESTINATION_DIR="$2"

# Handle optional --batch argument
if [ "$#" -eq 3 ] && [ "$3" == "--batch" ]; then
    python3 "$(dirname "$0")/python/archive_sources.py" "$SOURCE_DIR" "$DESTINATION_DIR" --batch
else
    python3 "$(dirname "$0")/python/archive_sources.py" "$SOURCE_DIR" "$DESTINATION_DIR"
fi
