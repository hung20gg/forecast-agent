import os
from client import BigQueryClient
from google.cloud import bigquery
from logger import logger
import pandas as pd
import anyio
from datetime import datetime 


async def _get_exact_financial_ratio_code(
    client: BigQueryClient,
    query: str,
) -> str:
        
    sql = f"""
        SELECT
            ratio_code,
            ratio_name
        FROM `neusolution.ktln.financial_ratio_dim`
        WHERE SEARCH((ratio_code, ratio_name), @query);
    """

    job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("query", "STRING", query),
            ]
        )
        
    results = await client.aexecute_query(sql, job_config=job_config)
    df = pd.DataFrame([dict(row) for row in results])
    if df.empty:
        return "No data found for the given parameters."
    
    return df.to_markdown(index=False)



async def _query_financial_ratio(
    client: BigQueryClient,
    stock_code: str,
    ratio_code: str,
    start_date: str,
    end_date: str,
    duration: str  # "quarter" or "year"
):
    
    # Check ratio_code exists
    sql_check = """

        SELECT
            COUNT(1) AS cnt
        FROM `neusolution.ktln.financial_ratio_dim`
        WHERE ratio_code = @ratio_code;
        
    """
    job_config_check = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("ratio_code", "STRING", ratio_code),
        ]
    )
    results_check = await client.aexecute_query(sql_check, job_config=job_config_check)
    row_check = list(results_check)[0]
    if row_check['cnt'] == 0:
        return f"Ratio code '{ratio_code}' does not exist. Please use the tool 'get_exact_financial_ratio_code' to find the correct ratio code."
    
    
    start_dt = datetime.fromisoformat(start_date)
    end_dt = datetime.fromisoformat(end_date)

    start_year = start_dt.year
    end_year = end_dt.year
    start_quarter = (start_dt.month - 1) // 3 + 1
    end_quarter = (end_dt.month - 1) // 3 + 1

    if duration == "annually":
        sql = """
        SELECT
          year,
          data
        FROM `ktln.financial_ratio`
        WHERE stock_code = @stock_code
          AND ratio_code = @ratio_code
          AND quarter = 0
          AND year BETWEEN @start_year AND @end_year
        ORDER BY year
        """
        params = [
            bigquery.ScalarQueryParameter("stock_code", "STRING", stock_code),
            bigquery.ScalarQueryParameter("ratio_code", "STRING", ratio_code),
            bigquery.ScalarQueryParameter("start_year", "INT64", start_year),
            bigquery.ScalarQueryParameter("end_year", "INT64", end_year),
        ]

    elif duration == "quarterly":
        sql = """
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
        """
        params = [
            bigquery.ScalarQueryParameter("stock_code", "STRING", stock_code),
            bigquery.ScalarQueryParameter("ratio_code", "STRING", ratio_code),
            bigquery.ScalarQueryParameter("start_year", "INT64", start_year),
            bigquery.ScalarQueryParameter("start_quarter", "INT64", start_quarter),
            bigquery.ScalarQueryParameter("end_year", "INT64", end_year),
            bigquery.ScalarQueryParameter("end_quarter", "INT64", end_quarter),
        ]

    else:
        raise ValueError("duration must be 'quarterly' or 'annually'")

    job_config = bigquery.QueryJobConfig(query_parameters=params)

    results = await client.aexecute_query(sql, job_config=job_config)
    df = pd.DataFrame([dict(row) for row in results])
    if df.empty:
        return "No data found for the given parameters."
    
    return df.to_markdown(index=False)


