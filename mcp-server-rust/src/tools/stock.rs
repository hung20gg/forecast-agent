//! Stock data tools for querying stock prices and indicators

use crate::bigquery::{BigQueryClient, QueryParameter};
use tracing::{debug, error};

/// Get stock value data (daily or monthly)
pub async fn get_stock_value(
    client: &BigQueryClient,
    stock_code: &str,
    start_date: &str,
    end_date: &str,
    duration: &str,
) -> String {
    match duration {
        "daily" => query_stock_value_daily(client, stock_code, start_date, end_date).await,
        "monthly" => query_stock_value_monthly(client, stock_code, start_date, end_date).await,
        _ => "Invalid duration specified. Use 'daily' or 'monthly'.".to_string(),
    }
}

/// Query daily stock values
async fn query_stock_value_daily(
    client: &BigQueryClient,
    stock_code: &str,
    start_date: &str,
    end_date: &str,
) -> String {
    let end_date = client.apply_limit_time(end_date);
    
    let query = r#"
        SELECT 
            time,
            close,
            volume,
            EMA20,
            EMA50
        FROM 
            `ktln.stock_daily`
        WHERE 
            stock_code = @stock_code
            AND time BETWEEN @start_date AND @end_date
        ORDER BY 
            time ASC
    "#;

    let params = vec![
        QueryParameter::string("stock_code", stock_code),
        QueryParameter::timestamp("start_date", start_date),
        QueryParameter::timestamp("end_date", &end_date),
    ];

    debug!(
        "Querying daily stock data for {} from {} to {}",
        stock_code, start_date, end_date
    );

    match client.execute_query(query, Some(params)).await {
        Ok(result) => {
            if result.is_empty() {
                "No data found for the given parameters.".to_string()
            } else {
                result.to_markdown()
            }
        }
        Err(e) => {
            error!("Error querying stock value: {}", e);
            format!("Error querying stock value: {}", e)
        }
    }
}

/// Query monthly stock values
async fn query_stock_value_monthly(
    client: &BigQueryClient,
    stock_code: &str,
    start_date: &str,
    end_date: &str,
) -> String {
    let end_date = client.apply_limit_time(end_date);
    
    let query = r#"
        SELECT 
            time,
            close,
            volume,
            EMA12,
            EMA26
        FROM 
            `ktln.stock_monthly`
        WHERE 
            stock_code = @stock_code
            AND time BETWEEN @start_date AND @end_date
        ORDER BY 
            time ASC
    "#;

    let params = vec![
        QueryParameter::string("stock_code", stock_code),
        QueryParameter::timestamp("start_date", start_date),
        QueryParameter::timestamp("end_date", &end_date),
    ];

    debug!(
        "Querying monthly stock data for {} from {} to {}",
        stock_code, start_date, end_date
    );

    match client.execute_query(query, Some(params)).await {
        Ok(result) => {
            if result.is_empty() {
                "No data found for the given parameters.".to_string()
            } else {
                result.to_markdown()
            }
        }
        Err(e) => {
            error!("Error querying stock value: {}", e);
            format!("Error querying stock value: {}", e)
        }
    }
}
