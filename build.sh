#!/bin/bash
echo "=== Setting up Environment ==="
uv venv
source .venv/Scripts/activate 2>/dev/null || source .venv/bin/activate 2>/dev/null

if ! command -v rustc &> /dev/null; then
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
    source "$HOME/.cargo/env"
fi


echo "=== 1. Building MCP Server ==="
bash scripts/build/mcp_server.sh

echo "=== 2. Setting up Qdrant ==="
bash scripts/build/setup_qdrant.sh

echo "=== 3. Initializing Vector DB ==="
bash scripts/build/setup_vectordb.sh

echo "=== 4. Building Text Embeddings Server ==="
bash scripts/build/embedding_server_gpu.sh

echo "=== Build Complete ==="
echo "All components are set up! You can now run the services."