//! BigQuery client module for Google Cloud BigQuery API interactions.

use anyhow::{Context, Result};
use reqwest::Client;
use serde::{Deserialize, Serialize};
use std::path::Path;
use std::sync::Arc;
use tokio::sync::RwLock;
use tracing::{debug, error, info};

/// BigQuery API base URL
const BIGQUERY_API_BASE: &str = "https://bigquery.googleapis.com/bigquery/v2";

/// BigQuery client for executing queries
pub struct BigQueryClient {
    http_client: Client,
    token_provider: Arc<RwLock<Option<Arc<gcp_auth::CustomServiceAccount>>>>,
    credentials_path: Option<String>,
    project_id: String,
    pub limit_time: Option<String>,
}

impl Clone for BigQueryClient {
    fn clone(&self) -> Self {
        Self {
            http_client: self.http_client.clone(),
            token_provider: self.token_provider.clone(),
            credentials_path: self.credentials_path.clone(),
            project_id: self.project_id.clone(),
            limit_time: self.limit_time.clone(),
        }
    }
}

/// BigQuery query request
#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
struct QueryRequest {
    query: String,
    use_legacy_sql: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    query_parameters: Option<Vec<QueryParameter>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    parameter_mode: Option<String>,
}

/// BigQuery query parameter
#[derive(Debug, Serialize, Clone)]
#[serde(rename_all = "camelCase")]
pub struct QueryParameter {
    pub name: String,
    pub parameter_type: ParameterType,
    pub parameter_value: ParameterValue,
}

/// Parameter type specification
#[derive(Debug, Serialize, Clone)]
#[serde(rename_all = "camelCase")]
pub struct ParameterType {
    #[serde(rename = "type")]
    pub type_name: String,
}

/// Parameter value
#[derive(Debug, Serialize, Clone)]
#[serde(rename_all = "camelCase")]
pub struct ParameterValue {
    pub value: String,
}

impl QueryParameter {
    pub fn string(name: &str, value: &str) -> Self {
        Self {
            name: name.to_string(),
            parameter_type: ParameterType {
                type_name: "STRING".to_string(),
            },
            parameter_value: ParameterValue {
                value: value.to_string(),
            },
        }
    }

    pub fn int64(name: &str, value: i64) -> Self {
        Self {
            name: name.to_string(),
            parameter_type: ParameterType {
                type_name: "INT64".to_string(),
            },
            parameter_value: ParameterValue {
                value: value.to_string(),
            },
        }
    }

    pub fn timestamp(name: &str, value: &str) -> Self {
        Self {
            name: name.to_string(),
            parameter_type: ParameterType {
                type_name: "TIMESTAMP".to_string(),
            },
            parameter_value: ParameterValue {
                value: value.to_string(),
            },
        }
    }
}

/// BigQuery query response
#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct QueryResponse {
    job_complete: bool,
    #[serde(default)]
    rows: Vec<QueryRow>,
    schema: Option<Schema>,
    #[serde(default)]
    errors: Vec<QueryError>,
    total_rows: Option<String>,
}

/// Query row
#[derive(Debug, Deserialize)]
struct QueryRow {
    f: Vec<QueryCell>,
}

/// Query cell
#[derive(Debug, Deserialize)]
struct QueryCell {
    v: Option<serde_json::Value>,
}

/// Schema definition
#[derive(Debug, Deserialize)]
struct Schema {
    fields: Vec<SchemaField>,
}

/// Schema field
#[derive(Debug, Deserialize)]
struct SchemaField {
    name: String,
    #[serde(rename = "type")]
    field_type: String,
}

/// Query error
#[derive(Debug, Deserialize)]
struct QueryError {
    message: String,
}

/// Query result with structured data
#[derive(Debug)]
pub struct QueryResult {
    pub columns: Vec<String>,
    pub rows: Vec<Vec<String>>,
}

impl QueryResult {
    /// Convert to markdown table format
    pub fn to_markdown(&self) -> String {
        if self.rows.is_empty() {
            return "No data found for the given parameters.".to_string();
        }

        let mut result = String::new();
        
        // Header row
        result.push_str("| ");
        result.push_str(&self.columns.join(" | "));
        result.push_str(" |\n");
        
        // Separator row
        result.push_str("|");
        for _ in &self.columns {
            result.push_str("---|");
        }
        result.push('\n');
        
        // Data rows
        for row in &self.rows {
            result.push_str("| ");
            result.push_str(&row.join(" | "));
            result.push_str(" |\n");
        }
        
        result
    }

    /// Check if the result is empty
    pub fn is_empty(&self) -> bool {
        self.rows.is_empty()
    }
}

