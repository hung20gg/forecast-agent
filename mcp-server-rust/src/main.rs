//! Financial Data Analysis MCP Server
//!
//! This server provides tools for querying financial data from BigQuery,
//! including stocks, commodities, indices, financial statements, and news.

mod bigquery;
mod config;
mod mcp;
mod tools;

use anyhow::Result;
use axum::{
    extract::{Json, State},
    http::StatusCode,
    response::{
        sse::{Event, Sse},
        IntoResponse,
    },
    routing::{get, post},
    Router,
};
use clap::Parser;
use futures::stream::{self, Stream};
use mcp::*;
use serde_json::Value;
use std::collections::HashMap;
use std::convert::Infallible;
use std::io::{BufRead, Write};
use std::sync::Arc;
use tokio::sync::{broadcast, RwLock};
use tower_http::cors::{Any, CorsLayer};
use tracing::{debug, error, info};
use tracing_subscriber::{self, fmt::format::FmtSpan, EnvFilter};

use bigquery::BigQueryClient;
use config::Config;

/// Financial Data Analysis MCP Server
#[derive(Parser, Debug, Clone)]
#[command(author, version, about, long_about = None)]
struct Args {
    /// Transport mode: stdio or sse
    #[arg(long, default_value = "stdio")]
    transport: String,

    /// Host for SSE transport
    #[arg(long, default_value = "0.0.0.0")]
    host: String,

    /// Port for SSE transport
    #[arg(long, default_value = "9003")]
    port: u16,
}

