# Forecase agent


This repository contains the Forecast Agent system, which includes a frontend UI, a backend OpenAI-compatible API server, and an MCP server for data storage using BigQuery.


This repo will help you make estimations and forecasts using LLMs with advanced agent strategies.


Start with Docker Compose for easy setup of all components.

```bash
cd forecast-agent

cp .env.example .env
```

Edit the `.env` file to set your API keys and configurations.

Start all services with Docker Compose (CPU version):

```bash
docker-compose up -d
```

Details on Docker Compose configurations and optimizations can be found in the `DOCKER_COMPOSE_GUIDE.md` and `DOCKER_OPTIMIZATION.md` files.

Init with vectordb installed

```bash
docker compose --profile vectordb-init run --rm vectordb-init
```


Fully run with MCP, TEI docker and GPU + vectordb init

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml --profile mcp-only --profile vectordb-init  up -d
```

Fully run for deployment with GPU + vectordb init

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml --profile full --profile vectordb-init  up -d
```


### For Development
To rebuild any service after making changes to the codebase.

Use the docker-compose.dev.yml file which maps the local code into the container for hot-reloading.

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml --profile full build mcp-server
```

Then restart the service:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml --profile full up -d
```

### For MacOS

Embedding service is not compatible with Apple Silicon (M1/M2) due to the base image being x86_64. 
You should run it independently via 

```
model=google/embeddinggemma-300m
export HF_TOKEN=<your CLI READ token>
text-embeddings-router --model-id $model --port 8080
```

This will start the embedding service on port 8080, and you can configure the backend to connect to this service by setting `EMBEDDING_MODEL_URL=http://host.docker.internal:8080` in the `.env` file, and use the following docker compose command to start the rest of the services without the embedding service:

```bash
docker compose -f docker-compose.yml -f docker-compose.mac.yml --profile full up -d
```


