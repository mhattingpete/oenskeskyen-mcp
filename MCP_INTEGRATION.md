# MCP Integration with Claude Desktop & Claude Code

This guide explains how to add the Onskeskyen Wishlist MCP server to Claude Desktop or Claude Code so that Claude can interact with your wishlist API directly.

## Prerequisites

1. **Credentials**: You need your Onskeskyen login credentials. You can provide them in two ways:
   
   **Option A: Environment Variables (Recommended for Claude Desktop)**
   - Set `ONSKESKYEN_USERNAME` and `ONSKESKYEN_PASSWORD` in your Claude Desktop configuration
   - No additional files needed
   
   **Option B: .env File (For development/local testing)**
   ```bash
   ONSKESKYEN_USERNAME=your_email@example.com
   ONSKESKYEN_PASSWORD=your_password
   ```

2. **Dependencies**: Make sure FastMCP is installed (already included in `pyproject.toml`):
   ```bash
   uv sync
   ```

## Adding MCP Server to Claude Desktop

### For Claude Desktop (macOS)

1. **Locate Claude Desktop's configuration file**:
   ```bash
   # The configuration file is located at:
   ~/Library/Application Support/Claude/claude_desktop_config.json
   ```

2. **Create or edit the configuration file**:
   ```bash
   # Create the directory if it doesn't exist
   mkdir -p ~/Library/Application\ Support/Claude
   
   # Edit the configuration file
   nano ~/Library/Application\ Support/Claude/claude_desktop_config.json
   ```

3. **Add the MCP server configuration**:
   ```json
   {
     "mcpServers": {
       "onskeskyen": {
         "command": "/opt/homebrew/bin/uv",
         "args": ["--directory", "/path/to/your/onskeskyen-batch-upload", "run", "python", "mcp_server.py"],
         "env": {
           "ONSKESKYEN_USERNAME": "your_email@example.com",
           "ONSKESKYEN_PASSWORD": "your_password"
         }
       }
     }
   }
   ```

   **Important Notes**:
   - Replace `/path/to/your/onskeskyen-batch-upload` with your actual project location
   - Add your real Onskeskyen credentials in the `env` section
   - The credentials in the `env` section will be used by the MCP server
   - You do NOT need a `.env` file when using Claude Desktop (credentials are passed via environment variables)

4. **Restart Claude Desktop** completely (quit and reopen the application).

### For Claude Desktop (Windows)

1. **Locate the configuration file**:
   ```
   %APPDATA%\Claude\claude_desktop_config.json
   ```

2. **Create or edit the configuration** with the same JSON structure as above, but adjust the paths for Windows:
   ```json
   {
     "mcpServers": {
       "onskeskyen": {
         "command": "uv",
         "args": ["run", "python", "mcp_server.py"],
         "cwd": "C:\\path\\to\\your\\project",
         "env": {
           "ONSKESKYEN_USERNAME": "your_email@example.com",
           "ONSKESKYEN_PASSWORD": "your_password"
         }
       }
     }
   }
   ```

## Adding MCP Server to Claude Code

### Option 1: Local Configuration (Recommended for Development)

1. **Create or edit your Claude Code settings file**:
   ```bash
   # Create the settings directory if it doesn't exist
   mkdir -p ~/.config/claude-code
   
   # Edit the settings file
   nano ~/.config/claude-code/settings.json
   ```

2. **Add the MCP server configuration**:
   ```json
   {
     "mcp": {
       "servers": {
         "onskeskyen": {
           "command": "/opt/homebrew/bin/uv",
           "args": ["--directory", "/path/to/your/project", "run", "python", "mcp_server.py"],
           "env": {
             "ONSKESKYEN_USERNAME": "your_email@example.com",
             "ONSKESKYEN_PASSWORD": "your_password"
           }
         }
       }
     }
   }
   ```

   **Important**: Replace `/path/to/your/project` with the actual absolute path to this repository.

### Option 2: Project-specific Configuration

1. **Create a `.claude-code` directory in your project**:
   ```bash
   mkdir .claude-code
   ```

