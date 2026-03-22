import os
import asyncio
from typing import Optional
from client import Client
from google.cloud import bigquery
from logger import logger
import pandas as pd
import anyio
import json
from env_config import get_env
import datetime

from utils import normalize_search_query


def truncate_text(text: str, max_length: int = 750) -> str:
    """Truncate text to max_length characters, adding ... if truncated."""
    if not text:
        return ""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."


def json_news_to_markdown(data: dict) -> str:
    """Convert JSON news data to a Markdown table format."""
    
    text = ''
    if 'title' in data:
        text += f"### {data['title']}\n\n"
    if 'source' in data:
        text += f"**Source:** {data['source']}\n\n"
    if 'pub_date' in data:
        if isinstance(data['pub_date'], str):
            pub_date = data['pub_date']
        elif isinstance(data['pub_date'], datetime.datetime):
            pub_date = data['pub_date'].strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(data['pub_date'], int):
            pub_date = datetime.datetime.fromtimestamp(data['pub_date']).strftime('%Y-%m-%d %H:%M:%S')

        text += f"**Published:** {pub_date}\n\n"
    if 'text' in data:
        text += f"{data['text']}\n\n"
    if 'url' in data:
        text += f"[Read more]({data['url']})\n\n"
    
    return text.strip()


async def query_news_from_vectordb(
    client: Client,
    user_query: str,
    start_date: str,
    end_date: str,
    limit: int = 5
) -> Optional[str]:
    """Query news using vector similarity search."""
    logger.info(f"Querying news from vectordb from {start_date} to {end_date} with limit {limit}")
    try:
        # Get embedding for the query

        end_date = min(end_date, client.limit_time) if client.limit_time else end_date

        if end_date < start_date:
            logger.warning(f"End date {end_date} is before start date {start_date}.")
            return "Invalid date range: end date is before start date."
        
        if start_date > client.limit_time:
            logger.warning(f"Start date {start_date} is after the limit time {client.limit_time}.")
            return "Invalid date range: start date is after the limit time." 
        
        # Query Qdrant
        collection_name = get_env('COLLECTION_NAME', 'news_embedding')
        
        # Convert dates to timestamp for filtering
        
        start_ts = int(datetime.datetime.strptime(start_date, '%Y-%m-%d').timestamp())
        end_ts = int(datetime.datetime.strptime(end_date, '%Y-%m-%d').timestamp())
        results = client.qdrant_client.query(
            collection_name=collection_name,
            query=user_query,
            start_date=start_ts,
            end_date=end_ts,
            limit=limit
        )
        
        if not results:
            return json.dumps([], ensure_ascii=False)
        
        # Extract unique URLs with their scores from results
        url_scores = {}
        for r in results:
            if 'url' in r['payload']:
                url = r['payload']['url']
                if url not in url_scores or r['score'] > url_scores[url]:
                    url_scores[url] = r['score']
        
        # Fetch full articles for each URL
        top_url_scores = list(url_scores.items())[:10]
        tasks = [get_new_from_url(client, url) for url, _ in top_url_scores]
        results = await asyncio.gather(*tasks)

        articles = []
        for (url, score), article_json in zip(top_url_scores, results):
            try:
                article_data = json.loads(article_json)
                if article_data and len(article_data) > 0:
                    article = article_data[0]
                    # Add similarity score
                    article['score'] = score
                    # Truncate text field
                    if 'text' in article:
                        article['text'] = truncate_text(article['text'], 750)
                    articles.append(article)
            except Exception as e:
                logger.error(f"Error parsing article from URL {url}: {e}")
                continue
        
        return '\n\n'.join([json_news_to_markdown(article) for article in articles])
        
    except Exception as e:
        logger.error(f"Error querying from vectordb: {e}")
        return None