async def _get_exact_financial_statement_account(
    client: BigQueryClient,
    query: str,
) -> str:
        
    sql = f"""
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
        LIMIT 10;
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("query", "STRING", query),
        ]
    )
    results = await client.aexecute_query(sql, job_config=job_config)
    df = pd.DataFrame([dict(row) for row in results])
    if df.empty:
        return "No data found for the given parameters."
    
    return df.to_markdown(index=False)


async def _query_financial_statement(
    client: BigQueryClient,
    stock_code: str,
    category_code: str,
    start_date: str,
    end_date: str,
    duration: str  # "quarter" or "year"
):
    
    # Check category_code exists
    sql_check = """
        SELECT
            COUNT(1) AS cnt
        FROM `neusolution.ktln.financial_statement_dim`
        WHERE category_code = @category_code;
    """
    job_config_check = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("category_code", "STRING", category_code),
        ]
    )
    results_check = await client.aexecute_query(sql_check, job_config=job_config_check)
    row_check = list(results_check)[0]
    if row_check['cnt'] == 0:
        return f"Category code '{category_code}' does not exist. Please use the tool 'get_exact_financial_statement_account' to find the correct category code."
    
    start_dt = datetime.fromisoformat(start_date)
    end_dt = datetime.fromisoformat(end_date)

    start_year = start_dt.year
    end_year = end_dt.year
    start_quarter = (start_dt.month - 1) // 3 + 1
    end_quarter = (end_dt.month - 1) // 3 + 1

    if duration == "annually":
        sql = """
        SELECT
          year,
          data
        FROM `ktln.financial_statement`
        WHERE stock_code = @stock_code
          AND category_code = @category_code
            AND quarter = 0
          AND year BETWEEN @start_year AND @end_year
        ORDER BY year
        """
        params = [
            bigquery.ScalarQueryParameter("stock_code", "STRING", stock_code),
            bigquery.ScalarQueryParameter("category_code", "STRING", category_code),
            bigquery.ScalarQueryParameter("start_year", "INT64", start_year),
            bigquery.ScalarQueryParameter("end_year", "INT64", end_year),
        ]

    elif duration == "quarterly":
        sql = """
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
        """
        params = [
            bigquery.ScalarQueryParameter("stock_code", "STRING", stock_code),
            bigquery.ScalarQueryParameter("category_code", "STRING", category_code),
            bigquery.ScalarQueryParameter("start_year", "INT64", start_year),
            bigquery.ScalarQueryParameter("start_quarter", "INT64", start_quarter),
            bigquery.ScalarQueryParameter("end_year", "INT64", end_year),
            bigquery.ScalarQueryParameter("end_quarter", "INT64", end_quarter),
        ]

    else:
        raise ValueError("duration must be 'quarterly' or 'annually'")

    job_config = bigquery.QueryJobConfig(query_parameters=params)
        
    results = await client.aexecute_query(sql, job_config=job_config)
    df = pd.DataFrame([dict(row) for row in results])
    if df.empty:
        return "No data found for the given parameters."
    
    return df.to_markdown(index=False)



def register_tool(mcp, client: BigQueryClient):
    @mcp.tool()
    
    async def get_exact_financial_ratio_code(query: str) -> str:
        """
        Since financial ratio codes and names can be numerous and complex, this tool helps to find the exact financial ratio code based on a user query.
        
        Args:
            query: User query to find the exact financial ratio code. Should be in English.
        Returns:
            Financial ratio code as a string or error message
        """
        return await _get_exact_financial_ratio_code(client, query)
    

    @mcp.tool()
    async def query_financial_ratio(
        stock_code: str,
        ratio_code: str,
        start_date: str,
        end_date: str,
        duration: str
    ):
        """
        Fetch financial ratio data from BigQuery for the given stock code, ratio code, and date range.
        
        Args:
            stock_code: Stock code to query
            ratio_code: Financial ratio code to query
            start_date: Start date in 'YYYY-MM-DD' format
            end_date: End date in 'YYYY-MM-DD' format
            duration: 'quarterly' or 'annually' to specify the data frequency
        Returns:
            Financial ratio data as a string or error message
        """
        return await _query_financial_ratio(client, stock_code, ratio_code, start_date, end_date, duration)
    

    @mcp.tool()
    async def get_exact_financial_statement_account(query: str) -> str:
        """
        Since financial statement accounts can be numerous and complex, this tool helps to find the exact account based on a user query.
        
        Args:
            query: User query to find the exact financial statement account. Should be in English.
        Returns:
            Financial statement account as a string or error message
        """
        return await _get_exact_financial_statement_account(client, query)
    

    @mcp.tool()
    async def query_financial_statement(
        stock_code: str,
        category_code: str,
        start_date: str,
        end_date: str,
        duration: str
    ):
        """
        Fetch financial statement data from BigQuery for the given stock code, category code, and date range.
        
        Args:
            stock_code: Stock code to query
            category_code: Financial statement category code to query
            start_date: Start date in 'YYYY-MM-DD' format
            end_date: End date in 'YYYY-MM-DD' format
            duration: 'quarterly' or 'annually' to specify the data frequency
        Returns:
            Financial statement data as a string or error message
        """
        return await _query_financial_statement(client, stock_code, category_code, start_date, end_date, duration)