2. **Create `settings.json` in the project directory**:
   ```bash
   cat > .claude-code/settings.json << 'EOF'
   {
     "mcp": {
       "servers": {
         "onskeskyen": {
           "command": "/opt/homebrew/bin/uv",
           "args": ["--directory", ".", "run", "python", "mcp_server.py"],
           "env": {}
         }
       }
     }
   }
   EOF
   ```

   This option uses your existing `.env` file for credentials.

### Option 3: Using Environment Variables

If you prefer to keep credentials in your shell environment:

```json
{
  "mcp": {
    "servers": {
      "onskeskyen": {
        "command": "/opt/homebrew/bin/uv",
        "args": ["--directory", "/path/to/your/project", "run", "python", "mcp_server.py"]
      }
    }
  }
}
```

And set environment variables in your shell:
```bash
export ONSKESKYEN_USERNAME="your_email@example.com"
export ONSKESKYEN_PASSWORD="your_password"
```

## Verifying the Integration

### For Claude Desktop
1. **Restart Claude Desktop** completely (quit and reopen the application).
2. Look for a 🔌 plug icon in the chat interface, which indicates MCP servers are connected.
3. You should see "onskeskyen" listed when you hover over or click the plug icon.

### For Claude Code
1. **Restart Claude Code** after adding the MCP configuration.

2. **Test the connection** by asking Claude to use the wishlist tools:
   ```
   Can you show me my wishlists using the MCP tools?
   ```

3. **Check available tools** - Claude should have access to these tools:
   - `get_user_profile` - Get your profile information
   - `get_wishlists` - List all your wishlists
   - `get_wishlist_items` - Get items from a specific wishlist
   - `add_wishlist_item` - Add new items to wishlists
   - `get_wishlist_details` - Get detailed wishlist information
   - `get_product_metadata` - Extract product metadata from URLs

## Usage Examples

Once integrated, you can ask Claude to:

### View Your Wishlists
```
Show me all my wishlists and how many items are in each one.
```

### Add Items to Wishlists
```
Add this LEGO set to my wishlist: https://www.lego.com/en-us/product/hogwarts-castle-71043
Use wishlist ID: ZhgfNVLL8ydtRJgc
```

### Get Product Information
```
Can you get the product details for this URL: https://www.lego.com/en-us/product/millennium-falcon-75375
```

### Manage Wishlist Items
```
Show me all items in wishlist ZhgfNVLL8ydtRJgc and their prices.
```

## Troubleshooting

### MCP Server Not Starting
- Check that the path in the configuration is correct
- Verify that `uv` is installed and accessible
- Ensure your `.env` file has the correct credentials

### Authentication Issues
- Verify your Onskeskyen username and password are correct
- Check that the environment variables are properly set
- Try running the MCP server manually to test authentication:
  ```bash
  uv run python mcp_server.py
  ```

### Tool Not Available in Claude
- Restart Claude Code after configuration changes
- Check the Claude Code logs for MCP connection errors
- Verify the JSON syntax in your settings file

## Security Notes

- Keep your credentials secure and never commit them to version control
- Consider using environment variables instead of hardcoding credentials in config files
- The MCP server only runs locally and doesn't expose your credentials externally

## Advanced Configuration

### Custom Server Name
You can change the server name in the configuration:
```json
{
  "mcp": {
    "servers": {
      "my-wishlist-api": {
        "command": "uv",
        "args": ["run", "python", "mcp_server.py"],
        "cwd": "/path/to/your/project"
      }
    }
  }
}
```

### Multiple Environments
You can configure different servers for different environments:
```json
{
  "mcp": {
    "servers": {
      "onskeskyen-dev": {
        "command": "uv",
        "args": ["run", "python", "mcp_server.py"],
        "cwd": "/path/to/dev/project"
      },
      "onskeskyen-prod": {
        "command": "uv",
        "args": ["run", "python", "mcp_server.py"],
        "cwd": "/path/to/prod/project"
      }
    }
  }
}
```