async def get_new_from_url(client: Client, url: str) -> str:
    
    query = f"""
        SELECT
            url,
            title,
            source,
            pub_date,
            text
        FROM `ktln.news`
        WHERE url = @url
        LIMIT 1
    """
    logger.info(f"Querying news by URL: {url}")
    try:
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("url", "STRING", url),
            ]
        )
        
        results = await client.aexecute_query(query, job_config=job_config)
        if not results:
            return "No news found for the given URL."
        
        return json.dumps([dict(row) for row in results], default=str, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error querying news by URL: {e}")
        return f"Error querying news by URL: {e}"


async def query_news(
    client: Client,
    user_query: str,
    start_date: str,
    end_date: str,
    limit: int = 5,
    channel: Optional[str] = None
) -> str:

    user_query = normalize_search_query(user_query)
    
    end_date = min(end_date, client.limit_time) if client.limit_time else end_date

    if start_date > client.limit_time:
        logger.error(f"Start date {start_date} is after the limit time {client.limit_time}.")
        raise ValueError("Invalid date range: start date is after the limit time.")
    
    if end_date < start_date:
        logger.error(f"End date {end_date} is before start date {start_date}.")
        raise ValueError("Invalid date range: end date is before start date.")

    logger.info(f"Querying news from {start_date} to {end_date} with limit {limit}")
          
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
        LIMIT @limit
    """
    else:
    
        query = f"""
                
            SELECT
                url,
                title,
                source,
                pub_date,
                text,
                (
                    IF(SEARCH(title, @q), 2, 0) +
                    IF(SEARCH(text, @q), 1, 0)
                ) AS score
            FROM `ktln.news`
            WHERE SEARCH((title, text), @q)
            AND pub_date BETWEEN @start_date AND @end_date
            ORDER BY score DESC, pub_date DESC
            LIMIT @limit
        """
    try:
        query_params = [
            bigquery.ScalarQueryParameter("q", "STRING", user_query),
            bigquery.ScalarQueryParameter("start_date", "STRING", start_date),
            bigquery.ScalarQueryParameter("end_date", "STRING", end_date),
            bigquery.ScalarQueryParameter("limit", "INT64", limit if limit is not None else 5),
        ]
        if channel:
            query_params.append(bigquery.ScalarQueryParameter("channel", "STRING", channel))
            
        job_config = bigquery.QueryJobConfig(query_parameters=query_params)
        
        results = client.execute_query(query, job_config=job_config)
        if not results:
            return "No data found for the given parameters."
        
        # Truncate text field to 750 characters
        formatted_results = []
        for row in results:
            row_dict = dict(row)
            if 'text' in row_dict:
                row_dict['text'] = truncate_text(row_dict['text'], 750)
            formatted_results.append(row_dict)
        
        return '\n\n'.join([json_news_to_markdown(article) for article in formatted_results])
    except Exception as e:
        logger.error(f"Error querying news: {e}")
        return f"Error querying news: {e}"


def register_tool(mcp, client: Client):
    # Initialize Qdrant client

    @mcp.tool()
    async def query_relevant_news(query: str, start_date: str, end_date: str, limit: int = 5) -> str:
        """
        Fetch relevant news articles based on query, date range, and optional channel filter.
        Results are truncated to 750 characters per article.
        
        Args:
            query: Search query string
            start_date: Start date in 'YYYY-MM-DD' format
            end_date: End date in 'YYYY-MM-DD' format
            limit: Maximum number of articles to return.
        Returns:
            JSON array of truncated news articles
        """
        channel = None
        # Try vector search first if available
        if client.qdrant_client.test_connection():
            result = await query_news_from_vectordb(client, query, start_date, end_date, limit)
            if result is not None:
                return result
            # If vector search fails, fall back to BigQuery
            logger.warning("Vector search failed, falling back to BigQuery")
        
        # Fallback to BigQuery full-text search
        return await query_news(client, query, start_date, end_date, channel, limit)
    
    @mcp.tool()
    async def read_full_article(url: str) -> str:
        """
        Fetch the complete content of a news article by its URL.
        
        Args:
            url: The URL of the article to fetch
        Returns:
            Full article content as JSON
        """
        return await get_new_from_url(client, url)