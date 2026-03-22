#!/bin/bash

# Parse flags
FORCE_MODE=""
for arg in "$@"; do
    case "$arg" in
        --cpu) FORCE_MODE="cpu" ;;
        --gpu) FORCE_MODE="gpu" ;;
        --mps) FORCE_MODE="mps" ;;
    esac
done

echo "=== Setting up Environment ==="
# Check if venv exists, if not create it
if [ ! -d ".venv" ]; then
    uv venv
fi
source .venv/bin/activate 2>/dev/null || source .venv/Scripts/activate 2>/dev/null

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
if [[ -z "$FORCE_MODE" ]]; then
    # Auto-detect
    if [[ "$(uname -s)" == "Darwin" ]]; then
        FORCE_MODE="mps"
    elif command -v nvidia-smi >/dev/null 2>&1 || command -v nvcc >/dev/null 2>&1; then
        FORCE_MODE="gpu"
    else
        FORCE_MODE="cpu"
    fi
fi

case "$FORCE_MODE" in
    mps)
        echo "Building MPS (Mac) version"
        bash scripts/build/embedding_server_mac.sh
        ;;
    gpu)
        echo "Building GPU (CUDA) version"
        bash scripts/build/embedding_server_gpu.sh
        ;;
    cpu)
        echo "Building CPU version"
        bash scripts/build/embedding_server_cpu.sh
        ;;
esac

echo "=== Build Complete ==="
echo "All components are set up! You can now run the services."