# Makefile for Ønskeskyen API Reconstruction

.PHONY: help monitor analyze reconstruct clean install lint format api mcp setup-claude test-cache test

# Default target
help:
	@echo "Available targets:"
	@echo "  install     - Install dependencies with uv"
	@echo "  monitor     - Run network monitoring to capture API calls"
	@echo "  analyze     - Parse captured network data and reconstruct API"
	@echo "  reconstruct - Run full reconstruction (monitor + analyze)"
	@echo "  api         - Start the FastAPI server"
	@echo "  mcp         - Start the MCP server for Claude Code integration"
	@echo "  setup-claude- Setup Claude Desktop MCP integration (macOS only)"
	@echo "  test        - Run all unit and integration tests"
	@echo "  test-cache  - Test caching functionality (requires running API)"
	@echo "  clean       - Remove captured data files"
	@echo "  lint        - Run ruff linting"
	@echo "  format      - Format code with ruff"

# Install dependencies
install:
	uv sync --dev

# Monitor network traffic and capture API calls
monitor:
	@echo "🔍 Starting network monitoring..."
	@echo "⚠️  Make sure ONSKESKYEN_USERNAME and ONSKESKYEN_PASSWORD are set in .env"
	uv run python src/network_monitor.py

# Analyze captured data and reconstruct API
analyze:
	@echo "📊 Analyzing captured API data..."
	uv run python src/api_parser.py

# Full reconstruction workflow
reconstruct: monitor analyze
	@echo "✅ API reconstruction complete!"
	@echo ""
	@echo "Generated files:"
	@echo "  - captured_api_calls_*.json (raw network data)"
	@echo "  - api_reconstruction_report.json (analysis report)"
	@echo "  - src/reconstructed_api_client.py (Python client template)"

# Clean up generated files
clean:
	@echo "🧹 Cleaning up captured data files..."
	rm -f captured_api_calls_*.json
	rm -f api_reconstruction_report.json
	rm -f src/reconstructed_api_client.py
	rm -f debug_screenshot.png
	@echo "✅ Cleanup complete"

# Lint code
lint:
	uv run ruff check .

# Format code
format:
	uv run ruff format .

# Run linting and formatting
check: lint format

# Start the FastAPI server
api:
	@echo "🚀 Starting Ønskeskyen API Gateway..."
	@echo "⚠️  Make sure ONSKESKYEN_USERNAME and ONSKESKYEN_PASSWORD are set in .env"
	@echo "📡 Server will be available at http://localhost:8000"
	@echo "📖 API docs at http://localhost:8000/docs"
	@echo "🛑 Press Ctrl+C to stop"
	@echo ""
	uv run python start_api.py

# Start the MCP server
mcp:
	@echo "🔗 Starting Ønskeskyen MCP Server for Claude Code..."
	@echo "⚠️  Make sure ONSKESKYEN_USERNAME and ONSKESKYEN_PASSWORD are set in .env"
	@echo "🤖 Server will provide these tools to Claude:"
	@echo "   • get_user_profile - Get your profile information"
	@echo "   • get_wishlists - List all your wishlists"
	@echo "   • get_wishlist_items - Get items from a specific wishlist"
	@echo "   • add_wishlist_item - Add new items to wishlists"
	@echo "   • get_wishlist_details - Get detailed wishlist information"
	@echo "   • get_product_metadata - Extract product metadata from URLs"
	@echo "📖 See MCP_INTEGRATION.md for Claude Code setup instructions"
	@echo "🛑 Press Ctrl+C to stop"
	@echo ""
	uv run python mcp_server.py

# Setup Claude Desktop MCP integration
setup-claude:
	@echo "🔗 Setting up Claude Desktop MCP integration..."
	@echo ""
	./setup_claude_desktop.sh

# Run all tests
test:
	@echo "🧪 Running all unit and integration tests..."
	uv run pytest tests/ -v

# Test caching functionality
test-cache:
	@echo "🧪 Testing caching functionality..."
	@echo "📋 Make sure the API server is running (make api)"
	@echo ""
	uv run python src/test_cache.py