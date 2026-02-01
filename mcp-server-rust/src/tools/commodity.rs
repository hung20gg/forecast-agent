//! Commodity data tools for querying commodity prices

use crate::bigquery::BigQueryClient;
use tracing::{debug, error};

/// Get commodities value data (daily or monthly)
pub async fn get_commodities_value(
    client: &BigQueryClient,
    commodity_code: &str,
    start_date: &str,
    end_date: &str,
    duration: &str,
) -> String {
    match duration {
        "daily" => query_commodities_value_daily(client, commodity_code, start_date, end_date).await,
        "monthly" => query_commodities_value_monthly(client, commodity_code, start_date, end_date).await,
        _ => "Invalid duration specified. Use 'daily' or 'monthly'.".to_string(),
    }
}

/// Query daily commodity values
async fn query_commodities_value_daily(
    client: &BigQueryClient,
    commodity_code: &str,
    start_date: &str,
    end_date: &str,
) -> String {
    let end_date = client.apply_limit_time(end_date);
    
    let query = format!(
        r#"
        SELECT 
            time,
            value,
            volume,
            EMA20,
            EMA50
        FROM 
            `ktln.commodities_daily`
        WHERE 
            indicator_code = '{}'
            AND time BETWEEN '{}' AND '{}'
        ORDER BY 
            time ASC
        "#,
        commodity_code, start_date, end_date
    );

    debug!(
        "Querying daily commodity data for {} from {} to {}",
        commodity_code, start_date, end_date
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
            error!("Error querying commodity value: {}", e);
            format!("Error querying commodity value: {}", e)
        }
    }
}

/// Query monthly commodity values
async fn query_commodities_value_monthly(
    client: &BigQueryClient,
    commodity_code: &str,
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
            `ktln.commodities_monthly`
        WHERE 
            indicator_code = '{}'
            AND time BETWEEN '{}' AND '{}'
        ORDER BY 
            time ASC
        "#,
        commodity_code, start_date, end_date
    );

    debug!(
        "Querying monthly commodity data for {} from {} to {}",
        commodity_code, start_date, end_date
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
            error!("Error querying commodity value: {}", e);
            format!("Error querying commodity value: {}", e)
        }
    }
}
