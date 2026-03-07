#!/bin/bash
echo "=== Starting Forecast Agent Services Natively ==="

# Load environment
source .venv/Scripts/activate 2>/dev/null || source .venv/bin/activate 2>/dev/null
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
fi

echo "[1/3] Starting Qdrant..."
if [ -f "./qdrant/qdrant.exe" ]; then
    QDRANT_BIN="./qdrant/qdrant.exe"
else
    QDRANT_BIN="./qdrant/qdrant"
fi
$QDRANT_BIN &
QDRANT_PID=$!

echo "[2/3] Starting Text Embedding Service..."
MODEL_ID=${EMBEDDING_MODEL_ID:-"google/embeddinggemma-300m"}
text-embeddings-router --model-id $MODEL_ID --port 8080 &
EMBED_PID=$!

echo "[3/3] Starting MCP Server..."
# Override service URLs to localhost for native execution
export QDRANT_URL="http://localhost:6333"
export EMBEDDING_URL="http://localhost:8080/embed"

cd mcp-server
python src/server.py --transport sse --host ${MCP_SERVER_HOST:-0.0.0.0} --port ${MCP_SERVER_PORT:-9003} &
MCP_PID=$!
cd ..

echo "All services started!"
echo "- Qdrant PID: $QDRANT_PID"
echo "- Embeddings PID: $EMBED_PID"
echo "- MCP Server PID: $MCP_PID"
echo "Press Ctrl+C to stop all services."

# Trap SIGINT to cleanly shut down background processes
trap "echo 'Stopping services...'; kill $QDRANT_PID $EMBED_PID $MCP_PID; taskkill //PID $QDRANT_PID //F 2>/dev/null; taskkill //PID $EMBED_PID //F 2>/dev/null; taskkill //PID $MCP_PID //F 2>/dev/null; exit" INT

# Wait for background processes
wait
