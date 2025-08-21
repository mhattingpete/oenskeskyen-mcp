#!/bin/bash

# Check if container exists and remove if it does
if docker ps -a --format '{{.Names}}' | grep -q '^crawl4ai$'; then
    echo "Removing existing crawl4ai container..."
    docker rm -f crawl4ai
fi

# Start the Docker container
echo "Starting crawl4ai Docker container..."
docker run -d \
  -p 11235:11235 \
  --name crawl4ai \
  --shm-size=1g \
  unclecode/crawl4ai:latest

# Wait for container to be ready
echo "Waiting for container to be ready..."
sleep 5

# Check if container is running
if ! docker ps --format '{{.Names}}' | grep -q '^crawl4ai$'; then
    echo "Error: Container failed to start"
    exit 1
fi

# Set up MCP connection
echo "Setting up MCP connection..."
claude mcp add --transport sse c4ai-sse http://localhost:11235/mcp/sse

echo "Setup complete!"