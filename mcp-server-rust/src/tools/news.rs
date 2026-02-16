//! News search tools

use crate::bigquery::{BigQueryClient, QueryParameter};
use tracing::{debug, error, warn};
use serde::Deserialize;
use qdrant_client::{Qdrant, qdrant};
use std::env;

#[derive(Debug, Deserialize)]
struct EmbeddingResponse {
    #[serde(flatten)]
    embeddings: Vec<f32>,
}

/// Get embedding vector for a text query
async fn get_embedding(query: &str) -> Option<Vec<f32>> {
    let embedding_url = env::var("EMBEDDING_URL").unwrap_or_else(|_| "http://127.0.0.1:8081/embed".to_string());
    
    let client = reqwest::Client::new();
    let body = serde_json::json!({
        "inputs": query,
        "truncate": true
    });
    
    match client.post(&embedding_url)
        .json(&body)
        .timeout(std::time::Duration::from_secs(10))
        .send()
        .await
    {
        Ok(response) => {
            match response.json::<Vec<f32>>().await {
                Ok(embedding) => Some(embedding),
                Err(e) => {
                    error!("Failed to parse embedding response: {}", e);
                    None
                }
            }
        }
        Err(e) => {
            error!("Failed to get embedding: {}", e);
            None
        }
    }
}

/// Truncate text to max_length characters, adding ... if truncated
fn truncate_text(text: &str, max_length: usize) -> String {
    if text.len() <= max_length {
        text.to_string()
    } else {
        format!("{}...", &text[..max_length])
    }
}

/// Get news article by URL from BigQuery
pub async fn get_new_from_url(
    client: &BigQueryClient,
    url: &str,
) -> String {
    let query = r#"
        SELECT
            url,
            title,
            source,
            pub_date,
            text
        FROM `ktln.news`
        WHERE url = @url
        LIMIT 1
    "#;
    
    let params = vec![QueryParameter::string("url", url)];
    
    match client.execute_query(query, Some(params)).await {
        Ok(result) => {
            if result.is_empty() {
                serde_json::json!("No news found for the given URL.").to_string()
            } else {
                format_news_results_json(&result)
            }
        }
        Err(e) => {
            error!("Error querying news by URL: {}", e);
            format!("Error querying news by URL: {}", e)
        }
    }
}