/// Define all available tools
fn get_tools() -> Vec<Tool> {
    vec![
        // Stock tool
        Tool {
            name: "get_stock_value".to_string(),
            description: "Fetch stock value from BigQuery for the given stock symbol and date range. Returns daily or monthly data including close price, volume, and EMA indicators.".to_string(),
            input_schema: InputSchema {
                schema_type: "object".to_string(),
                properties: HashMap::from([
                    ("stock_code".to_string(), string_property("Stock code to query (e.g., 'VNM', 'FPT')")),
                    ("start_date".to_string(), string_property("Start date in 'YYYY-MM-DD' format")),
                    ("end_date".to_string(), string_property("End date in 'YYYY-MM-DD' format")),
                    ("duration".to_string(), enum_property("Data frequency", vec!["daily", "monthly"])),
                ]),
                required: vec!["stock_code".to_string(), "start_date".to_string(), "end_date".to_string(), "duration".to_string()],
            },
        },
        // Commodity tool
        Tool {
            name: "get_commodities_value".to_string(),
            description: "Fetch commodities value from BigQuery for the given commodity code and date range. Returns daily or monthly price data with EMA indicators.".to_string(),
            input_schema: InputSchema {
                schema_type: "object".to_string(),
                properties: HashMap::from([
                    ("commodity_code".to_string(), string_property("Commodity code to query")),
                    ("start_date".to_string(), string_property("Start date in 'YYYY-MM-DD' format")),
                    ("end_date".to_string(), string_property("End date in 'YYYY-MM-DD' format")),
                    ("duration".to_string(), enum_property("Data frequency", vec!["daily", "monthly"])),
                ]),
                required: vec!["commodity_code".to_string(), "start_date".to_string(), "end_date".to_string(), "duration".to_string()],
            },
        },
        // Indices tool
        Tool {
            name: "get_indices_value".to_string(),
            description: "Fetch indices value from BigQuery for the given index name and date range. Returns daily or monthly data including close price, volume, and EMA indicators.".to_string(),
            input_schema: InputSchema {
                schema_type: "object".to_string(),
                properties: HashMap::from([
                    ("index_name".to_string(), string_property("Index name to query (e.g., 'VN30', 'VNINDEX')")),
                    ("start_date".to_string(), string_property("Start date in 'YYYY-MM-DD' format")),
                    ("end_date".to_string(), string_property("End date in 'YYYY-MM-DD' format")),
                    ("duration".to_string(), enum_property("Data frequency", vec!["daily", "monthly"])),
                ]),
                required: vec!["index_name".to_string(), "start_date".to_string(), "end_date".to_string(), "duration".to_string()],
            },
        },
        // Financial ratio code search
        Tool {
            name: "get_exact_financial_ratio_code".to_string(),
            description: "Find the exact financial ratio code based on a user query. Since financial ratio codes and names can be numerous and complex, this tool helps to search and find the correct code.".to_string(),
            input_schema: InputSchema {
                schema_type: "object".to_string(),
                properties: HashMap::from([
                    ("query".to_string(), string_property("User query to find the exact financial ratio code. Should be in English.")),
                ]),
                required: vec!["query".to_string()],
            },
        },
        // Financial ratio query
        Tool {
            name: "query_financial_ratio".to_string(),
            description: "Fetch financial ratio data from BigQuery for the given stock code, ratio code, and date range.".to_string(),
            input_schema: InputSchema {
                schema_type: "object".to_string(),
                properties: HashMap::from([
                    ("stock_code".to_string(), string_property("Stock code to query")),
                    ("ratio_code".to_string(), string_property("Financial ratio code to query")),
                    ("start_date".to_string(), string_property("Start date in 'YYYY-MM-DD' format")),
                    ("end_date".to_string(), string_property("End date in 'YYYY-MM-DD' format")),
                    ("duration".to_string(), enum_property("Data frequency", vec!["quarterly", "annually"])),
                ]),
                required: vec!["stock_code".to_string(), "ratio_code".to_string(), "start_date".to_string(), "end_date".to_string(), "duration".to_string()],
            },
        },
        // Financial statement account search
        Tool {
            name: "get_exact_financial_statement_account".to_string(),
            description: "Find the exact financial statement account based on a user query. Since financial statement accounts can be numerous and complex, this tool helps to search and find the correct account code.".to_string(),
            input_schema: InputSchema {
                schema_type: "object".to_string(),
                properties: HashMap::from([
                    ("query".to_string(), string_property("User query to find the exact financial statement account. Should be in English.")),
                ]),
                required: vec!["query".to_string()],
            },
        },
        // Financial statement query
        Tool {
            name: "query_financial_statement".to_string(),
            description: "Fetch financial statement data from BigQuery for the given stock code, category code, and date range.".to_string(),
            input_schema: InputSchema {
                schema_type: "object".to_string(),
                properties: HashMap::from([
                    ("stock_code".to_string(), string_property("Stock code to query")),
                    ("category_code".to_string(), string_property("Financial statement category code to query")),
                    ("start_date".to_string(), string_property("Start date in 'YYYY-MM-DD' format")),
                    ("end_date".to_string(), string_property("End date in 'YYYY-MM-DD' format")),
                    ("duration".to_string(), enum_property("Data frequency", vec!["quarterly", "annually"])),
                ]),
                required: vec!["stock_code".to_string(), "category_code".to_string(), "start_date".to_string(), "end_date".to_string(), "duration".to_string()],
            },
        },
        // News search
        Tool {
            name: "query_relevant_news".to_string(),
            description: "Search and fetch relevant news articles from BigQuery based on a query and date range.".to_string(),
            input_schema: InputSchema {
                schema_type: "object".to_string(),
                properties: HashMap::from([
                    ("query".to_string(), string_property("Search query for news articles")),
                    ("start_date".to_string(), string_property("Start date in 'YYYY-MM-DD' format")),
                    ("end_date".to_string(), string_property("End date in 'YYYY-MM-DD' format")),
                    ("channel".to_string(), string_property("Optional channel name to filter news")),
                ]),
                required: vec!["query".to_string(), "start_date".to_string(), "end_date".to_string()],
            },
        },
    ]
}

