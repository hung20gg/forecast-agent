# Financial MCP Server (Rust)

A high-performance Model Context Protocol (MCP) server implementation in Rust for financial data analysis. This server provides tools for querying financial data from Google BigQuery, including stocks, commodities, indices, financial statements, and news.

## Features

- **High Performance**: Written in Rust for optimal performance and low memory footprint
- **Dual Transport**: Supports both stdio (for MCP clients) and SSE/HTTP (for web applications)
- **Stock Data**: Query daily and monthly stock prices with EMA indicators
- **Commodities**: Fetch commodity prices and trends
- **Market Indices**: Access index values (VN30, VNINDEX, etc.)
- **Financial Statements**: Query balance sheets, income statements, cash flows
- **Financial Ratios**: Search and query financial ratios (P/E, ROE, etc.)
- **News**: Search relevant financial news articles

## Prerequisites

- Rust 1.83 or higher (for local builds)
- Docker (for containerized deployment)
- Google Cloud Platform account with BigQuery access
- Service account credentials (JSON key file)

## Installation

### From Source

```bash
# Clone the repository
cd mcp-server-rust

# Build the release binary
cargo build --release

# The binary will be at target/release/financial-mcp-server
```

### Using Docker

```bash
# Build the Docker image
docker build -t financial-mcp-server-rust .

# Run with SSE transport (recommended for web/HTTP clients)
docker run -d \
  -p 9003:9003 \
  -e GCP_PROJECT_ID=your-project-id \
  -e LIMIT_TIME=2025-01-01 \
  -v /path/to/keys:/app/keys:ro \
  financial-mcp-server-rust \
  --transport sse --host 0.0.0.0 --port 9003

# Run with stdio transport (for MCP clients like Claude Desktop)
docker run -it \
  -e GCP_PROJECT_ID=your-project-id \
  -v /path/to/keys:/app/keys:ro \
  financial-mcp-server-rust \
  --transport stdio
```

### Using Docker Compose

The Rust MCP server is included in the main `docker-compose.yml` as the default:

```bash
# Start all services (uses Rust MCP server by default)
docker-compose up -d

# Or explicitly use Rust profile
docker-compose --profile rust up -d

# To use Python MCP server instead
docker-compose --profile python up -d
```

## Configuration

The server is configured via environment variables:

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `GCP_PROJECT_ID` | Google Cloud project ID | Yes | - |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to service account JSON | Yes* | `/app/keys/bigquery.json` |
| `LIMIT_TIME` | Maximum date for queries (YYYY-MM-DD) | No | - |
| `RUST_LOG` | Log level (info, debug, trace) | No | `info` |

*Required unless running in a GCP environment with default credentials.

### Command Line Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `--transport` | Transport mode: `stdio` or `sse` | `stdio` |
| `--host` | Host address for SSE transport | `0.0.0.0` |
| `--port` | Port for SSE transport | `9003` |

### Environment File

Create a `.env` file in the project root:

```env
GCP_PROJECT_ID=your-gcp-project-id
GOOGLE_APPLICATION_CREDENTIALS=/path/to/keys/bigquery.json
LIMIT_TIME=2025-01-01
RUST_LOG=info
```

## Usage

### Running the Server

```bash
# Using stdio transport (default, for MCP clients like Claude Desktop)
./target/release/financial-mcp-server --transport stdio

# Using SSE transport (for HTTP/web clients)
./target/release/financial-mcp-server --transport sse --port 9003

# With custom host and port
./target/release/financial-mcp-server --transport sse --host 127.0.0.1 --port 8080
```

### SSE Transport Endpoints

When running with SSE transport, the server exposes:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/sse` | GET | SSE connection endpoint |
| `/message` | POST | JSON-RPC message endpoint |
| `/health` | GET | Health check endpoint |

Example SSE client connection:
```bash
# Health check
curl http://localhost:9003/health

