# Forecase agent


This repository contains the Forecast Agent system, which includes a frontend UI, a backend OpenAI-compatible API server, and an MCP server for data storage using BigQuery.


This repo will help you make estimations and forecasts using LLMs with advanced agent strategies.


Start with Docker Compose for easy setup of all components.

```bash
cd forecast-agent

cp .env.example .env
```

Edit the `.env` file to set your API keys and configurations.

Start all services with Docker Compose:

```bash
docker-compose up -d
```


Init with vectordb installed

```
docker compose --profile vectordb-init run --rm vectordb-init
```