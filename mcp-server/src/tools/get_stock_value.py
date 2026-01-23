import os
from google.cloud import bigquery
from client import BigQueryClient
from logger import logger
import pandas as pd
import anyio


async def query_stock_value_daily(
    client: BigQueryClient,
    stock_symbol: str,
    start_date: str,
    end_date: str
) -> str:

    end_date = min(end_date, client.limit_time) if client.limit_time else end_date

    sql = """
        SELECT 
            time,
            close,
            volume,
            EMA20,
            EMA50
        FROM 
            `ktln.stock_daily`
        WHERE 
            stock_code = @stock_symbol
            AND time BETWEEN @start_date AND @end_date
        ORDER BY 
            time ASC
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("stock_symbol", "STRING", stock_symbol),
            bigquery.ScalarQueryParameter("start_date", "TIMESTAMP", start_date),
            bigquery.ScalarQueryParameter("end_date", "TIMESTAMP", end_date),
        ]
    )

    try:
        results = await client.aexecute_query(sql, job_config=job_config)
        df = pd.DataFrame([dict(row) for row in results])

        if df.empty:
            return "No data found for the given parameters."

        return df.to_markdown(index=False)

    except Exception as e:
        logger.error(f"Error querying stock value: {e}")
        return f"Error querying stock value: {e}"



async def query_stock_value_monthly(
    client: BigQueryClient,
    stock_symbol: str,
    start_date: str,
    end_date: str
) -> str:
    
    end_date = min(end_date, client.limit_time) if client.limit_time else end_date
    
    query = f"""
        SELECT 
            time,
            close,
            volume,
            EMA12,
            EMA26
        FROM 
            `ktln.stock_monthly`
        WHERE 
            stock_code = @stock_symbol
            AND time BETWEEN @start_date AND @end_date
        ORDER BY 
            time ASC
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("stock_symbol", "STRING", stock_symbol),
            bigquery.ScalarQueryParameter("start_date", "TIMESTAMP", start_date),
            bigquery.ScalarQueryParameter("end_date", "TIMESTAMP", end_date),
        ]
    )


    try:
        results = await client.aexecute_query(query)
        df = pd.DataFrame([dict(row) for row in results])
        if df.empty:
            return "No data found for the given parameters."
        
        return df.to_markdown(index=False)
    except Exception as e:
        logger.error(f"Error querying stock value: {e}")
        return f"Error querying stock value: {e}"


def register_tool(mcp, client: BigQueryClient):
    @mcp.tool()
    
    async def get_stock_value(stock_code: str, start_date: str, end_date: str, duration: str) -> str:
        """
        Fetch stock value from BigQuery for the given stock symbol and date range.
        
        Args:
            stock_code: Stock symbol to query
            start_date: Start date in 'YYYY-MM-DD' format
            end_date: End date in 'YYYY-MM-DD' format
            duration: 'daily' or 'monthly' to specify the data frequency
        Returns:
            Stock value as a string or error message
        """
        if duration == 'daily':
            return await query_stock_value_daily(client, stock_code, start_date, end_date)
        elif duration == 'monthly':
            return await query_stock_value_monthly(client, stock_code, start_date, end_date)
        else:
            return "Invalid duration specified. Use 'daily' or 'monthly'."