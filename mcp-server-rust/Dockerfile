# Build stage
FROM rust:1.84-slim-bookworm AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    pkg-config \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy manifests
COPY Cargo.toml Cargo.lock* ./

# Create a dummy main.rs to cache dependencies
RUN mkdir -p src && echo "fn main() {}" > src/main.rs

# Build dependencies (this layer will be cached)
RUN cargo build --release && rm -rf src

# Copy actual source code
COPY src ./src

# Build the actual application
RUN touch src/main.rs && cargo build --release

# Runtime stage
FROM debian:bookworm-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    ca-certificates \
    libssl3 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy the binary from builder
COPY --from=builder /app/target/release/financial-mcp-server /app/financial-mcp-server

# Create keys directory
RUN mkdir -p /app/keys

# Set environment variables
ENV RUST_LOG=info
ENV GCP_PROJECT_ID=""
ENV GOOGLE_APPLICATION_CREDENTIALS="/app/keys/bigquery.json"

# The server uses stdio transport by default for MCP
# Expose port for SSE/HTTP transport (if used in future)
EXPOSE 9003

# Run the server with stdio transport
ENTRYPOINT ["/app/financial-mcp-server"]
CMD ["--transport", "stdio"]
