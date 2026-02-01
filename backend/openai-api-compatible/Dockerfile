# Multi-stage build for optimized final image
FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    git \
    build-essential && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /build

# Copy and install dependencies first (better layer caching)
COPY agent/requirements.txt /build/agent-requirements.txt
COPY backend/openai-api-compatible/requirements.txt /build/backend-requirements.txt

# Install Python dependencies to a separate location
RUN pip install --no-cache-dir --user -r /build/agent-requirements.txt && \
    pip install --no-cache-dir --user -r /build/backend-requirements.txt

# Clone LLM repository if needed
ARG LLM_REPO_URL=""
RUN if [ -n "$LLM_REPO_URL" ]; then \
        git clone "$LLM_REPO_URL" /build/llm; \
    fi

# Final stage - minimal runtime image
FROM python:3.11-slim

# Install only runtime dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    git && \
    rm -rf /var/lib/apt/lists/* && \
    apt-get clean

# Create non-root user for security
RUN useradd -m -u 1000 -s /bin/bash appuser && \
    mkdir -p /app/backend/openai-api-compatible /app/agent && \
    chown -R appuser:appuser /app

WORKDIR /app/backend/openai-api-compatible

# Copy installed Python packages from builder
COPY --from=builder --chown=appuser:appuser /root/.local /home/appuser/.local

# Copy LLM repository if it was cloned
COPY --from=builder /build/llm /app/agent/llm

# Copy agent code
COPY --chown=appuser:appuser agent/ /app/agent/

# Copy backend code
COPY --chown=appuser:appuser backend/openai-api-compatible/ .

# Update PATH for user-installed packages
ENV PATH=/home/appuser/.local/bin:$PATH

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health', timeout=5)"

# Run the server
CMD ["python", "server.py"]
