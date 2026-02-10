import os
from client import Client
from logger import logger
import pandas as pd
import anyio


async def query_commodities_value_daily(
    client: Client,
    commodity_code: str,
    start_date: str,
    end_date: str
) -> str:
    
    end_date = min(end_date, client.limit_time) if client.limit_time else end_date
    
    query = f"""
        SELECT 
            time,
            value,
            volume,
            EMA20,
            EMA50
        FROM 
            `ktln.commodities_daily`
        WHERE 
            indicator_code = '{commodity_code}'
            AND time BETWEEN '{start_date}' AND '{end_date}'
        ORDER BY 
            time ASC
    """
    results = await client.aexecute_query(query)
    df = pd.DataFrame([dict(row) for row in results])
    if df.empty:
        return "No data found for the given parameters."
    
    return df.to_markdown(index=False)



async def query_commodities_value_monthly(
    client: Client,
    commodity_code: str,
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
            `ktln.commodities_monthly`
        WHERE 
            indicator_code = '{commodity_code}'
            AND time BETWEEN '{start_date}' AND '{end_date}'
        ORDER BY 
            time ASC
    """
    results = await client.aexecute_query(query)
    df = pd.DataFrame([dict(row) for row in results])
    if df.empty:
        return "No data found for the given parameters."
    
    return df.to_markdown(index=False)


def register_tool(mcp, client: Client):
    @mcp.tool()
    
    async def get_commodities_value(commodity_code: str, start_date: str, end_date: str, duration: str) -> str:
        """
        Fetch commodities value from BigQuery for the given commodity code and date range.
        Commodity code examples: 'GOLD', 'SILVER', 'OIL', etc.
        
        Args:
            commodity_code: Commodity code to query
            start_date: Start date in 'YYYY-MM-DD' format
            end_date: End date in 'YYYY-MM-DD' format
            duration: 'daily' or 'monthly' to specify the data frequency
        Returns:
            Commodities value as a string or error message
        """
        if duration == 'daily':
            return await query_commodities_value_daily(client, commodity_code, start_date, end_date)
        elif duration == 'monthly':
            return await query_commodities_value_monthly(client, commodity_code, start_date, end_date)
        else:
            return "Invalid duration specified. Use 'daily' or 'monthly'."