/// Handle a tool call
async fn handle_tool_call(
    client: &BigQueryClient,
    name: &str,
    args: &HashMap<String, Value>,
) -> CallToolResult {
    // Helper to extract string arg
    let get_str = |key: &str| -> Option<String> {
        args.get(key).and_then(|v| v.as_str()).map(|s| s.to_string())
    };

    match name {
        "get_stock_value" => {
            let Some(stock_code) = get_str("stock_code") else {
                return CallToolResult::error("Missing required parameter: stock_code".to_string());
            };
            let Some(start_date) = get_str("start_date") else {
                return CallToolResult::error("Missing required parameter: start_date".to_string());
            };
            let Some(end_date) = get_str("end_date") else {
                return CallToolResult::error("Missing required parameter: end_date".to_string());
            };
            let Some(duration) = get_str("duration") else {
                return CallToolResult::error("Missing required parameter: duration".to_string());
            };

            let result = tools::stock::get_stock_value(client, &stock_code, &start_date, &end_date, &duration).await;
            CallToolResult::text(result)
        }

        "get_commodities_value" => {
            let Some(commodity_code) = get_str("commodity_code") else {
                return CallToolResult::error("Missing required parameter: commodity_code".to_string());
            };
            let Some(start_date) = get_str("start_date") else {
                return CallToolResult::error("Missing required parameter: start_date".to_string());
            };
            let Some(end_date) = get_str("end_date") else {
                return CallToolResult::error("Missing required parameter: end_date".to_string());
            };
            let Some(duration) = get_str("duration") else {
                return CallToolResult::error("Missing required parameter: duration".to_string());
            };

            let result = tools::commodity::get_commodities_value(client, &commodity_code, &start_date, &end_date, &duration).await;
            CallToolResult::text(result)
        }

        "get_indices_value" => {
            let Some(index_name) = get_str("index_name") else {
                return CallToolResult::error("Missing required parameter: index_name".to_string());
            };
            let Some(start_date) = get_str("start_date") else {
                return CallToolResult::error("Missing required parameter: start_date".to_string());
            };
            let Some(end_date) = get_str("end_date") else {
                return CallToolResult::error("Missing required parameter: end_date".to_string());
            };
            let Some(duration) = get_str("duration") else {
                return CallToolResult::error("Missing required parameter: duration".to_string());
            };

            let result = tools::indices::get_indices_value(client, &index_name, &start_date, &end_date, &duration).await;
            CallToolResult::text(result)
        }

        "get_exact_financial_ratio_code" => {
            let Some(query) = get_str("query") else {
                return CallToolResult::error("Missing required parameter: query".to_string());
            };

            let result = tools::financial::get_exact_financial_ratio_code(client, &query).await;
            CallToolResult::text(result)
        }

        "query_financial_ratio" => {
            let Some(stock_code) = get_str("stock_code") else {
                return CallToolResult::error("Missing required parameter: stock_code".to_string());
            };
            let Some(ratio_code) = get_str("ratio_code") else {
                return CallToolResult::error("Missing required parameter: ratio_code".to_string());
            };
            let Some(start_date) = get_str("start_date") else {
                return CallToolResult::error("Missing required parameter: start_date".to_string());
            };
            let Some(end_date) = get_str("end_date") else {
                return CallToolResult::error("Missing required parameter: end_date".to_string());
            };
            let Some(duration) = get_str("duration") else {
                return CallToolResult::error("Missing required parameter: duration".to_string());
            };

            let result = tools::financial::query_financial_ratio(client, &stock_code, &ratio_code, &start_date, &end_date, &duration).await;
            CallToolResult::text(result)
        }

        "get_exact_financial_statement_account" => {
            let Some(query) = get_str("query") else {
                return CallToolResult::error("Missing required parameter: query".to_string());
            };

            let result = tools::financial::get_exact_financial_statement_account(client, &query).await;
            CallToolResult::text(result)
        }

        "query_financial_statement" => {
            let Some(stock_code) = get_str("stock_code") else {
                return CallToolResult::error("Missing required parameter: stock_code".to_string());
            };
            let Some(category_code) = get_str("category_code") else {
                return CallToolResult::error("Missing required parameter: category_code".to_string());
            };
            let Some(start_date) = get_str("start_date") else {
                return CallToolResult::error("Missing required parameter: start_date".to_string());
            };
            let Some(end_date) = get_str("end_date") else {
                return CallToolResult::error("Missing required parameter: end_date".to_string());
            };
            let Some(duration) = get_str("duration") else {
                return CallToolResult::error("Missing required parameter: duration".to_string());
            };

            let result = tools::financial::query_financial_statement(client, &stock_code, &category_code, &start_date, &end_date, &duration).await;
            CallToolResult::text(result)
        }

        "query_relevant_news" => {
            let Some(query) = get_str("query") else {
                return CallToolResult::error("Missing required parameter: query".to_string());
            };
            let Some(start_date) = get_str("start_date") else {
                return CallToolResult::error("Missing required parameter: start_date".to_string());
            };
            let Some(end_date) = get_str("end_date") else {
                return CallToolResult::error("Missing required parameter: end_date".to_string());
            };
            let channel = get_str("channel");

            let result = tools::news::query_relevant_news(client, &query, &start_date, &end_date, channel.as_deref()).await;
            CallToolResult::text(result)
        }

        _ => CallToolResult::error(format!("Unknown tool: {}", name)),
    }
}

