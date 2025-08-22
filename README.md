# Oenskeskyen Batch Upload

A tool for batch uploading bookmarks to your Onskeskyen wishlist with MCP integration for Claude Desktop and Claude Code.

## Installation

### Prerequisites

1. Install dependencies:
   ```bash
   uv sync
   ```

2. Set up your Onskeskyen credentials:
   ```bash
   # Create a .env file (for local development)
   ONSKESKYEN_USERNAME=your_email@example.com
   ONSKESKYEN_PASSWORD=your_password
   ```

### MCP Integration

For Claude Desktop and Claude Code integration, see [MCP_INTEGRATION.md](MCP_INTEGRATION.md) for detailed setup instructions.

## Usage

### Extracting .webloc files from Safari

To extract bookmarks from Safari as .webloc files:

1. Open Safari and go to your bookmarks (Bookmarks > Show Bookmarks or Cmd+Option+B)
2. Select the bookmarks you want to export
3. Drag the selected bookmarks to a folder in Finder
4. Safari will create .webloc files for each bookmark

### Extracting URLs from .webloc files

Once you have the .webloc files in a folder, use the extraction script:

```bash
./scripts/extract_urls.sh <folder_path>
```

This will create an `wishes.txt` file with all the extracted URLs.
