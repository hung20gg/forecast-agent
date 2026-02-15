import os
from google.cloud import bigquery
from client import Client
from logger import logger
import pandas as pd
import anyio

async def query_commodities_available(client: Client) -> str:

    query = """
        SELECT DISTINCT indicator_code, indicator_name
        FROM `ktln.commodities_daily`
        ORDER BY indicator_code
    """
    results = await client.aexecute_query(query)
    df = pd.DataFrame([dict(row) for row in results])
    if df.empty:
        return "No commodities data found. The commodities data might not be available in the database."
    
    return df.to_markdown(index=False)


async def query_commodities_value(
    client: Client,
    commodity_name: str,
    start_date: str,
    end_date: str,
    duration: str = 'monthly'
) -> str:
    
    end_date = min(end_date, client.limit_time) if client.limit_time else end_date
    
    query = f"""
        SELECT 
            time,
            value,
            volume,
            EMA12,
            EMA26
        FROM 
            `ktln.commodities_{duration}`
        WHERE 
            indicator_name = @indicator_name
            AND time BETWEEN @start_date AND @end_date
        ORDER BY 
            time ASC
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("indicator_name", "STRING", commodity_name),
            bigquery.ScalarQueryParameter("start_date", "TIMESTAMP", start_date),
            bigquery.ScalarQueryParameter("end_date", "TIMESTAMP", end_date),
        ]
    )
    results = await client.aexecute_query(query, job_config=job_config)
    df = pd.DataFrame([dict(row) for row in results])
    if df.empty:
        return "No data found for the given parameters."
    
    return df.to_markdown(index=False)


def register_tool(mcp, client: Client):

    @mcp.tool()
    async def get_commodities_available() -> str:
        """
        Fetch available commodities from BigQuery to provide filtering options for `get_commodities_value`.
        
        Returns:
            Available commodities as a string or error message
        """
        return await query_commodities_available(client)

    @mcp.tool()
    async def get_commodities_value(commodity_name: str, start_date: str, end_date: str, duration: str = 'monthly') -> str:
        """
        Fetch commodities value from BigQuery for the given commodity name and date range.
        Commodity name examples: 'Gold', 'Silver', 'Oil', etc.
        
        Args:
            commodity_name: Commodity name to query
            start_date: Start date in 'YYYY-MM-DD' format
            end_date: End date in 'YYYY-MM-DD' format
            duration: 'daily' or 'monthly' to specify the data frequency
        Returns:
            Commodities value as a string or error message
        """
        if duration not in ['daily', 'monthly']:
            raise ValueError("Invalid duration specified. Use 'daily' or 'monthly'.")
        return await query_commodities_value(client, commodity_name, start_date, end_date, duration)