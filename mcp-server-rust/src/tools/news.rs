//! News search tools

use crate::bigquery::{BigQueryClient, QueryParameter};
use tracing::{debug, error};

/// Query relevant news articles
pub async fn query_relevant_news(
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
                // Convert to JSON-like format for news
                format_news_results(&result)
            }
        }
        Err(e) => {
            error!("Error querying news: {}", e);
            format!("Error querying news: {}", e)
        }
    }
}

/// Format news results as a readable list
fn format_news_results(result: &crate::bigquery::QueryResult) -> String {
    let mut output = String::new();
    
    for (i, row) in result.rows.iter().enumerate() {
        if row.len() >= 4 {
            output.push_str(&format!("**{}. {}**\n", i + 1, row.get(1).unwrap_or(&"".to_string())));
            output.push_str(&format!("   - Source: {}\n", row.get(2).unwrap_or(&"".to_string())));
            output.push_str(&format!("   - Date: {}\n", row.get(3).unwrap_or(&"".to_string())));
            output.push_str(&format!("   - URL: {}\n\n", row.get(0).unwrap_or(&"".to_string())));
        }
    }
    
    if output.is_empty() {
        "No data found for the given parameters.".to_string()
    } else {
        output
    }
}
