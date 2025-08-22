#!/bin/bash
# Setup script for Claude Desktop MCP integration

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔗 Claude Desktop MCP Setup${NC}"
echo -e "${BLUE}==============================${NC}"
echo

# Check if we're on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo -e "${RED}❌ This script is designed for macOS. For Windows, please follow the manual instructions in MCP_INTEGRATION.md${NC}"
    exit 1
fi

# Get the current directory
CURRENT_DIR=$(pwd)
echo -e "${BLUE}📁 Project directory: ${CURRENT_DIR}${NC}"

# Get credentials from .env file or environment variables
USERNAME=""
PASSWORD=""

# First, try to get credentials from environment variables
if [[ -n "$ONSKESKYEN_USERNAME" && -n "$ONSKESKYEN_PASSWORD" ]]; then
    USERNAME="$ONSKESKYEN_USERNAME"
    PASSWORD="$ONSKESKYEN_PASSWORD"
    echo -e "${GREEN}✅ Using credentials from environment variables${NC}"
# If not in environment, try .env file
elif [[ -f ".env" ]]; then
    if grep -q "ONSKESKYEN_USERNAME" .env && grep -q "ONSKESKYEN_PASSWORD" .env; then
        USERNAME=$(grep "ONSKESKYEN_USERNAME" .env | cut -d '=' -f2 | tr -d '"' | tr -d "'")
        PASSWORD=$(grep "ONSKESKYEN_PASSWORD" .env | cut -d '=' -f2 | tr -d '"' | tr -d "'")
        echo -e "${GREEN}✅ Found credentials in .env file${NC}"
    else
        echo -e "${RED}❌ Missing ONSKESKYEN_USERNAME or ONSKESKYEN_PASSWORD in .env file${NC}"
        exit 1
    fi
else
    echo -e "${RED}❌ No credentials found. Please either:${NC}"
    echo -e "${YELLOW}1. Set environment variables: ONSKESKYEN_USERNAME and ONSKESKYEN_PASSWORD${NC}"
    echo -e "${YELLOW}2. Create a .env file with:${NC}"
    echo -e "${YELLOW}   ONSKESKYEN_USERNAME=your_email@example.com${NC}"
    echo -e "${YELLOW}   ONSKESKYEN_PASSWORD=your_password${NC}"
    exit 1
fi

if [[ -z "$USERNAME" || -z "$PASSWORD" ]]; then
    echo -e "${RED}❌ Empty credentials found${NC}"
    exit 1
fi

# Create Claude Desktop config directory if it doesn't exist
CLAUDE_CONFIG_DIR="$HOME/Library/Application Support/Claude"
mkdir -p "$CLAUDE_CONFIG_DIR"

CONFIG_FILE="$CLAUDE_CONFIG_DIR/claude_desktop_config.json"

# Create the configuration
cat > "$CONFIG_FILE" << EOF
{
  "mcpServers": {
    "onskeskyen": {
      "command": "/opt/homebrew/bin/uv",
      "args": ["--directory", "$CURRENT_DIR", "run", "python", "mcp_server.py"],
      "env": {
        "ONSKESKYEN_USERNAME": "$USERNAME",
        "ONSKESKYEN_PASSWORD": "$PASSWORD"
      }
    }
  }
}
EOF

echo -e "${GREEN}✅ Claude Desktop configuration created at:${NC}"
echo -e "${BLUE}   $CONFIG_FILE${NC}"
echo

# Test that uv and the MCP server work
echo -e "${BLUE}🧪 Testing MCP server...${NC}"
if command -v uv &> /dev/null; then
    echo -e "${GREEN}✅ uv is installed${NC}"
    
    # Test that the MCP server can start (just check help)
    if uv run python mcp_server.py --help &> /dev/null; then
        echo -e "${GREEN}✅ MCP server can start successfully${NC}"
    else
        echo -e "${YELLOW}⚠️  MCP server test failed, but configuration was created${NC}"
    fi
else
    echo -e "${RED}❌ uv is not installed. Please install it first: https://docs.astral.sh/uv/getting-started/installation/${NC}"
    exit 1
fi

echo
echo -e "${GREEN}🎉 Setup complete!${NC}"
echo
echo -e "${YELLOW}Next steps:${NC}"
echo -e "${BLUE}1. ${NC}Restart Claude Desktop completely (quit and reopen)"
echo -e "${BLUE}2. ${NC}Look for the 🔌 plug icon in the chat interface"
echo -e "${BLUE}3. ${NC}Test with: 'Can you show me my wishlists using the MCP tools?'"
echo
echo -e "${BLUE}Available tools:${NC}"
echo -e "${GREEN}• ${NC}get_user_profile - Get your profile information"
echo -e "${GREEN}• ${NC}get_wishlists - List all your wishlists"  
echo -e "${GREEN}• ${NC}get_wishlist_items - Get items from a specific wishlist"
echo -e "${GREEN}• ${NC}add_wishlist_item - Add new items to wishlists"
echo -e "${GREEN}• ${NC}get_wishlist_details - Get detailed wishlist information"
echo -e "${GREEN}• ${NC}get_product_metadata - Extract product metadata from URLs"