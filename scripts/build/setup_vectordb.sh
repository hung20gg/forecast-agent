#!/bin/bash
echo "=== Initializing Vector DB ==="

# Get the directory of this script and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT/setup"
uv pip install --python "$PROJECT_ROOT/.venv/bin/python" -r requirements.txt

echo "Starting temporary Qdrant server for initialization..."
if [ -f "$PROJECT_ROOT/qdrant/qdrant.exe" ]; then
    QDRANT_BIN="$PROJECT_ROOT/qdrant/qdrant.exe"
else
    QDRANT_BIN="$PROJECT_ROOT/qdrant/qdrant"
fi
$QDRANT_BIN &
QDRANT_PID=$!
echo "Waiting 10 seconds for Qdrant to start..."
sleep 10

# Override QDRANT_URL to localhost since we are running natively
export QDRANT_URL="http://localhost:6333"

python setup_vectordb.py

echo "Stopping temporary Qdrant server..."
kill $QDRANT_PID 2>/dev/null || taskkill //PID $QDRANT_PID //F 2>/dev/null