#!/bin/bash

# OpenAI-Compatible API Server - cURL Examples
# Make sure the server is running: python server.py

BASE_URL="http://localhost:8000"

echo "=== 1. Health Check ==="
curl -X GET "$BASE_URL/health"
echo -e "\n\n"

echo "=== 2. List Available Models ==="
curl -X GET "$BASE_URL/v1/models" \
  -H "Content-Type: application/json" | jq '.'
echo -e "\n\n"

echo "=== 4. Streaming Chat Completion (ReAct Strategy) ==="
curl -X POST "$BASE_URL/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "react:gpt-4.1-mini",
    "messages": [
      {
        "role": "user",
        "content": "Analyze VIC stock performance"
      }
    ],
    "stream": true
  }'
echo -e "\n\n"

