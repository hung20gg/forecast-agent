//! Index data tools for querying market indices

use crate::bigquery::BigQueryClient;
use tracing::{debug, error};

/// Get indices value data (daily or monthly)
pub async fn get_indices_value(
    client: &BigQueryClient,
    index_name: &str,
    start_date: &str,
    end_date: &str,
    duration: &str,
) -> String {
    match duration {
        "daily" => query_indices_value_daily(client, index_name, start_date, end_date).await,
        "monthly" => query_indices_value_monthly(client, index_name, start_date, end_date).await,
        _ => "Invalid duration specified. Use 'daily' or 'monthly'.".to_string(),
    }
}

/// Query daily index values
async fn query_indices_value_daily(
    client: &BigQueryClient,
    index_name: &str,
    start_date: &str,
    end_date: &str,
) -> String {
    let end_date = client.apply_limit_time(end_date);
    
    let query = format!(
        r#"
        SELECT 
            time,
            close,
            volume,
            EMA20,
            EMA50
        FROM 
            `ktln.indices_daily`
        WHERE 
            index_name = '{}'
            AND time BETWEEN '{}' AND '{}'
        ORDER BY 
            time ASC
        "#,
        index_name, start_date, end_date
    );

    debug!(
        "Querying daily index data for {} from {} to {}",
        index_name, start_date, end_date
    );

    match client.execute_query(&query, None).await {
        Ok(result) => {
            if result.is_empty() {
                "No data found for the given parameters.".to_string()
            } else {
                result.to_markdown()
            }
        }
        Err(e) => {
            error!("Error querying index value: {}", e);
            format!("Error querying index value: {}", e)
        }
    }
}

/// Query monthly index values
async fn query_indices_value_monthly(
    client: &BigQueryClient,
    index_name: &str,
    start_date: &str,
    end_date: &str,
) -> String {
    let end_date = client.apply_limit_time(end_date);
    
    let query = format!(
        r#"
        SELECT 
            time,
            close,
            volume,
            EMA12,
            EMA26
        FROM 
            `ktln.indices_monthly`
        WHERE 
            index_name = '{}'
            AND time BETWEEN '{}' AND '{}'
        ORDER BY 
            time ASC
        "#,
        index_name, start_date, end_date
    );

    debug!(
        "Querying monthly index data for {} from {} to {}",
        index_name, start_date, end_date
    );

    match client.execute_query(&query, None).await {
        Ok(result) => {
            if result.is_empty() {
                "No data found for the given parameters.".to_string()
            } else {
                result.to_markdown()
            }
        }
        Err(e) => {
            error!("Error querying index value: {}", e);
            format!("Error querying index value: {}", e)
        }
    }
}
