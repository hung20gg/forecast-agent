#!/bin/bash
set -e

# Check if SETUP_VECTORDB_ON_START is true
if [ "$SETUP_VECTORDB_ON_START" = "true" ]; then
    echo "🚀 SETUP_VECTORDB_ON_START is enabled. Running vectordb setup..."
    python src/setup_vectordb.py
    
    if [ $? -eq 0 ]; then
        echo "✅ Vector database setup completed successfully"
    else
        echo "❌ Vector database setup failed"
        exit 1
    fi
fi

# Start the MCP server with provided arguments
echo "🚀 Starting MCP Server..."
exec python src/server.py "$@"