impl BigQueryClient {
    /// Create a new BigQuery client
    pub async fn new(
        credentials_path: Option<&str>,
        project_id: &str,
        limit_time: Option<&str>,
    ) -> Result<Self> {
        let http_client = Client::builder()
            .build()
            .context("Failed to create HTTP client")?;

        info!("BigQuery client created for project: {}", project_id);

        Ok(Self {
            http_client,
            token_provider: Arc::new(RwLock::new(None)),
            credentials_path: credentials_path.map(|s| s.to_string()),
            project_id: project_id.to_string(),
            limit_time: limit_time.map(|s| s.to_string()),
        })
    }

    /// Get access token for API requests
    async fn get_token(&self) -> Result<String> {
        use gcp_auth::TokenProvider;
        
        // Initialize token provider if needed
        {
            let provider = self.token_provider.read().await;
            if provider.is_none() {
                drop(provider);
                let mut provider = self.token_provider.write().await;
                if provider.is_none() {
                    let path = self.credentials_path.as_ref()
                        .context("GOOGLE_APPLICATION_CREDENTIALS not set and no credentials path provided")?;
                    let creds = gcp_auth::CustomServiceAccount::from_file(Path::new(path))
                        .context("Failed to load service account credentials")?;
                    *provider = Some(Arc::new(creds));
                }
            }
        }

        let provider = self.token_provider.read().await;
        let provider = provider.as_ref().unwrap();
        
        let token = provider
            .token(&["https://www.googleapis.com/auth/bigquery"])
            .await
            .context("Failed to get access token")?;
        
        Ok(token.as_str().to_string())
    }

    /// Execute a query with optional parameters
    pub async fn execute_query(
        &self,
        query: &str,
        parameters: Option<Vec<QueryParameter>>,
    ) -> Result<QueryResult> {
        let token = self.get_token().await?;
        
        let url = format!(
            "{}/projects/{}/queries",
            BIGQUERY_API_BASE, self.project_id
        );

        let request_body = QueryRequest {
            query: query.to_string(),
            use_legacy_sql: false,
            query_parameters: parameters.clone(),
            parameter_mode: if parameters.is_some() {
                Some("NAMED".to_string())
            } else {
                None
            },
        };

        debug!("Executing BigQuery query: {}", query);

        let response = self
            .http_client
            .post(&url)
            .bearer_auth(&token)
            .json(&request_body)
            .send()
            .await
            .context("Failed to send query request")?;

        let status = response.status();
        let response_text = response.text().await?;

        if !status.is_success() {
            error!("BigQuery API error: {} - {}", status, response_text);
            return Err(anyhow::anyhow!("BigQuery API error: {} - {}", status, response_text));
        }

        let query_response: QueryResponse = serde_json::from_str(&response_text)
            .context("Failed to parse query response")?;

        if !query_response.errors.is_empty() {
            let error_messages: Vec<_> = query_response.errors.iter().map(|e| e.message.clone()).collect();
            return Err(anyhow::anyhow!("Query errors: {}", error_messages.join(", ")));
        }

        // Extract column names from schema
        let columns: Vec<String> = query_response
            .schema
            .map(|s| s.fields.iter().map(|f| f.name.clone()).collect())
            .unwrap_or_default();

        // Extract row data
        let rows: Vec<Vec<String>> = query_response
            .rows
            .iter()
            .map(|row| {
                row.f
                    .iter()
                    .map(|cell| {
                        cell.v
                            .as_ref()
                            .map(|v| match v {
                                serde_json::Value::String(s) => s.clone(),
                                serde_json::Value::Number(n) => n.to_string(),
                                serde_json::Value::Bool(b) => b.to_string(),
                                serde_json::Value::Null => "".to_string(),
                                _ => v.to_string(),
                            })
                            .unwrap_or_default()
                    })
                    .collect()
            })
            .collect();

        debug!("Query returned {} rows", rows.len());

        Ok(QueryResult { columns, rows })
    }

    /// Apply limit time to end_date if configured
    pub fn apply_limit_time(&self, end_date: &str) -> String {
        match &self.limit_time {
            Some(limit) if end_date > limit.as_str() => limit.clone(),
            _ => end_date.to_string(),
        }
    }

    /// Test the BigQuery connection
    pub async fn test_connection(&self) -> Result<bool> {
        let query = "SELECT 1 as test";
        match self.execute_query(query, None).await {
            Ok(_) => {
                info!("BigQuery connection test successful");
                Ok(true)
            }
            Err(e) => {
                error!("BigQuery connection test failed: {}", e);
                Ok(false)
            }
        }
    }
}