/// Query news using vector similarity search from Qdrant
async fn query_news_from_vectordb(
    client: &BigQueryClient,
    user_query: &str,
    start_date: &str,
    end_date: &str,
) -> Option<String> {
    // Get embedding for the query
    let embedding = match get_embedding(user_query).await {
        Some(emb) => emb,
        None => {
            warn!("Failed to get embedding, falling back to BigQuery");
            return None;
        }
    };
    
    // Initialize Qdrant client
    let qdrant_host = env::var("QDRANT_HOST").unwrap_or_else(|_| "http://localhost:6333".to_string());
    let collection_name = env::var("COLLECTION_NAME").unwrap_or_else(|_| "news_embedding".to_string());
    
    let qdrant_client = match Qdrant::from_url(&qdrant_host).build() {
        Ok(client) => client,
        Err(e) => {
            error!("Failed to create Qdrant client: {}", e);
            return None;
        }
    };
    
    // Convert dates to timestamps
    use chrono::NaiveDate;
    let start_ts = match NaiveDate::parse_from_str(start_date, "%Y-%m-%d") {
        Ok(date) => date.and_hms_opt(0, 0, 0).unwrap().and_utc().timestamp(),
        Err(e) => {
            error!("Failed to parse start_date: {}", e);
            return None;
        }
    };
    let end_ts = match NaiveDate::parse_from_str(end_date, "%Y-%m-%d") {
        Ok(date) => date.and_hms_opt(23, 59, 59).unwrap().and_utc().timestamp(),
        Err(e) => {
            error!("Failed to parse end_date: {}", e);
            return None;
        }
    };
    
    // Build filter for date range
    let filter = qdrant::Filter {
        must: vec![
            qdrant::Condition::range(
                "pub_date",
                qdrant::Range {
                    gte: Some(start_ts as f64),
                    lte: Some(end_ts as f64),
                    ..Default::default()
                },
            ),
        ],
        ..Default::default()
    };
    
    // Query Qdrant
    let search_result = match qdrant_client
        .query(
            qdrant::QueryPointsBuilder::new(&collection_name)
                .query(embedding)
                .filter(filter)
                .limit(5_u64)
        )
        .await
    {
        Ok(result) => result,
        Err(e) => {
            error!("Failed to query Qdrant: {}", e);
            return None;
        }
    };
    
    // Extract unique URLs with scores
    let mut url_scores: std::collections::HashMap<String, f32> = std::collections::HashMap::new();
    for point in search_result.result {
        let payload = point.payload;
        if let Some(url_value) = payload.get("url") {
            if let Some(qdrant::value::Kind::StringValue(url)) = &url_value.kind {
                let score = point.score;
                url_scores.entry(url.to_string())
                    .and_modify(|s| *s = s.max(score))
                    .or_insert(score);
            }
        }
    }
    
    // Sort by score and take top 10
    let mut url_score_vec: Vec<_> = url_scores.into_iter().collect();
    url_score_vec.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap());
    url_score_vec.truncate(10);
    
    // Fetch full articles for each URL
    let mut articles = Vec::new();
    for (url, score) in url_score_vec {
        let article_json = get_new_from_url(client, &url).await;
        match serde_json::from_str::<Vec<serde_json::Value>>(&article_json) {
            Ok(mut article_data) => {
                if !article_data.is_empty() {
                    if let Some(article) = article_data.get_mut(0) {
                        // Add similarity score
                        article["score"] = serde_json::json!(score);
                        // Truncate text field
                        if let Some(text) = article.get("text").and_then(|t| t.as_str()) {
                            article["text"] = serde_json::json!(truncate_text(text, 750));
                        }
                        articles.push(article.clone());
                    }
                }
            }
            Err(e) => {
                error!("Error parsing article from URL {}: {}", url, e);
                continue;
            }
        }
    }
    
    match serde_json::to_string_pretty(&articles) {
        Ok(json) => Some(json),
        Err(e) => {
            error!("Failed to serialize articles: {}", e);
            None
        }
    }
}

/// Query relevant news articles with vector search fallback
pub async fn query_relevant_news(
    client: &BigQueryClient,
    user_query: &str,
    start_date: &str,
    end_date: &str,
    channel: Option<&str>,
    use_vectordb: bool,
) -> String {
    // Try vector search first if enabled and no channel filter
    if use_vectordb && channel.is_none() {
        if let Some(result) = query_news_from_vectordb(client, user_query, start_date, end_date).await {
            return result;
        }
        warn!("Vector search failed, falling back to BigQuery");
    }
    
    // Fallback to BigQuery full-text search
    query_news_bigquery(client, user_query, start_date, end_date, channel).await
}

