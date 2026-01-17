import os
from typing import Optional
from client import BigQueryClient
from google.cloud import bigquery
from logger import logger
import pandas as pd
import anyio
import json

async def query_news(
    client: BigQueryClient,
    user_query: str,
    start_date: str,
    end_date: str,
    channel: Optional[str] = None
) -> str:
    
    end_date = min(end_date, client.limit_time) if client.limit_time else end_date
    
    if channel:
        query = f"""
            
        SELECT
            url,
            title,
            source,
            pub_date,
            (
                IF(SEARCH(title, @q), 2, 0) +
                IF(SEARCH(text, @q), 1, 0)
            ) AS score
        FROM `ktln.news`
        WHERE SEARCH((title, text), @q)
        AND pub_date BETWEEN @start_date AND @end_date
        AND channel_name = @channel
        ORDER BY score DESC, pub_date DESC
        LIMIT 10
    """
    else:
    
        query = f"""
                
            SELECT
                url,
                title,
                source,
                pub_date,
                (
                    IF(SEARCH(title, @q), 2, 0) +
                    IF(SEARCH(text, @q), 1, 0)
                ) AS score
            FROM `ktln.news`
            WHERE SEARCH((title, text), @q)
            AND pub_date BETWEEN @start_date AND @end_date
            ORDER BY score DESC, pub_date DESC
            LIMIT 10
        """
    try:
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("q", "STRING", user_query),
                bigquery.ScalarQueryParameter("start_date", "STRING", start_date),
                bigquery.ScalarQueryParameter("end_date", "STRING", end_date),
                # bigquery.ScalarQueryParameter("channel", "STRING", channel) if channel else None,
            ]
        )
        
        results = client.execute_query(query, job_config=job_config)
        if not results:
            return "No data found for the given parameters."
        
        return json.dumps([dict(row) for row in results], default=str, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error querying news: {e}")
        return f"Error querying news: {e}"


def register_tool(mcp, client: BigQueryClient):
    @mcp.tool()
    
    async def query_relevant_news(query: str, start_date: str, end_date: str, channel: Optional[str] = None) -> str:
        """
        Fetch stock value from BigQuery for the given stock symbol and date range.
        
        Args:
            stock_symbol: Stock symbol to query
            start_date: Start date in 'YYYY-MM-DD' format
            end_date: End date in 'YYYY-MM-DD' format
            duration: 'daily' or 'monthly' to specify the data frequency
        Returns:
            Stock value as a string or error message
        """
        return await query_news(client, query, start_date, end_date, channel)