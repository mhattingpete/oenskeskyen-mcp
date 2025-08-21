#!/bin/bash

# Check if folder argument is provided
if [ $# -eq 0 ]; then
    echo "Usage: $0 <folder_path>"
    exit 1
fi

FOLDER="$1"

# Check if folder exists
if [ ! -d "$FOLDER" ]; then
    echo "Error: Folder '$FOLDER' does not exist"
    exit 1
fi

# Extract URLs from .webloc files in the specified folder
for file in "$FOLDER"/*.webloc; do
    if [ -f "$file" ]; then
        plutil -p "$file" | grep URL
    fi
done > wishes.txt