/// Query news using BigQuery full-text search
async fn query_news_bigquery(
    client: &BigQueryClient,
    user_query: &str,
    start_date: &str,
    end_date: &str,
    channel: Option<&str>,
) -> String {
    let end_date = client.apply_limit_time(end_date);

    let (query, params) = if let Some(channel_name) = channel {
        let sql = r#"
            SELECT
                url,
                title,
                source,
                pub_date,
                text,
                (
                    IF(SEARCH(title, @q), 2, 0) +
                    IF(SEARCH(text, @q), 1, 0)
                ) AS score
            FROM `ktln.news`
            WHERE SEARCH((title, text), @q)
                AND pub_date BETWEEN @start_date AND @end_date
                AND channel_name = @channel
            ORDER BY score DESC, pub_date DESC
            LIMIT 10
        "#;
        let params = vec![
            QueryParameter::string("q", user_query),
            QueryParameter::string("start_date", start_date),
            QueryParameter::string("end_date", &end_date),
            QueryParameter::string("channel", channel_name),
        ];
        (sql, params)
    } else {
        let sql = r#"
            SELECT
                url,
                title,
                source,
                pub_date,
                text,
                (
                    IF(SEARCH(title, @q), 2, 0) +
                    IF(SEARCH(text, @q), 1, 0)
                ) AS score
            FROM `ktln.news`
            WHERE SEARCH((title, text), @q)
                AND pub_date BETWEEN @start_date AND @end_date
            ORDER BY score DESC, pub_date DESC
            LIMIT 10
        "#;
        let params = vec![
            QueryParameter::string("q", user_query),
            QueryParameter::string("start_date", start_date),
            QueryParameter::string("end_date", &end_date),
        ];
        (sql, params)
    };

    debug!(
        "Querying news for '{}' from {} to {}",
        user_query, start_date, end_date
    );

    match client.execute_query(query, Some(params)).await {
        Ok(result) => {
            if result.is_empty() {
                "No data found for the given parameters.".to_string()
            } else {
                // Truncate text and convert to JSON format
                format_news_results_json_with_truncation(&result)
            }
        }
        Err(e) => {
            error!("Error querying news: {}", e);
            format!("Error querying news: {}", e)
        }
    }
}

/// Test Qdrant connection
pub async fn test_qdrant_connection() -> bool {
    let qdrant_host = env::var("QDRANT_HOST").unwrap_or_else(|_| "http://localhost:6333".to_string());
    
    match Qdrant::from_url(&qdrant_host).build() {
        Ok(client) => {
            match client.health_check().await {
                Ok(_) => {
                    debug!("Qdrant connection successful - using vector search");
                    true
                }
                Err(e) => {
                    warn!("Qdrant health check failed: {} - using BigQuery fallback", e);
                    false
                }
            }
        }
        Err(e) => {
            warn!("Failed to initialize Qdrant client: {} - using BigQuery fallback", e);
            false
        }
    }
}

/// Format news results as JSON with text truncation
fn format_news_results_json_with_truncation(result: &crate::bigquery::QueryResult) -> String {
    let mut articles = Vec::new();
    
    for row in &result.rows {
        let mut article = serde_json::Map::new();
        
        if let Some(url) = row.get(0) {
            article.insert("url".to_string(), serde_json::json!(url));
        }
        if let Some(title) = row.get(1) {
            article.insert("title".to_string(), serde_json::json!(title));
        }
        if let Some(source) = row.get(2) {
            article.insert("source".to_string(), serde_json::json!(source));
        }
        if let Some(pub_date) = row.get(3) {
            article.insert("pub_date".to_string(), serde_json::json!(pub_date));
        }
        if let Some(text) = row.get(4) {
            article.insert("text".to_string(), serde_json::json!(truncate_text(text, 750)));
        }
        if let Some(score) = row.get(5) {
            article.insert("score".to_string(), serde_json::json!(score));
        }
        
        articles.push(serde_json::Value::Object(article));
    }
    
    serde_json::to_string_pretty(&articles).unwrap_or_else(|_| "[]".to_string())
}

/// Format news results as JSON (without truncation, for full article view)
fn format_news_results_json(result: &crate::bigquery::QueryResult) -> String {
    let mut articles = Vec::new();
    
    for row in &result.rows {
        let mut article = serde_json::Map::new();
        
        if let Some(url) = row.get(0) {
            article.insert("url".to_string(), serde_json::json!(url));
        }
        if let Some(title) = row.get(1) {
            article.insert("title".to_string(), serde_json::json!(title));
        }
        if let Some(source) = row.get(2) {
            article.insert("source".to_string(), serde_json::json!(source));
        }
        if let Some(pub_date) = row.get(3) {
            article.insert("pub_date".to_string(), serde_json::json!(pub_date));
        }
        if let Some(text) = row.get(4) {
            article.insert("text".to_string(), serde_json::json!(text));
        }
        
        articles.push(serde_json::Value::Object(article));
    }
    
    serde_json::to_string_pretty(&articles).unwrap_or_else(|_| "[]".to_string())
}
