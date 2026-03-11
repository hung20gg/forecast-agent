#!/bin/bash

if [ ! -d "text-embeddings-inference" ]; then
    git clone https://github.com/huggingface/text-embeddings-inference.git
fi

export PATH=$PATH:/usr/local/cuda/bin

cd text-embeddings-inference
cargo install --path router -F metal

MODEL_NAME=${MODEL_NAME:-"sentence-transformers/all-MiniLM-L6-v2"}
export HF_TOKEN=${HF_TOKEN:-""}


text-embeddings-router --model-id $MODEL_NAME --port 8080