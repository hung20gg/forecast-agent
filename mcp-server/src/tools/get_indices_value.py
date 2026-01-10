import os
from client import BigQueryClient
from logger import logger
import pandas as pd
import anyio


async def query_indices_value_daily(
    client: BigQueryClient,
    index_name: str,
    start_date: str,
    end_date: str
) -> str:
    
    end_date = min(end_date, client.limit_time) if client.limit_time else end_date
    
    query = f"""
        SELECT 
            time,
            close,
            volume,
            EMA20,
            EMA50
        FROM 
            `ktln.indices_daily`
        WHERE 
            index_name = '{index_name}'
            AND time BETWEEN '{start_date}' AND '{end_date}'
        ORDER BY 
            time ASC
    """
    try:
        results = await client.aexecute_query(query)
        df = pd.DataFrame([dict(row) for row in results])
        if df.empty:
            return "No data found for the given parameters."
        
        return df.to_markdown(index=False)
    except Exception as e:
        logger.error(f"Error querying stock value: {e}")
        return f"Error querying stock value: {e}"


async def query_indices_value_monthly(
    client: BigQueryClient,
    index_name: str,
    start_date: str,
    end_date: str
) -> str:
    
    end_date = min(end_date, client.limit_time) if client.limit_time else end_date
    
    query = f"""
        SELECT 
            time,
            close,
            volume,
            EMA20,
            EMA50
        FROM 
            `ktln.indices_monthly`
        WHERE 
            index_name = '{index_name}'
            AND time BETWEEN '{start_date}' AND '{end_date}'
        ORDER BY 
            time ASC
    """
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
    
    async def get_indices_value(index_name: str, start_date: str, end_date: str, duration: str) -> str:
        """
        Fetch indices value from BigQuery for the given index name and date range.
        
        Args:
            index_name: Index name to query
            start_date: Start date in 'YYYY-MM-DD' format
            end_date: End date in 'YYYY-MM-DD' format
            duration: 'daily' or 'monthly' to specify the data frequency
        Returns:
            Indices value as a string or error message
        """
        if duration == 'daily':
            return await query_indices_value_daily(client, index_name, start_date, end_date)
        elif duration == 'monthly':
            return await query_indices_value_monthly(client, index_name, start_date, end_date)
        else:
            return "Invalid duration specified. Use 'daily' or 'monthly'."