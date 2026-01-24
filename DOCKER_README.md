# WTF - Financial Analysis Platform

A complete Docker Compose setup for financial data analysis and AI-powered forecasting.

## Services

- **MCP Server** (Port 9003): Financial data analysis tools with BigQuery integration
- **Backend API** (Port 8000): OpenAI-compatible agent API server
- **Frontend** (Port 3000): Open WebUI for interaction

## Quick Start

### 1. Setup LLM Submodule

The `agent/llm` directory is a separate git repository. Set it up first:

```bash
# If it's a git submodule:
git submodule init
git submodule update

# OR if you need to clone it separately:
# cd agent && git clone <llm-repo-url> llm
```

### 2. Setup Environment Variables

Copy the example environment file and configure your settings:

```bash
cp .env.example .env
```

Edit `.env` and fill in your values:
- API keys (OpenAI, Nvidia, Groq)
- GCP Project ID
- Database credentials (optional)

**Note**: The `agent/llm` directory is a separate git repo and should not be modified. Environment variables will be loaded before it's imported.

### 3. Setup BigQuery Credentials

Place your BigQuery service account JSON file in:
```
mcp-server/keys/bigquery.json
```

### 4. Start All Services

```bash
docker-compose up -d
```

### 5. Access the Services

- **Frontend (Open WebUI)**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **MCP Server**: http://localhost:9003

## Running Services Independently

Each service can still run independently without Docker:

### MCP Server

```bash
cd mcp-server
cp ../.env .env  # Or create your own .env
python src/server.py
```

### Backend API

```bash
cd backend/openai-api-compatible
cp ../../.env .env  # Or create your own .env
python server.py
```

### Agent (Library)

The agent is used as a library by the backend service.

## Environment Variables

All environment variables are centralized in the root `.env` file:

- **LLM API Keys**: OPENAI_API_KEY, NVIDIA_API_KEY, GROQ_API_KEY
- **MCP Server**: MCP_SERVER_URL, MCP_SERVER_HOST, MCP_SERVER_PORT
- **BigQuery**: GCP_PROJECT_ID, GOOGLE_APPLICATION_CREDENTIALS, LIMIT_TIME
- **Backend**: BACKEND_HOST, BACKEND_PORT, BACKEND_API_KEY
- **Frontend**: FRONTEND_PORT, OFFLINE_MODE
- **Database** (optional): MongoDB and PostgreSQL settings

When running independently, each service will:
1. Check for environment variables
2. Fall back to local `.env` file
3. Fall back to parent directory `.env` file

## Architecture

```
┌─────────────┐
│  Frontend   │ (Port 3000)
│ (Open WebUI)│
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Backend   │ (Port 8000)
│  Agent API  │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ MCP Server  │ (Port 9003)
│  (BigQuery) │
└─────────────┘
```

## Useful Commands

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f backend

# Stop all services
docker-compose down

# Rebuild and restart
docker-compose up -d --build

# Stop and remove volumes
docker-compose down -v
```

## Troubleshooting

### Services not starting

Check logs:
```bash
docker-compose logs
```

### Environment variables not working

Make sure `.env` file exists and is properly formatted.

### BigQuery credentials not found

Ensure `mcp-server/keys/bigquery.json` exists and is a valid service account key.

### Port conflicts

Edit `.env` and change port numbers:
```
FRONTEND_PORT=3001
BACKEND_PORT=8001
MCP_SERVER_PORT=9004
```

## Development

The docker-compose setup includes volume mounts for live development:
- Code changes in `backend/` and `agent/` are reflected immediately
- MCP server code in `mcp-server/src/` is mounted for development

## License

See individual service directories for license information.
