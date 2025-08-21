# Makefile for Ønskeskyen API Reconstruction

.PHONY: help monitor analyze reconstruct clean install lint format api test-cache test

# Default target
help:
	@echo "Available targets:"
	@echo "  install     - Install dependencies with uv"
	@echo "  monitor     - Run network monitoring to capture API calls"
	@echo "  analyze     - Parse captured network data and reconstruct API"
	@echo "  reconstruct - Run full reconstruction (monitor + analyze)"
	@echo "  api         - Start the FastAPI server"
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