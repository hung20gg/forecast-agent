#!/bin/bash
set -e
echo "=== Starting Forecast Agent Services Natively ==="

# Parse arguments
SETUP_VECTORDB=0
while [[ $# -gt 0 ]]; do
    case "$1" in
        --setup-vectordb) SETUP_VECTORDB=1; shift ;;
        *) echo "Unknown argument: $1"; echo "Usage: $0 [--setup-vectordb]"; exit 1 ;;
    esac
done

# Load environment
source .venv/Scripts/activate 2>/dev/null || source .venv/bin/activate 2>/dev/null
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Helper: wait for an HTTP endpoint to respond
wait_for_http() {
    local url="$1"
    local name="$2"
    local retries=30
    echo "Waiting for $name at $url..."
    for i in $(seq 1 $retries); do
        if curl -sf "$url" -o /dev/null 2>/dev/null; then
            echo "$name is ready."
            return 0
        fi
        sleep 2
    done
    echo "ERROR: $name did not become ready in time."
    exit 1
}

echo "[1/3] Starting Qdrant..."
# Kill any stale process already using port 6333
if lsof -ti:6333 &>/dev/null; then
    echo "  Port 6333 in use — killing stale process..."
    kill $(lsof -ti:6333) 2>/dev/null && sleep 1
fi
if [ -f "./qdrant/qdrant.exe" ]; then
    QDRANT_BIN="./qdrant/qdrant.exe"
else
    QDRANT_BIN="./qdrant/qdrant"
fi
$QDRANT_BIN &
QDRANT_PID=$!
wait_for_http "http://localhost:6333/healthz" "Qdrant"

if [[ $SETUP_VECTORDB -eq 1 ]]; then
    echo "[1.5/3] Loading Vector DB into Qdrant..."
    export QDRANT_URL="http://localhost:6333"
    export ALLOW_VECTORDB_RESET="true"
    (cd setup && python setup_vectordb.py)
    echo "Vector DB setup complete."
fi

echo "[2/3] Starting Text Embedding Service..."
# Kill any stale process already using port 8008
EMBED_PORT=${EMBEDDING_PORT:-8008}
if lsof -ti:$EMBED_PORT &>/dev/null; then
    echo "  Port $EMBED_PORT in use — killing stale process..."
    kill $(lsof -ti:$EMBED_PORT) 2>/dev/null && sleep 1
fi
MODEL_ID=${EMBEDDING_MODEL_ID:-"google/embeddinggemma-300m"}
text-embeddings-router --model-id $MODEL_ID --port $EMBED_PORT &
EMBED_PID=$!
wait_for_http "http://localhost:$EMBED_PORT/health" "Embedding Service"

echo "[3/3] Starting MCP Server..."
# Kill any stale process already using MCP port
if lsof -ti:${MCP_SERVER_PORT:-9003} &>/dev/null; then
    echo "  Port ${MCP_SERVER_PORT:-9003} in use — killing stale process..."
    kill $(lsof -ti:${MCP_SERVER_PORT:-9003}) 2>/dev/null && sleep 1
fi
export QDRANT_URL="http://localhost:6333"
export EMBEDDING_URL="http://localhost:$EMBED_PORT/embed"

cd mcp-server
python src/server.py --transport sse --host ${MCP_SERVER_HOST:-0.0.0.0} --port ${MCP_SERVER_PORT:-9003} &
MCP_PID=$!
cd ..

echo ""
echo "All services started!"
echo "- Qdrant     PID: $QDRANT_PID"
echo "- Embeddings PID: $EMBED_PID"
echo "- MCP Server PID: $MCP_PID"
echo "Press Ctrl+C to stop all services."

cleanup() {
    echo "Stopping services..."
    kill $QDRANT_PID $EMBED_PID $MCP_PID 2>/dev/null
    wait $QDRANT_PID $EMBED_PID $MCP_PID 2>/dev/null
    exit 0
}
trap cleanup INT TERM

wait
