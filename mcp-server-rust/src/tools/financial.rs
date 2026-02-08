//! Financial statement and ratio tools

use crate::bigquery::{BigQueryClient, QueryParameter};
use chrono::NaiveDate;
use tracing::{debug, error};

/// Find exact financial ratio code based on a query
pub async fn get_exact_financial_ratio_code(client: &BigQueryClient, query: &str) -> String {
    let sql = r#"
        SELECT
            ratio_code,
            ratio_name
        FROM `neusolution.ktln.financial_ratio_dim`
        WHERE SEARCH((ratio_code, ratio_name), @query)
    "#;

    let params = vec![QueryParameter::string("query", query)];

    debug!("Searching for financial ratio code: {}", query);

    match client.execute_query(sql, Some(params)).await {
        Ok(result) => {
            if result.is_empty() {
                "[FAILED] No ratio found for the given parameters.".to_string()
            } else {
                result.to_markdown()
            }
        }
        Err(e) => {
            error!("Error searching financial ratio code: {}", e);
            format!("Error searching financial ratio code: {}", e)
        }
    }
}

/// Query financial ratio data
pub async fn query_financial_ratio(
    client: &BigQueryClient,
    stock_code: &str,
    ratio_code: &str,
    start_date: &str,
    end_date: &str,
    duration: &str,
) -> String {

    // Check if ratio_code exists
    let sql = r#"
        SELECT
            COUNT(1) AS cnt
        FROM `neusolution.ktln.financial_ratio_dim`
        WHERE ratio_code = @ratio_code;
    "#;

    let params = vec![QueryParameter::string("ratio_code", ratio_code)];

    match client.execute_query(sql, Some(params)).await {
        Ok(result) => {
            let cnt: i64 = result.rows.first()
                .and_then(|row| row.first())
                .and_then(|v| v.parse().ok())
                .unwrap_or(0);
            if cnt == 0 {
                let similarity_result = get_exact_financial_ratio_code(client, ratio_code).await;
                if similarity_result.contains("[FAILED]") {
                    return format!("Ratio code '{}' or similar names do not exist. Please change your query and use the tool 'get_exact_financial_ratio_code' to find the correct ratio code.", ratio_code);
                }
                return format!("Ratio code '{}' does not exist. Here are some similar ratio codes or names that available:\n{}", ratio_code, similarity_result); 
            } 
        }
        Err(e) => {
            error!("Error searching financial ratio code: {}", e);
            return format!("Error searching financial ratio code: {}", e);
        }
    }

    let start_dt = match NaiveDate::parse_from_str(start_date, "%Y-%m-%d") {
        Ok(d) => d,
        Err(e) => return format!("Invalid start_date format: {}", e),
    };
    let end_dt = match NaiveDate::parse_from_str(end_date, "%Y-%m-%d") {
        Ok(d) => d,
        Err(e) => return format!("Invalid end_date format: {}", e),
    };

    let start_year = start_dt.year() as i64;
    let end_year = end_dt.year() as i64;
    let start_quarter = ((start_dt.month() - 1) / 3 + 1) as i64;
    let end_quarter = ((end_dt.month() - 1) / 3 + 1) as i64;

    let (sql, params) = match duration {
        "annually" => {
            let sql = r#"
                SELECT
                    year,
                    data
                FROM `ktln.financial_ratio`
                WHERE stock_code = @stock_code
                    AND ratio_code = @ratio_code
                    AND quarter = 0
                    AND year BETWEEN @start_year AND @end_year
                ORDER BY year
            "#;
            let params = vec![
                QueryParameter::string("stock_code", stock_code),
                QueryParameter::string("ratio_code", ratio_code),
                QueryParameter::int64("start_year", start_year),
                QueryParameter::int64("end_year", end_year),
            ];
            (sql, params)
        }
        "quarterly" => {
            let sql = r#"
                SELECT
                    year,
                    quarter,
                    data
                FROM `ktln.financial_ratio`
                WHERE stock_code = @stock_code
                    AND ratio_code = @ratio_code
                    AND quarter <> 0
                    AND (
                        (year > @start_year OR (year = @start_year AND quarter >= @start_quarter))
                        AND
                        (year < @end_year OR (year = @end_year AND quarter <= @end_quarter))
                    )
                ORDER BY year, quarter
            "#;
            let params = vec![
                QueryParameter::string("stock_code", stock_code),
                QueryParameter::string("ratio_code", ratio_code),
                QueryParameter::int64("start_year", start_year),
                QueryParameter::int64("start_quarter", start_quarter),
                QueryParameter::int64("end_year", end_year),
                QueryParameter::int64("end_quarter", end_quarter),
            ];
            (sql, params)
        }
        _ => return "duration must be 'quarterly' or 'annually'".to_string(),
    };

    debug!(
        "Querying {} financial ratio {} for {} from {} to {}",
        duration, ratio_code, stock_code, start_date, end_date
    );

    match client.execute_query(sql, Some(params)).await {
        Ok(result) => {
            if result.is_empty() {
                "No data found for the given parameters.".to_string()
            } else {
                result.to_markdown()
            }
        }
        Err(e) => {
            error!("Error querying financial ratio: {}", e);
            format!("Error querying financial ratio: {}", e)
        }
    }
}

