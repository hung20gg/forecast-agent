FROM python:3.11-slim

# Install git for cloning llm submodule if needed
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

WORKDIR /app/backend/openai-api-compatible

# Copy agent library first (needed for imports)
COPY agent/ /app/agent/

# Install agent dependencies
COPY agent/requirements.txt /app/agent/requirements.txt
RUN pip install --no-cache-dir -r /app/agent/requirements.txt

# Copy and install backend dependencies
COPY backend/openai-api-compatible/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/openai-api-compatible/ .

# Optional: Clone LLM repository if not present in agent/ and URL is provided
ARG LLM_REPO_URL=""
RUN if [ ! -d "/app/agent/llm" ] && [ -n "$LLM_REPO_URL" ]; then \
        echo "Cloning LLM repository from $LLM_REPO_URL"; \
        cd /app/agent && git clone "$LLM_REPO_URL" llm; \
    elif [ ! -d "/app/agent/llm" ]; then \
        echo "WARNING: agent/llm directory not found and LLM_REPO_URL not provided"; \
        echo "The backend may not work without the llm module"; \
    fi

# Expose port
EXPOSE 8000

# Run the server
CMD ["python", "server.py"]
