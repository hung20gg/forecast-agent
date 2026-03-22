#!/bin/bash
echo "=== Building Embedding Server ==="
if [ ! -d "text-embeddings-inference" ]; then
    git clone https://github.com/huggingface/text-embeddings-inference.git
fi

sudo apt-get install libssl-dev gcc -y

export PATH=$PATH:/usr/local/cuda/bin

cd text-embeddings-inference
cargo install --path router -F candle-cuda
cd ..