# List available tools
curl -X POST http://localhost:9003/message \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}'
```

### Configuring with Claude Desktop

Add to your `claude_desktop_config.json`:

**macOS/Linux:**
```json
{
  "mcpServers": {
    "financial-data": {
      "command": "/path/to/financial-mcp-server",
      "env": {
        "GCP_PROJECT_ID": "your-project-id",
        "GOOGLE_APPLICATION_CREDENTIALS": "/path/to/keys/bigquery.json"
      }
    }
  }
}
```

**Windows:**
```json
{
  "mcpServers": {
    "financial-data": {
      "command": "C:\\path\\to\\financial-mcp-server.exe",
      "env": {
        "GCP_PROJECT_ID": "your-project-id",
        "GOOGLE_APPLICATION_CREDENTIALS": "C:\\path\\to\\keys\\bigquery.json"
      }
    }
  }
}
```

## Available Tools

### Stock Tools

#### `get_stock_value`
Fetch stock price data for a given symbol and date range.

**Parameters:**
- `stock_code`: Stock symbol (e.g., "VNM", "FPT")
- `start_date`: Start date in YYYY-MM-DD format
- `end_date`: End date in YYYY-MM-DD format
- `duration`: "daily" or "monthly"

### Commodity Tools

#### `get_commodities_value`
Fetch commodity price data.

**Parameters:**
- `commodity_code`: Commodity code
- `start_date`: Start date in YYYY-MM-DD format
- `end_date`: End date in YYYY-MM-DD format
- `duration`: "daily" or "monthly"

### Index Tools

#### `get_indices_value`
Fetch market index data.

**Parameters:**
- `index_name`: Index name (e.g., "VN30", "VNINDEX")
- `start_date`: Start date in YYYY-MM-DD format
- `end_date`: End date in YYYY-MM-DD format
- `duration`: "daily" or "monthly"

### Financial Statement Tools

#### `get_exact_financial_ratio_code`
Search for financial ratio codes.

**Parameters:**
- `query`: Search query in English

#### `query_financial_ratio`
Query financial ratio data for a stock.

**Parameters:**
- `stock_code`: Stock symbol
- `ratio_code`: Ratio code (from search)
- `start_date`: Start date
- `end_date`: End date
- `duration`: "quarterly" or "annually"

#### `get_exact_financial_statement_account`
Search for financial statement account codes.

**Parameters:**
- `query`: Search query in English

#### `query_financial_statement`
Query financial statement data.

**Parameters:**
- `stock_code`: Stock symbol
- `category_code`: Category code (from search)
- `start_date`: Start date
- `end_date`: End date
- `duration`: "quarterly" or "annually"

### News Tools

#### `query_relevant_news`
Search for relevant news articles.

**Parameters:**
- `query`: Search query
- `start_date`: Start date
- `end_date`: End date
- `channel`: (Optional) Channel name filter

## Development

### Project Structure

```
mcp-server-rust/
├── Cargo.toml          # Dependencies and project config
├── Cargo.lock          # Locked dependencies
├── Dockerfile          # Docker build configuration
├── README.md           # This file
├── .env                # Local environment variables
├── src/
│   ├── main.rs         # Entry point, MCP handlers, SSE server
│   ├── mcp.rs          # MCP protocol types (JSON-RPC)
│   ├── bigquery.rs     # BigQuery client implementation
│   ├── config.rs       # Configuration management
│   └── tools/          # Tool implementations
│       ├── mod.rs
│       ├── stock.rs
│       ├── commodity.rs
│       ├── indices.rs
│       ├── financial.rs
│       └── news.rs
└── keys/               # Credentials (not in git)
    └── bigquery.json
```

### Building

```bash
# Debug build
cargo build

# Release build (optimized)
cargo build --release

# Run tests
cargo test

# Run with logging
RUST_LOG=debug cargo run -- --transport sse --port 9003
```

### Key Dependencies

- `tokio` - Async runtime
- `axum` - Web framework for SSE/HTTP transport
- `reqwest` - HTTP client for BigQuery API
- `gcp_auth` - Google Cloud authentication
- `serde` / `serde_json` - Serialization
- `chrono` - Date/time handling
- `tracing` - Structured logging
- `clap` - Command line argument parsing

### Architecture

The server implements the Model Context Protocol (MCP) manually without external MCP SDKs:

1. **Transport Layer**: Supports both stdio and SSE/HTTP transports
2. **Protocol Layer**: JSON-RPC 2.0 message handling
3. **Tool Layer**: Financial data query tools
4. **Data Layer**: BigQuery client for data retrieval

## Troubleshooting

### Common Issues

1. **Authentication Errors**
   - Ensure `GOOGLE_APPLICATION_CREDENTIALS` points to a valid JSON key file
   - Verify the service account has BigQuery permissions
   - For Docker, ensure the keys volume is mounted correctly: `-v /path/to/keys:/app/keys:ro`

2. **Connection Issues**
   - Check network connectivity to Google Cloud
   - Verify the project ID is correct
   - For SSE transport, ensure the port is not already in use

3. **No Data Returned**
   - Verify the date range and parameters
   - Check if `LIMIT_TIME` is restricting results
   - Ensure the stock/commodity code is valid

4. **Docker Build Fails**
   - Requires Rust 1.84+ in the Docker image (already configured)
   - Ensure sufficient disk space for cargo cache

### Logging

Enable debug logging for more details:

```bash
# Local
RUST_LOG=debug ./target/release/financial-mcp-server --transport sse

# Docker
docker run -e RUST_LOG=debug ... financial-mcp-server-rust
```

## Performance

Compared to the Python version:
- **Binary Size**: ~10MB (statically linked)
- **Memory Usage**: ~20MB at idle vs ~100MB+ for Python
- **Startup Time**: <100ms vs ~2s for Python
- **Request Latency**: Lower due to no interpreter overhead

## License

MIT License

## Contributing

Contributions are welcome! Please read the contributing guidelines before submitting PRs.