/// Handle incoming JSON-RPC request
/// Returns None for notifications (which don't require responses)
async fn handle_request(
    client: &BigQueryClient,
    request: JsonRpcRequest,
) -> Option<JsonRpcResponse> {
    debug!("Handling request: {}", request.method);

    match request.method.as_str() {
        "initialize" => {
            let result = InitializeResult {
                protocol_version: "2024-11-05".to_string(),
                capabilities: ServerCapabilities {
                    tools: Some(ToolsCapability { list_changed: false }),
                },
                server_info: ServerInfo {
                    name: "financial-mcp-server".to_string(),
                    version: env!("CARGO_PKG_VERSION").to_string(),
                },
            };
            Some(JsonRpcResponse::success(request.id, serde_json::to_value(result).unwrap()))
        }

        "notifications/initialized" | "initialized" => {
            // This is a notification, no response needed
            debug!("Received notification: {}", request.method);
            None
        }

        "tools/list" => {
            let result = ToolsListResult { tools: get_tools() };
            Some(JsonRpcResponse::success(request.id, serde_json::to_value(result).unwrap()))
        }

        "tools/call" => {
            let params: CallToolParams = match request.params {
                Some(p) => match serde_json::from_value(p) {
                    Ok(params) => params,
                    Err(e) => {
                        return Some(JsonRpcResponse::error(
                            request.id,
                            INVALID_PARAMS,
                            &format!("Invalid params: {}", e),
                        ));
                    }
                },
                None => {
                    return Some(JsonRpcResponse::error(
                        request.id,
                        INVALID_PARAMS,
                        "Missing params for tools/call",
                    ));
                }
            };

            let result = handle_tool_call(client, &params.name, &params.arguments).await;
            Some(JsonRpcResponse::success(request.id, serde_json::to_value(result).unwrap()))
        }

        "ping" => {
            Some(JsonRpcResponse::success(request.id, serde_json::json!({})))
        }

        // Handle other notifications (methods starting with "notifications/")
        method if method.starts_with("notifications/") => {
            debug!("Received notification: {}", method);
            None
        }

        _ => {
            debug!("Method not found: {}", request.method);
            Some(JsonRpcResponse::error(
                request.id,
                METHOD_NOT_FOUND,
                &format!("Method not found: {}", request.method),
            ))
        }
    }
}

fn init_tracing() {
    tracing_subscriber::fmt()
        .with_env_filter(EnvFilter::from_default_env().add_directive(tracing::Level::INFO.into()))
        .with_span_events(FmtSpan::CLOSE)
        .with_writer(std::io::stderr)
        .init();
}

/// Shared application state for SSE transport
#[derive(Clone)]
struct AppState {
    client: Arc<BigQueryClient>,
    // Channel for SSE events - stores pending responses
    sse_responses: Arc<RwLock<HashMap<String, broadcast::Sender<String>>>>,
}

/// SSE endpoint - client connects here to receive server-sent events
async fn sse_handler(
    State(state): State<AppState>,
) -> Sse<impl Stream<Item = Result<Event, Infallible>>> {
    let session_id = uuid::Uuid::new_v4().to_string();
    info!("New SSE connection: {}", session_id);

    // Create a channel for this session
    let (tx, mut rx) = broadcast::channel::<String>(100);
    
    // Store the sender
    {
        let mut responses = state.sse_responses.write().await;
        responses.insert(session_id.clone(), tx);
    }

    // Send initial endpoint event with the session ID
    let endpoint_url = format!("/message?session_id={}", session_id);
    
    let stream = async_stream::stream! {
        // First, send the endpoint event
        yield Ok(Event::default()
            .event("endpoint")
            .data(endpoint_url));

        // Then listen for responses
        loop {
            match rx.recv().await {
                Ok(data) => {
                    yield Ok(Event::default()
                        .event("message")
                        .data(data));
                }
                Err(broadcast::error::RecvError::Closed) => {
                    break;
                }
                Err(broadcast::error::RecvError::Lagged(_)) => {
                    continue;
                }
            }
        }
    };

    Sse::new(stream)
}

