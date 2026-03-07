#!/bin/bash
echo "=== Initializing Vector DB ==="
cd setup
uv pip install -r requirements.txt

echo "Starting temporary Qdrant server for initialization..."
if [ -f "../qdrant/qdrant.exe" ]; then
    QDRANT_BIN="../qdrant/qdrant.exe"
else
    QDRANT_BIN="../qdrant/qdrant"
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
cd ..
