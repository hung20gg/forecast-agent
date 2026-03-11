from google.cloud import bigquery
from qdrant_client import QdrantClient, models
from google.oauth2 import service_account
from google.auth.transport.requests import AuthorizedSession
from requests.adapters import HTTPAdapter
import requests
from logger import logger
import os
from typing import List, Optional
import asyncio
from env_config import get_env

def get_embedding(query: str) -> Optional[list[float]]:
    """Get embedding vector for a text query."""
    embedding_url = get_env('EMBEDDING_URL', 'http://127.0.0.1:8080/embed')
    if not embedding_url:
        raise ValueError("EMBEDDING_URL is not set in environment variables.")
    
    try:
        response = requests.post(
            embedding_url,
            json={"inputs": query, "truncate": True},
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        response.raise_for_status()
        try:
            embedding = response.json()
        except ValueError:
            logger.error(f"Invalid JSON from embedding service. Status: {response.status_code}, Response: {response.text}")
            return None

        if isinstance(embedding, list) and len(embedding) > 0 and isinstance(embedding[0], list):
            embedding = embedding[0]
        return embedding
    except Exception as e:
        logger.error(f"Error getting embedding: {e}")
        return None

class Qdrant:
    """Client for authenticating and interacting with Qdrant vector database."""
    
    def __init__(self, url: Optional[str] = None, api_key: Optional[str] = None):
        """
        Initialize Qdrant client with authentication.
        
        Args:
            url: Qdrant host URL
            api_key: API key for Qdrant authentication
        """
        logger.info(f"Initializing Qdrant client with URL: {url} and API Key: {'***' if api_key else 'None'}")
        self.url = url or get_env('QDRANT_URL', 'http://localhost:6333')
        self.api_key = api_key or get_env('QDRANT_API_KEY')
        
        self.client = self._initialize_client()
        logger.info(f"Qdrant client initialized with host: {self.url}")    
    
    def _initialize_client(self) -> QdrantClient:
        """Initialize and return the Qdrant client."""
        if self.api_key:
            return QdrantClient(url=self.url, api_key=self.api_key)
        return QdrantClient(url=self.url)

    def count_vectors(self, collection_name: str) -> int:
        """Calculate the number of existing vectors in a collection."""
        try:
            response = self.client.count(collection_name=collection_name)
            return response.count
        except Exception as e:
            logger.error(f"Error counting vectors in {collection_name}: {e}")
            return 0
        
    def test_connection(self) -> bool:
        """Test the Qdrant connection."""
        try:
            self.client.get_collections()
            return True
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
    
    def query(self, collection_name: str, query: str, start_date: Optional[int] = None, end_date: Optional[int] = None, limit: int = 5):
        """Execute a query against the Qdrant collection."""
        query_filter = None
        vector = get_embedding(query)
        if vector is None:
            raise RuntimeError(f"Failed to get embedding for query — embedding service may be unavailable.")
        
        if start_date or end_date:
            filter_conditions = []
            if start_date:
                filter_conditions.append(
                    models.FieldCondition(
                        key="pub_date",
                        range=models.Range(gte=start_date)
                    )
                )
            if end_date:
                filter_conditions.append(
                    models.FieldCondition(
                        key="pub_date",
                        range=models.Range(lte=end_date)
                    )
                )
            query_filter = models.Filter(must=filter_conditions)
        
        results = self.client.search(
            collection_name=collection_name,
            query_vector=vector,
            query_filter=query_filter,
            limit=limit,
        )
        
        # Convert results to JSON format
        formatted_results = []
        for result in results:
            formatted_results.append({
                "score": result.score,
                "payload": result.payload
            })
        
        return formatted_results
        

class BigQueryClient:
    """Client for authenticating and interacting with Google BigQuery."""
    
    def __init__(self, credentials_path:  Optional[str], project_id: Optional[str], limit_time: Optional[str] = None):
        """
        Initialize BigQuery client with authentication.
        
        Args:
            credentials_path: Path to service account JSON credentials file
            project_id: Google Cloud project ID
        """
        self.credentials_path = credentials_path or get_env('GOOGLE_APPLICATION_CREDENTIALS')
        self.project_id = project_id or get_env('GCP_PROJECT_ID')
        self.limit_time = limit_time or get_env('LIMIT_TIME')
        
        if self.credentials_path:
            credentials = service_account.Credentials.from_service_account_file(
                self.credentials_path,
                scopes=["https://www.googleapis.com/auth/bigquery",
                        "https://www.googleapis.com/auth/cloud-platform"],
            )
            session = AuthorizedSession(credentials)
            adapter = HTTPAdapter(pool_connections=25, pool_maxsize=25)
            session.mount("https://", adapter)
            self.client = bigquery.Client(project=self.project_id, credentials=credentials, _http=session)
        else:
            # Use default credentials (for Cloud environments)
            self.client = bigquery.Client(project=self.project_id)
    
    def get_client(self) -> bigquery.Client:
        """Return the authenticated BigQuery client."""
        return self.client
    
    def test_connection(self) -> bool:
        """Test the BigQuery connection."""
        try:
            list(self.client.list_datasets(max_results=1))
            return True
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
        
    def execute_query(self, query: str, **kwargs):
        """Execute a SQL query and return the results."""
        query_job = self.client.query(query, **kwargs)
        return query_job.result()
    
    async def aexecute_query(self, query: str, **kwargs):
        """Execute a SQL query asynchronously and return the results."""
        loop = asyncio.get_running_loop()

        def run():
            return self.client.query(query, **kwargs).result()

        return await loop.run_in_executor(None, run)


class Client:
    """Unified client for BigQuery and Qdrant interactions."""
    
    def __init__(self,
                 bq_credentials_path: Optional[str] = None,
                 bq_project_id: Optional[str] = None,
                 qdrant_url: Optional[str] = None,
                 qdrant_api_key: Optional[str] = None,
                 limit_time: Optional[str] = None):
        """
        Initialize both BigQuery and Qdrant clients.
        
        Args:
            bq_credentials_path: Path to BigQuery service account JSON credentials file
            bq_project_id: Google Cloud project ID for BigQuery
            qdrant_url: Qdrant host URL
            qdrant_api_key: API key for Qdrant authentication
        """
        self.bigquery_client = BigQueryClient(
            credentials_path=bq_credentials_path,
            project_id=bq_project_id,
            limit_time=limit_time
        )
        
        self.qdrant_client = Qdrant(
            url=qdrant_url,
            api_key=qdrant_api_key
        )

        embedding_url = get_env('EMBEDDING_URL')
        logger.info(f"Client initialized with embedding URL: {embedding_url}")
        
        self.limit_time = limit_time    
        
        self.bigquery_client_status = self.bigquery_client.test_connection()
        self.qdrant_client_status = self.qdrant_client.test_connection()
        
    def get_bigquery_client(self) -> bigquery.Client:
        """Return the authenticated BigQuery client."""
        return self.bigquery_client.get_client()
    
    def get_qdrant_client(self) -> QdrantClient:
        """Return the authenticated Qdrant client."""
        return self.qdrant_client.client
    
    def test_connections(self) -> bool:
        """Test connections to both BigQuery and Qdrant."""
        if not self.qdrant_client_status:
            logger.error("Qdrant connection failed.")
        return self.bigquery_client_status
    
    def execute_query(self, query: str, **kwargs):
        """Execute a SQL query on BigQuery and return the results."""
        return self.bigquery_client.execute_query(query, **kwargs)
    
    async def aexecute_query(self, query: str, **kwargs):
        """Execute a SQL query asynchronously on BigQuery and return the results."""
        return await self.bigquery_client.aexecute_query(query, **kwargs)
    
    def query_qdrant(self, collection_name: str, query: str, start_date: Optional[int] = None, end_date: Optional[int] = None):
        """Execute a query against the Qdrant collection."""
        return self.qdrant_client.query(collection_name, query, start_date, end_date)
    
    async def aquery_qdrant(self, collection_name: str, query: str, start_date: Optional[int] = None, end_date: Optional[int] = None):
        """Asynchronously execute a query against the Qdrant collection."""
        loop = asyncio.get_running_loop()

        def run():
            return self.qdrant_client.query(collection_name, query, start_date, end_date)

        try:
            return await loop.run_in_executor(None, run)
        except RuntimeError as e:
            logger.error(f"Qdrant query failed: {e}")
            return []