#!/bin/bash

# Wrapper script for the Python script archive_sources.py

# Ensure the script exits on errors
set -euo pipefail

# Check if the correct number of arguments is provided
if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <source_directory> <destination_directory>"
    exit 1
fi

# Assign arguments to variables
SOURCE_DIR="$1"
DESTINATION_DIR="$2"

# Run the Python script with the provided arguments
python3 "$(dirname "$0")/python/archive_sources.py" "$SOURCE_DIR" "$DESTINATION_DIR"