/// Message endpoint - client sends JSON-RPC requests here
async fn message_handler(
    State(state): State<AppState>,
    axum::extract::Query(params): axum::extract::Query<HashMap<String, String>>,
    Json(request): Json<JsonRpcRequest>,
) -> impl IntoResponse {
    let session_id = params.get("session_id").cloned().unwrap_or_default();
    debug!("Received request for session {}: {:?}", session_id, request.method);

    // Handle the request
    let response = handle_request(&state.client, request).await;

    // If it's a notification, return accepted but don't send response
    match response {
        Some(resp) => {
            let response_json = serde_json::to_string(&resp).unwrap();

            // Send response via SSE if session exists
            {
                let responses = state.sse_responses.read().await;
                if let Some(tx) = responses.get(&session_id) {
                    let _ = tx.send(response_json.clone());
                }
            }

            // Also return the response directly
            (StatusCode::OK, Json(serde_json::to_value(&resp).unwrap()))
        }
        None => {
            // Notification - return accepted with empty body
            (StatusCode::OK, Json(serde_json::json!({})))
        }
    }
}

/// Health check endpoint
async fn health_handler() -> impl IntoResponse {
    (StatusCode::OK, "OK")
}

/// Run the SSE transport
async fn run_sse_transport(client: BigQueryClient, host: &str, port: u16) -> Result<()> {
    let state = AppState {
        client: Arc::new(client),
        sse_responses: Arc::new(RwLock::new(HashMap::new())),
    };

    let cors = CorsLayer::new()
        .allow_origin(Any)
        .allow_methods(Any)
        .allow_headers(Any);

    let app = Router::new()
        .route("/sse", get(sse_handler))
        .route("/message", post(message_handler))
        .route("/health", get(health_handler))
        .layer(cors)
        .with_state(state);

    let addr = format!("{}:{}", host, port);
    info!("Starting SSE server on http://{}", addr);
    info!("  - SSE endpoint: http://{}/sse", addr);
    info!("  - Message endpoint: http://{}/message", addr);
    info!("  - Health endpoint: http://{}/health", addr);

    let listener = tokio::net::TcpListener::bind(&addr).await?;
    axum::serve(listener, app).await?;

    Ok(())
}

/// Run the stdio transport
async fn run_stdio_transport(client: BigQueryClient) -> Result<()> {
    let stdin = std::io::stdin();
    let stdout = std::io::stdout();
    let reader = stdin.lock();
    let mut writer = stdout.lock();

    info!("MCP Server ready, waiting for requests on stdio...");

    for line in reader.lines() {
        let line = match line {
            Ok(l) => l,
            Err(e) => {
                error!("Error reading line: {}", e);
                continue;
            }
        };

        if line.is_empty() {
            continue;
        }

        debug!("Received: {}", line);

        let request: JsonRpcRequest = match serde_json::from_str(&line) {
            Ok(r) => r,
            Err(e) => {
                error!("Parse error: {}", e);
                let response = JsonRpcResponse::error(None, PARSE_ERROR, &format!("Parse error: {}", e));
                let output = serde_json::to_string(&response).unwrap();
                writeln!(writer, "{}", output)?;
                writer.flush()?;
                continue;
            }
        };

        let response = handle_request(&client, request).await;

        // Only send response if it's not a notification
        if let Some(resp) = response {
            let output = serde_json::to_string(&resp)?;
            debug!("Sending: {}", output);
            writeln!(writer, "{}", output)?;
            writer.flush()?;
        } else {
            debug!("Notification handled, no response sent");
        }
    }

    Ok(())
}

#[tokio::main]
async fn main() -> Result<()> {
    // Initialize tracing (logging to stderr for MCP compatibility)
    init_tracing();

    let args = Args::parse();

    // Load configuration
    let config = Config::from_env()?;

    info!("Starting Financial MCP Server...");
    info!("Transport: {}", args.transport);

    // Initialize BigQuery client
    let client = BigQueryClient::new(
        config.credentials_path.as_deref(),
        &config.project_id,
        config.limit_time.as_deref(),
    )
    .await?;

    info!("BigQuery client initialized successfully");

    // Run the appropriate transport
    match args.transport.as_str() {
        "sse" | "http" => {
            run_sse_transport(client, &args.host, args.port).await?;
        }
        "stdio" | _ => {
            run_stdio_transport(client).await?;
        }
    }

    Ok(())
}
