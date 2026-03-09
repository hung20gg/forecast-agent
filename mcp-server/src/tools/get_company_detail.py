import os
from google.cloud import bigquery
from client import Client
from logger import logger
import pandas as pd
import anyio
import re


async def query_company_detail(
    client: Client,
    stock_symbol: str
) -> str:

    sql = """
        SELECT 
            stock_code,
            company_name,
            combine_profile,
            industry,
            exchange
        FROM 
            `ktln.company_info`
        WHERE 
            stock_code = @stock_symbol
        LIMIT 1
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("stock_symbol", "STRING", stock_symbol),
        ]
    )

    logger.info(f"Querying company detail for {stock_symbol}")

    try:
        results = await client.bigquery_client.aexecute_query(sql, job_config=job_config)
        rows = []
        for row in results:
            temp_row = dict(row)
            temp_row['combine_profile'] = temp_row['combine_profile'].replace('\n', '').replace("\xa0", " ").strip()
            rows.append(temp_row)
        df = pd.DataFrame(rows)
        if df.empty:
            return f"No data found for the given stock symbol '{stock_symbol}'."

        df_markdown = df.to_markdown(index=False)

        # limit spaces to at most 3
        df_markdown = re.sub(r" {4,}", "   ", df_markdown)

        # limit dashes to at most 3
        df_markdown = re.sub(r"-{4,}", "---", df_markdown)
        

        return f"[SUCCESS] Company Detail for {stock_symbol}:\n\n{df_markdown}"

    except Exception as e:
        logger.error(f"Error querying company detail: {e}")
        return f"[FAIL] Error querying company detail: {e}"
    

async def query_similar_companies(
    client: Client,
    stock_symbol: str
) -> str:

    sql = """
        SELECT 
            stock_code,
            company_name,
            industry,
            market_cap,
            exchange
        FROM 
            `ktln.company_info`
        WHERE 
            industry = (SELECT industry FROM `ktln.company_info` WHERE stock_code = @stock_symbol)
            AND stock_code != @stock_symbol
        ORDER BY 
            issue_share DESC
        LIMIT 5
    """

    logger.info(f"Querying similar companies for {stock_symbol}")

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("stock_symbol", "STRING", stock_symbol),
        ]
    )

    try:
        results = await client.bigquery_client.aexecute_query(sql, job_config=job_config)
        df = pd.DataFrame([dict(row) for row in results])

        if df.empty:
            return "[FAIL] No similar companies found for the given stock symbol."

        df_markdown = df.to_markdown(index=False)

        return f"[SUCCESS] Similar Companies to {stock_symbol}:\n\n{df_markdown}"

    except Exception as e:
        logger.error(f"Error querying similar companies: {e}")
        return f"[FAIL] Error querying similar companies: {e}"
    

def register_tool(mcp, client: Client):
    @mcp.tool()

    async def get_company_detail(stock_symbol: str) -> str:
        """
        Get detailed information about a company based on its stock symbol.

        Args:
            stock_symbol: The stock symbol of the company (e.g., "AAPL" for Apple Inc.)
        Returns:
            A markdown-formatted string containing the company's details, or an error message if the query fails.
        """

        return await query_company_detail(client, stock_symbol)
    

    @mcp.tool()
    async def get_similar_companies(stock_symbol: str) -> str:
        """
        Get a list of companies in the same industry as the given stock symbol.

        Args:
            stock_symbol: The stock symbol of the company to find similar companies for.
        Returns:
            A markdown-formatted string containing a list of similar companies, or an error message if the query fails.
        """

        return await query_similar_companies(client, stock_symbol)