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
if [[ "$(uname -s)" == "Darwin" ]]; then
    echo "macOS detected -> building mac version"
    bash scripts/build/embedding_server_mac.sh
elif command -v nvidia-smi >/dev/null 2>&1 || command -v nvcc >/dev/null 2>&1; then
    echo "CUDA detected -> building GPU version"
    bash scripts/build/embedding_server_gpu.sh
else
    echo "Error: Unsupported device. Requires macOS or CUDA-capable environment."
    exit 1
fi

echo "=== Build Complete ==="
echo "All components are set up! You can now run the services."