/// Find exact financial statement account based on a query
pub async fn get_exact_financial_statement_account(client: &BigQueryClient, query: &str) -> String {
    let sql = r#"
        SELECT
            category_name,
            category_code,
            (
                IF(category_name = @query, 3, 0) +
                IF(STARTS_WITH(category_name, @query), 2, 0) +
                IF(SEARCH(category_name, @query), 1, 0)
            ) AS score
        FROM `neusolution.ktln.financial_statement_dim`
        ORDER BY score DESC
        LIMIT 10
    "#;

    let params = vec![QueryParameter::string("query", query)];

    debug!("Searching for financial statement account: {}", query);

    match client.execute_query(sql, Some(params)).await {
        Ok(result) => {
            if result.is_empty() {
                "[FAILED] No category found for the given parameters.".to_string()
            } else {
                result.to_markdown()
            }
        }
        Err(e) => {
            error!("Error searching financial statement account: {}", e);
            format!("Error searching financial statement account: {}", e)
        }
    }
}

/// Query financial statement data
pub async fn query_financial_statement(
    client: &BigQueryClient,
    stock_code: &str,
    category_code: &str,
    start_date: &str,
    end_date: &str,
    duration: &str,
) -> String {


    // Check if category_code exists
    let sql = r#"
        SELECT
            COUNT(1) AS cnt
        FROM `neusolution.ktln.financial_statement_dim`
        WHERE category_code = @category_code;
    "#;

    let params = vec![QueryParameter::string("category_code", category_code)];

    match client.execute_query(sql, Some(params)).await {
        Ok(result) => {
            let cnt: i64 = result.rows.first()
                .and_then(|row| row.first())
                .and_then(|v| v.parse().ok())
                .unwrap_or(0);
            if cnt == 0 {
                let similarity_result = get_exact_financial_statement_account(client, category_code).await;
                if similarity_result.contains("[FAILED]") {
                    return format!("Category code '{}' or similar names do not exist. Please change your query and use the tool 'get_exact_financial_statement_account' to find the correct category code.", category_code);
                }
                return format!("Category code '{}' does not exist. Here are some similar ratio codes or names that available:\n{}", category_code, similarity_result); 
            } 
        }
        Err(e) => {
            error!("Error searching financial statement category code: {}", e);
            return format!("Error searching financial statement category code: {}", e);
        }
    }

    let start_dt = match NaiveDate::parse_from_str(start_date, "%Y-%m-%d") {
        Ok(d) => d,
        Err(e) => return format!("Invalid start_date format: {}", e),
    };
    let end_dt = match NaiveDate::parse_from_str(end_date, "%Y-%m-%d") {
        Ok(d) => d,
        Err(e) => return format!("Invalid end_date format: {}", e),
    };

    let start_year = start_dt.year() as i64;
    let end_year = end_dt.year() as i64;
    let start_quarter = ((start_dt.month() - 1) / 3 + 1) as i64;
    let end_quarter = ((end_dt.month() - 1) / 3 + 1) as i64;

    let (sql, params) = match duration {
        "annually" => {
            let sql = r#"
                SELECT
                    year,
                    data
                FROM `ktln.financial_statement`
                WHERE stock_code = @stock_code
                    AND category_code = @category_code
                    AND quarter = 0
                    AND year BETWEEN @start_year AND @end_year
                ORDER BY year
            "#;
            let params = vec![
                QueryParameter::string("stock_code", stock_code),
                QueryParameter::string("category_code", category_code),
                QueryParameter::int64("start_year", start_year),
                QueryParameter::int64("end_year", end_year),
            ];
            (sql, params)
        }
        "quarterly" => {
            let sql = r#"
                SELECT
                    year,
                    quarter,
                    data
                FROM `ktln.financial_statement`
                WHERE stock_code = @stock_code
                    AND category_code = @category_code
                    AND quarter <> 0
                    AND (
                        (year > @start_year OR (year = @start_year AND quarter >= @start_quarter))
                        AND
                        (year < @end_year OR (year = @end_year AND quarter <= @end_quarter))
                    )
                ORDER BY year, quarter
            "#;
            let params = vec![
                QueryParameter::string("stock_code", stock_code),
                QueryParameter::string("category_code", category_code),
                QueryParameter::int64("start_year", start_year),
                QueryParameter::int64("start_quarter", start_quarter),
                QueryParameter::int64("end_year", end_year),
                QueryParameter::int64("end_quarter", end_quarter),
            ];
            (sql, params)
        }
        _ => return "duration must be 'quarterly' or 'annually'".to_string(),
    };

    debug!(
        "Querying {} financial statement {} for {} from {} to {}",
        duration, category_code, stock_code, start_date, end_date
    );

    match client.execute_query(sql, Some(params)).await {
        Ok(result) => {
            if result.is_empty() {
                "No data found for the given parameters.".to_string()
            } else {
                result.to_markdown()
            }
        }
        Err(e) => {
            error!("Error querying financial statement: {}", e);
            format!("Error querying financial statement: {}", e)
        }
    }
}

// Use chrono's Datelike trait for year() and month() methods
use chrono::Datelike;
