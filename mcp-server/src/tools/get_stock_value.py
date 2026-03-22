import os
from google.cloud import bigquery
from client import Client
from logger import logger
import pandas as pd
import anyio


async def query_stock_value(
    client: Client,
    stock_symbol: str,
    start_date: str,
    end_date: str,
    duration: str = 'daily'
) -> str:

    end_date = min(end_date, client.limit_time) if client.limit_time else end_date

    if start_date > client.limit_time:
        logger.error(f"Start date {start_date} is after the limit time {client.limit_time}.")
        raise ValueError("Invalid date range: start date is after the limit time.")
    
    if end_date < start_date:
        logger.error(f"End date {end_date} is before start date {start_date}.")
        raise ValueError("Invalid date range: end date is before start date.")
    
    logger.info(f"Querying stock value for {stock_symbol} from {start_date} to {end_date} with duration {duration}")

    if duration == 'daily':
        sql = f"""
            SELECT 
                time,
                close * 1000 AS close,
                volume,
                EMA20 * 1000 AS EMA20,
                EMA50 * 1000 AS EMA50,
                EMA200 * 1000 AS EMA200
            FROM 
                `ktln.stock_daily`
            WHERE 
                stock_code = @stock_symbol
                AND time BETWEEN @start_date AND @end_date
            ORDER BY 
                time ASC
        """
    else:
        sql = f"""
            SELECT 
                time,
                AVG(close) * 1000 AS close,
                SUM(volume) AS volume,
                AVG(EMA12) * 1000 AS EMA12,
                AVG(EMA26) * 1000 AS EMA26
            FROM 
                `ktln.stock_monthly`
            WHERE 
                stock_code = @stock_symbol
                AND time BETWEEN @start_date AND @end_date
            GROUP BY 
                time
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
        results = await client.bigquery_client.aexecute_query(sql, job_config=job_config)
        df = pd.DataFrame([dict(row) for row in results])

        if df.empty:
            return "[FAILED] No data found for the given parameters."

        return f"[SUCCESS] Stock Symbol: {stock_symbol}, Duration: {duration}\n\n{df.to_markdown(index=False)}"

    except Exception as e:
        logger.error(f"Error querying stock value: {e}")
        return f"[FAILED] Error querying stock {stock_symbol} value: {e}"


def register_tool(mcp, client: Client):
    @mcp.tool()
    
    async def get_stock_value(stock_code: str, start_date: str, end_date: str, duration: str = 'daily') -> str:
        """
        Fetch stock value for the given stock symbol and date range. The unit is in VND
        
        Args:
            stock_code: Stock to query. e.g., 'VIC', 'VHM'
            start_date: Start date in 'YYYY-MM-DD' format
            end_date: End date in 'YYYY-MM-DD' format
            duration: 'daily' or 'monthly' to specify the frequency
        Returns:
            Stock value
        """
        if duration not in ['daily', 'monthly']:
            logger.error(f"Invalid duration specified for get_stock_value: {duration}")
            raise ValueError(f"Invalid duration {duration} for get_stock_value. Use 'daily' or 'monthly'.")
        return await query_stock_value(client, stock_code, start_date, end_date, duration)
