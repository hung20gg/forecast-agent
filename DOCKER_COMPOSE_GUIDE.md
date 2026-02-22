# Docker Compose Configuration Guide

This project uses Docker Compose with profiles and override files to support 6 different deployment configurations.

## Available Configurations

### 1. **Full Stack - CPU** (Default for development)
```bash
docker compose --profile full up -d
```
Includes: MCP Server, Backend API, Frontend UI, Qdrant, Text Embedding (CPU)

### 2. **Full Stack - GPU**
```bash
docker compose -f docker-compose.gpu.yml --profile full up -d
```
Includes: All services with NVIDIA GPU acceleration

### 3. **Full Stack - macOS**
```bash
docker compose -f docker-compose.mac.yml --profile full up -d
```
Includes: All services with macOS-specific networking (host.docker.internal)

### 4. **MCP Server Only - CPU**
```bash
docker compose --profile mcp-only up -d
```
Includes: MCP Server, Qdrant, Text Embedding (CPU)

### 5. **MCP Server Only - GPU**
```bash
docker compose -f docker-compose.gpu.yml --profile mcp-only up -d
```
Includes: MCP services with NVIDIA GPU acceleration

### 6. **MCP Server Only - macOS**
```bash
docker compose -f docker-compose.mac.yml --profile mcp-only up -d
```
Includes: MCP services with macOS-specific networking

## File Structure

- **docker-compose.yml** - Base configuration with all services and profiles
- **docker-compose.override.yml** - Auto-loaded defaults for local development (exposes ports)
- **docker-compose.gpu.yml** - GPU-specific overrides (NVIDIA runtime, GPU image)
- **docker-compose.mac.yml** - macOS-specific overrides (host.docker.internal, port mappings)

## Profiles Explained

- **`full`** - Complete stack: MCP Server + Backend + Frontend + Qdrant + Embedding
- **`mcp-only`** - Minimal stack: MCP Server + Qdrant + Embedding (no backend/frontend)
- **`vectordb-init`** - One-time initialization service for vector database

## Common Commands

### Start services in detached mode
```bash
docker compose --profile full up -d
```

### View logs
```bash
docker compose logs -f
docker compose logs -f mcp-server  # specific service
```

### Stop services
```bash
docker compose down
```

### Rebuild after changes
```bash
docker compose --profile full up --build
```

### Production deployment (no dev overrides)
```bash
docker compose -f docker-compose.yml --profile full up
```

### Initialize vector database (one-time)
```bash
docker compose --profile vectordb-init up vectordb-init
```

## Environment Variables

Create a `.env` file in the project root:

```bash
# GCP Configuration
GCP_PROJECT_ID=your-project-id

# API Keys
OPENAI_API_KEY=sk-...
NVIDIA_API_KEY=nvapi-...
GROQ_API_KEY=gsk_...
BACKEND_API_KEY=your-backend-key
HF_TOKEN=hf_...

# Ports
MCP_SERVER_PORT=9003
BACKEND_PORT=8000
FRONTEND_PORT=3000

# Model Configuration
EMBEDDING_MODEL_ID=google/embeddinggemma-300m

# Vector DB Initialization
GCS_BUCKET_NAME=your-bucket
COLLECTION_NAME=financial-data
```

## Tips

- **docker-compose.override.yml** is automatically loaded. To skip it, use:
  ```bash
  docker compose -f docker-compose.yml --profile full up
  ```

- Combine multiple override files:
  ```bash
  docker compose -f docker-compose.yml -f docker-compose.gpu.yml -f custom.yml --profile full up
  ```

- Check which services will start:
  ```bash
  docker compose --profile full config --services
  ```
