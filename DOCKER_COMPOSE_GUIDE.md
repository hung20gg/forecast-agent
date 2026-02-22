# Docker Compose Configuration Guide

This project uses Docker Compose with profiles and override files to support 6 different deployment configurations.

## Up-down

```bash
docker compose -p forecast-agent down
```

## Available Configurations

### 1. **Full Stack - CPU** (Default for development)
```bash
docker compose --profile full up -d
```
Includes: MCP Server, Backend API, Frontend UI, Qdrant, Text Embedding (CPU)

### 2. **Full Stack - GPU**
```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml --profile full up -d
```
Includes: All services with NVIDIA GPU acceleration

### 3. **Full Stack - macOS**
```bash
docker compose -f docker-compose.yml -f docker-compose.mac.yml --profile full up -d
```
Includes: All services with macOS-specific networking (host.docker.internal)

### 4. **MCP Server Only - CPU**
```bash
docker compose --profile mcp-only up -d
```
Includes: MCP Server, Qdrant, Text Embedding (CPU)

### 5. **MCP Server Only - GPU**
```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml --profile mcp-only up -d
```
Includes: MCP services with NVIDIA GPU acceleration

### 6. **MCP Server Only - macOS**
```bash
docker compose -f docker-compose.yml -f docker-compose.mac.yml --profile mcp-only up -d
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
