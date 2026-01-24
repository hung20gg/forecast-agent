FROM python:3.11-slim

# Install git for cloning llm submodule if needed
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

WORKDIR /app/agent

# Copy and install agent dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire agent directory (excluding what's in .dockerignore)
COPY . .

# Optional: Clone LLM repository if not present and URL is provided
# You can override this at build time: --build-arg LLM_REPO_URL=https://github.com/your/llm-repo.git
ARG LLM_REPO_URL=""
RUN if [ ! -d "llm" ] && [ -n "$LLM_REPO_URL" ]; then \
        echo "Cloning LLM repository from $LLM_REPO_URL"; \
        git clone "$LLM_REPO_URL" llm; \
    elif [ ! -d "llm" ]; then \
        echo "WARNING: llm directory not found and LLM_REPO_URL not provided"; \
        echo "The agent may not work without the llm module"; \
    fi

# The agent is used as a library by backend service
# This container can also be used for testing
CMD ["python", "test_agent.py"]
