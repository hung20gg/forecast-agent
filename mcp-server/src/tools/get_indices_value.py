import os
from google.cloud import bigquery
from client import Client
from logger import logger
import pandas as pd
import anyio


async def query_indices_available(client: Client) -> str:
    
    query = """
        SELECT DISTINCT index_name
        FROM `ktln.indices_daily`
        ORDER BY index_name
    """
    logger.info(f"Querying available indices")
    results = await client.aexecute_query(query)
    df = pd.DataFrame([dict(row) for row in results])
    if df.empty:
        return "[FAILED] No indices data found. The indices data might not be available in the database."
    
    return f"[SUCCESS] Available indices:\n\n{df.to_markdown(index=False)}"


async def query_indices_value(
    client: Client,
    index_name: str,
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

    logger.info(f"Querying indices value for {index_name} from {start_date} to {end_date} with duration {duration}")
      
    if duration == 'daily':
        query = f"""
            SELECT 
                index_name,
                time,
                close,
                volume,
                EMA20,
                EMA50
            FROM 
                `ktln.indices_daily`
            WHERE 
                index_name = @index_name
                AND time BETWEEN @start_date AND @end_date
            ORDER BY 
                time ASC
        """
    else:
        query = f"""
            SELECT 
                index_name,
                time,
                close,
                volume,
                EMA12,
                EMA26
            FROM 
                `ktln.indices_monthly`
            WHERE 
                index_name = @index_name
                AND time BETWEEN @start_date AND @end_date
            ORDER BY 
                time ASC
        """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("index_name", "STRING", index_name),
            bigquery.ScalarQueryParameter("start_date", "TIMESTAMP", start_date),
            bigquery.ScalarQueryParameter("end_date", "TIMESTAMP", end_date),
        ]
    )
    try:
        results = await client.bigquery_client.aexecute_query(query, job_config=job_config)
        df = pd.DataFrame([dict(row) for row in results])
        if df.empty:
            return "[FAILED] No data found for the given parameters."
        
        return f"[SUCCESS] Index: {index_name}\n\n{df.to_markdown(index=False)}"
    except Exception as e:
        logger.error(f"Error querying stock value: {e}")
        return f"[FAILED] Error querying stock value: {e}"


def register_tool(mcp, client: Client):
    
    @mcp.tool()
    async def get_indices_available() -> str:
        """
        Fetch available stock indices from BigQuery.
        
        Returns:
            Available indices as a string or error message
        """
        return await query_indices_available(client)
    
    @mcp.tool()
    async def get_indices_value(index_name: str, start_date: str, end_date: str, duration: str = 'daily') -> str:
        """
        Fetch indices value for the given index name and date range.
        Index is the name for stock indices like 'KOSPI', 'NASDAQ', 'VNINDEX', etc.
        
        Args:
            index_name: Index name to query
            start_date: Start date in 'YYYY-MM-DD' format
            end_date: End date in 'YYYY-MM-DD' format
            duration: 'daily' or 'monthly' to specify the data frequency
        Returns:
            Indices value
        """
        if duration not in ['daily', 'monthly']:
            logger.error(f"Invalid duration specified: {duration}")
            raise ValueError(f"Invalid duration {duration} for get_indices_value. Use 'daily' or 'monthly'.")
        
        else:
            return await query_indices_value(client, index_name, start_date, end_date, duration)
